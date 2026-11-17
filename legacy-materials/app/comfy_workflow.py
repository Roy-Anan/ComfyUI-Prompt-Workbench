# -*- coding: utf-8 -*-
"""ComfyUI 工作流解析（阶段 4：完整工作流管理）。

支持两种格式：
- UI Workflow JSON：顶层有 "nodes" 列表 + "links" 连线表，参数在 widgets_values
- API Prompt JSON：{node_id: {"class_type": ..., "inputs": {...}}}，输入是 [来源节点, 槽位]

**正负提示词一律按连线判定**：从 KSampler 的 `positive` / `negative` 输入沿连线往上游
回溯，直到碰到的 CLIPTextEncode（或同类文本节点）。不按节点编号大小、不按节点标题、
不按“正向=4 负向=5”这类固定编号猜——标题和编号都可能被用户改乱。

人工映射（mapping）可覆盖判定结果，用于连线缺失、自定义节点等边缘情况。
"""

import io
import json
import os

CHECKPOINT_TYPES = {"CheckpointLoaderSimple", "CheckpointLoader", "CheckpointLoader|pysssss"}
LORA_TYPES = {"LoraLoader", "LoraLoaderModelOnly"}
SAMPLER_TYPES = {"KSampler", "KSamplerAdvanced"}
LATENT_TYPES = {"EmptyLatentImage", "EmptySD3LatentImage", "EmptyLatentImage|pysssss"}
TEXT_TYPES = {"CLIPTextEncode", "CLIPTextEncodeSDXL", "CLIPTextEncodeSDXLRefiner",
              "BNK_CLIPTextEncodeAdvanced"}

MAX_DEPTH = 14


def load_json(path):
    with io.open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def detect_format(data):
    if not isinstance(data, dict):
        raise ValueError("工作流 JSON 顶层必须是对象")
    if isinstance(data.get("nodes"), list):
        return "ui"
    if any(isinstance(v, dict) and "class_type" in v for v in data.values()):
        return "api"
    raise ValueError("既不是 UI Workflow（无 nodes 列表）也不是 API Prompt（无 class_type）")


# ---------------------------------------------------------------- UI 格式

def _ui_nodes(data):
    return {str(n.get("id")): n for n in (data.get("nodes") or []) if isinstance(n, dict)}


def _ui_links(data):
    mapping = {}
    for link in data.get("links") or []:
        if isinstance(link, (list, tuple)) and len(link) >= 5:
            mapping[str(link[0])] = {"origin": str(link[1]), "origin_slot": link[2],
                                     "target": str(link[3]), "target_slot": link[4],
                                     "type": link[5] if len(link) > 5 else ""}
        elif isinstance(link, dict) and link.get("id") is not None:
            mapping[str(link["id"])] = {"origin": str(link.get("origin_id")),
                                        "origin_slot": link.get("origin_slot"),
                                        "target": str(link.get("target_id")),
                                        "target_slot": link.get("target_slot"),
                                        "type": link.get("type", "")}
    return mapping


def _ui_text(node):
    widgets = node.get("widgets_values")
    if isinstance(widgets, list) and widgets:
        return str(widgets[0])
    if isinstance(widgets, dict) and "text" in widgets:
        return str(widgets.get("text") or "")
    return None


def _ui_input_link(node, name):
    for item in node.get("inputs") or []:
        if item.get("name") == name and item.get("link") is not None:
            return item.get("link")
    return None


def _trace_ui(node_id, nodes, links, depth=0):
    """沿连线向上游回溯，收集文本节点。返回 {node_ids, texts}。"""
    result = {"node_ids": [], "texts": []}
    if depth > MAX_DEPTH:
        return result
    node = nodes.get(str(node_id))
    if not node:
        return result
    if node.get("type") in TEXT_TYPES:
        text = _ui_text(node)
        if text is not None:
            result["node_ids"].append(str(node_id))
            result["texts"].append(text)
        return result
    for item in node.get("inputs") or []:
        link_id = item.get("link")
        if link_id is None:
            continue
        via = links.get(str(link_id))
        if not via:
            continue
        sub = _trace_ui(via["origin"], nodes, links, depth + 1)
        result["node_ids"].extend(sub["node_ids"])
        result["texts"].extend(sub["texts"])
    return result


def _sampler_from_widgets(node):
    widgets = node.get("widgets_values") or []
    ntype = node.get("type", "")
    if not isinstance(widgets, list) or not widgets:
        return {}
    if ntype == "KSamplerAdvanced":
        def at(i):
            return widgets[i] if len(widgets) > i else None
        return {"seed": at(1), "steps": at(2), "cfg": at(3), "sampler_name": at(4),
                "scheduler": at(5), "denoise": None, "start_at_step": at(6),
                "end_at_step": at(7), "add_noise": at(0)}
    def at2(i):
        return widgets[i] if len(widgets) > i else None
    return {"seed": at2(0), "steps": at2(2), "cfg": at2(3), "sampler_name": at2(4),
            "scheduler": at2(5), "denoise": at2(6)}


