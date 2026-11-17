import ast
from pathlib import Path
import unittest
from prepare_clone_pilot import validate_url
from evaluate_clone_pilot import normalized_words, edit_distance

namespace = {}
tree = ast.parse(Path(__file__).with_name('run_clone_pilot.py').read_text(encoding='utf-8'))
function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'select_windows')
exec(compile(ast.Module(body=[function], type_ignores=[]), '<windows>', 'exec'), namespace)


class PilotTests(unittest.TestCase):
    def test_transcript_normalization_preserves_diacritics(self):
        self.assertEqual(normalized_words('Xin CHÀO, bạn!'), ['xin', 'chào', 'bạn'])
        self.assertEqual(edit_distance(['xin', 'chào'], ['xin', 'cháo']), 1)
        self.assertEqual(edit_distance(['xin', 'chào'], ['xin']), 1)
        self.assertEqual(edit_distance([], ['xin']), 1)

    def test_external_or_local_urls_rejected(self):
        for url in ('http://storage.googleapis.com/x', 'https://127.0.0.1/x',
                    'https://storage.googleapis.com.evil.example/x', 'https://user@storage.googleapis.com/x'):
            with self.assertRaises(ValueError):
                validate_url(url)
        validate_url('https://storage.googleapis.com/eleven-public-prod/test.mp3')

    def test_sentence_boundaries_and_nonoverlap(self):
        chunks = [{'timestamp': [i * 4, i * 4 + 4], 'text': f'Sentence {i}.'} for i in range(4)]
        selected = namespace['select_windows'](chunks)
        self.assertEqual(len(selected), 2)
        self.assertTrue(all(3 <= x['end'] - x['start'] <= 10 for x in selected))
        self.assertLessEqual(selected[0]['end'], selected[1]['start'])
        self.assertEqual(selected[0]['text'], 'Sentence 0. Sentence 1.')

    def test_missing_timestamps_require_manual_selection(self):
        self.assertEqual(namespace['select_windows']([{'timestamp': [0, None], 'text': 'Unknown.'}]), [])


if __name__ == '__main__':
    unittest.main()
