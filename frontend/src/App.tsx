import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";

type BackendConfig = {
  port: number;
  token: string;
};

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
};

async function api<T>(
  config: BackendConfig,
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(
    `http://127.0.0.1:${config.port}${path}`,
    {
      ...init,
      headers: {
        Authorization: `Bearer ${config.token}`,
        "Content-Type": "application/json",
        ...init.headers,
      },
    },
  );

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status}: ${detail}`);
  }

  return response.json() as Promise<T>;
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
  const [config, setConfig] = useState<BackendConfig | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [services, setServices] = useState<ServiceStatus | null>(null);
  const [checks, setChecks] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(true);
  const [message, setMessage] = useState("正在连接本地服务…");

  async function refresh(current: BackendConfig) {
    const [healthResult, settingsResult, serviceResult] =
      await Promise.all([
        api<Health>(current, "/api/health"),
        api<Settings>(current, "/api/settings"),
        api<ServiceStatus>(current, "/api/services/status"),
      ]);

    setHealth(healthResult);
    setSettings(settingsResult);
    setServices(serviceResult);
  }

  useEffect(() => {
    let alive = true;

    async function connect() {
      try {
        const backend = await invoke<BackendConfig>(
          "get_backend_config",
        );

        if (!alive) return;

        setConfig(backend);
        await refresh(backend);

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
    if (!config) return;

    setBusy(true);

    try {
      await refresh(config);
      setMessage("状态已刷新");
    } catch (error) {
      setMessage(`刷新失败：${String(error)}`);
    } finally {
      setBusy(false);
    }
  }

  async function checkPath(key: string) {
    if (!config || !settings) return;

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
      const result = await api<PathCheck>(
        config,
        "/api/storage/validate",
        {
          method: "POST",
          body: JSON.stringify({
            path,
            create: key !== "checkpoint" && key !== "lora",
          }),
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

  async function saveSettings() {
    if (!config || !settings) return;

    setBusy(true);

    try {
      const { root: _fixedRoot, ...editableStorage } =
        settings.storage;

      const updated = await api<Settings>(
        config,
        "/api/settings",
        {
          method: "POST",
          body: JSON.stringify({
            storage: editableStorage,
            connections: settings.connections,
          }),
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
          disabled={busy || !config}
        >
          刷新状态
        </button>
      </header>

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
              根目录由桌面宿主固定。本版本只允许修改子目录，
              不会自动迁移已有数据。
            </p>
          </div>
        </div>

        {settings ? (
          <div className="path-list">
            {Object.entries(settings.storage).map(
              ([key, value]) => {
                const fixed = key === "root";
                const optional =
                  key === "checkpoint" || key === "lora";

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

      <footer>
        <span>版本 {health?.version ?? "读取中"}</span>
        <span>M0 · 本地服务基础版</span>
      </footer>
    </main>
  );
}
