import { useEffect, useState } from "react";
import { apiGet, apiPost } from "./api";
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
type ComparePayload = {
  status: string;
  checkpoint: string | null;
  architecture: string | null;
  architecture_family?: string | null;
  architecture_label?: string | null;
  actuals: Record<string, unknown>;
  comparisons: ComparisonEntry[];
  counts: Record<string, number>;
};
type RoleChoice = "" | "positive" | "negative";

const STATUS_LABEL: Record<string, string> = {
  match: "匹配",
  out_of_range: "超出范围",
  out_of_set: "不在集合",
  unknown: "无法判定",
};

function formatActual(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
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
                  **{detail.manifest.filename}** ·{" "}
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
        </>
      )}
      <div className="workflow-message" role="status">
        {message}
      </div>
    </section>
  );
}