def _parse_ui(data, mapping=None):
    nodes = _ui_nodes(data)
    links = _ui_links(data)
    result = {
        "format": "ui",
        "checkpoint": None,
        "checkpoints": [],
        "loras": [],
        "sampler": {},
        "samplers": [],
        "latent": {},
        "text_nodes": [],
        "positive": {"node_ids": [], "text": "", "source": "unresolved", "via": ""},
        "negative": {"node_ids": [], "text": "", "source": "unresolved", "via": ""},
        "nodes": [],
        "warnings": [],
    }

    for node_id, node in nodes.items():
        ntype = node.get("type", "")
        widgets = node.get("widgets_values") or []
        result["nodes"].append({
            "id": node_id, "type": ntype, "title": node.get("title", ""),
            "widgets": widgets if isinstance(widgets, list) else [],
        })

        if ntype in CHECKPOINT_TYPES and isinstance(widgets, list) and widgets:
            info = {"node_id": node_id, "name": str(widgets[0]), "type": ntype}
            result["checkpoints"].append(info)
            if result["checkpoint"] is None:
                result["checkpoint"] = info
        elif ntype in LORA_TYPES and isinstance(widgets, list) and widgets:
            result["loras"].append({
                "node_id": node_id, "name": str(widgets[0]),
                "strength_model": widgets[1] if len(widgets) > 1 else None,
                "strength_clip": widgets[2] if len(widgets) > 2 else None,
                "type": ntype,
            })
        elif ntype in LATENT_TYPES and isinstance(widgets, list) and len(widgets) >= 3:
            if not result["latent"]:
                result["latent"] = {"node_id": node_id, "width": widgets[0],
                                    "height": widgets[1], "batch": widgets[2]}
        elif ntype in SAMPLER_TYPES and isinstance(widgets, list) and widgets:
            info = {"node_id": node_id, "type": ntype}
            info.update(_sampler_from_widgets(node))
            result["samplers"].append(info)
            if not result["sampler"]:
                result["sampler"] = info
        elif ntype in TEXT_TYPES:
            result["text_nodes"].append({"node_id": node_id,
                                         "text": _ui_text(node) or "",
                                         "title": node.get("title", "")})

    sampler = result["sampler"]
    if len(result["samplers"]) > 1:
        result["warnings"].append("工作流里有 %d 个采样节点，当前按第一个（节点 %s）读取参数；"
                                  "需要换请在人工映射里指定。" % (len(result["samplers"]),
                                                  sampler.get("node_id")))

    # ---- 按连线判定正负
    if sampler:
        s_node = nodes.get(str(sampler["node_id"])) or {}
        for role in ("positive", "negative"):
            link_id = _ui_input_link(s_node, role)
            if link_id is None:
                result["warnings"].append("采样节点 %s 没有 %s 输入连线，无法判定%s节点。"
                                          % (sampler.get("node_id"), role,
                                             "正" if role == "positive" else "负"))
                continue
            via = links.get(str(link_id))
            if not via:
                result["warnings"].append("%s 连线 %s 在工作流的 links 表里找不到。"
                                          % (role, link_id))
                continue
            traced = _trace_ui(via["origin"], nodes, links)
            result[role] = {
                "node_ids": traced["node_ids"],
                "text": "\n\n".join(t for t in traced["texts"] if t.strip()),
                "source": "link",
                "via": "KSampler.%s ← 节点 %s 的连线 %s" % (role, via["origin"], link_id),
            }
            if not traced["node_ids"]:
                result["warnings"].append("%s 连线上没有 CLIPTextEncode，可能用了自定义节点；"
                                          "可用人工映射指定。" % role)
    else:
        result["warnings"].append("没有找到 KSampler / KSamplerAdvanced，正负节点无法判定。")

    _apply_mapping(result, mapping)
    return result


# ---------------------------------------------------------------- API 格式

def _api_text(node):
    text = (node.get("inputs") or {}).get("text")
    if isinstance(text, list) and text:
        return None, text[0]          # text 也是连线
    return (str(text) if text is not None else None), None


