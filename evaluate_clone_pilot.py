"""Whisper transcript check; run in the same Colab runtime as the pilot."""
from pathlib import Path
import json
import re
import unicodedata
import zipfile


def normalized_words(text):
    text = unicodedata.normalize('NFC', text).casefold()
    return re.findall(r'\w+', text, flags=re.UNICODE)


def edit_distance(expected, actual):
    previous = list(range(len(actual) + 1))
    for i, left in enumerate(expected, 1):
        current = [i]
        for j, right in enumerate(actual, 1):
            current.append(min(current[-1] + 1, previous[j] + 1,
                               previous[j - 1] + (left != right)))
        previous = current
    return previous[-1]


def evaluate(model, root):
    report = json.loads((root / 'report.json').read_text(encoding='utf-8'))
    checks = []
    for voice in report['voices']:
        folder = root / voice['folder']
        for output in voice['outputs']:
            cache = folder / (output['file'] + '.asr.json')
            if cache.exists():
                result = json.loads(cache.read_text(encoding='utf-8'))
            else:
                expected = report['texts'][output['text_index'] - 1]
                actual = model._asr_pipe(str(folder / output['file']),
                    generate_kwargs={'language': 'vi', 'task': 'transcribe'})['text']
                words = normalized_words(expected)
                errors = edit_distance(words, normalized_words(actual))
                result = {'voice': voice['name'], 'folder': voice['folder'], 'file': output['file'],
                    'text_index': output['text_index'], 'seed': output['seed'],
                    'expected': expected, 'transcribed': actual, 'word_errors': errors,
                    'word_count': len(words), 'wer': errors / len(words),
                    'review_status': 'needs_listening', 'metric': 'whitespace-token WER, punctuation removed, NFC/casefold'}
                cache.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
            checks.append(result)
            print(f'ASR {len(checks)}: WER={result["wer"]:.3f} — {voice["folder"]}', flush=True)
    metrics = {'asr_model': getattr(model, '_asr_model_name', None),
               'metric_limitations': 'Whisper errors and Vietnamese word spacing affect scores. This is not speaker similarity or a human quality score.',
               'checks': checks}
    (root / 'asr-evaluation.json').write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding='utf-8')
    return metrics


if __name__ == '__main__':
    root = Path('/content/clone-pilot')
    evaluate(model, root)
    archive = Path('/content/clone-pilot-reviewed.zip')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for path in root.rglob('*'):
            if path.is_file() and path.suffix != '.pt':
                bundle.write(path, str(path.relative_to(root)))
    import gradio as gr
    if 'pilot_results' in globals():
        pilot_results.close()
    with gr.Blocks(title='Kết quả kiểm tra clone') as reviewed_results:
        gr.Markdown('# Kết quả kiểm tra clone\nBáo cáo ASR là kiểm tra tự động, vẫn cần nghe chất lượng và độ giống giọng.')
        gr.File(value=[str(archive), str(root / 'asr-evaluation.json')], interactive=False)
    reviewed_results.launch(share=True, debug=False)
    print('ASR_COMPLETE', flush=True)
