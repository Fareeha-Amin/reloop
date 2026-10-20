"""Image storage interface.

Phase 1 stores files on local disk (LocalImageStorage, under app.constants.UPLOAD_DIR,
which is git-ignored). Object storage (S3 / GCS / R2) replaces it by implementing
`ImageStorage` and changing `get_storage`. Files are never served from a static path:
they are read back through an endpoint that checks who is asking.
"""

import os
import re
import secrets
from pathlib import Path
from typing import Protocol

from app.constants import UPLOAD_DIR

_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{32,}\.[a-z]{3,4}$")


class StorageKeyInvalid(ValueError):
    pass


class ImageStorage(Protocol):
    def save(self, data: bytes, extension: str) -> str:
        """Store bytes under a new random, non-guessable key and return the key."""
        ...

    def read(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...


class LocalImageStorage:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, key: str) -> Path:
        # Keys are generated here, but validate anyway: a key read back from the database
        # must never be able to escape the storage root.
        if not _KEY_PATTERN.fullmatch(key):
            raise StorageKeyInvalid(f"Invalid storage key: {key!r}")
        return self.root / key

    def save(self, data: bytes, extension: str) -> str:
        key = f"{secrets.token_urlsafe(32)}.{extension}"
        path = self._path(key)
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".part")
        tmp.write_bytes(data)
        os.replace(tmp, path)
        return key

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


def get_storage() -> ImageStorage:
    return LocalImageStorage(UPLOAD_DIR)
