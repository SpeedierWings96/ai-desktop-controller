import subprocess
import tempfile
from pathlib import Path


def run_command(command: str) -> str:
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {command}\n{result.stderr}")
    return result.stdout.strip()


def move_mouse(x: int, y: int) -> None:
    run_command(f"xdotool mousemove {x} {y}")


def click(button: int = 1) -> None:
    run_command(f"xdotool click {button}")


def type_text(text: str) -> None:
    escaped = text.replace("\n", " ")
    run_command(f"xdotool type --delay 1 --clearmodifiers -- '{escaped}'")


def key_press(key: str) -> None:
    run_command(f"xdotool key --clearmodifiers {key}")


def window_list() -> str:
    return run_command("wmctrl -lx")


def window_activate(window_id: str) -> None:
    run_command(f"wmctrl -ia {window_id}")


def screenshot_png() -> bytes:
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "screen.png"
        run_command(f"scrot -o -q 75 {path}")
        return path.read_bytes()


