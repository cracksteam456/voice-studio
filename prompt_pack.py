"""Portable OmniVoice prompts, pinned to one model checkpoint and audio content."""

import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import re
import tempfile
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import zipfile

MODEL_ID = "k2-fsa/OmniVoice"
MODEL_REVISION = "c5fdb5ccb189668d56333f77ba2629f4cd7535f4"
OMNIVOICE_VERSION = "0.2.1"
IDENTITY = {"format": 1, "model": MODEL_ID, "revision": MODEL_REVISION,
            "omnivoice": OMNIVOICE_VERSION, "preprocess_prompt": True}
PACK_URL = "https://github.com/cracksteam456/voice-studio/releases/download/vietvoice-prompts-v1/vietvoice-prompts.zip"
MAX_PROMPT = 2 * 1024 * 1024
MAX_PACK = 64 * 1024 * 1024


def audio_key(reference_audio, transcript=""):
    audio, rate = reference_audio
    digest = hashlib.sha256(audio.astype("<f4", copy=False).tobytes()).hexdigest()
    return hashlib.sha256(f"{digest}:{rate}:{transcript.strip()}".encode("utf-8")).hexdigest()


def load_prompt(path):
    import torch
    from omnivoice import VoiceClonePrompt

    if importlib.metadata.version("omnivoice") != OMNIVOICE_VERSION:
        raise ValueError("Prompt cần OmniVoice " + OMNIVOICE_VERSION)
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_PROMPT:
        raise ValueError("Prompt giọng vượt giới hạn hoặc không tồn tại.")
    # Upstream uses torch.load(weights_only=True, map_location='cpu').
    prompt = VoiceClonePrompt.load(str(path), map_location="cpu")
    tokens = prompt.ref_audio_tokens
    if (not isinstance(tokens, torch.Tensor) or tokens.ndim != 2
            or tokens.dtype not in (torch.int32, torch.int64)
            or not 1 <= tokens.shape[0] <= 64 or not 1 <= tokens.shape[1] <= 10000
            or tokens.min().item() < 0 or tokens.max().item() > 65535
            or not isinstance(prompt.ref_text, str) or not 0 < len(prompt.ref_text) <= 4000
            or not math.isfinite(prompt.ref_rms) or not 0 < prompt.ref_rms <= 10):
        raise ValueError("Dữ liệu prompt giọng không hợp lệ.")
    return prompt


def read_manifest(root):
    root = Path(root)
    path = root / "manifest.json"
    if not path.is_file() or path.stat().st_size > 1_000_000:
        raise ValueError("Thiếu danh sách prompt hoặc danh sách vượt giới hạn.")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or any(manifest.get(k) != v for k, v in IDENTITY.items()):
        raise ValueError("Gói prompt khác phiên bản mô hình; cần phân tích lại bộ giọng.")
    entries = manifest.get("voices")
    if not isinstance(entries, list) or not 1 <= len(entries) <= 200:
        raise ValueError("Danh sách prompt không hợp lệ.")
    seen = set()
    for entry in entries:
        if (not isinstance(entry, dict) or not re.fullmatch(r"[0-9a-f]{64}", entry.get("source_sha256", ""))
                or not re.fullmatch(r"[0-9a-f]{64}", entry.get("key", ""))
                or not re.fullmatch(r"[0-9a-f]{64}", entry.get("prompt_sha256", ""))
                or entry["source_sha256"] in seen):
            raise ValueError("Checksum hoặc khóa prompt không hợp lệ.")
        seen.add(entry["source_sha256"])
        prompt = root / (entry["key"] + ".pt")
        if (not prompt.is_file() or prompt.is_symlink() or prompt.stat().st_size > MAX_PROMPT
                or hashlib.sha256(prompt.read_bytes()).hexdigest() != entry["prompt_sha256"]):
            raise ValueError("Prompt thiếu hoặc sai checksum.")
    return entries


