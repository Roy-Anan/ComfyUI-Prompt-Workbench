import { useEffect, useState } from "react";
import { apiDelete, apiGet, apiPost } from "./api";
import { formatActual } from "./format";
type PromptNode = {
  node_id: string;
  class_type: string;
  roles: string[];
  text: string;
  editable: boolean;
};
type Analysis = {
  format: "api" | "ui";
  node_count: number;
  model_nodes: Array<{
    node_id: string;
    class_type: string;
    inputs: Record<string, unknown>;
  }>;
  lora_nodes: Array<{
    node_id: string;
    class_type: string;
    inputs: Record<string, unknown>;
  }>;
  prompt_groups: Array<{
    sampler_node_id: string;
    sampler_class: string;
    positive_node_ids: string[];
    negative_node_ids: string[];
  }>;
  prompt_nodes: PromptNode[];
  safe_prompt_write_supported: boolean;
  notes: string[];
};
type WorkflowListItem = {
  id: string;
  filename: string;
  format: "api" | "ui";
  imported_at: string;
  confirmed: boolean;
};
type WorkflowDetail = {
  manifest: {
    id: string;
    filename: string;
    format: "api" | "ui";
    confirmed: boolean;
    whitelist: Array<{
      node_id: string;
      role: "positive" | "negative";
    }>;
  };
  report: Analysis;
  working_prompts: Array<{
    node_id: string;
    role: "positive" | "negative";
    text: string;
  }>;
};
type VersionEntry = {
  stamp: string;
  prompts: Array<{
    node_id: string;
    role: "positive" | "negative";
    text: string;
  }>;
};
type ImportResult = {
  id: string;
  filename: string;
  format: "api" | "ui";
  report: Analysis;
};
type WriteResult = {
  ok: boolean;
  changes: Array<{
    node_id: string;
    role: string;
    old_text: string;
    new_text: string;
  }>;
  workflow: WorkflowDetail;
};
type ComparisonEntry = {
  key: string;
  rule_status: string;
  actual_key: string | null;
  actual: unknown;
  status: string;
  reason?: string;
  rule?: unknown;
};
type GroupComparison = {
  sampler_node_id: string | null;
  params: Record<string, unknown>;
  comparisons: ComparisonEntry[];
  counts: Record<string, number>;
};
type ComparePayload = {
  status: string;
  checkpoint: string | null;
  architecture: string | null;
  architecture_family?: string | null;
  architecture_label?: string | null;
  actuals: Record<string, unknown>;
  comparisons: ComparisonEntry[];
  counts: Record<string, number>;
  sampler_group_comparisons?: GroupComparison[];
};
type RoleChoice = "" | "positive" | "negative";
type OllamaModelsResponse = {
  online: boolean;
  models: string[];
  error: string | null;
};
type CandidateResponse = {
  model: string;
  candidates: string[];
  rule_status: string;
  conflicts: unknown[];
  unknown: unknown[];
};
type ComfyTask = {
  prompt_id: string;
  workflow_id: string;
  status: string;
  submitted_at: string;
  updated_at: string;
  node_errors: unknown;
  last_error: string | null;
  outputs: unknown;
};
type TasksResponse = {
  items: ComfyTask[];
  sync_error: string | null;
};
type SnapshotFile = { node_id?: string; file: string };

type EnvSnapshot = {
  checkpoints?: SnapshotFile[];
  loras?: SnapshotFile[];
  vaes?: SnapshotFile[];
  clips?: SnapshotFile[];
  resolution?: string | null;
  clip_skip?: number | null;
  samplers?: Record<string, unknown>[];
};

type DraftEntry = {
  id: string;
  name: string;
  positive: string;
  negative: string;
  note: string;
  favored?: boolean;
  pinned?: boolean;
  tags?: string[];
  trashed?: boolean;
  source_history_id?: string | null;
  env_snapshot?: EnvSnapshot | null;
  created_at: string | null;
  updated_at: string | null;
};

function snapshotFiles(files: SnapshotFile[] | undefined): string {
  return (files || []).map((item) => item.file).filter(Boolean).join("、");
}

function envSnapshotSummary(snapshot: EnvSnapshot | null | undefined): string {
  if (!snapshot) return "";
  const parts: string[] = [];
  const checkpoint = snapshotFiles(snapshot.checkpoints);
  if (checkpoint) parts.push(`模型 ${checkpoint}`);
  const lora = snapshotFiles(snapshot.loras);
  if (lora) parts.push(`LoRA ${lora}`);
  if (snapshot.resolution) parts.push(`尺寸 ${snapshot.resolution}`);
  if (typeof snapshot.clip_skip === "number") parts.push(`Clip Skip ${snapshot.clip_skip}`);
  const sampler = (snapshot.samplers || [])[0];
  if (sampler) {
    const bits: string[] = [];
    if (sampler.steps != null) bits.push(`Steps ${sampler.steps}`);
    if (sampler.cfg != null) bits.push(`CFG ${sampler.cfg}`);
    if (sampler.sampler_name) bits.push(String(sampler.sampler_name));
    if (sampler.scheduler) bits.push(String(sampler.scheduler));
    if (bits.length) parts.push(bits.join(" · "));
  }
  return parts.join(" · ");
}

function parseDraftTags(text: string): string[] {
  const parts = text.split(/[,，、;；\s]+/);
  const tags: string[] = [];
  const seen = new Set<string>();
  for (const part of parts) {
    const tag = part.trim();
    if (!tag || seen.has(tag)) continue;
    seen.add(tag);
    tags.push(tag);
  }
  return tags.slice(0, 12);
}

const STATUS_LABEL: Record<string, string> = {
  match: "匹配",
  out_of_range: "超出范围",
  out_of_set: "不在集合",
  unknown: "无法判定",
};

const TASK_STATUS_LABEL: Record<string, string> = {
  submitted: "待运行",
  running: "运行中",
  succeeded: "已完成",
  failed: "失败",
  interrupted: "已中断",
  unknown: "未知",
};

function formatTaskTime(value: string): string {
  if (!value) return "—";
  return value.replace("T", " ").slice(0, 16);
}

function formatVersionStamp(stamp: string): string {
  if (!stamp) return "—";
  const [date, time] = stamp.split("-");
  if (date && time && date.length === 8 && time.length >= 6) {
    return `${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)} ${time.slice(0, 2)}:${time.slice(2, 4)}:${time.slice(4, 6)}`;
  }
  return stamp;
}

function clipText(text: string, limit = 80): string {
  if (!text) return "—";
  return text.length > limit ? `${text.slice(0, limit)}…` : text;
}

type PromptImport = { positive: string; negative: string };

function parsePromptJson(text: string): PromptImport {
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new Error("JSON 文件无法解析。");
  }
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    throw new Error("不是有效的 Prompt 导出 JSON。");
  }
  const record = parsed as Record<string, unknown>;
  const positive = typeof record.positive === "string" ? record.positive : "";
  const negative = typeof record.negative === "string" ? record.negative : "";
  if (!positive.trim() && !negative.trim()) {
    throw new Error("JSON 中未包含有效的正向/负向 Prompt。");
  }
  return { positive, negative };
}

