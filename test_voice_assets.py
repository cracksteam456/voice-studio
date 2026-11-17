import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from voice_assets import read_voice_pack, unpack_voice_pack


class PackTests(unittest.TestCase):
    def test_actual_pack_and_checksums(self):
        root = Path(__file__).parent / 'outputs/hot-voices'
        entries = read_voice_pack(root)
        self.assertEqual(len({v['voice_id'] for v in entries}), 150)
        self.assertEqual(sum(v['primary_language'] == 'vi' for v in entries), 50)

    def test_zip_traversal_rejected_before_extraction(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w') as bundle:
            bundle.writestr('../outside.txt', 'bad')
        archive.seek(0)
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                unpack_voice_pack(archive, Path(folder) / 'pack')
            self.assertFalse((Path(folder) / 'outside.txt').exists())

    def test_corrupt_pack_does_not_replace_existing_catalog(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w') as bundle:
            bundle.writestr('catalog.json', '[]')
        archive.seek(0)
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'pack'
            target.mkdir()
            (target / 'catalog.json').write_text('original')
            with self.assertRaises(ValueError):
                unpack_voice_pack(archive, target)
            self.assertEqual((target / 'catalog.json').read_text(), 'original')


if __name__ == '__main__':
    unittest.main()
