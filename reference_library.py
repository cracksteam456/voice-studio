"""Fetch the private reference pack without persisting GitHub credentials."""

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import zipfile

REPOSITORY = "cracksteam456/voice-studio"
RELEASE_TAG = "vietvoice-references"
PACK_NAME = "vietvoice-references.zip"
MAX_PACK = 25 * 1024 * 1024


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
                or not 0 < len(entry["name"]) <= 150):
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


def download_library(token, destination):
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    opener = build_opener(NoRedirect())
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "VietVoice-Studio"}
    if token:
        headers["Authorization"] = "Bearer " + token
    release_url = f"https://api.github.com/repos/{REPOSITORY}/releases/tags/{RELEASE_TAG}"
    with opener.open(Request(release_url, headers=headers), timeout=30) as response:
        release = json.loads(response.read(1_000_000))
    asset = next((a for a in release.get("assets", []) if a["name"] == PACK_NAME), None)
    if not asset or not 0 < asset.get("size", 0) <= MAX_PACK:
        raise ValueError("Chưa có gói giọng mẫu hợp lệ trên GitHub Release.")
    url = asset["url"]
    if not re.fullmatch(r"https://api\.github\.com/repos/cracksteam456/voice-studio/releases/assets/[0-9]+", url):
        raise ValueError("Địa chỉ tải mẫu không hợp lệ.")
    headers["Accept"] = "application/octet-stream"
    try:
        response = opener.open(Request(url, headers=headers), timeout=45)
    except HTTPError as exc:
        parsed = urlsplit(exc.headers.get("Location", ""))
        if (exc.code not in (301, 302, 303, 307, 308) or parsed.scheme != "https"
                or parsed.hostname not in {"release-assets.githubusercontent.com", "objects.githubusercontent.com"}):
            raise
        # Never forward Authorization across the release CDN redirect.
        response = opener.open(Request(parsed.geturl(), headers={"User-Agent": headers["User-Agent"]}), timeout=45)
    with response, tempfile.TemporaryFile() as archive:
        count = 0
        while block := response.read(256 * 1024):
            count += len(block)
            if count > MAX_PACK:
                raise ValueError("Gói tải vượt 25 MB.")
            archive.write(block)
        archive.seek(0)
        return unpack_library(archive, destination)


def load_library():
    """Check the current GitHub Release every time the preparation cell runs."""
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        try:
            from google.colab import userdata
            token = userdata.get("GITHUB_TOKEN")
        except Exception:
            pass
    if not token:
        from getpass import getpass
        print("Repo riêng tư: thêm GITHUB_TOKEN trong Colab Secrets để các phiên sau tự tải. "
              "Token cần Contents: Read cho cracksteam456/voice-studio.")
        token = getpass("GitHub token (nhập ẩn, không lưu): ").strip()
    if not token:
        raise RuntimeError("Cần GITHUB_TOKEN để tải bộ giọng mẫu từ kho riêng tư.")
    folder = Path(tempfile.mkdtemp(prefix="vietvoice-library-"))
    target = folder / "samples"
    try:
        entries = download_library(token, target)
    except HTTPError as exc:
        raise RuntimeError(f"GitHub HTTP {exc.code}: kiểm tra quyền đọc kho của GITHUB_TOKEN.") from None
    finally:
        token = None
    print(f"Đã tải và kiểm tra {len(entries)} giọng từ {REPOSITORY}.")
    return entries
