from __future__ import annotations
import copy
import hashlib
import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
MAX_WORKFLOW_BYTES = 20 * 1024 * 1024
MAX_PROMPT_CHARS = 200_000
TEXT_ENCODER_MARKERS = ("CLIPTextEncode", "TextEncode")
SAMPLER_MARKERS = ("KSampler", "SamplerCustom", "SamplerAdvanced")
# 中转 conditioning 节点：自身不是文本编码器，但会把上游条件继续向下传。
CONDITIONING_PASSTHROUGH_MARKERS = (
    "ConditioningCombine",
    "ConditioningConcat",
    "ConditioningSetArea",
    "ConditioningSetAreaPercentage",
    "ConditioningSetAreaStrength",
    "ConditioningAverage",
    "ConditioningMask",
    "ConditioningZeroOut",
    "ConditioningDrop",
    "ConditioningBias",
)
# 这些输入名携带 conditioning 链路，追溯时沿它们继续向上。
CONDITIONING_INPUT_KEYS = (
    "conditioning",
    "positive",
    "negative",
    "conditioning1",
    "conditioning2",
    "cond",
)
MODEL_NODE_NAMES = {
    "CheckpointLoaderSimple",
    "CheckpointLoader",
    "UNETLoader",
    "DualCLIPLoader",
    "CLIPLoader",
    "VAELoader",
}
class WorkflowError(Exception):
    """A workflow cannot be safely processed."""
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
def _json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
def fingerprint(value: Any) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()
def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"无法读取工作流数据：{exc}") from exc
def _safe_filename(name: str) -> str:
    name = Path(name.replace("\\", "/")).name
    name = re.sub(r"[^0-9A-Za-z._\-\u4e00-\u9fff ]", "_", name)
    name = name.strip(" .")[:100]
    return name or "workflow.json"
def _valid_api_nodes(nodes: Any) -> bool:
    return (
        isinstance(nodes, dict)
        and bool(nodes)
        and all(
            isinstance(node, dict)
            and isinstance(node.get("class_type"), str)
            and isinstance(node.get("inputs"), dict)
            for node in nodes.values()
        )
    )
def detect_format(workflow: Any) -> str:
    if not isinstance(workflow, dict):
        raise WorkflowError("工作流 JSON 根节点必须是对象")
    nodes = workflow.get("nodes")
    # ComfyUI API prompt 的兼容包装格式。
    if _valid_api_nodes(nodes):
        return "api"
    # ComfyUI 标准 API prompt：
    # {"1": {"class_type": "...", "inputs": {...}}, ...}
    if _valid_api_nodes(workflow):
        return "api"
    # ComfyUI UI workflow。
    if (
        isinstance(nodes, list)
        and isinstance(workflow.get("links"), list)
        and all(isinstance(node, dict) for node in nodes)
    ):
        return "ui"
    raise WorkflowError(
        "无法识别工作流格式。请导入 ComfyUI API workflow 或 UI workflow JSON。"
    )
def _api_nodes(workflow: dict[str, Any]) -> dict[str, dict[str, Any]]:
    nodes = workflow.get("nodes")
    if _valid_api_nodes(nodes):
        return {str(key): value for key, value in nodes.items()}
    if _valid_api_nodes(workflow):
        return {str(key): value for key, value in workflow.items()}
    raise WorkflowError("API workflow 节点结构无效")
def _is_text_encoder(class_type: str) -> bool:
    return any(marker in class_type for marker in TEXT_ENCODER_MARKERS)
def _is_conditioning_passthrough(class_type: str) -> bool:
    return any(
        marker in class_type
        for marker in CONDITIONING_PASSTHROUGH_MARKERS
    )
def _is_sampler(class_type: str, inputs: dict[str, Any]) -> bool:
    return (
        any(marker in class_type for marker in SAMPLER_MARKERS)
        or ("positive" in inputs and "negative" in inputs)
    )
