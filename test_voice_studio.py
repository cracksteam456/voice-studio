"""CPU checks of the actual text splitting and exports without downloading a model."""
import ast
from pathlib import Path
import re
import unittest


source = (Path(__file__).parent / 'voice_studio.py').read_text(encoding='utf-8')
tree = ast.parse(source)
namespace = {'re': re}
function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'split_text')
exec(compile(ast.Module(body=[function], type_ignores=[]), '<split_text>', 'exec'), namespace)
split_text = namespace['split_text']


class ChunkTests(unittest.TestCase):
    def test_optional_reference_text_accepts_none(self):
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'get_prompt')
        setup = ast.Module(body=function.body[:1], type_ignores=[])
        values = {'reference_text': None}
        exec(compile(setup, '<optional-reference-text>', 'exec'), values)
        self.assertEqual(values['reference_text'], '')

    def test_preserves_words_and_limits(self):
        text = ('Xin chào! Đây là kịch bản tiếng Việt. ' * 60) + '\n\nĐoạn cuối. ' * 3
        chunks = split_text(text, 150)
        self.assertEqual(' '.join(text.split()), ' '.join(chunks))
        self.assertTrue(all(0 < len(chunk) <= 150 for chunk in chunks))

    def test_repeated_paragraphs_are_preserved(self):
        self.assertEqual(split_text('Lặp lại.\n\nLặp lại.', 150), ['Lặp lại.', 'Lặp lại.'])

    def test_empty_and_oversized_word(self):
        self.assertEqual(split_text(' \n ', 150), [])
        with self.assertRaises(ValueError):
            split_text('a' * 151, 150)


if __name__ == '__main__':
    unittest.main()