def _api_text_of(node_id, data, depth=0, seen=None):
    result = {"node_ids": [], "texts": []}
    if depth > MAX_DEPTH:
        return result
    seen = seen or set()
    if str(node_id) in seen:
        return result
    seen.add(str(node_id))
    node = data.get(str(node_id)) or {}
    if not isinstance(node, dict):
        return result
    if node.get("class_type") in TEXT_TYPES:
        text, via = _api_text(node)
        if text is not None:
            result["node_ids"].append(str(node_id))
            result["texts"].append(text)
        elif via is not None:
            sub = _api_text_of(via, data, depth + 1, seen)
            result["node_ids"].extend(sub["node_ids"])
            result["texts"].extend(sub["texts"])
        return result
    for value in (node.get("inputs") or {}).values():
        if isinstance(value, list) and value and isinstance(value[0], (str, int)):
            sub = _api_text_of(value[0], data, depth + 1, seen)
            result["node_ids"].extend(sub["node_ids"])
            result["texts"].extend(sub["texts"])
    return result


def _parse_api(data, mapping=None):
    result = {
        "format": "api",
        "checkpoint": None,
        "checkpoints": [],
        "loras": [],
        "sampler": {},
        "samplers": [],
        "latent": {},
        "text_nodes": [],
        "positive": {"node_ids": [], "text": "", "source": "unresolved", "via": ""},
        "negative": {"node_ids": [], "text": "", "source": "unresolved", "via": ""},
        "nodes": [],
        "warnings": [],
    }
    sampler_node = None
    for node_id, node in data.items():
        if not isinstance(node, dict) or "class_type" not in node:
            continue
        ctype = node.get("class_type", "")
        inputs = node.get("inputs") or {}
        result["nodes"].append({"id": str(node_id), "type": ctype,
                                "title": (node.get("_meta") or {}).get("title", ""),
                                "widgets": []})

        if ctype in CHECKPOINT_TYPES and inputs.get("ckpt_name"):
            info = {"node_id": str(node_id), "name": str(inputs["ckpt_name"]), "type": ctype}
            result["checkpoints"].append(info)
            if result["checkpoint"] is None:
                result["checkpoint"] = info
        elif ctype in LORA_TYPES and inputs.get("lora_name"):
            result["loras"].append({"node_id": str(node_id), "name": str(inputs["lora_name"]),
                                    "strength_model": inputs.get("strength_model"),
                                    "strength_clip": inputs.get("strength_clip"), "type": ctype})
        elif ctype in LATENT_TYPES and inputs.get("width"):
            if not result["latent"]:
                result["latent"] = {"node_id": str(node_id), "width": inputs.get("width"),
                                    "height": inputs.get("height"),
                                    "batch": inputs.get("batch_size")}
        elif ctype in SAMPLER_TYPES:
            info = {"node_id": str(node_id), "type": ctype,
                    "seed": inputs.get("seed") if inputs.get("seed") is not None
                    else inputs.get("noise_seed"),
                    "steps": inputs.get("steps"), "cfg": inputs.get("cfg"),
                    "sampler_name": inputs.get("sampler_name"),
                    "scheduler": inputs.get("scheduler"), "denoise": inputs.get("denoise"),
                    "start_at_step": inputs.get("start_at_step"),
                    "end_at_step": inputs.get("end_at_step"),
                    "add_noise": inputs.get("add_noise")}
            result["samplers"].append(info)
            if sampler_node is None:
                result["sampler"] = info
                sampler_node = node
        elif ctype in TEXT_TYPES:
            text, _ = _api_text(node)
            result["text_nodes"].append({"node_id": str(node_id),
                                         "text": text or "",
                                         "title": (node.get("_meta") or {}).get("title", "")})

    if len(result["samplers"]) > 1:
        result["warnings"].append("API Prompt 里有 %d 个采样节点，当前按第一个（节点 %s）读取参数。"
                                  % (len(result["samplers"]), result["sampler"].get("node_id")))

    if sampler_node:
        for role in ("positive", "negative"):
            ref = (sampler_node.get("inputs") or {}).get(role)
            if not isinstance(ref, list) or not ref:
                result["warnings"].append("采样节点 %s 的 %s 不是连线引用，无法判定。"
                                          % (result["sampler"].get("node_id"), role))
                continue
            traced = _api_text_of(ref[0], data)
            result[role] = {
                "node_ids": traced["node_ids"],
                "text": "\n\n".join(t for t in traced["texts"] if t.strip()),
                "source": "link",
                "via": "KSampler.%s ← 节点 %s" % (role, ref[0]),
            }
            if not traced["node_ids"]:
                result["warnings"].append("%s 连线上没有 CLIPTextEncode 文本，可用人工映射指定。" % role)
    else:
        result["warnings"].append("API Prompt 里没有 KSampler / KSamplerAdvanced。")

    _apply_mapping(result, mapping)
    return result


# ---------------------------------------------------------------- 人工映射