function parsePromptText(text: string): PromptImport {
  const lines = text.split(/\r?\n/);
  const positiveLines: string[] = [];
  const negativeLines: string[] = [];
  const markPositive = /^\s*正向\s*[:：]/;
  const markNegative = /^\s*负向\s*[:：]/;
  let section: "positive" | "negative" = "positive";
  let anyMark = false;
  for (const line of lines) {
    if (markPositive.test(line)) {
      section = "positive";
      anyMark = true;
      const rest = line.replace(markPositive, "").trim();
      if (rest) positiveLines.push(rest);
      continue;
    }
    if (markNegative.test(line)) {
      section = "negative";
      anyMark = true;
      const rest = line.replace(markNegative, "").trim();
      if (rest) negativeLines.push(rest);
      continue;
    }
    if (!anyMark || section === "positive") {
      positiveLines.push(line);
    } else {
      negativeLines.push(line);
    }
  }
  const positive = positiveLines.join("\n").trim();
  const negative = negativeLines.join("\n").trim();
  if (!positive && !negative) {
    throw new Error("未解析到有效的 Prompt 文本。");
  }
  return { positive, negative };
}

function parsePromptImport(filename: string, text: string): PromptImport {
  const name = filename.toLowerCase();
  if (name.endsWith(".json")) {
    return parsePromptJson(text);
  }
  return parsePromptText(text);
}

function parsePromptContent(text: string): PromptImport {
  const trimmed = text.trim();
  if (trimmed.startsWith("{")) {
    try {
      return parsePromptJson(trimmed);
    } catch {
      // 非导出 JSON 结构时回退按纯文本分段，不臆造字段。
    }
  }
  return parsePromptText(text);
}

// 与后端 workflow_service.MAX_PROMPT_CHARS 对齐；前端仅只读提示，不做硬拦截。
const PROMPT_MAX_CHARS = 200_000;

function promptCountLabel(text: string): string {
  const len = text.length;
  return len > PROMPT_MAX_CHARS
    ? `${len} / ${PROMPT_MAX_CHARS}（已超上限）`
    : `${len} / ${PROMPT_MAX_CHARS}`;
}

function outputFilenames(outputs: unknown): string[] {
  if (typeof outputs !== "object" || outputs === null) return [];
  const record = outputs as Record<string, unknown>;
  const names: string[] = [];
  for (const entry of Object.values(record)) {
    if (Array.isArray(entry)) {
      for (const item of entry) {
        if (typeof item === "object" && item !== null) {
          const filename = (item as Record<string, unknown>).filename;
          if (typeof filename === "string") names.push(filename);
        }
      }
    }
  }
  return names;
}

const ACTUAL_SUMMARY: Array<{ key: string; label: string }> = [
  { key: "steps", label: "步数" },
  { key: "cfg", label: "CFG" },
  { key: "sampler_name", label: "采样器" },
  { key: "scheduler", label: "调度器" },
  { key: "clip_skip", label: "Clip Skip" },
];

