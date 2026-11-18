import { useEffect, useState } from "react";
import { apiGet, apiPost } from "./api";
import { formatStructured } from "./format";
import HistoryPanel from "./HistoryPanel";
import WorkflowWorkbench from "./WorkflowWorkbench";

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

type CatalogEntry = {
  name: string;
  on_disk: boolean | null;
  identity?: IdentitySummary;
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
  const [catalog, setCatalog] = useState<ModelCatalog | null>(null);
  const [rules, setRules] = useState<RuleRecord[] | null>(null);
  const [profiles, setProfiles] = useState<ProfileSummary[] | null>(null);
  const [openProfile, setOpenProfile] = useState<string | null>(null);
  const [preview, setPreview] = useState<ProfilePreview | null>(null);
  const [checks, setChecks] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(true);
  const [message, setMessage] = useState("正在连接本地服务…");
  const [activePage, setActivePage] = useState<"settings" | "workflows" | "history">("settings");

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

        <button
          onClick={refreshStatus}
          disabled={busy}
        >
          刷新状态
        </button>
      </header>

      <nav className="page-nav">
        <button
          className={activePage === "settings" ? "" : "secondary"}
          onClick={() => setActivePage("settings")}
        >
          服务与设置
        </button>
        <button
          className={activePage === "workflows" ? "" : "secondary"}
          onClick={() => setActivePage("workflows")}
        >
          工作流工作区
        </button>
        <button
          className={activePage === "history" ? "" : "secondary"}
          onClick={() => setActivePage("history")}
        >
          生成历史
        </button>
      </nav>

      {activePage === "workflows" ? (
        <WorkflowWorkbench />
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
                  {catalog.loras.map((entry) => (
                    <li key={entry.name}>
                      <span>{entry.name}</span>
                      <small>{identityLabel(entry)}</small>
                    </li>
                  ))}
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
            <h2>规则库（只读）</h2>
            <p>
              规则记录来自档案导入与本地登记；本版本只展示，
              不提供新增、修改或删除入口。
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
                  {group.map((rule) => (
                    <div className="rule-row" key={rule.id}>
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
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })
        )}
      </section>

      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>旧档案候选（只读）</h2>
            <p>
              名单来自 legacy 档案文本解析，仅预览待审核候选；
              本版本不提供导入、勾选或驳回入口。
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
                        {preview.candidates.length === 0 ? (
                          <p className="catalog-empty">无可导入候选。</p>
                        ) : (
                          preview.candidates.map((candidate, index) => (
                            <div className="rule-row" key={index}>
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
                              </div>
                            </div>
                          ))
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
