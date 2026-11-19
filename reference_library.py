"""Fetch the public reference pack from GitHub on each Colab session."""

import hashlib
import json
from pathlib import Path
import re
import tempfile
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import zipfile

REPOSITORY = "cracksteam456/voice-studio"
RELEASE_TAG = "vietvoice-library-158"
PACK_NAME = "vietvoice-library-158.zip"
MAX_PACK = 50 * 1024 * 1024
GROUPS = {
    "preset": "8 giọng ban đầu",
    "vietnamese_primary_50": "50 giọng tiếng Việt",
    "trending_global_50": "50 giọng thịnh hành toàn cầu",
    "usage_global_50": "50 giọng dùng nhiều toàn cầu",
}


def read_library(root):
    root = Path(root).resolve()
    catalog = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
    if not isinstance(catalog, list) or not 1 <= len(catalog) <= 200:
        raise ValueError("Danh sách giọng mẫu không hợp lệ.")
    seen = set()
    for entry in catalog:
        filename = entry.get("file", "")
        if (not re.fullmatch(r"[a-z0-9-]+\.(mp3|wav|flac|ogg)", filename)
                or filename in seen or not isinstance(entry.get("name"), str)
                or not 0 < len(entry["name"]) <= 150
                or entry.get("group", "preset") not in GROUPS):
            raise ValueError("Tên hoặc đường dẫn giọng mẫu không hợp lệ.")
        seen.add(filename)
        path = root / filename
        if (not path.is_file() or path.is_symlink() or path.stat().st_size > 20 * 1024 * 1024
                or hashlib.sha256(path.read_bytes()).hexdigest() != entry.get("sha256")):
            raise ValueError("Giọng mẫu thiếu hoặc sai checksum: " + filename)
    return [{**entry, "path": str(root / entry["file"])} for entry in catalog]


def unpack_library(archive, destination):
    destination = Path(destination)
    if destination.exists():
        raise ValueError("Thư mục đích phải là thư mục mới.")
    with zipfile.ZipFile(archive) as bundle:
        infos = bundle.infolist()
        names = [info.filename for info in infos]
        if (not infos or len(infos) > 201 or len(set(names)) != len(names)
                or sum(info.file_size for info in infos) > MAX_PACK):
            raise ValueError("Gói giọng mẫu vượt giới hạn hoặc có tệp trùng.")
        for info in infos:
            if (not re.fullmatch(r"(?:catalog\.json|[a-z0-9-]+\.(?:mp3|wav|flac|ogg))", info.filename)
                    or (info.external_attr >> 16) & 0o170000 == 0o120000):
                raise ValueError("Đường dẫn trong gói mẫu không an toàn.")
        bundle.extractall(destination)
    return read_library(destination)


def download_library(destination):
    url = f"https://github.com/{REPOSITORY}/releases/download/{RELEASE_TAG}/{PACK_NAME}"
    request = Request(url, headers={"User-Agent": "VietVoice-Studio"})
    with urlopen(request, timeout=60) as response, tempfile.TemporaryFile() as archive:
        count = 0
        while block := response.read(256 * 1024):
            count += len(block)
            if count > MAX_PACK:
                raise ValueError("Gói tải vượt 50 MB.")
            archive.write(block)
        archive.seek(0)
        return unpack_library(archive, destination)


def load_library():
    """Check the current GitHub Release every time the preparation cell runs."""
    folder = Path(tempfile.mkdtemp(prefix="vietvoice-library-"))
    target = folder / "samples"
    try:
        entries = download_library(target)
    except HTTPError as exc:
        raise RuntimeError(f"Không tải được bộ mẫu từ GitHub (HTTP {exc.code}). Hãy chạy lại ô 2.") from None
    print(f"Đã tải và kiểm tra {len(entries)} giọng từ {REPOSITORY}.")
    return entries
