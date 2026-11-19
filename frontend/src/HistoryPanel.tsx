import { useEffect, useState } from "react";
import { apiGet, apiPost } from "./api";

type HistoryView = "list" | "grid" | "timeline";

const VIEW_OPTIONS: { key: HistoryView; label: string }[] = [
  { key: "list", label: "列表" },
  { key: "grid", label: "网格" },
  { key: "timeline", label: "时间轴" },
];

function readStoredView(): HistoryView {
  try {
    const value = localStorage.getItem("workbench.historyView");
    if (value === "list" || value === "grid" || value === "timeline") return value;
  } catch {
    // 本地存储不可用时回落到列表视图。
  }
  return "list";
}

function readStoredFilter(key: string): string {
  try {
    return localStorage.getItem(key) || "";
  } catch {
    // 本地存储不可用时回落到全部。
  }
  return "";
}

function persistFilter(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // 忽略本地存储写入失败。
  }
}

type HistoryImage = {
  node_id: string;
  filename: string;
  subfolder: string;
  type: string;
  exists: boolean | null;
};

type ModelFile = { node_id: string; file: string };

type SamplerParams = Record<string, string | number | boolean | null>;

type ModelSnapshot = {
  checkpoints: ModelFile[];
  loras: ModelFile[];
  vaes: ModelFile[];
  clips: ModelFile[];
  resolution?: string | null;
  clip_skip?: number | null;
  samplers?: SamplerParams[];
};

type ModelFileKey = "checkpoints" | "loras" | "vaes" | "clips";

type LinkedDraft = { id: string; name: string };

type HistoryRecord = {
  prompt_id: string;
  workflow_id: string;
  created_at: string;
  positive_prompt: string | null;
  negative_prompt: string | null;
  model_snapshot: ModelSnapshot;
  task_status: string;
  images: HistoryImage[] | null;
  last_error: string | null;
  linked_draft: LinkedDraft | null;
};

const STATUS_LABEL: Record<string, string> = {
  submitted: "待运行",
  running: "运行中",
  succeeded: "已完成",
  failed: "失败",
  interrupted: "已中断",
  unknown: "未知",
};

function formatTime(value: string): string {
  if (!value) return "—";
  return value.replace("T", " ").slice(0, 16);
}

function snapshotFiles(snapshot: ModelSnapshot, key: ModelFileKey): string[] {
  return (snapshot[key] || []).map((entry) => entry.file).filter(Boolean);
}

function samplerSummary(samplers: SamplerParams[] | undefined): string {
  if (!samplers || samplers.length === 0) return "—";
  return samplers
    .map((params) => {
      const parts = [
        params.steps != null ? `Steps ${params.steps}` : "",
        params.cfg != null ? `CFG ${params.cfg}` : "",
        params.sampler_name ? String(params.sampler_name) : "",
        params.scheduler ? String(params.scheduler) : "",
      ].filter(Boolean);
      return parts.join(" / ");
    })
    .filter(Boolean)
    .join("；") || "—";
}

function existenceLabel(image: HistoryImage): string {
  if (image.exists === null) return "目录未配置";
  return image.exists ? "存在" : "丢失";
}

function historyImageUrl(image: HistoryImage): string {
  const params = new URLSearchParams({
    filename: image.filename,
    subfolder: image.subfolder || "",
  });
  return `/api/history/image?${params.toString()}`;
}

function summarize(text: string | null, limit = 80): string {
  if (!text) return "—";
  return text.length > limit ? `${text.slice(0, limit)}…` : text;
}

function recordHasPrompt(record: HistoryRecord): boolean {
  return Boolean(record.positive_prompt?.trim() || record.negative_prompt?.trim());
}

function autoDraftName(record: HistoryRecord): string {
  const date = record.created_at.slice(5, 10) || "历史";
  const source = (record.positive_prompt || record.negative_prompt || "").trim();
  const summary = source.length > 30 ? `${source.slice(0, 30)}…` : source;
  return `${date} ${summary}`.trim().slice(0, 120);
}

