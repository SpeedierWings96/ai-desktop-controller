import os
import subprocess
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn


APP_ROOT = Path(__file__).parent
ENV_FILE = APP_ROOT / ".env"
COMPOSE_WORKDIR = Path(os.environ.get("COMPOSE_WORKDIR", str(APP_ROOT)))


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
        run_compose("build")
    elif action == "up":
        run_compose("up -d")
    elif action == "down":
        run_compose("down")
    elif action == "restart":
        run_compose("down")
        run_compose("up -d")
    return RedirectResponse("/", status_code=303)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)


