"""Build a local side-by-side listening page from the downloaded pilot results."""
from html import escape
import json
from pathlib import Path


def build(root):
    report = json.loads((root / 'report.json').read_text(encoding='utf-8'))
    metrics_path = root / 'asr-evaluation.json'
    metrics = json.loads(metrics_path.read_text(encoding='utf-8'))['checks'] if metrics_path.exists() else []
    indexed = {(item['folder'], item['file']): item for item in metrics}
    sections = []
    for voice in report['voices']:
        folder = voice['folder']
        assert folder.startswith('voice-') and folder[6:].isdigit()
        references = ''.join(
            f'<p>{escape(window["text"])}</p><audio controls preload="none" src="{folder}/reference-{index}.wav"></audio>'
            for index, window in enumerate(voice.get('references', []), 1))
        outputs = []
        for item in voice['outputs']:
            name = item['file']
            assert Path(name).name == name
            check = indexed.get((folder, name))
            details = (f'<p>WER tự động: {check["wer"]:.1%}</p><details><summary>Lời Whisper nhận được</summary>'
                       f'<p>{escape(check["transcribed"])}</p></details>') if check else ''
            outputs.append(f'<div class="output"><h3>Câu {item["text_index"]} · seed {item["seed"]}</h3>'
                           f'<p>{escape(report["texts"][item["text_index"] - 1])}</p>'
                           f'<audio controls preload="none" src="{folder}/{escape(name, quote=True)}"></audio>{details}</div>')
        sections.append(f'<section><h2>{escape(voice["name"])}</h2><div class="columns"><div>'
                        f'<h3>Preview gốc</h3><audio controls preload="none" src="{folder}/preview.mp3"></audio>'
                        f'<h3>Đoạn dùng để clone</h3>{references}</div><div>{"".join(outputs)}</div></div></section>')
    html = '''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>So sánh 10 giọng clone</title><style>
body{font:16px/1.6 system-ui,sans-serif;margin:auto;padding:24px;max-width:1120px;background:#f6f7f8;color:#20252b}
h1{font-size:28px}h2{font-size:22px;margin-top:0}h3{font-size:16px}section{background:white;border:1px solid #d5dbe0;padding:24px;margin:24px 0;border-radius:8px}
.columns{display:grid;grid-template-columns:1fr 1.5fr;gap:32px}.output{border-bottom:1px solid #ddd;padding-bottom:16px}audio{width:100%}summary{cursor:pointer;color:#154f7d}
@media(max-width:700px){.columns{grid-template-columns:1fr}body{padding:12px}section{padding:16px}}
</style><h1>So sánh 10 giọng clone</h1><p>Nghe preview gốc, đoạn tham chiếu và bốn đầu ra. WER do Whisper chấm chỉ là kiểm tra lời đọc; chưa đánh giá độ giống giọng hoặc chất lượng nghe. Quyền clone ngoài nền tảng của các mẫu chưa được xác minh.</p>'''
    (root / 'listen.html').write_text(html + ''.join(sections) + '</html>', encoding='utf-8')


if __name__ == '__main__':
    build(Path(__file__).parent / 'pilot/results')
    print('Built pilot/results/listen.html')
