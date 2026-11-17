use serde::Serialize;
use std::{
    fs::File,
    net::{TcpListener, TcpStream},
    path::{Path, PathBuf},
    process::{Child, Command, Stdio},
    sync::Mutex,
    thread,
    time::{Duration, Instant},
};
use tauri::{Manager, RunEvent};
use uuid::Uuid;

struct BackendState {
    port: u16,
    token: String,
    child: Mutex<Child>,
}

#[derive(Serialize)]
struct BackendConfig {
    port: u16,
    token: String,
}

#[tauri::command]
fn get_backend_config(state: tauri::State<'_, BackendState>) -> BackendConfig {
    BackendConfig {
        port: state.port,
        token: state.token.clone(),
    }
}

fn find_python(project_root: &PathBuf) -> String {
    if let Ok(value) = std::env::var("WORKBENCH_PYTHON") {
        if !value.trim().is_empty() {
            return value;
        }
    }

    let venv_python = project_root.join(".venv").join("Scripts").join("python.exe");
    if venv_python.exists() {
        return venv_python.to_string_lossy().to_string();
    }

    "python".to_string()
}

fn reserve_local_port() -> Result<u16, String> {
    let listener = TcpListener::bind(("127.0.0.1", 0))
        .map_err(|e| format!("Cannot reserve local port: {e}"))?;

    let port = listener
        .local_addr()
        .map_err(|e| format!("Cannot read local port: {e}"))?
        .port();

    drop(listener);
    Ok(port)
}

fn wait_for_backend(
    port: u16,
    token: &str,
    child: &mut Child,
    logs_dir: &Path,
) -> Result<(), String> {
    let deadline = Instant::now() + Duration::from_secs(20);

    loop {
        if let Some(status) = child
            .try_wait()
            .map_err(|e| format!("Cannot inspect Python process: {e}"))?
        {
            let stderr_log = logs_dir.join("sidecar-stderr.log");
            return Err(format!(
                "Python service exited during startup: {status}; check {}",
                stderr_log.display()
            ));
        }

        // A bare TCP connect only proves the port opened; verify the backend
        // actually answers the authed health endpoint before reporting ready.
        let ready = TcpStream::connect(("127.0.0.1", port)).is_ok()
            && check_health(port, token).unwrap_or(false);

        if ready {
            return Ok(());
        }

        if Instant::now() >= deadline {
            let _ = child.kill();
            let _ = child.wait();
            let stderr_log = logs_dir.join("sidecar-stderr.log");
            return Err(format!(
                "Python service startup timed out after 20 seconds; check {}",
                stderr_log.display()
            ));
        }

        thread::sleep(Duration::from_millis(200));
    }
}

fn check_health(port: u16, token: &str) -> Result<bool, String> {
    use std::io::{Read, Write};

    let mut stream = TcpStream::connect(("127.0.0.1", port))
        .map_err(|e| format!("health connect failed: {e}"))?;
    stream
        .set_read_timeout(Some(Duration::from_millis(500)))
        .map_err(|e| format!("health timeout set failed: {e}"))?;

    let request = format!(
        "GET /api/health HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n\
         Authorization: Bearer {token}\r\nConnection: close\r\n\r\n"
    );
    stream
        .write_all(request.as_bytes())
        .map_err(|e| format!("health request failed: {e}"))?;

    let mut body = String::new();
    stream
        .read_to_string(&mut body)
        .map_err(|e| format!("health read failed: {e}"))?;

    Ok(body.contains(" 200 ") && body.contains("\"ok\":true"))
}

fn start_backend(app: &tauri::App) -> Result<BackendState, String> {
    let project_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .map_err(|e| format!("Cannot locate project root: {e}"))?;

    let backend_dir = project_root.join("backend");
    if !backend_dir.join("main.py").exists() {
        return Err(format!(
            "Backend entry file not found: {}",
            backend_dir.display()
        ));
    }

    let python = find_python(&project_root);
    let port = reserve_local_port()?;
    let token = Uuid::new_v4().to_string();

    // The data root is shared with the Python backend and follows the default
    // LOCALAPPDATA layout; the host and backend must not use separate roots.
    let data_dir = default_data_dir()?;
    let logs_dir = data_dir.join("logs");
    std::fs::create_dir_all(&logs_dir)
        .map_err(|e| format!("Cannot create logs directory: {e}"))?;

    let stdout_log = File::create(logs_dir.join("sidecar-stdout.log"))
        .map_err(|e| format!("Cannot open sidecar stdout log: {e}"))?;
    let stderr_log = File::create(logs_dir.join("sidecar-stderr.log"))
        .map_err(|e| format!("Cannot open sidecar stderr log: {e}"))?;

    // NOTE: the session token is passed only through the WORKBENCH_SESSION_TOKEN
    // environment variable; it is never written to these log files.

    let mut child = Command::new(&python)
        .args([
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            "127.0.0.1",
            "--port",
            &port.to_string(),
            "--no-access-log",
        ])
        .current_dir(&backend_dir)
        .env("WORKBENCH_SESSION_TOKEN", &token)
        .env("WORKBENCH_DATA_ROOT", &data_dir)
        .stdin(Stdio::null())
        .stdout(Stdio::from(stdout_log))
        .stderr(Stdio::from(stderr_log))
        .spawn()
        .map_err(|e| {
            format!(
                "Cannot start Python service using '{python}'. \
                 Check Python environment and backend dependencies: {e}; \
                 see {}",
                logs_dir.join("sidecar-stderr.log").display()
            )
        })?;

    if let Err(error) = wait_for_backend(port, &token, &mut child, &logs_dir) {
        let _ = child.kill();
        let _ = child.wait();
        return Err(error);
    }

    Ok(BackendState {
        port,
        token,
        child: Mutex::new(child),
    })
}

/// Shared data root: %LOCALAPPDATA%\ComfyUI-Prompt-Workbench on Windows.
fn default_data_dir() -> Result<PathBuf, String> {
    let local_app_data = std::env::var("LOCALAPPDATA")
        .map(PathBuf::from)
        .or_else(|_| {
            std::env::var("USERPROFILE")
                .map(|home| PathBuf::from(home).join("AppData/Local"))
        })
        .map_err(|_| "Cannot resolve LOCALAPPDATA for data root".to_string())?;

    Ok(local_app_data.join("ComfyUI-Prompt-Workbench"))
}

pub fn run() {
    let app = tauri::Builder::default()
        .setup(|app| {
            let state = start_backend(app)
                .map_err(|error| std::io::Error::other(error))?;
            app.manage(state);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![get_backend_config])
        .build(tauri::generate_context!())
        .expect("error while building Tauri application");

    app.run(|app_handle, event| {
        if let RunEvent::Exit = event {
            if let Some(state) = app_handle.try_state::<BackendState>() {
                if let Ok(mut child) = state.child.lock() {
                    let _ = child.kill();
                    let _ = child.wait();
                }
            }
        }
    });
}
