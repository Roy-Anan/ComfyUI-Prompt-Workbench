use serde::Serialize;
use std::{
    net::{TcpListener, TcpStream},
    path::PathBuf,
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

fn wait_for_backend(port: u16, child: &mut Child) -> Result<(), String> {
    let deadline = Instant::now() + Duration::from_secs(20);

    loop {
        if let Some(status) = child
            .try_wait()
            .map_err(|e| format!("Cannot inspect Python process: {e}"))?
        {
            return Err(format!("Python service exited during startup: {status}"));
        }

        if TcpStream::connect(("127.0.0.1", port)).is_ok() {
            return Ok(());
        }

        if Instant::now() >= deadline {
            let _ = child.kill();
            let _ = child.wait();
            return Err("Python service startup timed out after 20 seconds".to_string());
        }

        thread::sleep(Duration::from_millis(200));
    }
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

    let app_data_dir = app
        .path()
        .app_local_data_dir()
        .map_err(|e| format!("Cannot resolve app data directory: {e}"))?;

    let data_dir = app_data_dir.join("data");
    std::fs::create_dir_all(&data_dir)
        .map_err(|e| format!("Cannot create app data directory: {e}"))?;

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
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|e| {
            format!(
                "Cannot start Python service using '{python}'.                  Check Python environment and backend dependencies: {e}"
            )
        })?;

    if let Err(error) = wait_for_backend(port, &mut child) {
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
