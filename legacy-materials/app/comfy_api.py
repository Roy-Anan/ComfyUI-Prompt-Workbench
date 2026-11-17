# -*- coding: utf-8 -*-
"""阶段 5：ComfyUI 提交与结果读取。

- `convert_ui_to_api`：把 UI Workflow JSON（nodes + links + widgets_values）转成
  ComfyUI `/prompt` 需要的 API Prompt JSON。转换规则由 `/object_info` 的节点定义驱动，
  不靠硬编码节点字段顺序。
- `ComfyClient`：提交 `/prompt`、轮询 `/history/{prompt_id}`、下载 `/view` 图片。
- `set_text_inputs`：把生成好的正 / 负提示词写进对应节点，替换原来的文本/连线。
- `apply_overrides`：可选改 seed / steps / cfg / 尺寸。

只监听本机 ComfyUI，不做远程调用。
"""

from __future__ import annotations

import copy
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

WIDGET_TYPES = {"INT", "FLOAT", "STRING", "BOOLEAN", "COMBO"}
CONTROL_VALUES = {"fixed", "increment", "decrement", "randomize"}
PASSTHROUGH_TYPES = {"Reroute"}
VALUE_NODE_TYPES = {"PrimitiveNode"}
SKIP_MODES = {2, 4}          # 2=静音, 4=旁路；都不参与执行


class ConversionError(Exception):
    pass


# ---------------------------------------------------------------- 工具
def _link_map(ui):
    mapping = {}
    for link in ui.get("links") or []:
        if isinstance(link, (list, tuple)) and len(link) >= 5:
            mapping[str(link[0])] = (str(link[1]), link[2])
        elif isinstance(link, dict) and link.get("id") is not None:
            mapping[str(link["id"])] = (str(link.get("origin_id")), link.get("origin_slot"))
    return mapping


def _node_map(ui):
    return {str(n.get("id")): n for n in (ui.get("nodes") or []) if isinstance(n, dict)}


def _resolve_origin(link_id, links, nodes, depth=0):
    """连线来源；Reroute 会被穿透。返回 (node_id, slot)。"""
    if depth > 10:
        raise ConversionError("连线回溯层数过深，疑似成环")
    if str(link_id) not in links:
        raise ConversionError("连线 %s 不存在" % link_id)
    origin, slot = links[str(link_id)]
    node = nodes.get(origin)
    if node and node.get("type") in PASSTHROUGH_TYPES:
        for item in node.get("inputs") or []:
            if item.get("link") is not None:
                return _resolve_origin(item["link"], links, nodes, depth + 1)
    return origin, slot


def _widget_spec(spec):
    """object_info 里的一个输入项是不是控件（而不是连线）。"""
    if not isinstance(spec, (list, tuple)) or not spec:
        return False
    head = spec[0]
    if isinstance(head, list):
        return True
    return str(head) in WIDGET_TYPES


def _spec_options(spec):
    if isinstance(spec, (list, tuple)) and len(spec) > 1 and isinstance(spec[1], dict):
        return spec[1]
    return {}


