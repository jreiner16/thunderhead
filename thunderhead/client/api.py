from __future__ import annotations

import httpx


class ThunderheadClient:
    def __init__(self, address: str, password: str, verify: bool = False):
        base = f"http://{address}" if not address.startswith("http") else address
        self.base = base.rstrip("/")
        self.password = password
        self.token: str | None = None
        self._client = httpx.AsyncClient(verify=verify, timeout=10)

    async def login(self) -> bool:
        try:
            r = await self._client.post(
                f"{self.base}/api/auth/login",
                json={"password": self.password},
            )
            if r.status_code == 200:
                data = r.json()
                self.token = data["token"]
                return True
            return False
        except httpx.ConnectError:
            return False

    async def list_files(self, path: str = "/") -> list[dict] | None:
        r = await self._client.get(
            f"{self.base}/api/fs/list",
            params={"path": path},
            headers=self._auth_headers(),
        )
        if r.status_code == 200:
            return r.json()["items"]
        return None

    async def file_info(self, path: str = "/") -> dict | None:
        r = await self._client.get(
            f"{self.base}/api/fs/info",
            params={"path": path},
            headers=self._auth_headers(),
        )
        if r.status_code == 200:
            return r.json()
        return None

    async def download(self, remote_path: str) -> bytes | None:
        r = await self._client.get(
            f"{self.base}/api/fs/download",
            params={"path": remote_path},
            headers=self._auth_headers(),
        )
        if r.status_code == 200:
            return r.content
        return None

    async def upload(self, remote_dir: str, filename: str, content: bytes) -> bool:
        r = await self._client.post(
            f"{self.base}/api/fs/upload",
            params={"path": remote_dir},
            files={"file": (filename, content)},
            headers=self._auth_headers(include_auth=False),
        )
        return r.status_code == 200

    async def mkdir(self, path: str) -> bool:
        r = await self._client.post(
            f"{self.base}/api/fs/mkdir",
            params={"path": path},
            headers=self._auth_headers(),
        )
        return r.status_code == 200

    async def remove(self, path: str) -> bool:
        r = await self._client.delete(
            f"{self.base}/api/fs/remove",
            params={"path": path},
            headers=self._auth_headers(),
        )
        return r.status_code == 200

    def _auth_headers(self, include_auth: bool = True) -> dict:
        headers = {}
        if include_auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def close(self):
        await self._client.aclose()