def _apply_mapping(result, mapping):
    if not mapping:
        return
    nodes = {str(n["id"]): n for n in result["nodes"]}
    for role, key in (("positive", "positive_node"), ("negative", "negative_node"),
                      ("sampler", "sampler_node")):
        target = mapping.get(key)
        if target in (None, ""):
            continue
        node = nodes.get(str(target))
        if not node:
            result["warnings"].append("人工映射指定的节点 %s 不存在（%s）。" % (target, key))
            continue
        if role == "sampler":
            found = next((s for s in result["samplers"]
                          if str(s.get("node_id")) == str(target)), None)
            if found:
                result["sampler"] = found
            else:
                result["warnings"].append("人工映射的采样节点 %s 不是 KSampler。" % target)
            continue
        text = node.get("widgets")
        if isinstance(text, list):
            text = text[0] if text else ""
        result[role] = {
            "node_ids": [str(target)],
            "text": str(text or ""),
            "source": "manual",
            "via": "人工映射（%s=%s）" % (key, target),
        }


# ---------------------------------------------------------------- 入口

def parse_workflow(source, mapping=None):
    """source 可以是路径，也可以是已解析的 dict；mapping 为人工映射覆盖。"""
    data = source
    if isinstance(source, str):
        data = load_json(source)

    fmt = detect_format(data)
    if fmt == "ui":
        parsed = _parse_ui(data, mapping)
    else:
        parsed = _parse_api(data, mapping)

    if isinstance(source, str):
        parsed["path"] = source
        parsed["name"] = os.path.basename(source)
    else:
        parsed.setdefault("name", data.get("name", ""))

    parsed["positive_text"] = parsed["positive"]["text"]
    parsed["negative_text"] = parsed["negative"]["text"]
    return parsed


def mapping_candidates(parsed):
    """给人工映射下拉用：文本节点与采样节点。"""
    texts = [{"id": n["node_id"], "type": "CLIPTextEncode",
              "preview": (n.get("text") or "").replace("\n", " ")[:56]}
             for n in parsed.get("text_nodes") or []]
    samplers = [{"id": s.get("node_id"), "type": s.get("type"),
                 "preview": "%s / %s 步 / CFG %s" % (s.get("sampler_name"), s.get("steps"),
                                                     s.get("cfg"))}
                for s in parsed.get("samplers") or []]
    return {"text_nodes": texts, "samplers": samplers}


def summarize(parsed, max_text_preview=70):
    """把解析结果压成一段给 LLM 看的文字。"""
    lines = []
    name = parsed.get("name") or "(未命名工作流)"
    fmt = "UI Workflow JSON" if parsed.get("format") == "ui" else "API Prompt JSON"
    lines.append("工作流：%s（%s，%d 个节点）" % (name, fmt, len(parsed.get("nodes") or [])))

    ckpt = parsed.get("checkpoint")
    if ckpt:
        lines.append("Checkpoint 节点：%s → %s" % (ckpt.get("node_id"), ckpt.get("name")))
    else:
        lines.append("Checkpoint 节点：未找到 CheckpointLoaderSimple")

    def brief_text(item):
        text = (item.get("text") or "").replace("\n", " ")
        if not text:
            return "（空）"
        return text[:max_text_preview] + ("…" if len(text) > max_text_preview else "")

    for role, label in (("positive", "正向"), ("negative", "负向")):
        item = parsed.get(role) or {}
        if item.get("node_ids"):
            lines.append("%s提示词节点：%s「%s」（%s）" % (
                label, "、".join(item["node_ids"]), brief_text(item),
                "按连线判定" if item.get("source") == "link" else "人工映射"))
        else:
            lines.append("%s提示词节点：未判定（工作流里找不到对应连线，可用人工映射指定）" % label)

    loras = parsed.get("loras") or []
    if loras:
        for item in loras:
            lines.append("LoRA 节点：%s → %s（model %s / clip %s）" % (
                item.get("node_id"), item.get("name"),
                item.get("strength_model"), item.get("strength_clip")))
    else:
        lines.append("LoRA 节点：无")

    sampler = parsed.get("sampler") or {}
    if sampler:
        lines.append("采样：节点 %s %s 采样器 %s / 调度 %s / %s 步 / CFG %s / denoise %s / seed %s" % (
            sampler.get("node_id"), sampler.get("type"),
            sampler.get("sampler_name"), sampler.get("scheduler"),
            sampler.get("steps"), sampler.get("cfg"), sampler.get("denoise"), sampler.get("seed")))

    latent = parsed.get("latent") or {}
    if latent:
        lines.append("尺寸：%s×%s，batch %s" % (latent.get("width"), latent.get("height"),
                                              latent.get("batch")))

    for item in parsed.get("warnings") or []:
        lines.append("提示：%s" % item)

    return "\n".join(lines)
