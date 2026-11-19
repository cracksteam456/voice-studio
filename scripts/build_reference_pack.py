"""Build the eight local reference files into a checksummed GitHub Release asset."""

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


def build(source, destination, archive):
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
        entries.append({"name": label, "file": path.name, "transcript": "",
                        "sha256": hashlib.sha256(data).hexdigest()})
    catalog = destination / "catalog.json"
    catalog.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.write(catalog, catalog.name)
        for entry in entries:
            bundle.write(destination / entry["file"], entry["file"])
    print(f"Built {len(entries)} references: {archive.name} ({archive.stat().st_size:,} bytes)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    build(args.source, args.destination, args.archive)
