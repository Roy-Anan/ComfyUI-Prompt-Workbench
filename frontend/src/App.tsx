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

const storageLabels: Record<string, string> = {
  root: "工作台数据根目录",
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
  const response = await fetch(`http://127.0.0.1:${config.port}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${config.token}`,
      "Content-Type": "application/json",
      ...init.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`${response.status}: ${await response.text()}`);
  }
  return response.json() as Promise<T>;
}

function StatusDot({ online }: { online: boolean }) {
  return <span className={`dot ${online ? "online" : "offline"}`} />;
}

export default function App() {
  const [config, setConfig] = useState<BackendConfig | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [services, setServices] = useState<ServiceStatus | null>(null);
  const [busy, setBusy] = useState(true);
  const [message, setMessage] = useState("正在连接本地服务…");

  async function refresh(current: BackendConfig) {
    const [h, s, serviceStatus] = await Promise.all([
      api<Health>(current, "/api/health"),
      api<Settings>(current, "/api/settings"),
      api<ServiceStatus>(current, "/api/services/status"),
    ]);
    setHealth(h);
    setSettings(s);
    setServices(serviceStatus);
  }

  useEffect(() => {
    let alive = true;

    async function connect() {
      try {
        const backend = await invoke<BackendConfig>("get_backend_config");
        if (!alive) return;
        setConfig(backend);
        await refresh(backend);
        if (!alive) return;
        setMessage("本地服务已连接");
      } catch (error) {
        if (alive) setMessage(`连接失败：${String(error)}`);
      } finally {
        if (alive) setBusy(false);
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

  async function saveSettings() {
    if (!config || !settings) return;
    setBusy(true);
    try {
      const updated = await api<Settings>(config, "/api/settings", {
        method: "POST",
        body: JSON.stringify(settings),
      });
      setSettings(updated);
      setMessage("设置已保存");
    } catch (error) {
      setMessage(`保存失败：${String(error)}`);
    } finally {
      setBusy(false);
    }
  }

  function updateStorage(key: string, value: string) {
    if (!settings) return;
    setSettings({
      ...settings,
      storage: { ...settings.storage, [key]: value },
    });
  }

  function updateConnection(key: "ollama_url" | "comfyui_url", value: string) {
    if (!settings) return;
    setSettings({
      ...settings,
      connections: { ...settings.connections, [key]: value },
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
        <button onClick={refreshStatus} disabled={busy || !config}>
          刷新状态
        </button>
      </header>

      <section className="status-grid">
        <article className="panel status-card">
          <div className="card-title">工作台本地服务</div>
          <div className="status-line">
            <StatusDot online={health?.ok === true} />
            <strong>{health?.ok ? "已连接" : "未连接"}</strong>
          </div>
          <small>{health ? `Python ${health.python}` : message}</small>
        </article>

        <article className="panel status-card">
          <div className="card-title">Ollama</div>
          <div className="status-line">
            <StatusDot online={services?.ollama.online === true} />
            <strong>{services?.ollama.online ? "在线" : "未连接"}</strong>
          </div>
          <small>{settings?.connections.ollama_url ?? "等待读取设置"}</small>
        </article>

        <article className="panel status-card">
          <div className="card-title">ComfyUI</div>
          <div className="status-line">
            <StatusDot online={services?.comfyui.online === true} />
            <strong>{services?.comfyui.online ? "在线" : "未连接"}</strong>
          </div>
          <small>{settings?.connections.comfyui_url ?? "等待读取设置"}</small>
        </article>
      </section>

      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>存储位置</h2>
            <p>管理工作台数据目录。修改路径会在保存时创建目录；本版本尚不迁移已有数据。</p>
          </div>
        </div>

        {settings ? (
          <div className="path-list">
            {Object.entries(settings.storage).map(([key, value]) => (
              <label className="field" key={key}>
                <span>{storageLabels[key] ?? key}</span>
                <input
                  value={value}
                  placeholder={key === "checkpoint" || key === "lora" ? "可留空" : ""}
                  onChange={(event) => updateStorage(key, event.target.value)}
                />
              </label>
            ))}
          </div>
        ) : (
          <p className="muted">正在读取存储设置…</p>
        )}
      </section>

      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>服务连接</h2>
            <p>服务地址与文件夹路径分开管理。</p>
          </div>
        </div>
        {settings && (
          <div className="path-list">
            <label className="field">
              <span>Ollama 地址</span>
              <input
                value={settings.connections.ollama_url}
                onChange={(event) =>
                  updateConnection("ollama_url", event.target.value)
                }
              />
            </label>
            <label className="field">
              <span>ComfyUI 地址</span>
              <input
                value={settings.connections.comfyui_url}
                onChange={(event) =>
                  updateConnection("comfyui_url", event.target.value)
                }
              />
            </label>
          </div>
        )}
      </section>

      <footer className="footer">
        <span>{message}</span>
        <button onClick={saveSettings} disabled={busy || !settings}>
          保存设置
        </button>
      </footer>
    </main>
  );
}