def import_pack(archive, destination, library):
    destination = Path(destination)
    if destination.exists():
        raise ValueError("Thư mục đích prompt phải là thư mục mới.")
    with zipfile.ZipFile(archive) as bundle:
        infos = bundle.infolist()
        if (not infos or len(infos) > 201 or len({i.filename for i in infos}) != len(infos)
                or sum(i.file_size for i in infos) > MAX_PACK):
            raise ValueError("Gói prompt vượt giới hạn hoặc có tệp trùng.")
        for info in infos:
            if (not re.fullmatch(r"(?:manifest\.json|[0-9a-f]{64}\.pt)", info.filename)
                    or info.file_size > (1_000_000 if info.filename == "manifest.json" else MAX_PROMPT)
                    or (info.external_attr >> 16) & 0o170000 == 0o120000):
                raise ValueError("Đường dẫn prompt không an toàn.")
        bundle.extractall(destination)
    prompts = {entry["source_sha256"]: entry for entry in read_manifest(destination)}
    count = 0
    for voice in library:
        entry = prompts.get(voice["sha256"])
        if entry:
            voice["prompt_key"] = entry["key"]
            voice["prompt_path"] = str(destination / (entry["key"] + ".pt"))
            count += 1
    return count


def download_prompts(library):
    root = Path(tempfile.mkdtemp(prefix="vietvoice-prompts-")) / "prompts"
    try:
        response = urlopen(Request(PACK_URL, headers={"User-Agent": "VietVoice-Studio"}), timeout=60)
    except HTTPError as exc:
        if exc.code == 404:
            print("Gói prompt GitHub chưa được xuất bản; phiên này phân tích rồi lưu vào RAM.")
            return library
        raise
    with response, tempfile.TemporaryFile() as archive:
        count = 0
        while block := response.read(256 * 1024):
            count += len(block)
            if count > MAX_PACK:
                raise ValueError("Gói prompt tải về vượt 64 MB.")
            archive.write(block)
        archive.seek(0)
        restored = import_pack(archive, root, library)
    print(f"Đã tải prompt phân tích sẵn cho {restored}/{len(library)} giọng; các giọng này không cần Whisper.")
    return library


def prepare_pack(engine, library, destination="/content/vietvoice-prepared", report=print):
    """Prepare only public library entries; never include custom uploaded voices."""
    from voice_core import Settings, read_reference

    if importlib.metadata.version("omnivoice") != OMNIVOICE_VERSION:
        raise ValueError("Cần OmniVoice " + OMNIVOICE_VERSION)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    manifest_path = destination / "manifest.json"
    existing = {entry["source_sha256"]: entry for entry in read_manifest(destination)} if manifest_path.exists() else {}
    engine._load_model()
    actual = str(getattr(engine.model.config, "_name_or_path", ""))
    if MODEL_REVISION not in actual:
        raise ValueError("Mô hình đang nạp khác checkpoint đã khóa; chạy lại ô 2 trong phiên mới.")
    for index, voice in enumerate(library):
        reference = Path(voice["path"])
        if hashlib.sha256(reference.read_bytes()).hexdigest() != voice["sha256"]:
            raise ValueError("Giọng mẫu đã thay đổi: " + voice["name"])
        report(f"{index + 1}/{len(library)} · {voice['name']}")
        if voice["sha256"] in existing:
            continue
        audio = read_reference(str(reference))
        key = audio_key(audio)
        with engine._lock:
            prompt = engine._get_prompt(audio, "", Settings(), lambda value, message: None)
        target = destination / (key + ".pt")
        prompt.save(str(target))
        load_prompt(target)
        existing[voice["sha256"]] = {"name": voice["name"], "source_sha256": voice["sha256"],
                                     "key": key, "prompt_sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
        pending = destination / "manifest.json.tmp"
        pending.write_text(json.dumps({**IDENTITY, "voices": list(existing.values())},
                                      ensure_ascii=False, indent=2), encoding="utf-8")
        pending.replace(manifest_path)
    # Export exactly this library, even if the checkpoint folder contains older entries.
    selected = [existing[voice["sha256"]] for voice in library]
    archive = destination.parent / "vietvoice-prompts.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("manifest.json", json.dumps({**IDENTITY, "voices": selected}, ensure_ascii=False, indent=2))
        for key in {entry["key"] for entry in selected}:
            bundle.write(destination / (key + ".pt"), key + ".pt")
    report(f"Đã xuất {len(selected)} giọng · {archive.stat().st_size:,} byte · {archive}")
    return str(archive)