def _structure_diff(
    original: Any,
    candidate: Any,
    allowed_paths: set[str],
    prefix: str = "",
) -> list[str]:
    """Return structural differences; only `allowed_paths` may differ.

    Paths use a dot/array index prefix, e.g. ``"6.inputs.seed"``. Node-level
    whitelist paths are stored as ``"<node_id>.inputs.text"``.
    """
    diffs: list[str] = []
    if type(original) is not type(candidate):
        return [prefix or "<root>"]
    if isinstance(original, dict):
        if original.keys() != candidate.keys():
            diffs.append(prefix or "<root>")
        for key, original_value in original.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            diffs.extend(
                _structure_diff(
                    original_value,
                    candidate[key],
                    allowed_paths,
                    child,
                )
            )
        return diffs
    if isinstance(original, list):
        if len(original) != len(candidate):
            diffs.append(prefix or "<root>")
        for index, original_value in enumerate(original):
            child = f"{prefix}[{index}]"
            diffs.extend(
                _structure_diff(
                    original_value,
                    candidate[index],
                    allowed_paths,
                    child,
                )
            )
        return diffs
    if original != candidate:
        diffs.append(prefix or "<root>")
    return [item for item in diffs if item not in allowed_paths]
def _api_link_node_id(value: Any, nodes: dict[str, Any]) -> str | None:
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return None
    candidate = str(value[0])
    return candidate if candidate in nodes else None
def _trace_api_encoders(
    nodes: dict[str, dict[str, Any]],
    start_value: Any,
) -> list[str]:
    first = _api_link_node_id(start_value, nodes)
    if first is None:
        return []
    found: list[str] = []
    visited: set[str] = set()
    stack = [first]
    while stack:
        node_id = stack.pop()
        if node_id in visited:
            continue
        visited.add(node_id)
        node = nodes.get(node_id)
        if not isinstance(node, dict):
            continue
        class_type = str(node.get("class_type", ""))
        inputs = node.get("inputs", {})
        if not isinstance(inputs, dict):
            continue
        if _is_text_encoder(class_type):
            if isinstance(inputs.get("text"), str):
                found.append(node_id)
                continue
        # 文本编码器的 clip 输入不携带 conditioning，不向上追溯；
        # 中转 conditioning 节点沿其 conditioning 输入（含 conditioning_1/2 等编号键）继续追溯。
        if _is_conditioning_passthrough(class_type):
            trace_keys = [
                key
                for key in inputs
                if key in CONDITIONING_INPUT_KEYS
                or str(key).startswith("conditioning")
            ]
        else:
            trace_keys = tuple(inputs.keys())
        for key in trace_keys:
            value = inputs.get(key)
            upstream = _api_link_node_id(value, nodes)
            if upstream is not None:
                stack.append(upstream)
    return sorted(set(found), key=lambda item: (len(item), item))
