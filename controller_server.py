from fastapi import FastAPI, Response
from pydantic import BaseModel
import uvicorn
from desktop_control import move_mouse, click, type_text, key_press, window_list, window_activate, screenshot_png


class Move(BaseModel):
    x: int
    y: int


class Click(BaseModel):
    button: int = 1


class TypeText(BaseModel):
    text: str


class Key(BaseModel):
    key: str


class Activate(BaseModel):
    id: str


app = FastAPI(title="Linux Desktop Controller")


@app.post("/move")
def api_move(body: Move):
    move_mouse(body.x, body.y)
    return {"status": "ok"}


@app.post("/click")
def api_click(body: Click):
    click(body.button)
    return {"status": "ok"}


@app.post("/type")
def api_type(body: TypeText):
    type_text(body.text)
    return {"status": "ok"}


@app.post("/key")
def api_key(body: Key):
    key_press(body.key)
    return {"status": "ok"}


@app.get("/windows")
def api_windows():
    return {"windows": window_list()}


@app.post("/activate")
def api_activate(body: Activate):
    window_activate(body.id)
    return {"status": "ok"}


@app.get("/screenshot")
def api_screenshot():
    img = screenshot_png()
    return Response(content=img, media_type="image/png")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8765)


