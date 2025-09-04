import os
import subprocess
import threading
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn


APP_ROOT = Path(__file__).parent
ENV_FILE = APP_ROOT / ".env"
COMPOSE_WORKDIR = Path(os.environ.get("COMPOSE_WORKDIR", str(APP_ROOT)))
LOG_DIR = APP_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Simple background job state
_job_lock = threading.Lock()
_job_name: Optional[str] = None
_job_proc: Optional[subprocess.Popen] = None
_job_log: Optional[Path] = None


def read_env_file() -> Dict[str, str]:
    values: Dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                values[key.strip()] = val.strip()
    return values


def write_env_file(values: Dict[str, str]) -> None:
    lines = [f"{k}={v}" for k, v in values.items()]
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_compose(args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        f"docker compose {args}",
        cwd=str(COMPOSE_WORKDIR),
        shell=True,
        text=True,
        capture_output=True,
    )


def start_compose_job(name: str, args: str) -> bool:
    global _job_name, _job_proc, _job_log
    with _job_lock:
        if _job_proc and _job_proc.poll() is None:
            return False  # job already running
        log_path = LOG_DIR / f"{name}.log"
        try:
            log_path.unlink(missing_ok=True)
        except Exception:
            pass
        log_file = open(log_path, "a", encoding="utf-8", buffering=1)
        proc = subprocess.Popen(
            f"docker compose {args}",
            cwd=str(COMPOSE_WORKDIR),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        def _pump():
            assert proc.stdout is not None
            for line in proc.stdout:
                try:
                    log_file.write(line)
                except Exception:
                    pass
            proc.wait()
            try:
                log_file.write(f"\n[exit_code]={proc.returncode}\n")
                log_file.close()
            except Exception:
                pass

        threading.Thread(target=_pump, daemon=True).start()
        _job_name = name
        _job_proc = proc
        _job_log = log_path
        return True


def get_job_status() -> Dict[str, Optional[str]]:
    with _job_lock:
        running = _job_proc is not None and _job_proc.poll() is None
        exit_code = None if running or _job_proc is None else str(_job_proc.returncode)
        return {
            "running": running,
            "name": _job_name,
            "exit_code": exit_code,
            "log": str(_job_log) if _job_log else None,
        }


def read_log_tail(path: Path, max_bytes: int = 64_000) -> str:
    if not path.exists():
        return ""
    data = path.read_bytes()
    if len(data) > max_bytes:
        data = data[-max_bytes:]
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        return ""


def get_container_status() -> str:
    # Returns running status string or empty if not running
    proc = subprocess.run(
        "docker ps --filter name=linux-desktop --format \"{{.Status}}\"",
        shell=True,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        return ""
    return (proc.stdout or "").strip()


app = FastAPI(title="AI Desktop Controller - Host GUI")

templates = Jinja2Templates(directory=str(APP_ROOT / "templates"))
(APP_ROOT / "static").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(APP_ROOT / "static")), name="static")


@app.get("/")
def index(request: Request):
    env = read_env_file()
    status = get_container_status()
    vnc_port = os.environ.get("NOVNC_PORT", "8080")
    vnc_password = env.get("VNC_PASSWORD", "")
    resolution = env.get("RESOLUTION", "1920x1080")
    depth = env.get("DEPTH", "24")
    novnc_url = f"http://localhost:{vnc_port}/vnc.html?autoconnect=1"
    if vnc_password:
        novnc_url += f"&password={vnc_password}"
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "status": status or "not running",
            "resolution": resolution,
            "depth": depth,
            "vnc_password": vnc_password,
            "novnc_url": novnc_url,
        },
    )


@app.post("/save")
def save(
    request: Request,
    vnc_password: str = Form(""),
    resolution: str = Form("1920x1080"),
    depth: str = Form("24"),
):
    env = read_env_file()
    env["VNC_PASSWORD"] = vnc_password or env.get("VNC_PASSWORD", "changeme")
    env["RESOLUTION"] = resolution
    env["DEPTH"] = depth
    write_env_file(env)
    return RedirectResponse("/", status_code=303)


@app.post("/action")
def action(request: Request, action: str = Form(...)):
    if action == "build":
        start_compose_job("build", "build")
    elif action == "up":
        start_compose_job("up", "up -d")
    elif action == "down":
        start_compose_job("down", "down")
    elif action == "restart":
        start_compose_job("restart", "down && docker compose up -d")
    return RedirectResponse("/", status_code=303)


@app.get("/status")
def status_api():
    job = get_job_status()
    return JSONResponse({
        "job": job,
        "desktop": get_container_status(),
    })


@app.get("/logs", response_class=PlainTextResponse)
def logs_api(name: Optional[str] = None):
    with _job_lock:
        log_path = None
        if name:
            candidate = LOG_DIR / f"{name}.log"
            log_path = candidate if candidate.exists() else _job_log
        else:
            log_path = _job_log
    if not log_path:
        return ""
    return read_log_tail(log_path)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)