def _parse_api(workflow: dict[str, Any]) -> dict[str, Any]:
    nodes = _api_nodes(workflow)
    prompt_roles: dict[str, set[str]] = {}
    prompt_groups: list[dict[str, Any]] = []
    model_nodes: list[dict[str, Any]] = []
    lora_nodes: list[dict[str, Any]] = []
    for node_id, node in nodes.items():
        class_type = str(node.get("class_type", ""))
        inputs = node.get("inputs", {})
        if not isinstance(inputs, dict):
            inputs = {}
        if (
            class_type in MODEL_NODE_NAMES
            or ("Loader" in class_type and "Lora" not in class_type)
        ):
            model_nodes.append({
                "node_id": node_id,
                "class_type": class_type,
                "inputs": {
                    key: value
                    for key, value in inputs.items()
                    if isinstance(value, (str, int, float, bool))
                    or value is None
                },
            })
        if "LoraLoader" in class_type:
            lora_nodes.append({
                "node_id": node_id,
                "class_type": class_type,
                "inputs": {
                    key: value
                    for key, value in inputs.items()
                    if isinstance(value, (str, int, float, bool))
                    or value is None
                },
            })
        if not _is_sampler(class_type, inputs):
            continue
        group: dict[str, Any] = {
            "sampler_node_id": node_id,
            "sampler_class": class_type,
            "positive_node_ids": [],
            "negative_node_ids": [],
        }
        for role in ("positive", "negative"):
            ids = _trace_api_encoders(nodes, inputs.get(role))
            group[f"{role}_node_ids"] = ids
            for encoder_id in ids:
                prompt_roles.setdefault(encoder_id, set()).add(role)
        prompt_groups.append(group)
    prompt_nodes: list[dict[str, Any]] = []
    for node_id, roles in prompt_roles.items():
        node = nodes[node_id]
        inputs = node["inputs"]
        prompt_nodes.append({
            "node_id": node_id,
            "class_type": str(node.get("class_type", "")),
            "roles": sorted(roles),
            "text": inputs.get("text", ""),
            "editable": isinstance(inputs.get("text"), str),
        })
    # 没有找到采样器连接时，仅提供可确认的文本节点候选。
    if not prompt_nodes:
        for node_id, node in nodes.items():
            class_type = str(node.get("class_type", ""))
            inputs = node.get("inputs", {})
            if (
                _is_text_encoder(class_type)
                and isinstance(inputs, dict)
                and isinstance(inputs.get("text"), str)
            ):
                prompt_nodes.append({
                    "node_id": node_id,
                    "class_type": class_type,
                    "roles": [],
                    "text": inputs["text"],
                    "editable": True,
                })
    return {
        "format": "api",
        "node_count": len(nodes),
        "model_nodes": model_nodes,
        "lora_nodes": lora_nodes,
        "prompt_groups": prompt_groups,
        "prompt_nodes": sorted(
            prompt_nodes,
            key=lambda item: (len(item["node_id"]), item["node_id"]),
        ),
        "safe_prompt_write_supported": True,
        "notes": [],
    }