function groupByDay(records: HistoryRecord[]): { day: string; items: HistoryRecord[] }[] {
  const sorted = [...records].sort((a, b) =>
    a.created_at < b.created_at ? 1 : -1,
  );
  const groups: { day: string; items: HistoryRecord[] }[] = [];
  const index = new Map<string, number>();
  for (const record of sorted) {
    const day = record.created_at.slice(0, 10) || "未知日期";
    const existing = index.get(day);
    if (existing === undefined) {
      index.set(day, groups.length);
      groups.push({ day, items: [record] });
    } else {
      groups[existing].items.push(record);
    }
  }
  return groups;
}

const STATUS_OPTIONS = [
  "submitted",
  "running",
  "succeeded",
  "failed",
  "interrupted",
  "unknown",
];

export default function HistoryPanel() {
  const [items, setItems] = useState<HistoryRecord[] | null>(null);
  const [error, setError] = useState("");
  const [openId, setOpenId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState(() => readStoredFilter("workbench.historyStatus"));
  const [workflowFilter, setWorkflowFilter] = useState(() => readStoredFilter("workbench.historyWorkflow"));
  const [keyword, setKeyword] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [view, setView] = useState<HistoryView>(readStoredView);
  const [draftingId, setDraftingId] = useState<string | null>(null);
  const [draftName, setDraftName] = useState("");
  const [draftBusy, setDraftBusy] = useState(false);
  const [savedIds, setSavedIds] = useState<string[]>([]);
  const [draftMessage, setDraftMessage] = useState<{
    id: string;
    kind: "ok" | "err";
    text: string;
  } | null>(null);

  function switchView(next: HistoryView) {
    setView(next);
    try {
      localStorage.setItem("workbench.historyView", next);
    } catch {
      // 忽略本地存储写入失败。
    }
  }

  async function load() {
    try {
      const body = await apiGet<{ items: HistoryRecord[] }>("/api/history");
      setItems(body.items);
      let jump: string | null = null;
      try {
        jump = localStorage.getItem("workbench.jumpHistory");
      } catch {
        // 忽略本地存储读取失败。
      }
      if (jump) {
        if (body.items.some((record) => record.prompt_id === jump)) {
          setOpenId(jump);
        }
        try {
          localStorage.removeItem("workbench.jumpHistory");
        } catch {
          // 忽略本地存储写入失败。
        }
      }
      setError("");
    } catch (err) {
      setError(`读取历史失败：${String(err)}`);
      setItems([]);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  function startDraft(record: HistoryRecord) {
    setDraftingId(record.prompt_id);
    setDraftName(autoDraftName(record));
    setDraftMessage(null);
  }

  function cancelDraft() {
    setDraftingId(null);
    setDraftName("");
    setDraftMessage(null);
  }

  async function saveAsDraft(record: HistoryRecord) {
    const name = draftName.trim();
    if (!name) {
      setDraftMessage({ id: record.prompt_id, kind: "err", text: "请填写草稿名称。" });
      return;
    }
    if (!recordHasPrompt(record)) {
      setDraftMessage({
        id: record.prompt_id,
        kind: "err",
        text: "这条历史没有可保存的 Prompt。",
      });
      return;
    }
    setDraftBusy(true);
    setDraftMessage(null);
    try {
      const note = `来自历史 ${record.prompt_id} · ${formatTime(record.created_at)}`;
      await apiPost(`/api/workflows/${record.workflow_id}/drafts`, {
        name,
        positive: record.positive_prompt ?? "",
        negative: record.negative_prompt ?? "",
        note,
        source_history_id: record.prompt_id,
      });
      setSavedIds((prev) =>
        prev.includes(record.prompt_id) ? prev : [...prev, record.prompt_id],
      );
      setDraftingId(null);
      setDraftName("");
      setDraftMessage({
        id: record.prompt_id,
        kind: "ok",
        text: "已存为草稿（未写入工作副本）。",
      });
    } catch (err) {
      setDraftMessage({
        id: record.prompt_id,
        kind: "err",
        text: `保存草稿失败：${String(err)}`,
      });
    } finally {
      setDraftBusy(false);
    }
  }

  function goToWorkbench() {
    window.dispatchEvent(
      new CustomEvent("workbench:navigate", { detail: { page: "workflows" } }),
    );
  }

  const workflowOptions = Array.from(
    new Set((items || []).map((record) => record.workflow_id)),
  );

  function exportHistory() {
    const payload = {
      exported_at: new Date().toISOString(),
      count: filtered.length,
      records: filtered,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const stamp = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 12);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `workbench-history-${stamp}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  const keywordTerm = keyword.trim().toLowerCase();
  const filtered = (items || []).filter((record) => {
    if (statusFilter && record.task_status !== statusFilter) return false;
    if (workflowFilter && record.workflow_id !== workflowFilter) return false;
    const day = record.created_at.slice(0, 10);
    if (fromDate && day < fromDate) return false;
    if (toDate && day > toDate) return false;
    if (keywordTerm) {
      const haystack = [
        record.positive_prompt,
        record.negative_prompt,
        JSON.stringify(record.model_snapshot),
      ]
        .join(" ")
        .toLowerCase();
      if (!haystack.includes(keywordTerm)) return false;
    }
    return true;
  });

  function renderRecord(record: HistoryRecord) {
    const open = openId === record.prompt_id;
    const checkpoints = snapshotFiles(record.model_snapshot, "checkpoints");
    const loras = snapshotFiles(record.model_snapshot, "loras");
    const images = record.images || [];
    return (
      <div className="rule-row" key={record.prompt_id}>
        <div className="rule-row-main">
          <strong>{summarize(record.positive_prompt)}</strong>
          <small>
            {formatTime(record.created_at)} · 工作流 {record.workflow_id.slice(0, 8)}
            {checkpoints.length > 0 && ` · ${checkpoints.join("、")}`}
            {loras.length > 0 && ` · LoRA ${loras.join("、")}`}
          </small>
          {record.last_error && (
            <small className="workflow-warning">{record.last_error}</small>
          )}
        </div>
        <div className="rule-row-meta">
          <span className={`compare-badge ${record.task_status}`}>
            {STATUS_LABEL[record.task_status] ?? record.task_status}
          </span>
          <button
            onClick={() => setOpenId(open ? null : record.prompt_id)}
          >
            {open ? "收起" : "详情"}
          </button>
        </div>

        {open && (
          <div className="profile-preview" style={{ width: "100%" }}>
            <div className="rule-row">
              <div className="rule-row-main">
                <strong>正向 Prompt</strong>
                <small>{record.positive_prompt || "—"}</small>
              </div>
            </div>
            <div className="rule-row">
              <div className="rule-row-main">
                <strong>负向 Prompt</strong>
                <small>{record.negative_prompt || "—"}</small>
              </div>
            </div>
            <div className="rule-row">
              <div className="rule-row-main">
                <strong>模型快照</strong>
                <small>
                  {[
                    `Checkpoint：${checkpoints.join("、") || "—"}`,
                    `LoRA：${loras.join("、") || "—"}`,
                    `VAE：${snapshotFiles(record.model_snapshot, "vaes").join("、") || "—"}`,
                    `CLIP：${snapshotFiles(record.model_snapshot, "clips").join("、") || "—"}`,
                  ].join(" · ")}
                </small>
              </div>
            </div>
            <div className="rule-row">
              <div className="rule-row-main">
                <strong>采样参数</strong>
                <small>
                  {[
                    `分辨率：${record.model_snapshot.resolution || "—"}`,
                    `Clip Skip：${
                      record.model_snapshot.clip_skip ?? "—"
                    }`,
                    `采样器：${samplerSummary(record.model_snapshot.samplers)}`,
                  ].join(" · ")}
                </small>
              </div>
            </div>
            {record.linked_draft && (
              <div className="rule-row">
                <div className="rule-row-main">
                  <strong>关联草稿</strong>
                  <small>
                    <button
                      className="secondary"
                      onClick={goToWorkbench}
                      title="跳转到工作流工作区查看草稿"
                    >
                      {record.linked_draft.name}
                    </button>
                  </small>
                </div>
              </div>
            )}
            {images.length > 0 && (
              <div className="rule-row">
                <div className="rule-row-main">
                  <strong>输出图片</strong>
                  <div className="history-images">
                    {images.map((image) => (
                      <figure key={`${image.subfolder}/${image.filename}`}>
                        {image.exists === true ? (
                          <img
                            src={historyImageUrl(image)}
                            alt={image.filename}
                            loading="lazy"
                          />
                        ) : (
                          <small className="muted">
                            {image.filename}（{existenceLabel(image)}）
                          </small>
                        )}
                        <figcaption>{image.filename}</figcaption>
                      </figure>
                    ))}
                  </div>
                </div>
              </div>
            )}
            <div className="rule-row">
              <div className="rule-row-main">
                {savedIds.includes(record.prompt_id) ? (
                  <small className="workflow-meta">已存为草稿</small>
                ) : !recordHasPrompt(record) ? (
                  <small className="muted">无 Prompt，无法存为草稿</small>
                ) : draftingId === record.prompt_id ? (
                  <div className="actions">
                    <input
                      type="text"
                      placeholder="草稿名称"
                      value={draftName}
                      disabled={draftBusy}
                      onChange={(event) => setDraftName(event.target.value)}
                    />
                    <button
                      onClick={() => void saveAsDraft(record)}
                      disabled={draftBusy}
                    >
                      确认保存
                    </button>
                    <button onClick={cancelDraft} disabled={draftBusy}>
                      取消
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => startDraft(record)}
                    disabled={draftBusy}
                  >
                    存为草稿
                  </button>
                )}
                {draftMessage && draftMessage.id === record.prompt_id && (
                  <small
                    className={
                      draftMessage.kind === "ok"
                        ? "workflow-meta"
                        : "workflow-warning"
                    }
                  >
                    {draftMessage.text}
                  </small>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <h2>生成历史</h2>
          <p>提交时刻固化的 Prompt 与模型快照；图片只记录文件名与存在性，不复制原图。</p>
        </div>
        <div className="actions">
          {VIEW_OPTIONS.map((option) => (
            <button
              key={option.key}
              onClick={() => switchView(option.key)}
              disabled={filtered.length === 0}
              className={view === option.key ? "active" : ""}
            >
              {option.label}视图
            </button>
          ))}
          <button onClick={exportHistory} disabled={filtered.length === 0}>
            导出 JSON
          </button>
          <button onClick={() => void load()} disabled={items === null}>
            刷新
          </button>
        </div>
      </div>

      {error && <p className="workflow-warning">{error}</p>}

      {items !== null && items.length > 0 && (
        <div className="history-filters">
          <label>
            状态
            <select
              value={statusFilter}
              onChange={(event) => {
                setStatusFilter(event.target.value);
                persistFilter("workbench.historyStatus", event.target.value);
              }}
            >
              <option value="">全部</option>
              {STATUS_OPTIONS.map((status) => (
                <option key={status} value={status}>
                  {STATUS_LABEL[status] ?? status}
                </option>
              ))}
            </select>
          </label>
          {workflowOptions.length > 1 && (
            <label>
              工作流
              <select
                value={workflowFilter}
                onChange={(event) => {
                  setWorkflowFilter(event.target.value);
                  persistFilter("workbench.historyWorkflow", event.target.value);
                }}
              >
                <option value="">全部</option>
                {workflowOptions.map((workflowId) => (
                  <option key={workflowId} value={workflowId}>
                    {workflowId.slice(0, 8)}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label>
            关键词
            <input
              type="text"
              value={keyword}
              placeholder="Prompt 或模型文件名"
              onChange={(event) => setKeyword(event.target.value)}
            />
          </label>
          <label>
            开始日期
            <input
              type="date"
              value={fromDate}
              onChange={(event) => setFromDate(event.target.value)}
            />
          </label>
          <label>
            结束日期
            <input
              type="date"
              value={toDate}
              onChange={(event) => setToDate(event.target.value)}
            />
          </label>
        </div>
      )}

      {items === null ? (
        <p>正在读取历史…</p>
      ) : items.length === 0 ? (
        <p className="catalog-empty">暂无生成历史。</p>
      ) : filtered.length === 0 ? (
        <p className="catalog-empty">没有符合筛选条件的历史记录。</p>
      ) : view === "timeline" ? (
        <div className="history-timeline">
          {groupByDay(filtered).map((group) => (
            <div className="timeline-group" key={group.day}>
              <div className="timeline-date">{group.day}</div>
              <div className="rule-list">
                {group.items.map(renderRecord)}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className={view === "grid" ? "history-grid" : "rule-list"}>
          {filtered.map(renderRecord)}
        </div>
      )}
    </section>
  );
}