# ---------------------------------------------------------------- 转换
def convert_ui_to_api(ui, object_info):
    """UI Workflow dict → (api_prompt, warnings)。缺少节点定义时抛 ConversionError。"""
    if not isinstance(ui.get("nodes"), list):
        raise ConversionError("不是 UI Workflow（没有 nodes 列表）")
    object_info = object_info or {}
    links = _link_map(ui)
    nodes = _node_map(ui)
    prompt = {}
    warnings = []

    for node_id, node in nodes.items():
        ntype = node.get("type", "")
        if ntype in PASSTHROUGH_TYPES or ntype in VALUE_NODE_TYPES:
            continue
        mode = node.get("mode", 0)
        if mode in SKIP_MODES:
            warnings.append("节点 %s（%s）被静音/旁路，已跳过" % (node_id, ntype))
            continue
        spec = object_info.get(ntype)
        if not spec:
            raise ConversionError(
                "节点 %s 的类型 %s 不在 ComfyUI 的 object_info 里（自定义节点未安装？）"
                % (node_id, ntype))

        inputs_spec = spec.get("input") or {}
        order = spec.get("input_order") or {}
        required = inputs_spec.get("required") or {}
        optional = inputs_spec.get("optional") or {}
        names = list(order.get("required") or required.keys())
        names += list(order.get("optional") or optional.keys())

        node_inputs = {i.get("name"): i.get("link") for i in (node.get("inputs") or [])}
        widgets = node.get("widgets_values")
        widget_dict = widgets if isinstance(widgets, dict) else None
        widget_list = widgets if isinstance(widgets, list) else []
        widget_pos = 0

        built = {}
        for name in names:
            spec_item = required.get(name, optional.get(name))
            if spec_item is None or name not in names:
                continue
            link_id = node_inputs.get(name)
            is_widget = _widget_spec(spec_item)

            # 1) 有连线：优先按连线接（控件也可以被转成输入）
            if link_id is not None:
                origin, slot = _resolve_origin(link_id, links, nodes)
                origin_node = nodes.get(origin) or {}
                if is_widget and origin_node.get("type") in VALUE_NODE_TYPES:
                    values = origin_node.get("widgets_values") or []
                    built[name] = values[0] if values else None
                    continue
                built[name] = [origin, slot]
                # KSampler 的 seed 被转成输入时，控件里那个操作值要跳过
                if _spec_options(spec_item).get("control_after_generate") and widget_dict is None:
                    if widget_pos < len(widget_list) and \
                            str(widget_list[widget_pos]) in CONTROL_VALUES:
                        widget_pos += 1
                continue

            if not is_widget:
                continue          # 没连线的纯连线输入，让 ComfyUI 用默认/报错

            # 2) 控件取值
            if widget_dict is not None:
                if name in widget_dict:
                    built[name] = widget_dict[name]
                continue
            if widget_pos >= len(widget_list):
                continue
            built[name] = widget_list[widget_pos]
            widget_pos += 1
            opts = _spec_options(spec_item)
            if opts.get("control_after_generate") and widget_pos < len(widget_list) and \
                    str(widget_list[widget_pos]) in CONTROL_VALUES:
                widget_pos += 1

        prompt[node_id] = {"class_type": ntype, "inputs": built,
                           "_meta": {"title": node.get("title") or ntype}}

    if not prompt:
        raise ConversionError("转换后没有任何可提交的节点")
    return prompt, warnings


def set_text_inputs(prompt, node_ids, text):
    """把文本写进指定节点（替换掉原来的 text 连线/值）。"""
    changed = []
    for node_id in node_ids or []:
        node = prompt.get(str(node_id))
        if not node:
            continue
        node["inputs"]["text"] = text
        changed.append(str(node_id))
    return changed


def apply_overrides(prompt, sampler_node_ids, overrides):
    """可选出图覆盖：seed / steps / cfg / width / height / batch。"""
    applied = {}
    overrides = overrides or {}
    for node_id in sampler_node_ids or []:
        node = prompt.get(str(node_id)) or {}
        inputs = node.get("inputs") or {}
        for key in ("seed", "noise_seed"):
            if key in overrides and key in inputs:
                inputs[key] = int(overrides[key])
                applied[key] = inputs[key]
        for key in ("steps", "cfg", "denoise"):
            if key in overrides and key in inputs:
                inputs[key] = overrides[key]
                applied[key] = inputs[key]
    for node_id, node in prompt.items():
        if node.get("class_type") in ("EmptyLatentImage", "EmptySD3LatentImage"):
            for key, field in (("width", "width"), ("height", "height"),
                               ("batch", "batch_size"), ("batch_size", "batch_size")):
                if key in overrides:
                    node["inputs"][field] = int(overrides[key])
                    applied[field] = node["inputs"][field]
    return applied


