import { useEffect, useRef, useState, type ChangeEvent } from "react";
import {
  apiDelete,
  apiGet,
  apiGetBlob,
  apiPost,
  apiPostBinary,
} from "./api";
import { formatStructured } from "./format";
import HistoryPanel from "./HistoryPanel";
import WorkflowWorkbench from "./WorkflowWorkbench";

type PageKey = "settings" | "workflows" | "history";

const PAGE_KEYS: PageKey[] = ["settings", "workflows", "history"];

function readStoredPage(): PageKey {
  try {
    const value = localStorage.getItem("workbench.activePage");
    if (PAGE_KEYS.includes(value as PageKey)) return value as PageKey;
  } catch {
    // 本地存储不可用时回落到默认页签。
  }
  return "settings";
}

type Theme = "dark" | "light";
type FontSize = "small" | "normal" | "large";

function systemTheme(): Theme {
  try {
    return window.matchMedia("(prefers-color-scheme: light)").matches
      ? "light"
      : "dark";
  } catch {
    return "dark";
  }
}

function readStoredTheme(): Theme {
  try {
    const value = localStorage.getItem("workbench.theme");
    if (value === "dark" || value === "light") return value;
  } catch {
    // 本地存储不可用时跟随系统。
  }
  return systemTheme();
}

function readStoredFont(): FontSize {
  try {
    const value = localStorage.getItem("workbench.font");
    if (value === "small" || value === "normal" || value === "large") return value;
  } catch {
    // 本地存储不可用时回落到标准字号。
  }
  return "normal";
}

type Health = {
  ok: boolean;
  app: string;
  version: string;
  python: string;
  platform: string;
};

type ServiceResult = {
  online: boolean;
  status_code: number | null;
  url: string;
  error: string | null;
};

type ServiceStatus = {
  ollama: ServiceResult;
  comfyui: ServiceResult;
};

type ComfyDevice = {
  index: number | null;
  name: string | null;
  type: string | null;
  vram_total: number | null;
  vram_free: number | null;
};

type ComfyStatus = {
  online: boolean;
  error: string | null;
  version: string | null;
  pytorch_version: string | null;
  ram_total: number | null;
  ram_free: number | null;
  devices: ComfyDevice[];
};

type ComfyQueue = {
  online: boolean;
  error: string | null;
  running: string[];
  pending: string[];
  history: string[];
};

function formatGiB(bytes: number | null): string {
  if (bytes === null || Number.isNaN(bytes) || bytes < 0) return "—";
  return `${(bytes / 1024 ** 3).toFixed(1)} GB`;
}

type Settings = {
  storage: Record<string, string>;
  connections: {
    ollama_url: string;
    comfyui_url: string;
  };
};

type PathCheck = {
  path: string;
  exists: boolean;
  is_directory: boolean;
  writable: boolean;
};

type IdentityCopy = {
  relative_name: string;
  absolute_path: string;
  on_disk: boolean;
};

type IdentitySummary = {
  known: boolean;
  on_disk?: boolean;
  size_bytes?: number | null;
  sha256?: string | null;
  hashed?: boolean;
  identity_key?: string | null;
  copy_count?: number;
  copies?: IdentityCopy[];
};

type LoraMetaStatus = "complete" | "partial" | "empty" | "missing" | "unreadable";

type LoraCombo = { name: string; trigger_words: string[] };

type LoraMeta = {
  name: string;
  status: LoraMetaStatus;
  has_json: boolean;
  trigger_words: string[];
  description: string;
  base_model: string;
  source?: "manual" | "sidecar" | "none";
  manual_present?: boolean;
  manual_unreadable?: boolean;
  combos?: LoraCombo[];
};

type CatalogEntry = {
  name: string;
  on_disk: boolean | null;
  identity?: IdentitySummary;
  meta?: LoraMeta | null;
};

const LORA_META_LABEL: Record<LoraMetaStatus, string> = {
  complete: "资料完整",
  partial: "部分资料",
  empty: "资料为空",
  missing: "缺资料",
  unreadable: "资料不可读",
};

const LORA_SOURCE_LABEL: Record<"manual" | "sidecar" | "none", string> = {
  manual: "手动资料",
  sidecar: "自动扫描",
  none: "无资料",
};

type ModelCatalog = {
  online: boolean;
  error: string | null;
  checkpoints: CatalogEntry[];
  clips: CatalogEntry[];
  vaes: CatalogEntry[];
  loras: CatalogEntry[];
};

type RuleRecord = {
  id: number;
  level: string;
  scope_key: string | null;
  rule_key: string;
  value: unknown;
  structured: unknown;
  provenance: string;
  confidence: string;
  version: string;
  note: string;
};

type RuleHistoryItem = {
  history_id: number;
  level: string;
  scope_key: string | null;
  rule_key: string;
  value: unknown;
  structured: unknown;
  provenance: string;
  confidence: string;
  version: string;
  note: string;
  snapshot_at: string;
  reason: string;
};

type ProfileCandidate = {
  level: string;
  scope_key: string | null;
  rule_key: string;
  value: unknown;
  structured: unknown;
  provenance: string;
  confidence: string;
  version: string;
  note: string;
};

type ProfileSummary = {
  file: string;
  filename: string | null;
  display_name: string | null;
  architecture: string | null;
  candidates: number;
  unknown_fields: string[];
  error: string | null;
};

type ProfilePreview = {
  file: string;
  filename: string | null;
  architecture: string | null;
  unknown_fields: string[];
  candidates: ProfileCandidate[];
};

type ProfileImportRejected = {
  rule_key: string;
  reason: string;
};

type ProfileImportReport = {
  file: string;
  filename: string;
  imported: number;
  rejected: ProfileImportRejected[];
  unknown_fields: string[];
  selected: boolean;
  unknown_keys: string[];
};

