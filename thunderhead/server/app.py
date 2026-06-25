import os
import uuid
import time
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from jinja2 import Environment, FileSystemLoader

from thunderhead.config import verify_password, load_config, DATA_DIR
from thunderhead.server.jail import VirtualFS

app = FastAPI(title="Thunderhead")

auth_scheme = HTTPBearer(auto_error=False)
_tokens: dict[str, float] = {}
_token_lock = Lock()
_vfs: VirtualFS | None = None

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "templates")
jinja_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))


def _init():
    global _vfs
    config = load_config()
    if config:
        _vfs = VirtualFS(config["storage_root"])
        app.mount("/static", StaticFiles(
            directory=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "static")
        ), name="static")


def _create_token() -> str:
    t = str(uuid.uuid4())
    with _token_lock:
        _tokens[t] = time.time() + 86400
    return t


def _verify_token(token: str) -> bool:
    with _token_lock:
        if token in _tokens and _tokens[token] > time.time():
            return True
    return False


def _require_auth(credentials: HTTPAuthorizationCredentials | None = Depends(auth_scheme)):
    if credentials is None:
        raise HTTPException(401, "Not authenticated")
    if not _verify_token(credentials.credentials):
        raise HTTPException(401, "Invalid or expired token")


@app.on_event("startup")
async def startup():
    _init()


@app.get("/", response_class=HTMLResponse)
async def index():
    config = load_config()
    if not config:
        return HTMLResponse("Thunderhead not configured. Run the setup first.", status_code=500)
    template = jinja_env.get_template("dashboard.html")
    return HTMLResponse(template.render())


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    template = jinja_env.get_template("login.html")
    return HTMLResponse(template.render())


@app.get("/files", response_class=HTMLResponse)
async def files_page():
    template = jinja_env.get_template("files.html")
    return HTMLResponse(template.render())


@app.post("/api/auth/login")
async def login(data: dict):
    config = load_config()
    if not config:
        raise HTTPException(500, "Not configured")
    password = data.get("password", "")
    if verify_password(password, config["password_hash"]):
        token = _create_token()
        return {"token": token}
    raise HTTPException(401, "Invalid password")


@app.get("/api/fs/list")
async def list_files(path: str = "/", _=Depends(_require_auth)):
    if _vfs is None:
        raise HTTPException(500, "Virtual FS not initialized")
    try:
        items = _vfs.list_dir(path)
        return {"items": items}
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except FileNotFoundError:
        raise HTTPException(404, "Path not found")
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/fs/info")
async def file_info(path: str = "/", _=Depends(_require_auth)):
    if _vfs is None:
        raise HTTPException(500, "Virtual FS not initialized")
    try:
        return _vfs.file_info(path)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except FileNotFoundError:
        raise HTTPException(404, "Path not found")


@app.get("/api/fs/download")
async def download_file(path: str, _=Depends(_require_auth)):
    if _vfs is None:
        raise HTTPException(500, "Virtual FS not initialized")
    try:
        real = _vfs.resolve(path)
        if not real.is_file():
            raise HTTPException(404, "Not a file")
        return FileResponse(str(real), filename=real.name)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except FileNotFoundError:
        raise HTTPException(404, "Path not found")


@app.post("/api/fs/upload")
async def upload_file(path: str = "/", file: UploadFile = File(...), _=Depends(_require_auth)):
    if _vfs is None:
        raise HTTPException(500, "Virtual FS not initialized")
    try:
        content = await file.read()
        real = _vfs.resolve(path)
        if not real.is_dir():
            raise HTTPException(400, "Target path is not a directory")
        dest = real / file.filename
        with open(dest, "wb") as f:
            f.write(content)
        return {"path": _vfs.to_vpath(dest)}
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except FileNotFoundError:
        raise HTTPException(404, "Path not found")


@app.post("/api/fs/mkdir")
async def create_folder(path: str, _=Depends(_require_auth)):
    if _vfs is None:
        raise HTTPException(500, "Virtual FS not initialized")
    try:
        _vfs.mkdir(path)
        return {"path": path}
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except FileNotFoundError:
        raise HTTPException(404, "Path not found")


@app.delete("/api/fs/remove")
async def delete_item(path: str, _=Depends(_require_auth)):
    if _vfs is None:
        raise HTTPException(500, "Virtual FS not initialized")
    try:
        _vfs.remove(path)
        return {"removed": path}
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except FileNotFoundError:
        raise HTTPException(404, "Path not found")
