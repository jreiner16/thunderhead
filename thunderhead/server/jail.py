import os
import time
from pathlib import Path


class VirtualFS:
    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self._init_structure()

    def _init_structure(self):
        dirs = [
            "home/user/documents",
            "home/user/projects",
            "home/user/uploads",
            "tmp",
            "var/log",
            "etc",
        ]
        for d in dirs:
            (self.root / d).mkdir(parents=True, exist_ok=True)

    def resolve(self, vpath: str) -> Path:
        clean = os.path.normpath(vpath.lstrip("/"))
        if clean == ".":
            clean = ""
        abs_path = (self.root / clean).resolve()
        if not str(abs_path).startswith(str(self.root)):
            raise PermissionError(f"Path escapes jail: {vpath}")
        return abs_path

    def to_vpath(self, real_path: Path) -> str:
        rel = real_path.resolve().relative_to(self.root)
        parts = str(rel).replace("\\", "/")
        return "/" + parts if parts != "." else "/"

    def list_dir(self, vpath: str) -> list[dict]:
        real = self.resolve(vpath)
        items = []
        for entry in sorted(real.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            try:
                stat = entry.stat()
                items.append({
                    "name": entry.name,
                    "path": self.to_vpath(entry),
                    "is_dir": entry.is_dir(),
                    "size": stat.st_size if entry.is_file() else 0,
                    "modified": int(stat.st_mtime),
                })
            except OSError:
                pass
        return items

    def file_info(self, vpath: str) -> dict:
        real = self.resolve(vpath)
        stat = real.stat()
        return {
            "name": real.name,
            "path": vpath,
            "is_dir": real.is_dir(),
            "size": stat.st_size if real.is_file() else 0,
            "modified": int(stat.st_mtime),
        }

    def mkdir(self, vpath: str):
        real = self.resolve(vpath)
        real.mkdir(parents=True, exist_ok=True)

    def remove(self, vpath: str):
        real = self.resolve(vpath)
        if real.is_dir():
            import shutil
            shutil.rmtree(real)
        else:
            real.unlink()

    def exists(self, vpath: str) -> bool:
        real = self.resolve(vpath)
        return real.exists()