function downloadLocalFile(filename: string, text: string, mime: string) {
  const blob = new Blob([text], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function promptStamp(): string {
  return new Date().toISOString().replace(/[-:T]/g, "").slice(0, 12);
}

function readStoredFavoredOnly(): boolean {
  try {
    return localStorage.getItem("workbench.favoredOnly") === "1";
  } catch {
    // 本地存储不可用时回落未启用收藏过滤。
  }
  return false;
}

function persistFavoredOnly(value: boolean): void {
  try {
    localStorage.setItem("workbench.favoredOnly", value ? "1" : "0");
  } catch {
    // 忽略本地存储写入失败。
  }
}

export default function WorkflowWorkbench() {
  const [items, setItems] = useState<WorkflowListItem[]>([]);
  const [detail, setDetail] = useState<WorkflowDetail | null>(null);
  const [compare, setCompare] = useState<ComparePayload | null>(null);
  const [workflowId, setWorkflowId] = useState("");
  const [roles, setRoles] = useState<Record<string, RoleChoice>>({});
  const [positiveText, setPositiveText] = useState("");
  const [negativeText, setNegativeText] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("请选择一个 ComfyUI 工作流 JSON 文件。");
  const [ollamaModels, setOllamaModels] = useState<string[]>([]);
  const [modelsOnline, setModelsOnline] = useState(true);
  const [selectedModel, setSelectedModel] = useState("");
  const [taskText, setTaskText] = useState("");
  const [candidate, setCandidate] = useState<string | null>(null);
  const [candidateBusy, setCandidateBusy] = useState(false);
  const [importedPrompt, setImportedPrompt] = useState<PromptImport | null>(null);
  const [pasteOpen, setPasteOpen] = useState(false);
  const [pasteText, setPasteText] = useState("");
  const [comfyTasks, setComfyTasks] = useState<ComfyTask[]>([]);
  const [taskBusy, setTaskBusy] = useState(false);
  const [taskSyncError, setTaskSyncError] = useState<string | null>(null);
  const [versions, setVersions] = useState<VersionEntry[]>([]);
  const [drafts, setDrafts] = useState<DraftEntry[]>([]);
  const [draftName, setDraftName] = useState("");
  const [draftNote, setDraftNote] = useState("");
  const [draftTags, setDraftTags] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [draftBusy, setDraftBusy] = useState(false);
  const [deletingDraftId, setDeletingDraftId] = useState<string | null>(null);
  const [updatingDraftId, setUpdatingDraftId] = useState<string | null>(null);
  const [copyingDraftId, setCopyingDraftId] = useState<string | null>(null);
  const [copyTargetId, setCopyTargetId] = useState("");
  const [showTrashed, setShowTrashed] = useState(false);
  const [purgingDraftId, setPurgingDraftId] = useState<string | null>(null);
  const [draftKeyword, setDraftKeyword] = useState("");
  const [favoredOnly, setFavoredOnly] = useState(readStoredFavoredOnly);
  async function refreshList() {
    const result = await apiGet<{ items: WorkflowListItem[] }>(
      "/api/workflows",
    );
    setItems(result.items);
  }
  useEffect(() => {
    void refreshList().catch((error) => {
      setMessage(`读取工作流列表失败：${String(error)}`);
    });
  }, []);
  useEffect(() => {
    void loadModels();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  function initialRoles(report: Analysis) {
    const next: Record<string, RoleChoice> = {};
    for (const node of report.prompt_nodes) {
      if (node.roles.includes("positive")) {
        next[node.node_id] = "positive";
      } else if (node.roles.includes("negative")) {
        next[node.node_id] = "negative";
      } else {
        next[node.node_id] = "";
      }
    }
    return next;
  }
  async function loadCompare(id: string) {
    try {
      const result = await apiGet<ComparePayload>(
        `/api/workflows/${id}/rules/compare`,
      );
      setCompare(result);
    } catch (error) {
      setCompare(null);
      setMessage(`读取规则比对失败：${String(error)}`);
    }
  }
  async function openWorkflow(id: string) {
    setBusy(true);
    try {
      const result = await apiGet<WorkflowDetail>(
        `/api/workflows/${id}`,
      );
      setWorkflowId(id);
      setDetail(result);
      setCompare(null);
      void loadCompare(id);
      setRoles(initialRoles(result.report));
      setPositiveText(
        result.working_prompts.find((item) => item.role === "positive")?.text ?? "",
      );
      setNegativeText(
        result.working_prompts.find((item) => item.role === "negative")?.text ?? "",
      );
      setComfyTasks([]);
      setTaskSyncError(null);
      setVersions([]);
      setDrafts([]);
      setDraftName("");
      setDraftNote("");
      setDraftTags("");
      setTagFilter("");
      setDeletingDraftId(null);
      setUpdatingDraftId(null);
      setCopyingDraftId(null);
      setCopyTargetId("");
      setShowTrashed(false);
      setPurgingDraftId(null);
      setDraftKeyword("");
      setFavoredOnly(false);
      persistFavoredOnly(false);
      setConfirmStamp(null);
      setComparingStamp(null);
      setImportedPrompt(null);
      setPasteOpen(false);
      setPasteText("");
      void loadTasks(false);
      void loadVersions(id);
      void loadDrafts(id, false);
      setMessage(`已打开：${result.manifest.filename}`);
    } catch (error) {
      setMessage(`打开失败：${String(error)}`);
    } finally {
      setBusy(false);
    }
  }
  async function importFile(file?: File) {
    if (!file) return;
    setBusy(true);
    setMessage("正在读取和解析工作流…");
    try {
      const parsed = JSON.parse(await file.text()) as Record<string, unknown>;
      const result = await apiPost<ImportResult>(
        "/api/workflows/import",
        {
          filename: file.name,
          workflow: parsed,
        },
      );
      setWorkflowId(result.id);
      setCompare(null);
      setRoles(initialRoles(result.report));
      setPositiveText("");
      setNegativeText("");
      setDetail({
        manifest: {
          id: result.id,
          filename: result.filename,
          format: result.format,
          confirmed: false,
          whitelist: [],
        },
        report: result.report,
        working_prompts: [],
      });
      void loadCompare(result.id);
      setComfyTasks([]);
      setTaskSyncError(null);
      setDrafts([]);
      setDraftName("");
      setDraftNote("");
      setDraftTags("");
      setTagFilter("");
      setDeletingDraftId(null);
      setUpdatingDraftId(null);
      setCopyingDraftId(null);
      setCopyTargetId("");
      setShowTrashed(false);
      setPurgingDraftId(null);
      setDraftKeyword("");
      setFavoredOnly(false);
      persistFavoredOnly(false);
      setComparingStamp(null);
      setImportedPrompt(null);
      setPasteOpen(false);
      setPasteText("");
      await refreshList();
      setMessage(`导入成功：${result.filename}`);
    } catch (error) {
      setMessage(`导入失败：${String(error)}`);
    } finally {
      setBusy(false);
    }
  }
  async function confirmNodes() {
    if (!workflowId || !detail) return;
    const positiveIds = Object.entries(roles)
      .filter(([, role]) => role === "positive")
      .map(([id]) => id);
    const negativeIds = Object.entries(roles)
      .filter(([, role]) => role === "negative")
      .map(([id]) => id);
    setBusy(true);
    try {
      const result = await apiPost<WorkflowDetail>(
        `/api/workflows/${workflowId}/confirm`,
        {
          positive_node_ids: positiveIds,
          negative_node_ids: negativeIds,
        },
      );
      setDetail(result);
      setPositiveText(
        result.working_prompts.find((item) => item.role === "positive")?.text ?? "",
      );
      setNegativeText(
        result.working_prompts.find((item) => item.role === "negative")?.text ?? "",
      );
      await refreshList();
      setMessage("Prompt 节点白名单已确认。现在可以编辑工作副本。");
    } catch (error) {
      setMessage(`确认失败：${String(error)}`);
    } finally {
      setBusy(false);
    }
  }
  async function writePrompts() {
    if (!workflowId || !detail?.manifest.confirmed) return;
    setBusy(true);
    try {
      const result = await apiPost<WriteResult>(
        `/api/workflows/${workflowId}/write`,
        {
          positive_text: detail.manifest.whitelist.some(
            (item) => item.role === "positive",
          )
            ? positiveText
            : null,
          negative_text: detail.manifest.whitelist.some(
            (item) => item.role === "negative",
          )
            ? negativeText
            : null,
        },
      );
      setDetail(result.workflow);
      const count = result.changes.length;
      setMessage(
        `写入完成：${count} 个 Prompt 节点发生变化。非白名单字段完整性校验通过。`,
      );
    } catch (error) {
      setMessage(`写入被拒绝或失败：${String(error)}`);
    } finally {
      setBusy(false);
    }
  }
  async function loadModels() {
    try {
      const result = await apiGet<OllamaModelsResponse>("/api/ollama/models");
      setOllamaModels(result.models);
      setModelsOnline(result.online);
      if (result.models.length > 0 && !selectedModel) {
        setSelectedModel(result.models[0]);
      }
    } catch (error) {
      setModelsOnline(false);
      setMessage(`读取本地模型列表失败：${String(error)}`);
    }
  }
  async function generateCandidate() {
    if (!workflowId || !selectedModel) return;
    setCandidateBusy(true);
    setCandidate(null);
    try {
      const result = await apiPost<CandidateResponse>(
        `/api/workflows/${workflowId}/prompt/candidates`,
        { model: selectedModel, task: taskText.trim() || null },
      );
      setCandidate(result.candidates[0] ?? null);
      setMessage(`已生成候选（规则状态：${result.rule_status}），采用前请核对。`);
    } catch (error) {
      setMessage(`候选生成失败：${String(error)}`);
    } finally {
      setCandidateBusy(false);
    }
  }
  function adoptCandidate() {
    if (candidate) setPositiveText(candidate);
  }

  async function copyCandidate() {
    if (!candidate) return;
    try {
      await navigator.clipboard.writeText(candidate);
      setMessage("候选已复制到剪贴板（未写入工作副本）。");
    } catch (error) {
      setMessage(`复制候选失败：${String(error)}`);
    }
  }

  function dismissCandidate() {
    setCandidate(null);
    setMessage("候选已放弃（未写入工作副本）。");
  }

  async function copyPromptText(text: string, label: string) {
    if (!text.trim()) {
      setMessage(`${label}为空，无需复制。`);
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      setMessage(`${label} 已复制到剪贴板（未写入工作副本）。`);
    } catch (error) {
      setMessage(`复制 ${label} 失败：${String(error)}`);
    }
  }

  function copyPositive() {
    void copyPromptText(positiveText, "正向 Prompt");
  }

  function copyNegative() {
    void copyPromptText(negativeText, "负向 Prompt");
  }

  function copyBoth() {
    const parts: string[] = [];
    if (positiveText.trim()) parts.push(`正向：\n${positiveText}`);
    if (negativeText.trim()) parts.push(`负向：\n${negativeText}`);
    if (parts.length === 0) {
      setMessage("正向与负向均为空，无需复制。");
      return;
    }
    void copyPromptText(parts.join("\n\n"), "完整 Prompt");
  }

  function exportPromptTxt() {
    if (!positiveText.trim() && !negativeText.trim()) {
      setMessage("正向与负向均为空，无需导出。");
      return;
    }
    const parts: string[] = [];
    if (positiveText.trim()) parts.push(`正向：\n${positiveText}`);
    if (negativeText.trim()) parts.push(`负向：\n${negativeText}`);
    downloadLocalFile(
      `workbench-prompt-${promptStamp()}.txt`,
      parts.join("\n\n"),
      "text/plain",
    );
    setMessage("Prompt 已导出为 TXT（仅本地下载，未写入工作副本）。");
  }

  function exportPromptJson() {
    if (!positiveText.trim() && !negativeText.trim()) {
      setMessage("正向与负向均为空，无需导出。");
      return;
    }
    const payload = {
      version: 1,
      positive: positiveText,
      negative: negativeText,
    };
    downloadLocalFile(
      `workbench-prompt-${promptStamp()}.json`,
      JSON.stringify(payload, null, 2),
      "application/json",
    );
    setMessage("Prompt 已导出为 JSON（仅本地下载，未写入工作副本）。");
  }

  async function onPromptFileChosen(file?: File) {
    if (!file) return;
    try {
      const text = await file.text();
      const parsed = parsePromptImport(file.name, text);
      setImportedPrompt(parsed);
      setMessage("已解析导入内容，采用前请核对（未写入编辑框与工作副本）。");
    } catch (error) {
      setMessage(`导入失败：${String(error)}`);
    }
  }

  function adoptImported() {
    if (!importedPrompt) return;
    setPositiveText(importedPrompt.positive);
    setNegativeText(importedPrompt.negative);
    setImportedPrompt(null);
    setMessage("已将导入内容填入编辑框（尚未写入工作副本）。");
  }

  function dismissImported() {
    setImportedPrompt(null);
    setMessage("导入内容已放弃（未写入编辑框与工作副本）。");
  }

  function parsePasted() {
    try {
      const parsed = parsePromptContent(pasteText);
      setImportedPrompt(parsed);
      setPasteOpen(false);
      setPasteText("");
      setMessage("已解析粘贴内容，采用前请核对（未写入编辑框与工作副本）。");
    } catch (error) {
      setMessage(`粘贴解析失败：${String(error)}`);
    }
  }

  function cancelPaste() {
    setPasteOpen(false);
    setPasteText("");
  }

  async function loadTasks(refresh: boolean) {
    if (!workflowId) return;
    try {
      const result = await apiGet<TasksResponse>(
        `/api/workflows/${workflowId}/tasks${refresh ? "?refresh=true" : ""}`,
      );
      setComfyTasks(result.items);
      setTaskSyncError(result.sync_error);
    } catch (error) {
      setTaskSyncError(String(error));
    }
  }

  async function loadVersions(id: string) {
    try {
      const result = await apiGet<{ items: VersionEntry[] }>(
        `/api/workflows/${id}/versions`,
      );
      setVersions(result.items);
    } catch {
      setVersions([]);
    }
  }

  async function loadDrafts(id: string, trashed: boolean) {
    try {
      const result = await apiGet<{ items: DraftEntry[] }>(
        `/api/workflows/${id}/drafts?include_trashed=${trashed}`,
      );
      setDrafts(result.items);
    } catch {
      setDrafts([]);
    }
  }

  async function saveDraft() {
    if (!workflowId) return;
    const name = draftName.trim();
    if (!name) {
      setMessage("请先填写草稿名称。");
      return;
    }
    if (!positiveText.trim() && !negativeText.trim()) {
      setMessage("正向与负向均为空，无法保存草稿。");
      return;
    }
    setDraftBusy(true);
    try {
      await apiPost(`/api/workflows/${workflowId}/drafts`, {
        name,
        positive: positiveText,
        negative: negativeText,
        note: draftNote.trim(),
        tags: parseDraftTags(draftTags),
      });
      setDraftName("");
      setDraftNote("");
      setDraftTags("");
      await loadDrafts(workflowId, showTrashed);
      setMessage("草稿已保存（未写入工作副本）。");
    } catch (error) {
      setMessage(`保存草稿失败：${String(error)}`);
    } finally {
      setDraftBusy(false);
    }
  }

  function adoptDraft(draft: DraftEntry) {
    setPositiveText(draft.positive);
    setNegativeText(draft.negative);
    setDraftName(draft.name);
    setDraftNote(draft.note);
    setDraftTags((draft.tags || []).join(", "));
    setMessage(`草稿「${draft.name}」已载入编辑框（尚未写入工作副本）。`);
  }

  function goToHistory(promptId: string) {
    try {
      localStorage.setItem("workbench.jumpHistory", promptId);
    } catch {
      // 忽略本地存储写入失败。
    }
    window.dispatchEvent(
      new CustomEvent("workbench:navigate", {
        detail: { page: "history", promptId },
      }),
    );
  }

  async function deleteDraft(draftId: string) {
    if (!workflowId) return;
    setDraftBusy(true);
    try {
      await apiDelete(`/api/workflows/${workflowId}/drafts/${draftId}`, {});
      setDeletingDraftId(null);
      await loadDrafts(workflowId, showTrashed);
      setMessage("草稿已移入回收站，可在回收站恢复。");
    } catch (error) {
      setMessage(`删除草稿失败：${String(error)}`);
    } finally {
      setDraftBusy(false);
    }
  }

  async function restoreDraft(draft: DraftEntry) {
    if (!workflowId) return;
    setDraftBusy(true);
    try {
      await apiPost(`/api/workflows/${workflowId}/drafts/${draft.id}/restore`, {});
      await loadDrafts(workflowId, showTrashed);
      setMessage(`草稿「${draft.name}」已恢复到草稿箱。`);
    } catch (error) {
      setMessage(`恢复草稿失败：${String(error)}`);
    } finally {
      setDraftBusy(false);
    }
  }

  async function purgeDraft(draftId: string) {
    if (!workflowId) return;
    setDraftBusy(true);
    try {
      await apiPost(`/api/workflows/${workflowId}/drafts/${draftId}/purge`, {});
      setPurgingDraftId(null);
      await loadDrafts(workflowId, true);
      setMessage("草稿已彻底删除，不可恢复。");
    } catch (error) {
      setMessage(`彻底删除失败：${String(error)}`);
    } finally {
      setDraftBusy(false);
    }
  }

  async function toggleFavorite(draft: DraftEntry) {
    if (!workflowId) return;
    setDraftBusy(true);
    try {
      await apiPost(`/api/workflows/${workflowId}/drafts/${draft.id}/favorite`, {});
      await loadDrafts(workflowId, showTrashed);
      setMessage(draft.favored ? `已取消收藏草稿「${draft.name}」。` : `已收藏草稿「${draft.name}」。`);
    } catch (error) {
      setMessage(`切换收藏失败：${String(error)}`);
    } finally {
      setDraftBusy(false);
    }
  }

  async function togglePin(draft: DraftEntry) {
    if (!workflowId) return;
    setDraftBusy(true);
    try {
      await apiPost(`/api/workflows/${workflowId}/drafts/${draft.id}/pin`, {});
      await loadDrafts(workflowId, showTrashed);
      setMessage(draft.pinned ? `已取消置顶草稿「${draft.name}」。` : `已置顶草稿「${draft.name}」。`);
    } catch (error) {
      setMessage(`切换置顶失败：${String(error)}`);
    } finally {
      setDraftBusy(false);
    }
  }

  function exportDrafts() {
    const payload = {
      exported_at: new Date().toISOString(),
      count: filteredDrafts.length,
      records: filteredDrafts,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const stamp = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 12);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `workbench-drafts-${stamp}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  async function updateDraft(draft: DraftEntry) {
    if (!workflowId) return;
    const name = draftName.trim();
    if (!name) {
      setMessage("请先填写草稿名称。");
      return;
    }
    if (!positiveText.trim() && !negativeText.trim()) {
      setMessage("正向与负向均为空，无法更新草稿。");
      return;
    }
    setDraftBusy(true);
    try {
      await apiPost(`/api/workflows/${workflowId}/drafts`, {
        draft_id: draft.id,
        name,
        positive: positiveText,
        negative: negativeText,
        note: draftNote.trim(),
        tags: parseDraftTags(draftTags),
        source_history_id: draft.source_history_id ?? null,
      });
      setUpdatingDraftId(null);
      await loadDrafts(workflowId, showTrashed);
      setMessage("草稿已更新（未写入工作副本）。");
    } catch (error) {
      setMessage(`更新草稿失败：${String(error)}`);
    } finally {
      setDraftBusy(false);
    }
  }

  async function copyDraftTo(draft: DraftEntry) {
    if (!copyTargetId) {
      setMessage("请先选择要复制到的目标工作流。");
      return;
    }
    setDraftBusy(true);
    try {
      await apiPost(`/api/workflows/${copyTargetId}/drafts`, {
        name: draft.name,
        positive: draft.positive,
        negative: draft.negative,
        note: draft.note,
        tags: draft.tags || [],
      });
      const target = items.find((workflow) => workflow.id === copyTargetId);
      setCopyingDraftId(null);
      setCopyTargetId("");
      setShowTrashed(false);
      setPurgingDraftId(null);
      setMessage(`已复制草稿「${draft.name}」到「${target?.filename || copyTargetId}」。`);
    } catch (error) {
      setMessage(`复制草稿失败：${String(error)}`);
    } finally {
      setDraftBusy(false);
    }
  }

  const allDraftTags = Array.from(
    new Set(drafts.flatMap((draft) => draft.tags || [])),
  ).sort();
  const copyTargets = items.filter((workflow) => workflow.id !== workflowId);
  const draftKeywordTerm = draftKeyword.trim().toLowerCase();
  const filteredDrafts = drafts.filter((draft) => {
    if (favoredOnly && !draft.favored) return false;
    if (tagFilter && !(draft.tags || []).includes(tagFilter)) return false;
    if (!draftKeywordTerm) return true;
    const haystack = [
      draft.name,
      draft.note,
      draft.positive,
      draft.negative,
      ...(draft.tags || []),
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(draftKeywordTerm);
  });
  const [restoringStamp, setRestoringStamp] = useState<string | null>(null);
  const [confirmStamp, setConfirmStamp] = useState<string | null>(null);
  const [comparingStamp, setComparingStamp] = useState<string | null>(null);

  async function restoreVersion(stamp: string) {
    if (!workflowId) return;
    setRestoringStamp(stamp);
    setConfirmStamp(null);
    try {
      const result = await apiPost<WriteResult>(
        `/api/workflows/${workflowId}/versions/${stamp}/restore`,
        {},
      );
      setDetail(result.workflow);
      setPositiveText(
        result.workflow.working_prompts.find((item) => item.role === "positive")
          ?.text ?? "",
      );
      setNegativeText(
        result.workflow.working_prompts.find((item) => item.role === "negative")
          ?.text ?? "",
      );
      await loadVersions(workflowId);
      setMessage(
        "已恢复所选版本；当前内容已另存为一个新的历史版本快照。",
      );
    } catch (error) {
      setMessage(`版本恢复失败：${String(error)}`);
    } finally {
      setRestoringStamp(null);
    }
  }
  async function submitTask() {
    if (!workflowId) return;
    setTaskBusy(true);
    try {
      await apiPost<ComfyTask>(`/api/workflows/${workflowId}/tasks`, {});
      setMessage("任务已提交到本地 ComfyUI。");
      await loadTasks(true);
    } catch (error) {
      setMessage(`提交被拒绝或失败：${String(error)}`);
    } finally {
      setTaskBusy(false);
    }
  }
  async function cancelTask(promptId: string) {
    if (!workflowId) return;
    setTaskBusy(true);
    try {
      await apiPost(
        `/api/workflows/${workflowId}/tasks/${promptId}/cancel`,
        {},
      );
      setMessage("任务已取消/中断。");
      await loadTasks(true);
    } catch (error) {
      setMessage(`取消/中断失败：${String(error)}`);
    } finally {
      setTaskBusy(false);
    }
  }
  async function retryTask(promptId: string) {
    if (!workflowId) return;
    setTaskBusy(true);
    try {
      await apiPost(
        `/api/workflows/${workflowId}/tasks/${promptId}/retry`,
        {},
      );
      setMessage("已按当前工作流重新提交任务。");
      await loadTasks(true);
    } catch (error) {
      setMessage(`重试失败：${String(error)}`);
    } finally {
      setTaskBusy(false);
    }
  }
  const canWrite =
    detail?.report.safe_prompt_write_supported === true &&
    detail.manifest.confirmed === true;
  return (
    <section className="workflow-page">
      <div className="panel">
        <div className="section-heading">
          <div>
            <h2>工作流工作区</h2>
            <p>
              导入、解析并确认 Prompt 节点。原始工作流只读，修改只写入工作副本。
            </p>
          </div>
          <label className="workflow-import-button">
            导入 JSON
            <input
              type="file"
              accept=".json,application/json"
              disabled={busy}
              onChange={(event) => {
                const file = event.target.files?.[0];
                void importFile(file);
                event.currentTarget.value = "";
              }}
            />
          </label>
        </div>
        <div className="workflow-columns">
          <div>
            <h3>已导入工作流</h3>
            {items.length === 0 ? (
              <p className="muted">还没有导入工作流。</p>
            ) : (
              <div className="workflow-list">
                {items.map((item) => (
                  <button
                    key={item.id}
                    className={`workflow-list-item ${
                      workflowId === item.id ? "selected" : ""
                    }`}
                    disabled={busy}
                    onClick={() => void openWorkflow(item.id)}
                  >
                    <strong>{item.filename}</strong>
                    <small>
                      {item.format.toUpperCase()} ·{" "}
                      {item.confirmed ? "已确认白名单" : "待确认"}
                    </small>
                  </button>
                ))}
              </div>
            )}
          </div>
          <div>
            <h3>当前工作流识别结果</h3>
            {!detail ? (
              <p className="muted">导入或从左侧选择一个工作流。</p>
            ) : (
              <>
                <p>
                  <strong>{detail.manifest.filename}</strong> ·{" "}
                  {detail.report.format.toUpperCase()} ·{" "}
                  {detail.report.node_count} 个节点
                </p>
                <h4>模型加载节点</h4>
                {detail.report.model_nodes.length === 0 ? (
                  <p className="muted">未识别到常见模型加载节点。</p>
                ) : (
                  <ul>
                    {detail.report.model_nodes.map((node) => (
                      <li key={node.node_id}>
                        节点 {node.node_id} · {node.class_type}
                        {Object.entries(node.inputs).map(([key, value]) => (
                          <span key={key} className="workflow-meta">
                            {key}: {String(value)}
                          </span>
                        ))}
                      </li>
                    ))}
                  </ul>
                )}
                <h4>LoRA 节点</h4>
                {detail.report.lora_nodes.length === 0 ? (
                  <p className="muted">未识别到常见 LoRA 节点。</p>
                ) : (
                  <ul>
                    {detail.report.lora_nodes.map((node) => (
                      <li key={node.node_id}>
                        节点 {node.node_id} · {node.class_type}
                        {Object.entries(node.inputs).map(([key, value]) => (
                          <span key={key} className="workflow-meta">
                            {key}: {String(value)}
                          </span>
                        ))}
                      </li>
                    ))}
                  </ul>
                )}
                <h4>历史版本</h4>
                {versions.length === 0 ? (
                  <p className="muted">暂无保存过的历史版本。</p>
                ) : (
                  <ul>
                    {versions.map((entry) => {
                      const positive =
                        entry.prompts.find((p) => p.role === "positive")?.text ?? "";
                      const negative =
                        entry.prompts.find((p) => p.role === "negative")?.text ?? "";
                      const restoring = restoringStamp === entry.stamp;
                      const confirming = confirmStamp === entry.stamp;
                      const comparing = comparingStamp === entry.stamp;
                      const positiveSame = positive.trim() === positiveText.trim();
                      const negativeSame = negative.trim() === negativeText.trim();
                      return (
                        <li key={entry.stamp}>
                          <small className="workflow-meta">
                            {formatVersionStamp(entry.stamp)}
                          </small>
                          <div>正向：{clipText(positive)}</div>
                          <div>负向：{clipText(negative)}</div>
                          <div className="actions">
                            {confirming ? (
                              <>
                                <button
                                  type="button"
                                  disabled={restoring || busy}
                                  onClick={() => void restoreVersion(entry.stamp)}
                                >
                                  {restoring ? "正在恢复…" : "再次点击确认恢复"}
                                </button>
                                <button
                                  type="button"
                                  disabled={restoring || busy}
                                  onClick={() => setConfirmStamp(null)}
                                >
                                  取消
                                </button>
                              </>
                            ) : (
                              <button
                                type="button"
                                disabled={restoring || busy}
                                onClick={() => setConfirmStamp(entry.stamp)}
                              >
                                {restoring ? "正在恢复…" : "恢复此版本"}
                              </button>
                            )}
                            <button
                              type="button"
                              disabled={restoring || busy}
                              onClick={() =>
                                setComparingStamp(comparing ? null : entry.stamp)
                              }
                            >
                              {comparing ? "收起比对" : "比对当前副本"}
                            </button>
                          </div>
                          {comparing && (
                            <div className="workflow-meta">
                              <div>
                                正向：{positiveSame ? "与当前副本一致" : "与当前副本不一致"}
                              </div>
                              {!positiveSame && (
                                <div>
                                  <div>快照：{positive || "（空）"}</div>
                                  <div>当前：{positiveText || "（空）"}</div>
                                </div>
                              )}
                              <div>
                                负向：{negativeSame ? "与当前副本一致" : "与当前副本不一致"}
                              </div>
                              {!negativeSame && (
                                <div>
                                  <div>快照：{negative || "（空）"}</div>
                                  <div>当前：{negativeText || "（空）"}</div>
                                </div>
                              )}
                            </div>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                )}
              </>
            )}
          </div>
        </div>
      </div>
      {detail && (
        <>
          {compare && (
            <div className="panel">
              <h3>规则与参数比对（只读）</h3>
              <div className="compare-meta">
                <span>
                  状态：{compare.status === "registered" ? "已登记" : "未登记"}
                </span>
                <span>Checkpoint：{compare.checkpoint ?? "—"}</span>
                <span>
                  架构：
                  {compare.architecture_label ?? compare.architecture ?? "—"}
                </span>
              </div>
              {compare.status !== "registered" ? (
                <p className="muted">
                  当前工作流未在规则库登记；不依据模型名猜测参数或风格。
                </p>
              ) : (
                <>
                  <div className="compare-counts">
                    {Object.entries(compare.counts).map(([status, count]) => (
                      <span key={status} className={`compare-badge ${status}`}>
                        {STATUS_LABEL[status] ?? status} · {count}
                      </span>
                    ))}
                  </div>
                  <h4>实际参数摘要</h4>
                  <div className="compare-actuals">
                    {ACTUAL_SUMMARY.map(({ key, label }) => (
                      <span key={key} className="workflow-meta">
                        {label}: {formatActual(compare.actuals[key])}
                      </span>
                    ))}
                    <span className="workflow-meta">
                      分辨率: {formatActual(compare.actuals.width)}×
                      {formatActual(compare.actuals.height)}
                    </span>
                  </div>
                  {(Number(compare.actuals.latent_node_count) ?? 0) > 1 && (
                    <p className="muted">
                      检测到 {formatActual(compare.actuals.latent_node_count)} 个
                      latent 节点，分辨率结论取首个；其余节点未参与比对。
                    </p>
                  )}
                  {(Number(compare.actuals.clip_skip_node_count) ?? 0) > 1 && (
                    <p className="muted">
                      检测到 {formatActual(compare.actuals.clip_skip_node_count)} 个
                      CLIP 跳过层节点，Clip Skip 结论取首个；其余节点未参与比对。
                    </p>
                  )}
                  <h4>比对条目</h4>
                  <div className="compare-table">
                    {compare.comparisons.length === 0 ? (
                      <p className="muted">无可比对的规则字段。</p>
                    ) : (
                      compare.comparisons.map((entry) => (
                        <div className="compare-row" key={entry.key}>
                          <div className="compare-row-main">
                            <strong>{entry.key}</strong>
                            <small>
                              规则：{formatActual(entry.rule)} · 实际：
                              {formatActual(entry.actual)}
                            </small>
                          </div>
                          <span className={`compare-badge ${entry.status}`}>
                            {STATUS_LABEL[entry.status] ?? entry.status}
                            {entry.reason ? `（${entry.reason}）` : ""}
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                  {compare.sampler_group_comparisons &&
                    compare.sampler_group_comparisons.length > 1 && (
                      <>
                        <h4>逐采样器组比对</h4>
                        <p className="muted">
                          多组采样器各自独立比对，不合并、不替选；顶层结论对应首组。
                        </p>
                        <div className="compare-groups">
                          {compare.sampler_group_comparisons.map((group, idx) => (
                            <div className="compare-group" key={idx}>
                              <div className="compare-group-head">
                                <strong>
                                  采样器组 {idx + 1}
                                  {group.sampler_node_id
                                    ? ` · 节点 ${group.sampler_node_id}`
                                    : ""}
                                </strong>
                                <span className="compare-counts">
                                  {Object.entries(group.counts).map(([status, count]) => (
                                    <span
                                      key={status}
                                      className={`compare-badge ${status}`}
                                    >
                                      {STATUS_LABEL[status] ?? status} · {count}
                                    </span>
                                  ))}
                                </span>
                              </div>
                              <div className="compare-actuals">
                                <span className="workflow-meta">
                                  步数: {formatActual(group.params.steps)}
                                </span>
                                <span className="workflow-meta">
                                  CFG: {formatActual(group.params.cfg)}
                                </span>
                                <span className="workflow-meta">
                                  采样器: {formatActual(group.params.sampler_name)}
                                </span>
                                <span className="workflow-meta">
                                  调度器: {formatActual(group.params.scheduler)}
                                </span>
                              </div>
                              <div className="compare-table">
                                {group.comparisons.map((entry) => (
                                  <div className="compare-row" key={entry.key}>
                                    <div className="compare-row-main">
                                      <strong>{entry.key}</strong>
                                      <small>
                                        规则：{formatActual(entry.rule)} · 实际：
                                        {formatActual(entry.actual)}
                                      </small>
                                    </div>
                                    <span className={`compare-badge ${entry.status}`}>
                                      {STATUS_LABEL[entry.status] ?? entry.status}
                                      {entry.reason ? `（${entry.reason}）` : ""}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      </>
                    )}
                </>
              )}
            </div>
          )}
          <div className="panel">
            <h3>Prompt 节点确认</h3>
            {detail.report.prompt_nodes.length === 0 ? (
              <p className="muted">
                没有识别到常见文本编码节点。请确认导入的工作流类型和节点结构。
              </p>
            ) : (
              <>
                <p className="muted">
                  请逐个确认节点用途。自动识别结果只是建议，最终以你的选择为准。
                </p>
                <div className="workflow-node-list">
                  {detail.report.prompt_nodes.map((node) => (
                    <div className="workflow-node-row" key={node.node_id}>
                      <div>
                        <strong>
                          节点 {node.node_id} · {node.class_type}
                        </strong>
                        <small>
                          {node.text.slice(0, 180) || "（空文本）"}
                        </small>
                      </div>
                      <select
                        value={roles[node.node_id] ?? ""}
                        disabled={
                          busy ||
                          !detail.report.safe_prompt_write_supported ||
                          !node.editable
                        }
                        onChange={(event) =>
                          setRoles((old) => ({
                            ...old,
                            [node.node_id]: event.target.value as RoleChoice,
                          }))
                        }
                      >
                        <option value="">不参与</option>
                        <option value="positive">正向 Prompt</option>
                        <option value="negative">负向 Prompt</option>
                      </select>
                    </div>
                  ))}
                </div>
              </>
            )}
            {detail.report.notes.map((note) => (
              <p className="workflow-warning" key={note}>{note}</p>
            ))}
            {detail.report.safe_prompt_write_supported && (
              <div className="actions">
                <button
                  disabled={busy || detail.report.prompt_nodes.length === 0}
                  onClick={() => void confirmNodes()}
                >
                  确认 Prompt 白名单
                </button>
                <span className="muted">
                  {detail.manifest.confirmed ? "白名单已确认" : "尚未确认"}
                </span>
              </div>
            )}
          </div>
          {detail && (
            <div className="panel">
              <h3>本地模型候选</h3>
              {!modelsOnline ? (
                <p className="muted">本地 Ollama 不可用，无法生成候选。</p>
              ) : ollamaModels.length === 0 ? (
                <p className="muted">未发现本地模型。</p>
              ) : (
                <>
                  <div className="actions">
                    <select
                      value={selectedModel}
                      disabled={busy || candidateBusy}
                      onChange={(event) => setSelectedModel(event.target.value)}
                    >
                      {ollamaModels.map((model) => (
                        <option key={model} value={model}>
                          {model}
                        </option>
                      ))}
                    </select>
                    <input
                      type="text"
                      placeholder="补充任务要求（可选）"
                      value={taskText}
                      disabled={busy || candidateBusy}
                      onChange={(event) => setTaskText(event.target.value)}
                    />
                    <button
                      disabled={busy || candidateBusy || !selectedModel}
                      onClick={() => void generateCandidate()}
                    >
                      {candidateBusy ? "生成中…" : "生成候选"}
                    </button>
                  </div>
                  {candidate && (
                    <div className="workflow-text-field">
                      <span>候选文本（只读，采用后进入下方编辑框）</span>
                      <textarea readOnly rows={7} value={candidate} />
                      <div className="actions">
                        <button onClick={adoptCandidate}>采用到正向 Prompt</button>
                        <button onClick={() => void copyCandidate()}>复制候选</button>
                        <button onClick={dismissCandidate}>放弃候选</button>
                        <span className="muted">
                          候选不会自动写入工作副本，需在下方确认写入。
                        </span>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
          {canWrite && (
            <div className="panel">
              <h3>编辑工作副本 Prompt</h3>
              {detail.manifest.whitelist.some(
                (item) => item.role === "positive",
              ) && (
                <label className="workflow-text-field">
                  <div className="workflow-field-head">
                    <span>
                      正向 Prompt{" "}
                      <span className="muted">{promptCountLabel(positiveText)}</span>
                    </span>
                    <button onClick={copyPositive}>复制正向</button>
                  </div>
                  <textarea
                    value={positiveText}
                    onChange={(event) => setPositiveText(event.target.value)}
                    rows={7}
                    disabled={busy}
                  />
                </label>
              )}
              {detail.manifest.whitelist.some(
                (item) => item.role === "negative",
              ) && (
                <label className="workflow-text-field">
                  <div className="workflow-field-head">
                    <span>
                      负向 Prompt{" "}
                      <span className="muted">{promptCountLabel(negativeText)}</span>
                    </span>
                    <button onClick={copyNegative}>复制负向</button>
                  </div>
                  <textarea
                    value={negativeText}
                    onChange={(event) => setNegativeText(event.target.value)}
                    rows={7}
                    disabled={busy}
                  />
                </label>
              )}
              <div className="actions">
                <button disabled={busy} onClick={() => void writePrompts()}>
                  写入工作副本并校验
                </button>
                <button onClick={copyBoth}>复制完整</button>
                <button onClick={exportPromptTxt}>导出 TXT</button>
                <button onClick={exportPromptJson}>导出 JSON</button>
                <label className="workflow-import-button">
                  导入 TXT/JSON
                  <input
                    type="file"
                    accept=".txt,.json,application/json,text/plain"
                    disabled={busy}
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      void onPromptFileChosen(file);
                      event.currentTarget.value = "";
                    }}
                  />
                </label>
                <button onClick={() => setPasteOpen((v) => !v)}>粘贴文本</button>
                <span className="muted">
                  不会修改原始文件，也不会提交 ComfyUI 任务。
                </span>
              </div>
              {pasteOpen && (
                <div className="workflow-text-field">
                  <span>粘贴 Prompt 文本（可含正向/负向标记，或导出 JSON）</span>
                  <textarea
                    rows={6}
                    value={pasteText}
                    disabled={busy}
                    onChange={(event) => setPasteText(event.target.value)}
                    placeholder={"正向：…\n负向：…"}
                  />
                  <div className="actions">
                    <button onClick={parsePasted}>解析到预览</button>
                    <button onClick={cancelPaste}>取消</button>
                    <span className="muted">
                      粘贴内容不会自动写入工作副本。
                    </span>
                  </div>
                </div>
              )}
              {importedPrompt && (
                <div className="workflow-text-field">
                  <span>导入预览（只读，采用后进入下方编辑框）</span>
                  {importedPrompt.positive && (
                    <>
                      <div className="workflow-field-head">
                        <span>正向 Prompt</span>
                      </div>
                      <textarea readOnly rows={5} value={importedPrompt.positive} />
                    </>
                  )}
                  {importedPrompt.negative && (
                    <>
                      <div className="workflow-field-head">
                        <span>负向 Prompt</span>
                      </div>
                      <textarea readOnly rows={5} value={importedPrompt.negative} />
                    </>
                  )}
                  <div className="actions">
                    <button onClick={adoptImported}>采用到编辑框</button>
                    <button onClick={dismissImported}>放弃导入</button>
                    <span className="muted">
                      导入内容不会自动写入工作副本。
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}
          {canWrite && (
            <div className="panel">
              <h3>草稿箱</h3>
              <p className="muted">
                手动保存的 Prompt 组合；保存与更新都不写入工作副本，载入编辑框后仍需确认写入。
                载入后可在上方名称 / 备注框修改，更新时用当前编辑框内容与名称备注一并覆盖该草稿。
              </p>
              <div className="actions">
                <input
                  type="text"
                  placeholder="草稿名称"
                  value={draftName}
                  disabled={draftBusy || busy}
                  onChange={(event) => setDraftName(event.target.value)}
                />
                <input
                  type="text"
                  placeholder="备注（可选）"
                  value={draftNote}
                  disabled={draftBusy || busy}
                  onChange={(event) => setDraftNote(event.target.value)}
                />
                <input
                  type="text"
                  placeholder="标签（逗号分隔）"
                  value={draftTags}
                  disabled={draftBusy || busy}
                  onChange={(event) => setDraftTags(event.target.value)}
                />
                <button
                  disabled={draftBusy || busy}
                  onClick={() => void saveDraft()}
                >
                  保存当前为草稿
                </button>
              </div>
              {drafts.length > 0 && (
                <div className="actions">
                  <input
                    type="text"
                    placeholder="按名称 / 备注 / Prompt 过滤草稿"
                    value={draftKeyword}
                    disabled={draftBusy || busy}
                    onChange={(event) => setDraftKeyword(event.target.value)}
                  />
                  {allDraftTags.length > 0 && (
                    <select
                      value={tagFilter}
                      disabled={draftBusy || busy}
                      onChange={(event) => setTagFilter(event.target.value)}
                    >
                      <option value="">全部标签</option>
                      {allDraftTags.map((tag) => (
                        <option key={tag} value={tag}>
                          {tag}
                        </option>
                      ))}
                    </select>
                  )}
                  <label className="workflow-meta">
                    <input
                      type="checkbox"
                      checked={favoredOnly}
                      disabled={draftBusy || busy || showTrashed}
                      onChange={(event) => {
                        setFavoredOnly(event.target.checked);
                        persistFavoredOnly(event.target.checked);
                      }}
                    />
                    仅看收藏
                  </label>
                  <label className="workflow-meta">
                    <input
                      type="checkbox"
                      checked={showTrashed}
                      disabled={draftBusy || busy}
                      onChange={(event) => {
                        const next = event.target.checked;
                        setShowTrashed(next);
                        if (workflowId) void loadDrafts(workflowId, next);
                      }}
                    />
                    回收站
                  </label>
                  <button
                    onClick={exportDrafts}
                    disabled={draftBusy || busy || filteredDrafts.length === 0}
                  >
                    导出 JSON
                  </button>
                </div>
              )}
              {drafts.length === 0 ? (
                <p className="muted">还没有保存的草稿。</p>
              ) : filteredDrafts.length === 0 ? (
                <p className="muted">没有匹配的草稿。</p>
              ) : (
                <div className="workflow-node-list">
                  {filteredDrafts.map((draft) => (
                    <div className="workflow-node-row" key={draft.id}>
                      <div>
                        <strong>{draft.name}</strong>
                        {showTrashed && (
                          <small className="workflow-meta">已删除</small>
                        )}
                        {draft.pinned && !showTrashed && (
                          <small className="workflow-meta">置顶</small>
                        )}
                        {draft.favored && !showTrashed && (
                          <small className="workflow-meta">已收藏</small>
                        )}
                        <small>正向：{clipText(draft.positive)}</small>
                        <small>负向：{clipText(draft.negative)}</small>
                        {draft.note && (
                          <small className="workflow-meta">备注：{draft.note}</small>
                        )}
                        {(draft.tags || []).length > 0 && (
                          <small className="workflow-meta">
                            标签：{(draft.tags || []).join("、")}
                          </small>
                        )}
                        {draft.source_history_id && (
                          <small className="workflow-meta">
                            来源历史：
                            <button
                              className="secondary"
                              onClick={() => goToHistory(draft.source_history_id!)}
                              title="跳转到生成历史"
                            >
                              {draft.source_history_id.slice(0, 8)}
                            </button>
                          </small>
                        )}
                        {envSnapshotSummary(draft.env_snapshot) && (
                          <small className="workflow-meta">
                            环境：{envSnapshotSummary(draft.env_snapshot)}
                          </small>
                        )}
                      </div>
                      <div className="actions">
                        {!showTrashed && (
                        <>
                        <button
                          onClick={() => adoptDraft(draft)}
                          disabled={draftBusy || busy}
                        >
                          载入到编辑框
                        </button>
                        <button
                          onClick={() => void toggleFavorite(draft)}
                          disabled={draftBusy || busy}
                        >
                          {draft.favored ? "取消收藏" : "收藏"}
                        </button>
                        <button
                          onClick={() => void togglePin(draft)}
                          disabled={draftBusy || busy}
                        >
                          {draft.pinned ? "取消置顶" : "置顶"}
                        </button>
                        {copyingDraftId === draft.id ? (
                          <>
                            <select
                              value={copyTargetId}
                              disabled={draftBusy || busy}
                              onChange={(event) => setCopyTargetId(event.target.value)}
                            >
                              <option value="">选择目标工作流</option>
                              {copyTargets.map((workflow) => (
                                <option key={workflow.id} value={workflow.id}>
                                  {workflow.filename}
                                </option>
                              ))}
                            </select>
                            <button
                              onClick={() => void copyDraftTo(draft)}
                              disabled={draftBusy || busy || !copyTargetId}
                            >
                              确认复制？
                            </button>
                            <button
                              onClick={() => {
                                setCopyingDraftId(null);
                                setCopyTargetId("");
                              }}
                              disabled={draftBusy || busy}
                            >
                              取消
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={() => {
                              setCopyingDraftId(draft.id);
                              setCopyTargetId("");
                            }}
                            disabled={draftBusy || busy || copyTargets.length === 0}
                          >
                            复制到…
                          </button>
                        )}
                        {updatingDraftId === draft.id ? (
                          <>
                            <button
                              onClick={() => void updateDraft(draft)}
                              disabled={draftBusy || busy}
                            >
                              确认更新？
                            </button>
                            <button
                              onClick={() => setUpdatingDraftId(null)}
                              disabled={draftBusy || busy}
                            >
                              取消
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={() => setUpdatingDraftId(draft.id)}
                            disabled={draftBusy || busy}
                          >
                            更新
                          </button>
                        )}
                        {deletingDraftId === draft.id ? (
                          <>
                            <button
                              onClick={() => void deleteDraft(draft.id)}
                              disabled={draftBusy || busy}
                            >
                              确认移入回收站？
                            </button>
                            <button
                              onClick={() => setDeletingDraftId(null)}
                              disabled={draftBusy || busy}
                            >
                              取消
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={() => setDeletingDraftId(draft.id)}
                            disabled={draftBusy || busy}
                          >
                            移入回收站
                          </button>
                        )}
                        </>
                        )}
                        {showTrashed && (
                        <>
                          <button
                            onClick={() => void restoreDraft(draft)}
                            disabled={draftBusy || busy}
                          >
                            恢复
                          </button>
                          {purgingDraftId === draft.id ? (
                            <>
                              <button
                                onClick={() => void purgeDraft(draft.id)}
                                disabled={draftBusy || busy}
                              >
                                确认彻底删除？
                              </button>
                              <button
                                onClick={() => setPurgingDraftId(null)}
                                disabled={draftBusy || busy}
                              >
                                取消
                              </button>
                            </>
                          ) : (
                            <button
                              onClick={() => setPurgingDraftId(draft.id)}
                              disabled={draftBusy || busy}
                            >
                              彻底删除
                            </button>
                          )}
                        </>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          {detail && (
            <div className="panel">
              <h3>ComfyUI 任务</h3>
              {detail.manifest.format !== "api" ? (
                <p className="muted">
                  UI 格式工作流不能直接提交，请先在 ComfyUI 中导出 API 格式。
                </p>
              ) : (
                <>
                  <div className="actions">
                    <button
                      disabled={taskBusy || busy || !detail.manifest.confirmed}
                      onClick={() => void submitTask()}
                    >
                      {taskBusy ? "提交中…" : "提交到 ComfyUI"}
                    </button>
                    <button
                      onClick={() => void loadTasks(true)}
                      disabled={taskBusy || busy}
                    >
                      刷新状态
                    </button>
                    <span className="muted">
                      {detail.manifest.confirmed ? "白名单已确认" : "需先确认白名单"}
                    </span>
                  </div>
                  {taskSyncError && (
                    <p className="workflow-warning">状态校准不可用：{taskSyncError}</p>
                  )}
                  {comfyTasks.length === 0 ? (
                    <p className="muted">当前工作流还没有已提交的任务。</p>
                  ) : (
                    <div className="workflow-node-list">
                      {comfyTasks.map((task) => (
                        <div className="workflow-node-row" key={task.prompt_id}>
                          <div>
                            <strong>任务 {task.prompt_id.slice(0, 8)}</strong>
                            <small>提交于 {formatTaskTime(task.submitted_at)}</small>
                            {task.last_error && (
                              <small className="workflow-warning">{task.last_error}</small>
                            )}
                            {outputFilenames(task.outputs).length > 0 && (
                              <small>
                                输出：{outputFilenames(task.outputs).join("、")}
                              </small>
                            )}
                          </div>
                          <div className="actions">
                            {(task.status === "submitted" ||
                              task.status === "running") && (
                              <button
                                onClick={() => void cancelTask(task.prompt_id)}
                                disabled={taskBusy || busy}
                              >
                                {task.status === "running" ? "中断" : "取消"}
                              </button>
                            )}
                            {(task.status === "failed" ||
                              task.status === "interrupted") && (
                              <button
                                onClick={() => void retryTask(task.prompt_id)}
                                disabled={taskBusy || busy}
                              >
                                重试
                              </button>
                            )}
                            <span className={`compare-badge ${task.status}`}>
                              {TASK_STATUS_LABEL[task.status] ?? task.status}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </>
      )}
      <div className="workflow-message" role="status">
        {message}
      </div>
    </section>
  );
}
