# -*- coding: utf-8 -*-
"""阶段 2：Profile 自动注入。

把一个请求拼成计划书 §6.3 要求的结构：
    系统提示词（精简版 / 全量版）
  + 当前 Checkpoint 完整文件名
  + 该模型对应的单个 Profile 全文
  + 当前工作流上下文（节点、LoRA、采样参数）
后续对话历史由调用方追加。

未登记的模型一律拒绝注入，不伪造 Profile。
"""

from __future__ import annotations

import io
import os

from app import comfy_workflow, lora_meta

SYSTEM_VARIANTS = {
    "精简版": "系统提示词_Ollama精简版.txt",
    "全量版": "系统提示词_全量版.txt",
}


def read_text(path):
    with io.open(path, encoding="utf-8-sig") as fh:
        return fh.read()


class ContextBuilder:
    def __init__(self, base_dir, lookup, loras_dir="", system_variant="精简版"):
        self.base_dir = os.path.abspath(base_dir)
        self.lookup = lookup
        self.loras_dir = loras_dir or ""
        self.system_variant = system_variant if system_variant in SYSTEM_VARIANTS else "精简版"

    # ------------------------------------------------------------ 系统提示词
    def system_prompt(self, variant=None):
        name = SYSTEM_VARIANTS.get(variant or self.system_variant, SYSTEM_VARIANTS["精简版"])
        path = os.path.join(self.base_dir, "rules", name)
        if not os.path.isfile(path):
            raise FileNotFoundError("找不到系统提示词：%s" % path)
        return read_text(path), path

    # ------------------------------------------------------------ LoRA 校验
    def check_loras(self, checkpoint_arch, parsed_workflow):
        """逐个 LoRA 读真实架构，给出兼容性结论。"""
        results = []
        for lora in (parsed_workflow or {}).get("loras") or []:
            info = lora_meta.detect_arch(lora.get("name"), self.loras_dir)
            verdict = lora_meta.compatibility(checkpoint_arch, info.get("arch"))
            results.append({
                "name": lora.get("name"),
                "node_id": lora.get("node_id"),
                "strength_model": lora.get("strength_model"),
                "strength_clip": lora.get("strength_clip"),
                "lora_arch": info.get("arch", "unknown"),
                "evidence": info.get("evidence", ""),
                "found": info.get("found"),
                "error": info.get("error", ""),
                **verdict,
            })
        return results

    # ------------------------------------------------------------ 注入
    def build(self, checkpoint_name, workflow=None, system_variant=None, mapping=None):
        """返回 {ok, system, meta} 或 {ok: False, reason, message}。mapping 为人工节点映射。"""
        match = self.lookup.lookup(checkpoint_name)
        if not match.get("ok"):
            return {
                "ok": False,
                "reason": match.get("reason", "unregistered"),
                "message": match.get("message", "无法匹配模型"),
                "checkpoint": match.get("checkpoint", ""),
                "hint": "请先在 rules\\模型数据库.txt 登记该 checkpoint，并放入对应 profile 后再使用。",
            }

        try:
            system_prompt, system_path = self.system_prompt(system_variant)
        except FileNotFoundError as exc:
            return {"ok": False, "reason": "system_prompt_missing", "message": str(exc)}

        profile_text = self.lookup.profile_text(match["registered_name"])
        if not profile_text:
            return {"ok": False, "reason": "profile_missing",
                    "message": "profile 文件为空或缺失：%s" % match.get("profile_file")}

        parsed = None
        if workflow:
            parsed = comfy_workflow.parse_workflow(workflow, mapping=mapping)
        lora_checks = self.check_loras(match.get("arch", ""), parsed) if parsed else []

        blocks = []
        blocks.append(system_prompt.rstrip())
        blocks.append("")
        blocks.append("=" * 24 + " 工作台注入上下文（阶段 2） " + "=" * 24)
        blocks.append("【当前模型】%s" % match["registered_name"])
        blocks.append("【架构 / 派系 / 画风】%s / %s / %s" % (
            match.get("arch") or "未给出", match.get("family") or "未给出", match.get("style") or "未给出"))
        blocks.append("【提示词体系】%s" % (match.get("prompt_system") or "未给出"))
        blocks.append("【匹配依据】模型数据库.txt 精确匹配 → %s" % match["profile_relpath"])
        blocks.append("")
        blocks.append("【当前模型 Profile（原文，未改写）】")
        blocks.append(profile_text.rstrip())

        if parsed:
            blocks.append("")
            blocks.append("【当前工作流上下文】")
            blocks.append(comfy_workflow.summarize(parsed))
            if lora_checks:
                blocks.append("")
                blocks.append("【LoRA 架构核对（读权重头部，非文件名猜测）】")
                for item in lora_checks:
                    blocks.append("- %s：%s；%s" % (
                        item["name"], item.get("message", ""), item.get("evidence", "")))
                bad = [x for x in lora_checks if x.get("state") == "incompatible"]
                if bad:
                    blocks.append("警告：检测到架构不兼容的 LoRA（%s），不要直接出图，先处理 LoRA。"
                                  % "、".join(x["name"] for x in bad))
            else:
                blocks.append("")
                blocks.append("【LoRA】当前工作流没有 LoRA 节点。")
        else:
            blocks.append("")
            blocks.append("【当前工作流上下文】未指定工作流，按用户描述生成。")

        blocks.append("")
        blocks.append("【工作台附加约束（由工作台追加，不属于规则文件；与上文规则冲突时以上文规则为准）】")
        blocks.append("1. 分段标题必须与系统提示词第 11 节完全一致，用中文："
                      "【当前模型】【Positive Prompt】【Negative Prompt】"
                      "【Generation Settings】【模型适配说明】【待确认项】；每段只出现一次，不要改用英文标题。")
        blocks.append("2. Profile 里写明「未给出」的字段，就写「未给出」，不要用「不适用 / 无需 / 默认」替代，也不要凭常识补值。")
        blocks.append("3. 参数后面必须带依据标记；没有依据的写 [待核实]。")
        blocks.append("4. 写完最后一段立即停止：不要追加说明、总结、寒暄、表情符号、营销语气或「已完成」之类的结束标记；不要输出分隔线；不要重复提示词。")
        blocks.append("5. Negative Prompt 最多 40 个标签，同一标签只出现一次。")
        blocks.append("")
        blocks.append("【要求】严格按系统提示词规定的输出格式回答；参数必须带依据标记；"
                      "不得把 [待核实] 写成确定值。")

        system_text = "\n".join(blocks)

        return {
            "ok": True,
            "system": system_text,
            "meta": {
                "checkpoint": match["registered_name"],
                "profile_file": match["profile_file"],
                "profile_relpath": match["profile_relpath"],
                "arch": match.get("arch", ""),
                "family": match.get("family", ""),
                "style": match.get("style", ""),
                "prompt_system": match.get("prompt_system", ""),
                "system_prompt_file": os.path.basename(system_path),
                "system_chars": len(system_prompt),
                "profile_chars": len(profile_text),
                "injected_chars": len(system_text),
                "workflow": {
                    "name": (parsed or {}).get("name", ""),
                    "format": (parsed or {}).get("format", ""),
                    "checkpoint": ((parsed or {}).get("checkpoint") or {}).get("name", ""),
                    "lora_count": len(((parsed or {}).get("loras") or [])),
                    "positive_nodes": ((parsed or {}).get("positive") or {}).get("node_ids", []),
                    "negative_nodes": ((parsed or {}).get("negative") or {}).get("node_ids", []),
                    "positive_source": ((parsed or {}).get("positive") or {}).get("source", ""),
                    "negative_source": ((parsed or {}).get("negative") or {}).get("source", ""),
                    "mapping_applied": bool(mapping),
                } if parsed else None,
                "lora_checks": lora_checks,
                "warnings": [x["message"] for x in lora_checks if x.get("state") != "ok"],
            },
        }
