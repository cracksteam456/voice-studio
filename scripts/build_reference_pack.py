"""Bundle the eight references and optional 150-voice archive without changing audio."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

VOICES = {
    "nam-cong-nghe": "Nam công nghệ",
    "minh-anh": "Minh Anh",
    "thanh-nien-tu-tin": "Thanh niên tự tin",
    "nam-tram-am": "Nam trầm ấm",
    "adam": "Adam",
    "ngoc-huyen": "Ngọc Huyền",
    "nho-ngot-ngao": "Nhỏ Ngọt Ngào",
    "kien": "Kiên",
}


def build(source, destination, archive, hot_voices=None):
    source, destination, archive = Path(source), Path(destination), Path(archive)
    destination.mkdir(parents=True, exist_ok=True)
    entries = []
    for slug, label in VOICES.items():
        path = source / f"{slug}.mp3"
        data = path.read_bytes()
        if not 0 < len(data) <= 20 * 1024 * 1024:
            raise ValueError(f"Mẫu không hợp lệ: {path.name}")
        target = destination / path.name
        if target.resolve() != path.resolve():
            shutil.copy2(path, target)
        entries.append({"name": label, "file": path.name, "transcript": "", "group": "preset",
                        "sha256": hashlib.sha256(data).hexdigest()})
    catalog = destination / "catalog.json"
    catalog.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    files = [(destination / entry["file"], entry["file"]) for entry in entries]
    if hot_voices is not None:
        root = Path(hot_voices).resolve()
        hot = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
        if len(hot) != 150 or len({entry["voice_id"] for entry in hot}) != 150:
            raise ValueError("Bộ giọng hot cần đủ 150 ID riêng biệt.")
        for entry in hot:
            path = (root / entry["sample_file"]).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                raise ValueError("Đường dẫn giọng hot không hợp lệ.")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != entry["sample_sha256"]:
                raise ValueError("Sai checksum giọng hot: " + entry["name"])
            filename = f"hot-{entry['voice_id'].lower()}{path.suffix.lower()}"
            entries.append({"name": entry["name"].strip(), "file": filename,
                            "transcript": "", "sha256": digest, "group": entry["group"],
                            "voice_id": entry["voice_id"], "language": entry.get("primary_language"),
                            "clone_permission": entry.get("clone_permission", "unknown")})
            files.append((path, filename))
    if len({entry["file"] for entry in entries}) != len(entries):
        raise ValueError("Trùng tên tệp trong bộ giọng.")
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("catalog.json", json.dumps(entries, ensure_ascii=False, indent=2))
        for path, filename in files:
            bundle.write(path, filename)
    print(f"Built {len(entries)} references: {archive.name} ({archive.stat().st_size:,} bytes)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--hot-voices", type=Path, help="Folder containing the original 150-voice catalog")
    args = parser.parse_args()
    build(args.source, args.destination, args.archive, args.hot_voices)