function profileCandidateKey(candidate: ProfileCandidate): string {
  return [candidate.level, candidate.scope_key || "", candidate.rule_key].join(
    "\u001f",
  );
}

const RULE_LEVEL_LABEL: Record<string, string> = {
  checkpoint: "模型档案",
  architecture: "架构基线",
  global: "全局规则",
};
const RULE_PROVENANCE_LABEL: Record<string, string> = {
  author: "作者",
  verified_mirror: "已核实镜像",
  community: "社区",
  local_test: "本机测试",
  unverified: "未核实",
};
const RULE_CONFIDENCE_LABEL: Record<string, string> = {
  authoritative: "权威",
  partial: "部分",
  unverified: "未核实",
};
const RULE_LEVEL_ORDER = ["checkpoint", "architecture", "global"];

const storageLabels: Record<string, string> = {
  root: "工作台数据根目录（固定）",
  database: "数据库目录",
  knowledge: "模型知识库",
  prompts: "Prompt 规则",
  workflows: "工作流资料",
  drafts: "草稿与版本",
  history: "历史记录",
  cache: "缓存",
  logs: "日志",
  backups: "备份",
  exports: "导入导出",
  checkpoint: "Checkpoint 模型目录（只读扫描）",
  lora: "LoRA 模型目录（只读扫描）",
  clip: "CLIP 模型目录（只读扫描）",
  vae: "VAE 模型目录（只读扫描）",
};

// Optional external ComfyUI model directories: read-only scanned, never
// created by the workbench and never copied into the data root.
const EXTERNAL_STORAGE_KEYS = ["checkpoint", "lora", "clip", "vae"];

function isExternalStorageKey(key: string): boolean {
  return EXTERNAL_STORAGE_KEYS.includes(key);
}

function diskLabel(onDisk: boolean | null): string {
  if (onDisk === null) return "目录未配置";
  return onDisk ? "本机存在" : "本机未找到";
}

function formatRuleValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function formatSize(bytes?: number | null): string {
  if (bytes === null || bytes === undefined) return "";
  if (bytes >= 1024 * 1024 * 1024) {
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  }
  if (bytes >= 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
  return `${bytes} B`;
}

function identityLabel(entry: CatalogEntry): string {
  const identity = entry.identity;
  if (!identity || !identity.known) return diskLabel(entry.on_disk);
  const size = formatSize(identity.size_bytes);
  const digest = identity.hashed ? "已校验" : "未哈希";
  return [size, digest].filter(Boolean).join(" · ");
}

function StatusDot({ online }: { online: boolean }) {
  return (
    <span
      className={`dot ${online ? "online" : "offline"}`}
      aria-label={online ? "在线" : "离线"}
    />
  );
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [services, setServices] = useState<ServiceStatus | null>(null);
  const [comfyStatus, setComfyStatus] = useState<ComfyStatus | null>(null);
  const [comfyQueue, setComfyQueue] = useState<ComfyQueue | null>(null);
  const [catalog, setCatalog] = useState<ModelCatalog | null>(null);
  const [rules, setRules] = useState<RuleRecord[] | null>(null);
  const [profiles, setProfiles] = useState<ProfileSummary[] | null>(null);
  const [openProfile, setOpenProfile] = useState<string | null>(null);
  const [preview, setPreview] = useState<ProfilePreview | null>(null);
  const settingsFileRef = useRef<HTMLInputElement>(null);
  const backupFileRef = useRef<HTMLInputElement>(null);
  const [restoreFile, setRestoreFile] = useState<File | null>(null);
  const [restoreOverwrite, setRestoreOverwrite] = useState(false);
  const [importingProfile, setImportingProfile] = useState<string | null>(null);
  const [deletingRule, setDeletingRule] = useState<string | null>(null);
  const [openRuleHistory, setOpenRuleHistory] = useState<string | null>(null);
  const [ruleHistory, setRuleHistory] = useState<RuleHistoryItem[]>([]);
  const [restoringHistory, setRestoringHistory] = useState<number | null>(null);
  const [importReports, setImportReports] = useState<
    Record<string, ProfileImportReport>
  >({});
  const [selectedByProfile, setSelectedByProfile] = useState<
    Record<string, string[]>
  >({});
  const [dismissedByProfile, setDismissedByProfile] = useState<
    Record<string, string[]>
  >({});
  const [checks, setChecks] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(true);
  const [message, setMessage] = useState("正在连接本地服务…");
  const [activePage, setActivePage] = useState<PageKey>(readStoredPage);
  const [theme, setTheme] = useState<Theme>(readStoredTheme);
  const [fontSize, setFontSize] = useState<FontSize>(readStoredFont);

  useEffect(() => {
    const root = document.documentElement;
    root.dataset.theme = theme;
    root.dataset.font = fontSize;
    try {
      localStorage.setItem("workbench.theme", theme);
      localStorage.setItem("workbench.font", fontSize);
    } catch {
      // 忽略本地存储写入失败。
    }
  }, [theme, fontSize]);

  function toggleTheme() {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  }

  function switchPage(page: PageKey) {
    setActivePage(page);
    try {
      localStorage.setItem("workbench.activePage", page);
    } catch {
      // 忽略本地存储写入失败。
    }
  }

  useEffect(() => {
    function onNavigate(event: Event) {
      const detail = (
        event as CustomEvent<{ page: PageKey; promptId?: string }>
      ).detail;
      if (detail && PAGE_KEYS.includes(detail.page)) {
        if (detail.promptId) {
          try {
            localStorage.setItem("workbench.jumpHistory", detail.promptId);
          } catch {
            // 忽略本地存储写入失败。
          }
        }
        switchPage(detail.page);
      }
    }
    window.addEventListener("workbench:navigate", onNavigate);
    return () => window.removeEventListener("workbench:navigate", onNavigate);
  }, []);

  async function refresh() {
    const [healthResult, settingsResult, serviceResult, catalogResult, ruleResult, profileResult] =
      await Promise.all([
        apiGet<Health>("/api/health"),
        apiGet<Settings>("/api/settings"),
        apiGet<ServiceStatus>("/api/services/status"),
        apiGet<ModelCatalog>("/api/models/catalog"),
        apiGet<{ items: RuleRecord[] }>("/api/rules"),
        apiGet<{ items: ProfileSummary[] }>("/api/profiles"),
      ]);

    setHealth(healthResult);
    setSettings(settingsResult);
    setServices(serviceResult);
    setCatalog(catalogResult);
    setRules(ruleResult.items);
    setProfiles(profileResult.items);

    // 显存与队列为只读摘要；独立容错，取不到置空，不影响主面板连接状态。
    apiGet<ComfyStatus>("/api/comfyui/status")
      .then(setComfyStatus)
      .catch(() => setComfyStatus(null));
    apiGet<ComfyQueue>("/api/comfyui/queue")
      .then(setComfyQueue)
      .catch(() => setComfyQueue(null));
  }

  useEffect(() => {
    let alive = true;

    async function connect() {
      try {
        await refresh();

        if (alive) {
          setMessage("本地服务已连接");
        }
      } catch (error) {
        if (alive) {
          setMessage(`连接失败：${String(error)}`);
        }
      } finally {
        if (alive) {
          setBusy(false);
        }
      }
    }

    void connect();

    return () => {
      alive = false;
    };
  }, []);

  async function refreshStatus() {
    setBusy(true);

    try {
      await refresh();
      setMessage("状态已刷新");
    } catch (error) {
      setMessage(`刷新失败：${String(error)}`);
    } finally {
      setBusy(false);
    }
  }

  async function checkPath(key: string) {
    if (!settings) return;

    const path = settings.storage[key]?.trim() ?? "";

    if (!path) {
      setChecks((old) => ({
        ...old,
        [key]: "路径为空",
      }));
      return;
    }

    setChecks((old) => ({
      ...old,
      [key]: "正在检查…",
    }));

    try {
      const result = await apiPost<PathCheck>(
        "/api/storage/validate",
        {
          path,
          create: !isExternalStorageKey(key),
        },
      );

      let status: string;

      if (
        result.exists &&
        result.is_directory &&
        result.writable
      ) {
        status = "目录存在且可写";
      } else {
        status =
          `存在：${result.exists}；` +
          `目录：${result.is_directory}；` +
          `可写：${result.writable}`;
      }

      setChecks((old) => ({
        ...old,
        [key]: status,
      }));
    } catch (error) {
      setChecks((old) => ({
        ...old,
        [key]: `检查失败：${String(error)}`,
      }));
    }
  }

  async function toggleProfile(file: string) {
    if (openProfile === file) {
      setOpenProfile(null);
      setPreview(null);
      return;
    }
    setOpenProfile(file);
    try {
      const detail = await apiGet<ProfilePreview>(
        `/api/profiles/${encodeURIComponent(file)}`,
      );
      setPreview(detail);
    } catch (error) {
      setPreview(null);
      setMessage(`档案预览失败：${String(error)}`);
    }
  }

  async function importProfile(file: string, selectedKeys?: string[]) {
    setImportingProfile(file);
    try {
      const body: Record<string, unknown> = { file_name: file };
      if (selectedKeys && selectedKeys.length > 0) {
        body.candidate_keys = selectedKeys;
      }
      const report = await apiPost<ProfileImportReport>(
        "/api/profiles/import",
        body,
      );
      setImportReports((old) => ({ ...old, [file]: report }));
      setSelectedByProfile((old) => ({ ...old, [file]: [] }));
      // Refresh rules and the profile summary after the write; the backend
      // validates each candidate and rejects invalid ones in the report.
      const [ruleResult, profileResult] = await Promise.all([
        apiGet<{ items: RuleRecord[] }>("/api/rules"),
        apiGet<{ items: ProfileSummary[] }>("/api/profiles"),
      ]);
      setRules(ruleResult.items);
      setProfiles(profileResult.items);
      const unknown = report.unknown_keys?.length
        ? `，${report.unknown_keys.length} 条未匹配被跳过`
        : "";
      setMessage(
        report.rejected.length > 0
          ? `档案已导入：${report.imported} 条入库，${report.rejected.length} 条被拒绝${unknown}。`
          : `档案已导入：${report.imported} 条规则入库${unknown}。`,
      );
    } catch (error) {
      setMessage(`档案导入失败：${String(error)}`);
    } finally {
      setImportingProfile(null);
    }
  }

  function toggleCandidateSelected(file: string, key: string) {
    setSelectedByProfile((old) => {
      const current = old[file] || [];
      const next = current.includes(key)
        ? current.filter((item) => item !== key)
        : [...current, key];
      return { ...old, [file]: next };
    });
  }

  function dismissSelectedCandidates(file: string) {
    const picked = selectedByProfile[file] || [];
    if (picked.length === 0) return;
    setDismissedByProfile((old) => ({
      ...old,
      [file]: [...new Set([...(old[file] || []), ...picked])],
    }));
    setSelectedByProfile((old) => ({ ...old, [file]: [] }));
    setMessage(`已驳回 ${picked.length} 条候选（仅本次预览忽略，未写入规则库）。`);
  }

  function ruleIdentity(rule: RuleRecord): string {
    return `${rule.level}::${rule.scope_key ?? ""}::${rule.rule_key}`;
  }

  async function copyLoraTriggers(meta: LoraMeta) {
    if (meta.trigger_words.length === 0) return;
    try {
      await navigator.clipboard.writeText(meta.trigger_words.join(", "));
      setMessage(`已复制「${meta.name}」触发词（未写入工作副本）。`);
    } catch (error) {
      setMessage(`复制触发词失败：${String(error)}`);
    }
  }

  async function removeRule(rule: RuleRecord) {
    const identity = ruleIdentity(rule);
    if (deletingRule !== identity) {
      // 两步确认第一步：进入确认态，不直接删除；不用原生弹窗。
      setDeletingRule(identity);
      return;
    }
    try {
      await apiDelete<{ removed: boolean }>("/api/rules", {
        level: rule.level,
        scope_key: rule.scope_key,
        rule_key: rule.rule_key,
      });
      const ruleResult = await apiGet<{ items: RuleRecord[] }>("/api/rules");
      setRules(ruleResult.items);
      setMessage("规则已删除。");
    } catch (error) {
      setMessage(`规则删除失败：${String(error)}`);
    } finally {
      setDeletingRule(null);
    }
  }

  async function loadRuleHistory(rule: RuleRecord) {
    const query = new URLSearchParams({
      level: rule.level,
      scope_key: rule.scope_key ?? "",
      rule_key: rule.rule_key,
    });
    const result = await apiGet<{ items: RuleHistoryItem[] }>(
      `/api/rules/history?${query.toString()}`,
    );
    setRuleHistory(result.items);
  }

  async function toggleRuleHistory(rule: RuleRecord) {
    const identity = ruleIdentity(rule);
    if (openRuleHistory === identity) {
      setOpenRuleHistory(null);
      setRuleHistory([]);
      return;
    }
    setOpenRuleHistory(identity);
    setRestoringHistory(null);
    try {
      await loadRuleHistory(rule);
    } catch (error) {
      setRuleHistory([]);
      setMessage(`读取规则历史失败：${String(error)}`);
    }
  }

  async function restoreRuleHistory(rule: RuleRecord, item: RuleHistoryItem) {
    if (restoringHistory !== item.history_id) {
      // 两步确认第一步：进入确认态，不直接回退；不用原生弹窗。
      setRestoringHistory(item.history_id);
      return;
    }
    try {
      await apiPost<RuleRecord>(
        `/api/rules/history/${item.history_id}/restore`,
        {},
      );
      const ruleResult = await apiGet<{ items: RuleRecord[] }>("/api/rules");
      setRules(ruleResult.items);
      await loadRuleHistory(rule);
      setMessage(`已回退到 v${item.version}。`);
    } catch (error) {
      setMessage(`规则回退失败：${String(error)}`);
    } finally {
      setRestoringHistory(null);
    }
  }

  async function saveSettings() {
    if (!settings) return;

    setBusy(true);

    try {
      const { root: _fixedRoot, ...editableStorage } =
        settings.storage;

      const updated = await apiPost<Settings>(
        "/api/settings",
        {
          storage: editableStorage,
          connections: settings.connections,
        },
      );

      setSettings(updated);
      setMessage("设置已保存");
    } catch (error) {
      setMessage(`保存失败：${String(error)}`);
    } finally {
      setBusy(false);
    }
  }

  async function exportDiagnostics() {
    setBusy(true);
    try {
      const report = await apiGet<Record<string, unknown>>("/api/diagnostics");
      const blob = new Blob([JSON.stringify(report, null, 2)], {
        type: "application/json;charset=utf-8",
      });
      const url = URL.createObjectURL(blob);
      const stamp = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 12);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `workbench-diagnostics-${stamp}.json`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setMessage("诊断报告已导出（仅本地，未上传）。");
    } catch (error) {
      setMessage(`导出诊断报告失败：${String(error)}`);
    } finally {
      setBusy(false);
    }
  }

  function exportSettings() {
    if (!settings) return;
    // 只导出白名单配置（本地路径与回环连接地址）；不含模型权重、原图、历史记录或遗留杂项。
    const payload = {
      version: 2,
      storage: settings.storage,
      connections: settings.connections,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const stamp = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 12);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `workbench-settings-${stamp}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    setMessage("设置已导出（仅本地，未上传；不含模型权重与原图）。");
  }

  async function exportBackup() {
    setBusy(true);
    try {
      const blob = await apiGetBlob("/api/backup/export");
      const url = URL.createObjectURL(blob);
      const stamp = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 12);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `workbench-backup-${stamp}.zip`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setMessage("整库备份已导出（仅本地 ZIP；不含模型权重与原图）。");
    } catch (error) {
      setMessage(`导出整库备份失败：${String(error)}`);
    } finally {
      setBusy(false);
    }
  }

  function pickBackupFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setRestoreOverwrite(false);
    setRestoreFile(file);
  }

  async function confirmRestore() {
    if (!restoreFile) return;
    setBusy(true);
    try {
      const buffer = await restoreFile.arrayBuffer();
      const query = restoreOverwrite ? "?overwrite=true" : "";
      const report = await apiPostBinary(`/api/backup/restore${query}`, buffer);
      const restored = Number(report.restored_count ?? 0);
      const skipped = Number(
        (report.skipped_existing as unknown[] | undefined)?.length ?? 0,
      );
      const overwritten = Number(report.overwritten_count ?? 0);
      setMessage(
        `恢复完成：写入 ${restored} 项，保留现有 ${skipped} 项，覆盖 ${overwritten} 项；` +
          `恢复前备份：${String(report.pre_backup ?? "")}。建议刷新页面。`,
      );
      setRestoreFile(null);
    } catch (error) {
      setMessage(`恢复失败：${String(error)}`);
    } finally {
      setBusy(false);
    }
  }

  function cancelRestore() {
    setRestoreFile(null);
    setRestoreOverwrite(false);
  }

  function importSettingsFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !settings) return;

    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(String(reader.result)) as Record<string, unknown>;
        if (
          typeof parsed !== "object" ||
          parsed === null ||
          Array.isArray(parsed)
        ) {
          throw new Error("设置文件根节点必须是对象");
        }

        const incomingConnections =
          (parsed.connections as Record<string, unknown>) ?? {};
        const incomingStorage =
          (parsed.storage as Record<string, unknown>) ?? {};

        const nextConnections = { ...settings.connections };
        let applied = 0;

        for (const key of ["ollama_url", "comfyui_url"] as const) {
          const value = incomingConnections[key];
          if (typeof value === "string" && /^https?:\/\//.test(value.trim())) {
            nextConnections[key] = value.trim().replace(/\/+$/, "");
            applied += 1;
          }
        }

        const nextStorage = { ...settings.storage };
        for (const key of EXTERNAL_STORAGE_KEYS) {
          const value = incomingStorage[key];
          if (typeof value === "string") {
            nextStorage[key] = value.trim();
            applied += 1;
          }
        }

        // Managed storage paths and root are rebuilt against the current data
        // root; values from the imported file are not trusted for those keys.
        setSettings({
          ...settings,
          storage: nextStorage,
          connections: nextConnections,
        });
        setMessage(
          applied > 0
            ? `已从文件载入 ${applied} 项配置；请检查后点「保存设置」落库。`
            : "文件中没有可采信的连接地址或外部模型目录。",
        );
      } catch (error) {
        setMessage(`设置导入失败：${String(error)}`);
      }
    };
    reader.onerror = () => setMessage("设置导入失败：无法读取文件。");
    reader.readAsText(file);
  }

  function updateStorage(key: string, value: string) {
    if (!settings || key === "root") return;

    setSettings({
      ...settings,
      storage: {
        ...settings.storage,
        [key]: value,
      },
    });

    setChecks((old) => ({
      ...old,
      [key]: "路径已修改，请重新检查",
    }));
  }

  function updateConnection(
    key: "ollama_url" | "comfyui_url",
    value: string,
  ) {
    if (!settings) return;

    setSettings({
      ...settings,
      connections: {
        ...settings.connections,
        [key]: value,
      },
    });
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <div className="eyebrow">LOCAL AI WORKSPACE</div>
          <h1>ComfyUI Prompt Workbench</h1>
          <p>本地提示词工作台 · M0 工程基础版</p>
        </div>

        <div className="topbar-controls">
          <button
            className="secondary"
            onClick={toggleTheme}
            title="切换深色/浅色主题"
          >
            {theme === "dark" ? "浅色" : "深色"}
          </button>
          <select
            value={fontSize}
            onChange={(event) => setFontSize(event.target.value as FontSize)}
            title="界面字号"
          >
            <option value="small">小字号</option>
            <option value="normal">标准字号</option>
            <option value="large">大字号</option>
          </select>
          <button
            onClick={refreshStatus}
            disabled={busy}
          >
            刷新状态
          </button>
        </div>
      </header>

      <nav className="page-nav">
        <button
          className={activePage === "settings" ? "" : "secondary"}
          onClick={() => switchPage("settings")}
        >
          服务与设置
        </button>
        <button
          className={activePage === "workflows" ? "" : "secondary"}
          onClick={() => switchPage("workflows")}
        >
          工作流工作区
        </button>
        <button
          className={activePage === "history" ? "" : "secondary"}
          onClick={() => switchPage("history")}
        >
          生成历史
        </button>
      </nav>

      {activePage === "workflows" ? (
        <WorkflowWorkbench
          comfyuiUrl={settings?.connections.comfyui_url ?? ""}
        />
      ) : activePage === "history" ? (
        <HistoryPanel />
      ) : (
        <>
      <section className="status-grid">
        <article className="panel status-card">
          <div className="card-title">工作台本地服务</div>
          <div className="status-line">
            <StatusDot online={health?.ok === true} />
            <strong>
              {health?.ok ? "已连接" : "未连接"}
            </strong>
          </div>
          <small>
            {health
              ? `Python ${health.python}`
              : message}
          </small>
        </article>

        <article className="panel status-card">
          <div className="card-title">Ollama</div>
          <div className="status-line">
            <StatusDot
              online={services?.ollama.online === true}
            />
            <strong>
              {services?.ollama.online ? "在线" : "未连接"}
            </strong>
          </div>
          <small>
            {settings?.connections.ollama_url ?? "等待读取设置"}
          </small>
        </article>

        <article className="panel status-card">
          <div className="card-title">ComfyUI</div>
          <div className="status-line">
            <StatusDot
              online={services?.comfyui.online === true}
            />
            <strong>
              {services?.comfyui.online ? "在线" : "未连接"}
            </strong>
          </div>
          <small>
            {settings?.connections.comfyui_url ?? "等待读取设置"}
          </small>
          {comfyStatus?.version ? (
            <small>版本 {comfyStatus.version}</small>
          ) : null}
          {comfyStatus?.online === true && comfyStatus.devices.length > 0 ? (
            comfyStatus.devices.map((device) => (
              <small key={device.index ?? device.name ?? "device"}>
                {device.name ?? device.type ?? `设备 ${device.index ?? "?"}`}
                ：显存 {formatGiB(device.vram_free)} 空闲 /{" "}
                {formatGiB(device.vram_total)}
              </small>
            ))
          ) : comfyStatus?.online === true ? (
            <small>显存信息未知</small>
          ) : null}
          <small>
            {comfyQueue?.online === true
              ? `队列：运行中 ${comfyQueue.running.length} · 待执行 ${comfyQueue.pending.length}`
              : "队列状态未知"}
          </small>
        </article>
      </section>

      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>存储位置</h2>
            <p>
              根目录由本地宿主固定。本版本只允许修改子目录，
              不会自动迁移已有数据。
            </p>
          </div>
        </div>

        {settings ? (
          <div className="path-list">
            {Object.entries(settings.storage).map(
              ([key, value]) => {
                const fixed = key === "root";
                const optional = isExternalStorageKey(key);

                return (
                  <div className="path-row" key={key}>
                    <label className="path-field">
                      <span>
                        {storageLabels[key] ?? key}
                      </span>

                      <input
                        value={value}
                        readOnly={fixed}
                        placeholder={
                          optional ? "可留空" : "请输入目录路径"
                        }
                        onChange={(event) =>
                          updateStorage(key, event.target.value)
                        }
                      />

                      {checks[key] && (
                        <small>{checks[key]}</small>
                      )}
                    </label>

                    <button
                      className="secondary"
                      disabled={fixed || busy}
                      onClick={() => void checkPath(key)}
                    >
                      检查
                    </button>
                  </div>
                );
              },
            )}
          </div>
        ) : (
          <p>正在读取存储配置…</p>
        )}
      </section>

      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>模型清单（只读）</h2>
            <p>
              名单来自 ComfyUI 已加载的模型；勾选目录后可核对本机文件是否存在。
              这里不复制、不修改模型权重。
            </p>
          </div>
        </div>

        {catalog ? (
          catalog.online ? (
            <div className="catalog-grid">
              <div className="catalog-col">
                <div className="catalog-title">
                  Checkpoint（{catalog.checkpoints.length}）
                </div>
                <ul className="catalog-list">
                  {catalog.checkpoints.map((entry) => (
                    <li key={entry.name}>
                      <span>{entry.name}</span>
                      <small>{identityLabel(entry)}</small>
                    </li>
                  ))}
                  {catalog.checkpoints.length === 0 && (
                    <li className="catalog-empty">ComfyUI 未列出 Checkpoint</li>
                  )}
                </ul>
              </div>
              <div className="catalog-col">
                <div className="catalog-title">
                  LoRA（{catalog.loras.length}）
                </div>
                <ul className="catalog-list">
                  {catalog.loras.map((entry) => {
                    const meta = entry.meta ?? null;
                    const detail = [
                      meta?.base_model ? `底座：${meta.base_model}` : "",
                      meta && meta.trigger_words.length > 0
                        ? `触发：${meta.trigger_words.slice(0, 4).join("、")}`
                        : "",
                      meta?.description
                        ? `说明：${
                            meta.description.length > 60
                              ? `${meta.description.slice(0, 60)}…`
                              : meta.description
                          }`
                        : "",
                    ]
                      .filter(Boolean)
                      .join("　");
                    const source: "manual" | "sidecar" | "none" | null = meta
                      ? meta.source ?? (meta.manual_present ? "manual" : "sidecar")
                      : null;
                    const combos = meta?.combos ?? [];
                    return (
                      <li
                        key={entry.name}
                        className={meta ? `lora-meta lora-meta-${meta.status}` : "lora-meta"}
                      >
                        <span>
                          {entry.name}
                          {meta && (
                            <small className="lora-meta-status">
                              {LORA_META_LABEL[meta.status]}
                            </small>
                          )}
                          {source && (
                            <small className="lora-meta-source">
                              {LORA_SOURCE_LABEL[source]}
                            </small>
                          )}
                        </span>
                        <small>{identityLabel(entry)}</small>
                        {detail && <small className="lora-meta-detail">{detail}</small>}
                        {meta && meta.trigger_words.length > 0 && (
                          <div className="lora-triggers">
                            {meta.trigger_words.map((word) => (
                              <span key={word} className="lora-trigger-chip">
                                {word}
                              </span>
                            ))}
                            <button
                              type="button"
                              onClick={() => void copyLoraTriggers(meta)}
                            >
                              复制触发词
                            </button>
                          </div>
                        )}
                        {combos.length > 0 && (
                          <ul className="lora-combos">
                            {combos.map((combo, index) => (
                              <li key={index}>
                                {combo.name && <strong>{combo.name}：</strong>}
                                {combo.trigger_words.join("、")}
                              </li>
                            ))}
                          </ul>
                        )}
                      </li>
                    );
                  })}
                  {catalog.loras.length === 0 && (
                    <li className="catalog-empty">ComfyUI 未列出 LoRA</li>
                  )}
                </ul>
              </div>
              <div className="catalog-col">
                <div className="catalog-title">
                  CLIP（{catalog.clips.length}）
                </div>
                <ul className="catalog-list">
                  {catalog.clips.map((entry) => (
                    <li key={entry.name}>
                      <span>{entry.name}</span>
                      <small>{identityLabel(entry)}</small>
                    </li>
                  ))}
                  {catalog.clips.length === 0 && (
                    <li className="catalog-empty">ComfyUI 未列出 CLIP</li>
                  )}
                </ul>
              </div>
              <div className="catalog-col">
                <div className="catalog-title">
                  VAE（{catalog.vaes.length}）
                </div>
                <ul className="catalog-list">
                  {catalog.vaes.map((entry) => (
                    <li key={entry.name}>
                      <span>{entry.name}</span>
                      <small>{identityLabel(entry)}</small>
                    </li>
                  ))}
                
                  {catalog.vaes.length === 0 && (
                    <li className="catalog-empty">ComfyUI 未列出 VAE</li>
                  )}
                </ul>
              </div>
            </div>
          ) : (
            <p className="catalog-offline">
              模型清单不可用：{catalog.error ?? "ComfyUI 未连接"}
            </p>
          )
        ) : (
          <p>正在读取模型清单…</p>
        )}
      </section>

      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>规则库</h2>
            <p>
              规则记录来自档案导入；可删除已入库规则做纠错。
              前端不提供手动新增或修改，新增与覆盖仍走档案导入。
            </p>
          </div>
        </div>

        {rules === null ? (
          <p>正在读取规则库…</p>
        ) : rules.length === 0 ? (
          <p className="catalog-empty">规则库为空。</p>
        ) : (
          RULE_LEVEL_ORDER.map((level) => {
            const group = rules.filter((rule) => rule.level === level);
            if (group.length === 0) return null;
            return (
              <div className="rule-group" key={level}>
                <div className="catalog-title">
                  {RULE_LEVEL_LABEL[level] ?? level}（{group.length}）
                </div>
                <div className="rule-list">
                  {group.map((rule) => {
                    const identity = ruleIdentity(rule);
                    const historyOpen = openRuleHistory === identity;
                    return (
                      <div className="rule-row-wrap" key={rule.id}>
                        <div className="rule-row">
                          <div className="rule-row-main">
                            <strong>{rule.rule_key}</strong>
                            <small>
                              {rule.scope_key || "全局"} · 值：
                              {formatRuleValue(rule.value)}
                              {rule.structured
                                ? ` · 结构：${formatStructured(rule.structured)}`
                                : ""}
                              {rule.note ? ` · 备注：${rule.note}` : ""}
                            </small>
                          </div>
                          <div className="rule-row-meta">
                            <span className="rule-tag">
                              {RULE_PROVENANCE_LABEL[rule.provenance] ??
                                rule.provenance}
                            </span>
                            <span className="rule-tag">
                              {RULE_CONFIDENCE_LABEL[rule.confidence] ??
                                rule.confidence}
                            </span>
                            <span className="rule-tag">v{rule.version}</span>
                            <button
                              onClick={() => void toggleRuleHistory(rule)}
                            >
                              {historyOpen ? "收起历史" : "历史版本"}
                            </button>
                            <button
                              onClick={() => void removeRule(rule)}
                              className={
                                deletingRule === identity ? "danger" : ""
                              }
                            >
                              {deletingRule === identity
                                ? "确认删除？"
                                : "删除"}
                            </button>
                          </div>
                        </div>
                        {historyOpen && (
                          <div className="rule-history">
                            {ruleHistory.length === 0 ? (
                              <p className="catalog-empty">暂无历史版本。</p>
                            ) : (
                              ruleHistory.map((item) => (
                                <div className="rule-history-item" key={item.history_id}>
                                  <div className="rule-row-main">
                                    <small>
                                      <span className="rule-tag">v{item.version}</span>{" "}
                                      {formatRuleValue(item.value)}
                                      {item.note ? ` · 备注：${item.note}` : ""}
                                      {item.reason === "restore"
                                        ? " · 由回退归档"
                                        : ""}
                                    </small>
                                    <small className="rule-history-time">
                                      {item.snapshot_at.replace("T", " ").slice(0, 19)}
                                    </small>
                                  </div>
                                  <div className="rule-row-meta">
                                    <button
                                      onClick={() => void restoreRuleHistory(rule, item)}
                                      className={
                                        restoringHistory === item.history_id
                                          ? "danger"
                                          : ""
                                      }
                                    >
                                      {restoringHistory === item.history_id
                                        ? "确认回退？"
                                        : "回退到此版本"}
                                    </button>
                                  </div>
                                </div>
                              ))
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })
        )}
      </section>

      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>旧档案候选</h2>
            <p>
              名单来自 legacy 档案文本解析；可整档导入为规则，落库前由后端逐条校验，
              非法候选在报告中拒绝。逐候选勾选 / 驳回与差异预览留后续版本。
            </p>
          </div>
        </div>

        {profiles === null ? (
          <p>正在读取旧档案…</p>
        ) : profiles.length === 0 ? (
          <p className="catalog-empty">未发现旧档案。</p>
        ) : (
          <div className="rule-list">
            {profiles.map((profile) => {
              const expanded = openProfile === profile.file;
              return (
                <div className="rule-row" key={profile.file}>
                  <div className="rule-row-main">
                    <button
                      className="profile-toggle"
                      onClick={() => void toggleProfile(profile.file)}
                      disabled={Boolean(profile.error)}
                    >
                      <strong>
                        {profile.filename ?? profile.display_name ?? profile.file}
                      </strong>
                      <small>
                        {profile.architecture ?? "架构未识别"} · 候选{" "}
                        {profile.candidates} · 未识别{" "}
                        {profile.unknown_fields.length}
                      </small>
                    </button>
                    {profile.error && (
                      <small className="catalog-empty">
                        解析失败：{profile.error}
                      </small>
                    )}
                    {expanded && preview && preview.file === profile.file && (
                      <div className="profile-preview">
                        {(() => {
                          const dismissed = new Set(
                            dismissedByProfile[profile.file] || [],
                          );
                          const visibleCandidates = preview.candidates.filter(
                            (candidate) =>
                              !dismissed.has(profileCandidateKey(candidate)),
                          );
                          const selected = selectedByProfile[profile.file] || [];
                          const busy = importingProfile === profile.file;
                          if (visibleCandidates.length === 0) {
                            return (
                              <p className="catalog-empty">
                                无可导入候选（其余已在本次预览驳回）。
                              </p>
                            );
                          }
                          return (
                            <>
                              {visibleCandidates.map((candidate, index) => {
                                const key = profileCandidateKey(candidate);
                                const checked = selected.includes(key);
                                return (
                                  <div className="rule-row" key={key || index}>
                                    <label className="rule-row-check">
                                      <input
                                        type="checkbox"
                                        checked={checked}
                                        disabled={busy}
                                        onChange={() =>
                                          toggleCandidateSelected(
                                            profile.file,
                                            key,
                                          )
                                        }
                                      />
                                    </label>
                                    <div className="rule-row-main">
                                      <strong>{candidate.rule_key}</strong>
                                      <small>
                                        {RULE_LEVEL_LABEL[candidate.level] ??
                                          candidate.level}
                                        {candidate.scope_key
                                          ? ` · ${candidate.scope_key}`
                                          : " · 作用域待定"}
                                        {" · 值："}
                                        {formatRuleValue(candidate.value)}
                                        {candidate.structured
                                          ? ` · 结构：${formatStructured(candidate.structured)}`
                                          : ""}
                                        {candidate.note
                                          ? ` · 备注：${candidate.note}`
                                          : ""}
                                      </small>
                                    </div>
                                    <div className="rule-row-meta">
                                      <span className="rule-tag">
                                        {RULE_PROVENANCE_LABEL[candidate.provenance] ??
                                          candidate.provenance}
                                      </span>
                                      <span className="rule-tag">
                                        {RULE_CONFIDENCE_LABEL[candidate.confidence] ??
                                          candidate.confidence}
                                      </span>
                                      <span className="rule-tag">
                                        v{candidate.version}
                                      </span>
                                      <button
                                        type="button"
                                        disabled={busy}
                                        onClick={() =>
                                          void importProfile(profile.file, [
                                            key,
                                          ])
                                        }
                                      >
                                        导入此条
                                      </button>
                                    </div>
                                  </div>
                                );
                              })}
                              <div className="profile-import-actions">
                                <button
                                  type="button"
                                  disabled={busy || selected.length === 0}
                                  onClick={() =>
                                    void importProfile(profile.file, selected)
                                  }
                                >
                                  {busy
                                    ? "正在导入…"
                                    : `导入所选（${selected.length}）`}
                                </button>
                                <button
                                  type="button"
                                  disabled={busy || selected.length === 0}
                                  onClick={() =>
                                    dismissSelectedCandidates(profile.file)
                                  }
                                >
                                  驳回所选（{selected.length}）
                                </button>
                                <button
                                  type="button"
                                  disabled={busy || Boolean(profile.error)}
                                  onClick={() => void importProfile(profile.file)}
                                >
                                  整档导入为规则
                                </button>
                              </div>
                            </>
                          );
                        })()}
                        {importReports[profile.file] && (
                          <div className="profile-import-report">
                            <p>
                              已导入 {importReports[profile.file].imported} 条
                              规则
                              {importReports[profile.file].rejected.length > 0 &&
                                `；拒绝 ${importReports[profile.file].rejected.length} 条`}
                            </p>
                            {importReports[profile.file].rejected.map((item) => (
                              <p
                                className="catalog-empty"
                                key={item.rule_key}
                              >
                                {item.rule_key}：{item.reason}
                              </p>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>服务连接</h2>
            <p>
              这里只配置和检测连接，不会自动启动、
              关闭或重启 ComfyUI。
            </p>
          </div>
        </div>

        {settings && (
          <div className="connection-list">
            <label>
              <span>Ollama 地址</span>
              <input
                value={settings.connections.ollama_url}
                onChange={(event) =>
                  updateConnection(
                    "ollama_url",
                    event.target.value,
                  )
                }
              />
            </label>

            <label>
              <span>ComfyUI 地址</span>
              <input
                value={settings.connections.comfyui_url}
                onChange={(event) =>
                  updateConnection(
                    "comfyui_url",
                    event.target.value,
                  )
                }
              />
            </label>
          </div>
        )}

        <div className="actions">
          <button
            onClick={saveSettings}
            disabled={busy || !settings}
          >
            保存设置
          </button>

          <button
            onClick={() => void exportDiagnostics()}
            disabled={busy}
          >
            导出诊断报告
          </button>

          <button
            onClick={exportSettings}
            disabled={busy || !settings}
          >
            导出设置
          </button>

          <button
            onClick={() => void exportBackup()}
            disabled={busy}
          >
            导出整库备份
          </button>

          <button
            onClick={() => backupFileRef.current?.click()}
            disabled={busy}
          >
            恢复备份
          </button>
          <input
            ref={backupFileRef}
            type="file"
            accept="application/zip,.zip"
            style={{ display: "none" }}
            onChange={pickBackupFile}
          />

          <button
            onClick={() => settingsFileRef.current?.click()}
            disabled={busy || !settings}
          >
            导入设置
          </button>
          <input
            ref={settingsFileRef}
            type="file"
            accept="application/json,.json"
            style={{ display: "none" }}
            onChange={importSettingsFile}
          />

          {restoreFile && (
            <div className="panel">
              <p className="muted">
                已选择备份：{restoreFile.name}。恢复前会先自动备份当前数据；
                默认保留同名现有文件，不触碰模型权重与原图。
              </p>
              <label>
                <input
                  type="checkbox"
                  checked={restoreOverwrite}
                  disabled={busy}
                  onChange={(event) =>
                    setRestoreOverwrite(event.target.checked)
                  }
                />
                覆盖同名现有文件（谨慎）
              </label>
              <div className="actions">
                <button
                  onClick={() => void confirmRestore()}
                  disabled={busy}
                >
                  {busy ? "恢复中…" : "确认恢复"}
                </button>
                <button onClick={cancelRestore} disabled={busy}>
                  取消
                </button>
              </div>
            </div>
          )}

          <span className="message" role="status">
            {message}
          </span>
        </div>
      </section>

  </>
)}
      <footer>
        <span>版本 {health?.version ?? "读取中"}</span>
        <span>M0 · 本地服务基础版</span>
      </footer>
    </main>
  );
}
