"""Index and bundle the 150 checked-in samples for Colab."""
import hashlib
import json
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parent
pack = root / 'outputs/hot-voices'
catalog_path = pack / 'catalog.json'
catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
assert len(catalog) == 150
assert len({v['voice_id'] for v in catalog}) == 150
for entry in catalog:
    matches = list((pack / entry['group']).glob('*-' + entry['voice_id'] + '.*'))
    if len(matches) != 1:
        raise ValueError('Cannot identify one sample for ' + entry['voice_id'])
    path = matches[0]
    entry['sample_file'] = path.relative_to(pack).as_posix()
    entry['sample_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
archive = root / 'outputs/hot-voices-150.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
    for path in pack.rglob('*'):
        if path.is_file():
            bundle.write(path, path.relative_to(pack).as_posix())
print(f'Bundled {len(catalog)} indexed samples: {archive.name}, {archive.stat().st_size / 1_000_000:.2f} MB')