def params_from_prompt(prompt, sampler_node_ids, positive_ids, negative_ids):
    """从最终 API Prompt 里取一份可回放的参数。"""
    sampler = {}
    for node_id in sampler_node_ids or []:
        node = prompt.get(str(node_id)) or {}
        inputs = node.get("inputs") or {}
        sampler = {
            "node_id": str(node_id),
            "type": node.get("class_type"),
            "seed": inputs.get("seed", inputs.get("noise_seed")),
            "steps": inputs.get("steps"),
            "cfg": inputs.get("cfg"),
            "sampler_name": inputs.get("sampler_name"),
            "scheduler": inputs.get("scheduler"),
            "denoise": inputs.get("denoise"),
        }
        if sampler["steps"] is not None:
            break
    latent = {}
    for node_id, node in prompt.items():
        if node.get("class_type") in ("EmptyLatentImage", "EmptySD3LatentImage"):
            latent = {"node_id": node_id,
                      "width": node["inputs"].get("width"),
                      "height": node["inputs"].get("height"),
                      "batch": node["inputs"].get("batch_size")}
            break
    text = {}
    for role, ids in (("positive", positive_ids), ("negative", negative_ids)):
        for node_id in ids or []:
            node = prompt.get(str(node_id)) or {}
            if "text" in (node.get("inputs") or {}):
                text[role] = {"node_id": str(node_id), "text": node["inputs"]["text"]}
                break
    return {"sampler": sampler, "latent": latent, "text": text}


def checkpoint_of(prompt):
    for node in prompt.values():
        if node.get("class_type") in ("CheckpointLoaderSimple", "CheckpointLoader"):
            return node.get("inputs", {}).get("ckpt_name")
    return ""


