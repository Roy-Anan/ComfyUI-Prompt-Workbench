# -*- coding: utf-8 -*-
"""LoRA 架构识别：直接读 safetensors 头部张量，不按文件名猜。

判据：交叉注意力 attn2_to_k 的 lora_down 输入维度
- 768  → SD1.5
- 2048 → SDXL
（这是 SD1.5 / SDXL 交叉注意力上下文维度差异，与文件名无关）
"""

import json
import os
import struct

SD15_ATTN_DIM = 768
SDXL_ATTN_DIM = 2048
_MAX_HEADER = 100 * 1024 * 1024


def read_header(path):
    """读 safetensors 的 JSON 头（8 字节长度 + JSON）。"""
    with open(path, "rb") as fh:
        raw = fh.read(8)
        if len(raw) < 8:
            raise ValueError("文件过短，不是 safetensors")
        length = struct.unpack("<Q", raw)[0]
        if length <= 0 or length > _MAX_HEADER:
            raise ValueError("safetensors 头部长度异常：%d" % length)
        blob = fh.read(length)
    return json.loads(blob.decode("utf-8"))


def detect_arch(lora_name, loras_dir):
    """返回 {found, path, arch, evidence, tensors, error}。"""
    name = os.path.basename(str(lora_name or "").replace("\\", "/").strip())
    if not name:
        return {"found": False, "arch": "unknown", "error": "没有 LoRA 文件名"}
    path = os.path.join(loras_dir, name)
    if not os.path.isfile(path):
        return {"found": False, "path": path, "arch": "unknown", "error": "LoRA 文件不存在：%s" % path}

    try:
        header = read_header(path)
    except Exception as exc:
        return {"found": True, "path": path, "arch": "unknown",
                "error": "读取 safetensors 头部失败：%s" % exc}

    keys = [k for k in header if k != "__metadata__"]
    dims = []
    for key in keys:
        if "attn2_to_k" in key and key.endswith("lora_down.weight"):
            shape = (header[key] or {}).get("shape") or []
            if shape:
                dims.append(shape[-1])

    arch = "unknown"
    evidence = "未找到交叉注意力张量（attn2_to_k），无法判定架构"
    if SDXL_ATTN_DIM in dims:
        arch = "SDXL"
        evidence = "attn2_to_k 输入维度 = %d" % SDXL_ATTN_DIM
    elif SD15_ATTN_DIM in dims:
        arch = "SD1.5"
        evidence = "attn2_to_k 输入维度 = %d" % SD15_ATTN_DIM
    elif any(k.startswith("lora_te2") for k in keys):
        arch = "SDXL"
        evidence = "存在第二文本编码器张量（lora_te2_*）"

    return {
        "found": True,
        "path": path,
        "arch": arch,
        "evidence": evidence,
        "tensors": len(keys),
        "error": "",
    }


def compatibility(checkpoint_arch, lora_arch):
    """底模架构 × LoRA 架构 → 兼容性结论。"""
    ckpt = (checkpoint_arch or "").upper().replace(" ", "")
    lora = (lora_arch or "").upper().replace(" ", "")

    if not lora or lora == "UNKNOWN":
        return {"state": "unknown", "compatible": None,
                "message": "LoRA 架构未能判定，无法确认兼容性，请先核对文件或metadata"}
    if not ckpt or ckpt == "UNKNOWN":
        return {"state": "unknown", "compatible": None,
                "message": "底模架构未知，无法核对 LoRA 兼容性"}
    if ckpt == "SDXL" and lora == "SDXL":
        return {"state": "ok", "compatible": True, "message": "SDXL 底模 + SDXL LoRA，架构一致"}
    if ckpt == "SD1.5" and lora == "SD1.5":
        return {"state": "ok", "compatible": True, "message": "SD1.5 底模 + SD1.5 LoRA，架构一致"}
    return {"state": "incompatible", "compatible": False,
            "message": "架构不兼容：底模 %s + LoRA %s，会在加载时报权重形状错配" % (ckpt, lora)}
