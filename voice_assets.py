"""Load the project's 150-voice pack locally or from its private GitHub release."""
from pathlib import Path
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.parse import urlsplit
from urllib.error import HTTPError
import hashlib
import json
import os
import tempfile
import zipfile

PACK_RELEASE = 'https://api.github.com/repos/cracksteam456/voice-studio/releases/tags/hot-voices-2026-11-17'
PACK_NAME = 'hot-voices-150.zip'
GROUP_NAMES = {'vietnamese_primary_50': 'Tiếng Việt · Top 50',
               'trending_global_50': 'Trending toàn cầu · Top 50',
               'usage_global_50': 'Dùng nhiều toàn cầu · Top 50'}


def read_voice_pack(root):
    root = Path(root).resolve()
    entries = json.loads((root / 'catalog.json').read_text(encoding='utf-8'))
    if not isinstance(entries, list) or len(entries) != 150:
        raise ValueError('Bộ giọng phải có đủ 150 bản ghi.')
    seen = set()
    for entry in entries:
        relative = entry.get('sample_file', '')
        path = (root / relative).resolve()
        if (not relative or not path.is_relative_to(root) or not path.is_file()
                or path.suffix.lower() not in ('.wav', '.mp3', '.m4a', '.flac', '.ogg')):
            raise ValueError('Đường dẫn mẫu trong catalog không hợp lệ.')
        if relative in seen or entry.get('group') not in GROUP_NAMES:
            raise ValueError('Catalog có mẫu trùng hoặc nhóm không hợp lệ.')
        seen.add(relative)
        expected = entry.get('sample_sha256')
        if not expected or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('File mẫu thiếu hoặc không khớp checksum: ' + relative)
    return entries


def unpack_voice_pack(archive, destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Validate in a fresh folder; a failed upload never damages the current pack.
    with tempfile.TemporaryDirectory(dir=destination.parent) as work:
        root = Path(work).resolve()
        with zipfile.ZipFile(archive) as bundle:
            entries = bundle.infolist()
            if len(entries) > 200 or sum(e.file_size for e in entries) > 60_000_000:
                raise ValueError('Gói mẫu vượt giới hạn kích thước.')
            for entry in entries:
                target = (root / entry.filename).resolve()
                if ('\\' in entry.filename or not target.is_relative_to(root)
                        or entry.file_size > 25_000_000 or (entry.external_attr >> 16) & 0o170000 == 0o120000):
                    raise ValueError('Gói mẫu chứa đường dẫn không hợp lệ.')
            bundle.extractall(root)
        read_voice_pack(root)
        destination.mkdir(parents=True, exist_ok=True)
        import shutil
        for source in root.rglob('*'):
            if source.is_file():
                target = destination / source.relative_to(root)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
    return destination


def download_voice_pack(token, destination):
    # Send credentials only to api.github.com, never to a release download redirect.
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    opener = build_opener(NoRedirect())
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'cracksteam456-voice-studio'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    with opener.open(Request(PACK_RELEASE, headers=headers), timeout=30) as response:
        release = json.loads(response.read(1_000_000))
    asset = next(a for a in release['assets'] if a['name'] == PACK_NAME)
    url = asset['url']
    if urlsplit(url).hostname != 'api.github.com' or not url.startswith('https://api.github.com/'):
        raise ValueError('Địa chỉ release không hợp lệ.')
    headers['Accept'] = 'application/octet-stream'
    try:
        response = opener.open(Request(url, headers=headers), timeout=45)
    except HTTPError as error:
        if error.code not in (301, 302, 303, 307, 308):
            raise
        url = error.headers['Location']
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or parsed.hostname not in ('release-assets.githubusercontent.com', 'objects.githubusercontent.com'):
            raise ValueError('Địa chỉ tải release không hợp lệ.') from None
        response = opener.open(Request(url, headers={'User-Agent': headers['User-Agent']}), timeout=45)
    with response, tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / PACK_NAME
        with path.open('wb') as output:
            total = 0
            while data := response.read(256 * 1024):
                total += len(data)
                if total > 40_000_000:
                    raise ValueError('Gói tải vượt 40 MB.')
                output.write(data)
        return unpack_voice_pack(path, destination)


def load_voice_pack():
    for root in (Path('outputs/hot-voices'), Path('/content/hot-voices')):
        if (root / 'catalog.json').exists():
            return root.resolve(), read_voice_pack(root)
    target = Path('/content/hot-voices') if Path('/content').is_dir() else Path('outputs/hot-voices')
    if Path(PACK_NAME).exists():
        root = unpack_voice_pack(PACK_NAME, target)
        return root, read_voice_pack(root)
    token = os.environ.get('GITHUB_TOKEN', '')
    if not token and Path('/content').is_dir():
        try:
            from google.colab import userdata
            token = userdata.get('GITHUB_TOKEN')
        except Exception:
            pass
    if not token:
        from getpass import getpass
        print('Repo private: dùng GitHub token quyền Contents: Read cho cracksteam456/voice-studio. '
              'Để trống để tải ZIP từ máy lên Colab. Token không được lưu.', flush=True)
        token = getpass('GitHub token (ẩn, hoặc Enter để chọn ZIP): ').strip()
    if token:
        try:
            root = download_voice_pack(token, target)
        except HTTPError as error:
            raise RuntimeError(f'GitHub HTTP {error.code}: kiểm tra token có quyền đọc repo private.') from None
    else:
        from google.colab import files
        print('Chọn hot-voices-150.zip (24 MB) đã tải từ GitHub Release.', flush=True)
        uploaded = files.upload()
        if PACK_NAME not in uploaded:
            raise ValueError('Cần chọn đúng file ' + PACK_NAME)
        root = unpack_voice_pack(PACK_NAME, target)
    return root, read_voice_pack(root)
