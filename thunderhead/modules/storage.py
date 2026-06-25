import os
import shutil
import zipfile
from pathlib import Path

from thunderhead.server.jail import VirtualFS


class StorageModule:
    def __init__(self, vfs: VirtualFS):
        self.vfs = vfs

    def list_files(self, path: str = "/") -> list[dict]:
        return self.vfs.list_dir(path)

    def get_file(self, path: str):
        real = self.vfs.resolve(path)
        if not real.is_file():
            raise FileNotFoundError(f"Not a file: {path}")
        return str(real)

    def upload_file(self, remote_dir: str, filename: str, content: bytes):
        real = self.vfs.resolve(remote_dir)
        dest = real / filename
        with open(dest, "wb") as f:
            f.write(content)
        return self.vfs.to_vpath(dest)

    def create_folder(self, path: str):
        self.vfs.mkdir(path)

    def delete(self, path: str):
        self.vfs.remove(path)

    def info(self, path: str) -> dict:
        return self.vfs.file_info(path)