def _ui_link_map(workflow: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for link in workflow.get("links", []):
        if isinstance(link, list) and len(link) >= 6:
            result[str(link[0])] = {
                "origin_id": str(link[1]),
                "target_id": str(link[3]),
            }
        elif isinstance(link, dict):
            link_id = link.get("id")
            origin_id = link.get("origin_id", link.get("originId"))
            target_id = link.get("target_id", link.get("targetId"))
            if link_id is not None and origin_id is not None:
                result[str(link_id)] = {
                    "origin_id": str(origin_id),
                    "target_id": str(target_id) if target_id is not None else "",
                }
    return result
def _trace_ui_encoders(
    nodes: dict[str, dict[str, Any]],
    links: dict[str, dict[str, Any]],
    start_node: dict[str, Any],
    start_input_name: str,
) -> list[str]:
    start_input = next(
        (
            item
            for item in start_node.get("inputs", [])
            if isinstance(item, dict)
            and item.get("name") == start_input_name
        ),
        None,
    )
    if not isinstance(start_input, dict) or start_input.get("link") is None:
        return []
    link = links.get(str(start_input["link"]))
    if not link:
        return []
    stack = [link["origin_id"]]
    visited: set[str] = set()
    found: list[str] = []
    while stack:
        node_id = stack.pop()
        if node_id in visited:
            continue
        visited.add(node_id)
        node = nodes.get(node_id)
        if not isinstance(node, dict):
            continue
        node_type = str(node.get("type", ""))
        if _is_text_encoder(node_type):
            found.append(node_id)
            continue
        for item in node.get("inputs", []):
            if not isinstance(item, dict) or item.get("link") is None:
                continue
            upstream = links.get(str(item["link"]))
            if upstream:
                stack.append(upstream["origin_id"])
    return sorted(set(found))
def _parse_ui(workflow: dict[str, Any]) -> dict[str, Any]:
    node_list = workflow.get("nodes", [])
    nodes = {
        str(node.get("id")): node
        for node in node_list
        if isinstance(node, dict) and node.get("id") is not None
    }
    links = _ui_link_map(workflow)
    prompt_roles: dict[str, set[str]] = {}
    prompt_groups: list[dict[str, Any]] = []
    model_nodes: list[dict[str, Any]] = []
    lora_nodes: list[dict[str, Any]] = []
    for node_id, node in nodes.items():
        node_type = str(node.get("type", ""))
        if node_type in MODEL_NODE_NAMES or (
            "Loader" in node_type and "Lora" not in node_type
        ):
            model_nodes.append({
                "node_id": node_id,
                "class_type": node_type,
                "inputs": {},
            })
        if "LoraLoader" in node_type:
            lora_nodes.append({
                "node_id": node_id,
                "class_type": node_type,
                "inputs": {},
            })
        input_items = node.get("inputs", [])
        input_names = {
            item.get("name")
            for item in input_items
            if isinstance(item, dict)
        }
        if not (
            any(marker in node_type for marker in SAMPLER_MARKERS)
            or {"positive", "negative"} <= input_names
        ):
            continue
        group = {
            "sampler_node_id": node_id,
            "sampler_class": node_type,
            "positive_node_ids": [],
            "negative_node_ids": [],
        }
        for role in ("positive", "negative"):
            ids = _trace_ui_encoders(nodes, links, node, role)
            group[f"{role}_node_ids"] = ids
            for encoder_id in ids:
                prompt_roles.setdefault(encoder_id, set()).add(role)
        prompt_groups.append(group)
    prompt_nodes: list[dict[str, Any]] = []
    for node_id, node in nodes.items():
        node_type = str(node.get("type", ""))
        if not _is_text_encoder(node_type):
            continue
        widgets = node.get("widgets_values", [])
        text_value = next(
            (value for value in widgets if isinstance(value, str)),
            "",
        )
        prompt_nodes.append({
            "node_id": node_id,
            "class_type": node_type,
            "roles": sorted(prompt_roles.get(node_id, set())),
            "text": text_value,
            "editable": False,
        })
    return {
        "format": "ui",
        "node_count": len(nodes),
        "model_nodes": model_nodes,
        "lora_nodes": lora_nodes,
        "prompt_groups": prompt_groups,
        "prompt_nodes": prompt_nodes,
        "safe_prompt_write_supported": False,
        "notes": [
            "UI workflow 当前仅支持只读解析。请从 ComfyUI 导出 API workflow 后再编辑 Prompt。"
        ],
    }
def analyze_workflow(workflow: dict[str, Any]) -> dict[str, Any]:
    workflow_format = detect_format(workflow)
    if workflow_format == "api":
        return _parse_api(workflow)
    return _parse_ui(workflow)
class WorkflowStore:
    """File-backed workflow storage under the workbench userdata directory."""
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
    def _folder(self, workflow_id: str) -> Path:
        try:
            normalized = str(uuid.UUID(workflow_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise WorkflowError("无效的工作流 ID") from exc
        folder = (self.root / normalized).resolve()
        try:
            folder.relative_to(self.root)
        except ValueError as exc:
            raise WorkflowError("工作流路径越界") from exc
        return folder
    def import_workflow(
        self,
        filename: str,
        workflow: dict[str, Any],
    ) -> dict[str, Any]:
        raw = _json_bytes(workflow)
        if len(raw) > MAX_WORKFLOW_BYTES:
            raise WorkflowError("工作流文件超过 20 MB 限制")
        workflow_format = detect_format(workflow)
        report = analyze_workflow(workflow)
        workflow_id = str(uuid.uuid4())
        folder = self._folder(workflow_id)
        source_hash = fingerprint(workflow)
        manifest = {
            "id": workflow_id,
            "filename": _safe_filename(filename),
            "format": workflow_format,
            "imported_at": _now(),
            "source_fingerprint": source_hash,
            "working_fingerprint": source_hash,
            "confirmed": False,
            "whitelist": [],
            "last_written_at": None,
        }
        try:
            folder.mkdir(parents=True, exist_ok=False)
            _atomic_json(folder / "original.json", workflow)
            _atomic_json(folder / "working.json", workflow)
            _atomic_json(folder / "analysis.json", report)
            _atomic_json(folder / "manifest.json", manifest)
        except Exception:
            shutil.rmtree(folder, ignore_errors=True)
            raise
        return {
            "id": workflow_id,
            "filename": manifest["filename"],
            "format": workflow_format,
            "source_fingerprint": source_hash,
            "report": report,
        }
    def list_workflows(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for folder in self.root.iterdir():
            if not folder.is_dir():
                continue
            manifest_file = folder / "manifest.json"
            if not manifest_file.is_file():
                continue
            try:
                manifest = _read_json(manifest_file)
            except WorkflowError:
                continue
            items.append({
                "id": manifest.get("id"),
                "filename": manifest.get("filename"),
                "format": manifest.get("format"),
                "imported_at": manifest.get("imported_at"),
                "confirmed": manifest.get("confirmed", False),
            })
        return sorted(
            items,
            key=lambda item: item.get("imported_at") or "",
            reverse=True,
        )
    def get_workflow(self, workflow_id: str) -> dict[str, Any]:
        folder = self._folder(workflow_id)
        if not folder.is_dir():
            raise FileNotFoundError("工作流不存在")
        manifest = _read_json(folder / "manifest.json")
        report = _read_json(folder / "analysis.json")
        original = _read_json(folder / "original.json")
        working = _read_json(folder / "working.json")
        prompts = []
        nodes = (
            _api_nodes(working)
            if manifest.get("format") == "api"
            else {}
        )
        for item in manifest.get("whitelist", []):
            node_id = str(item["node_id"])
            role = item["role"]
            node = nodes.get(node_id, {})
            text = node.get("inputs", {}).get("text", "")
            prompts.append({
                "node_id": node_id,
                "role": role,
                "text": text,
            })
        return {
            "manifest": manifest,
            "report": report,
            "working_prompts": prompts,
            "original_fingerprint": fingerprint(original),
            "working_fingerprint": fingerprint(working),
        }
    def confirm_prompt_nodes(
        self,
        workflow_id: str,
        positive_node_ids: list[str],
        negative_node_ids: list[str],
    ) -> dict[str, Any]:
        folder = self._folder(workflow_id)
        if not folder.is_dir():
            raise FileNotFoundError("工作流不存在")
        manifest = _read_json(folder / "manifest.json")
        if manifest.get("format") != "api":
            raise WorkflowError(
                "当前只允许对 API workflow 确认可写 Prompt 白名单"
            )
        original = _read_json(folder / "original.json")
        report = _read_json(folder / "analysis.json")
        if fingerprint(original) != manifest.get("source_fingerprint"):
            raise WorkflowError("原始工作流指纹变化，必须重新导入")
        candidates = {
            str(item["node_id"])
            for item in report.get("prompt_nodes", [])
            if item.get("editable") is True
        }
        positive = {str(value) for value in positive_node_ids}
        negative = {str(value) for value in negative_node_ids}
        if positive & negative:
            raise WorkflowError(
                "同一个节点不能同时指定为正向和负向 Prompt"
            )
        if not positive and not negative:
            raise WorkflowError(
                "至少确认一个正向或负向 Prompt 节点"
            )
        selected = positive | negative
        if not selected <= candidates:
            raise WorkflowError(
                "选择了未识别或不可编辑的 Prompt 节点"
            )
        nodes = _api_nodes(original)
        whitelist: list[dict[str, Any]] = []
        for role, ids in (
            ("positive", positive),
            ("negative", negative),
        ):
            for node_id in sorted(ids):
                node = nodes.get(node_id)
                inputs = node.get("inputs", {}) if isinstance(node, dict) else {}
                if not isinstance(inputs, dict) or not isinstance(
                    inputs.get("text"), str
                ):
                    raise WorkflowError(
                        f"节点 {node_id} 不存在可写 text 字段"
                    )
                whitelist.append({
                    "node_id": node_id,
                    "role": role,
                    "path": ["inputs", "text"],
                })
        manifest["confirmed"] = True
        manifest["whitelist"] = whitelist
        manifest["confirmed_at"] = _now()
        _atomic_json(folder / "manifest.json", manifest)
        return self.get_workflow(workflow_id)
    def write_prompts(
        self,
        workflow_id: str,
        positive_text: str | None,
        negative_text: str | None,
    ) -> dict[str, Any]:
        folder = self._folder(workflow_id)
        if not folder.is_dir():
            raise FileNotFoundError("工作流不存在")
        manifest = _read_json(folder / "manifest.json")
        if manifest.get("format") != "api":
            raise WorkflowError("UI workflow 当前不支持安全写入")
        if manifest.get("confirmed") is not True:
            raise WorkflowError("请先确认 Prompt 节点白名单")
        for value in (positive_text, negative_text):
            if value is not None and len(value) > MAX_PROMPT_CHARS:
                raise WorkflowError(
                    "Prompt 文本超过 200,000 字符限制"
                )
        if positive_text is None and negative_text is None:
            raise WorkflowError("没有提供需要写入的 Prompt")
        original = _read_json(folder / "original.json")
        working = _read_json(folder / "working.json")
        if fingerprint(original) != manifest.get("source_fingerprint"):
            raise WorkflowError(
                "原始工作流指纹变化，白名单已失效"
            )
        nodes_original = _api_nodes(original)
        nodes_working = _api_nodes(working)
        whitelist = manifest.get("whitelist", [])
        if not isinstance(whitelist, list) or not whitelist:
            raise WorkflowError("Prompt 白名单为空或格式无效")
        allowed: set[str] = set()
        for item in whitelist:
            if (
                not isinstance(item, dict)
                or item.get("role") not in {"positive", "negative"}
                or item.get("path") != ["inputs", "text"]
            ):
                raise WorkflowError("Prompt 白名单结构无效")
            node_id = str(item.get("node_id", ""))
            if node_id in allowed:
                raise WorkflowError("Prompt 白名单存在重复节点")
            allowed.add(node_id)
            if node_id not in nodes_original or node_id not in nodes_working:
                raise WorkflowError("白名单节点已不存在，拒绝写入")
            for nodes in (nodes_original, nodes_working):
                inputs = nodes[node_id].get("inputs")
                if (
                    not isinstance(inputs, dict)
                    or not isinstance(inputs.get("text"), str)
                ):
                    raise WorkflowError("白名单文本字段结构异常")
        # 检查当前工作副本：除白名单 text 字段外，逐节点逐字段必须与原始一致。
        allowed_paths = {f"{node_id}.inputs.text" for node_id in allowed}
        prewrite_diffs = _structure_diff(original, working, allowed_paths)
        if prewrite_diffs:
            raise WorkflowError(
                "工作副本存在非白名单变化，拒绝写入以保护工作流完整性"
            )
        # 在独立副本上写入，绝不直接修改读取到的原始对象。
        updated = copy.deepcopy(working)
        updated_nodes = _api_nodes(updated)
        changes: list[dict[str, Any]] = []
        for item in whitelist:
            node_id = str(item["node_id"])
            role = item["role"]
            replacement = (
                positive_text if role == "positive" else negative_text
            )
            if replacement is None:
                continue
            old_value = updated_nodes[node_id]["inputs"]["text"]
            updated_nodes[node_id]["inputs"]["text"] = replacement
            if old_value != replacement:
                changes.append({
                    "node_id": node_id,
                    "role": role,
                    "old_text": old_value,
                    "new_text": replacement,
                })
        # 写入后再次验证：还原全部白名单文本，结构化比对必须回到原始工作流。
        verified = copy.deepcopy(updated)
        verified_nodes = _api_nodes(verified)
        for node_id in allowed:
            verified_nodes[node_id]["inputs"]["text"] = (
                nodes_original[node_id]["inputs"]["text"]
            )
        postwrite_diffs = _structure_diff(original, verified, allowed_paths)
        if postwrite_diffs:
            raise WorkflowError(
                "写入后完整性校验失败，工作副本未更新"
            )
        # 保存真正的写入前版本，而不是已经修改的新版本。
        versions = folder / "versions"
        versions.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime(
            "%Y%m%d-%H%M%S-%f"
        )
        _atomic_json(versions / f"{stamp}.json", working)
        # 只有所有验证完成后才替换工作副本。
        _atomic_json(folder / "working.json", updated)
        manifest["working_fingerprint"] = fingerprint(updated)
        manifest["last_written_at"] = _now()
        _atomic_json(folder / "manifest.json", manifest)
        return {
            "ok": True,
            "changes": changes,
            "working_fingerprint": manifest["working_fingerprint"],
            "workflow": self.get_workflow(workflow_id),
        }