# ---------------------------------------------------------------- HTTP 客户端
class ComfyClient:
    def __init__(self, base_url="http://127.0.0.1:8188", timeout=30):
        self.base_url = (base_url or "http://127.0.0.1:8188").rstrip("/")
        self.timeout = timeout
        self._object_info = None
        self._object_info_at = 0

    # -------------------------------------------------- 基础请求
    def _request(self, path, method="GET", payload=None, timeout=None):
        url = self.base_url + path
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
            body = resp.read()
            ctype = resp.headers.get("Content-Type", "")
            if "application/json" in ctype:
                return json.loads(body.decode("utf-8"))
            return body

    def get(self, path, timeout=None):
        return self._request(path, "GET", timeout=timeout)

    def post(self, path, payload, timeout=None):
        return self._request(path, "POST", payload, timeout=timeout)

    # -------------------------------------------------- 状态
    def system_stats(self):
        try:
            return {"ok": True, "data": self.get("/system_stats", timeout=5)}
        except Exception as exc:
            return {"ok": False, "error": "%s" % exc}

    def queue_state(self):
        try:
            data = self.get("/queue", timeout=5)
            return {"ok": True, "running": data.get("queue_running", []),
                    "pending": data.get("queue_pending", [])}
        except Exception as exc:
            return {"ok": False, "error": "%s" % exc}

    def object_info(self, refresh=False, ttl=600):
        now = time.time()
        if refresh or not self._object_info or (now - self._object_info_at) > ttl:
            data = self.get("/object_info", timeout=60)
            self._object_info = data
            self._object_info_at = now
        return self._object_info

    # -------------------------------------------------- 提交与结果
    def queue_prompt(self, prompt, client_id=None):
        client_id = client_id or uuid.uuid4().hex
        try:
            data = self.post("/prompt", {"prompt": prompt, "client_id": client_id}, timeout=30)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            try:
                parsed = json.loads(body)
                detail = parsed.get("error") or parsed
                if parsed.get("node_errors"):
                    detail = {"error": parsed.get("error"), "node_errors": parsed["node_errors"]}
                return {"ok": False, "error": "ComfyUI 拒绝提交：%s" % json.dumps(detail, ensure_ascii=False)[:800]}
            except Exception:
                return {"ok": False, "error": "ComfyUI 返回 HTTP %s：%s" % (exc.code, body[:300])}
        except Exception as exc:
            return {"ok": False, "error": "连不上 ComfyUI（%s）：%s" % (self.base_url, exc)}

        if data.get("node_errors"):
            return {"ok": False, "error": "节点校验失败：%s"
                    % json.dumps(data["node_errors"], ensure_ascii=False)[:800]}
        if not data.get("prompt_id"):
            return {"ok": False, "error": "ComfyUI 没有返回 prompt_id：%s" % str(data)[:300]}
        return {"ok": True, "prompt_id": data["prompt_id"], "number": data.get("number"),
                "node_errors": data.get("node_errors") or {}}

    def history(self, prompt_id):
        try:
            return {"ok": True, "data": self.get("/history/%s" % urllib.parse.quote(prompt_id),
                                                  timeout=10)}
        except Exception as exc:
            return {"ok": False, "error": "%s" % exc}

    def wait(self, prompt_id, timeout=300, interval=1.0):
        """轮询 /history/{prompt_id}；返回 (status, data)。status: done/error/timeout。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            got = self.history(prompt_id)
            if not got.get("ok"):
                return "error", {"error": "查询 history 失败：%s" % got.get("error")}
            data = got["data"]
            entry = data.get(prompt_id)
            if entry:
                status = entry.get("status") or {}
                if status.get("status_str") == "error" or status.get("completed") is False \
                        and status.get("status_str") == "error":
                    return "error", {"entry": entry,
                                     "error": _error_from_messages(status.get("messages"))}
                if status.get("completed"):
                    return "done", {"entry": entry}
            time.sleep(interval)
        return "timeout", {"error": "等待 %s 秒仍未完成，prompt_id=%s" % (timeout, prompt_id)}

    def download_image(self, filename, subfolder="", folder_type="output"):
        params = urllib.parse.urlencode({"filename": filename, "subfolder": subfolder or "",
                                         "type": folder_type or "output"})
        return self.get("/view?" + params, timeout=60)

    def free(self, unload_models=True, free_memory=True):
        """释放 ComfyUI 已加载的模型与显存缓存（POST /free）。"""
        try:
            self.post("/free", {"unload_models": bool(unload_models),
                                "free_memory": bool(free_memory)})
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": "%s" % exc}


def _error_from_messages(messages):
    if not isinstance(messages, (list, tuple)):
        return str(messages)[:500]
    for item in messages:
        if isinstance(item, (list, tuple)) and len(item) == 2 and item[0] == "execution_error":
            detail = item[1] or {}
            return "执行出错：%s（节点 %s / %s）" % (
                detail.get("exception_message", "未知"),
                detail.get("node_id", "?"), detail.get("node_type", "?"))
        if isinstance(item, (list, tuple)) and len(item) == 2 and item[0] == "execution_interrupted":
            return "执行被中断"
    return "执行失败（无详细消息）"


def images_from_history(entry):
    """从 history 条目里取输出图片列表。"""
    images = []
    outputs = (entry or {}).get("outputs") or {}
    for node_id, output in outputs.items():
        for image in output.get("images") or []:
            images.append({
                "node_id": str(node_id),
                "filename": image.get("filename"),
                "subfolder": image.get("subfolder", ""),
                "type": image.get("type", "output"),
            })
    return images


def save_images(client, generation_id, images, out_dir):
    """把图片下载到工作台自己的 outputs 目录，返回带本地路径的列表。"""
    folder = os.path.join(out_dir, generation_id)
    os.makedirs(folder, exist_ok=True)
    saved = []
    for index, image in enumerate(images):
        try:
            data = client.download_image(image["filename"], image.get("subfolder"),
                                         image.get("type"))
        except Exception as exc:
            saved.append({**image, "local": "", "error": "下载失败：%s" % exc})
            continue
        ext = os.path.splitext(image["filename"])[1] or ".png"
        name = "%02d%s" % (index + 1, ext)
        path = os.path.join(folder, name)
        with open(path, "wb") as fh:
            fh.write(data)
        saved.append({**image, "local": path, "bytes": len(data)})
    return saved


def copy_prompt(prompt):
    return copy.deepcopy(prompt)
