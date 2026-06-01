from pathlib import Path


class FileSystemBlobStorage:
    def __init__(self, base_path: str) -> None:
        self._base = Path(base_path)
        self._base.mkdir(parents=True, exist_ok=True)

    async def put(self, key: str, content: bytes, _content_type: str = "") -> None:
        file_path = self._base / key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)

    async def get(self, key: str) -> bytes | None:
        file_path = self._base / key
        if not file_path.exists():
            return None
        return file_path.read_bytes()

    async def delete(self, key: str) -> None:
        file_path = self._base / key
        if file_path.exists():
            file_path.unlink()

    async def signed_url(self, key: str, _expires_in: int = 3600) -> str:
        return f"blob://{key}"
