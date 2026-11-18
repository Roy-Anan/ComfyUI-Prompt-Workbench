import { useEffect, useState } from "react";
import { apiGet, apiPost } from "./api";
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
  const [comfyTasks, setComfyTasks] = useState<ComfyTask[]>([]);
  const [taskBusy, setTaskBusy] = useState(false);
  const [taskSyncError, setTaskSyncError] = useState<string | null>(null);
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
      void loadTasks(false);
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
                  <span>正向 Prompt</span>
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
                  <span>负向 Prompt</span>
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
                <span className="muted">
                  不会修改原始文件，也不会提交 ComfyUI 任务。
                </span>
              </div>
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
