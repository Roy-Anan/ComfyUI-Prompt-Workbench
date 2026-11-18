import { useEffect, useState } from "react";
import { apiGet } from "./api";

type HistoryImage = {
  node_id: string;
  filename: string;
  subfolder: string;
  type: string;
  exists: boolean | null;
};

type ModelFile = { node_id: string; file: string };

type ModelSnapshot = {
  checkpoints: ModelFile[];
  loras: ModelFile[];
  vaes: ModelFile[];
  clips: ModelFile[];
};

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

function snapshotFiles(snapshot: ModelSnapshot, key: keyof ModelSnapshot): string[] {
  return (snapshot[key] || []).map((entry) => entry.file).filter(Boolean);
}

function existenceLabel(image: HistoryImage): string {
  if (image.exists === null) return "目录未配置";
  return image.exists ? "存在" : "丢失";
}

function summarize(text: string | null, limit = 80): string {
  if (!text) return "—";
  return text.length > limit ? `${text.slice(0, limit)}…` : text;
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
  const [statusFilter, setStatusFilter] = useState("");
  const [workflowFilter, setWorkflowFilter] = useState("");
  const [keyword, setKeyword] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [view, setView] = useState<"list" | "grid">("list");

  async function load() {
    try {
      const body = await apiGet<{ items: HistoryRecord[] }>("/api/history");
      setItems(body.items);
      setError("");
    } catch (err) {
      setError(`读取历史失败：${String(err)}`);
      setItems([]);
    }
  }

  useEffect(() => {
    void load();
  }, []);

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
            {images.length > 0 && (
              <div className="rule-row">
                <div className="rule-row-main">
                  <strong>输出图片</strong>
                  <small>
                    {images
                      .map(
                        (image) =>
                          `${image.filename}（${existenceLabel(image)}）`,
                      )
                      .join("、")}
                  </small>
                </div>
              </div>
            )}
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
          <button
            onClick={() => setView(view === "list" ? "grid" : "list")}
            disabled={filtered.length === 0}
          >
            {view === "list" ? "网格视图" : "列表视图"}
          </button>
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
              onChange={(event) => setStatusFilter(event.target.value)}
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
                onChange={(event) => setWorkflowFilter(event.target.value)}
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
      ) : (
        <div className={view === "grid" ? "history-grid" : "rule-list"}>
          {filtered.map(renderRecord)}
        </div>
      )}
    </section>
  );
}
