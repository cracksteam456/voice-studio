"""Run inside the pilot notebook after loading `model`; CANDIDATES is embedded."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import subprocess
import time
import zipfile
from urllib.request import Request, HTTPRedirectHandler, build_opener
from urllib.parse import urlsplit
import numpy as np
import soundfile as sf
import torch

TEXTS = [
    'Hôm nay, chúng ta tìm hiểu cách âm thanh truyền qua không khí. Mỗi dao động nhỏ đều có thể mang theo một thông điệp.',
    'Nếu Mặt Trăng biến mất, điều gì sẽ xảy ra với thủy triều? Hãy cùng xem những thay đổi đầu tiên trên Trái Đất.',
]
SEEDS = [42, 123]
DEST = Path('/content/clone-pilot')
DEST.mkdir(exist_ok=True)


def select_windows(chunks):
    """Prefer whole ASR sentence spans, never invent cut points within words."""
    windows = []
    for start in range(len(chunks)):
        first = chunks[start].get('timestamp', [None, None])[0]
        if first is None:
            continue
        for end in range(start, len(chunks)):
            last = chunks[end].get('timestamp', [None, None])[1]
            if last is None:
                continue
            duration = last - first
            if duration > 10:
                break
            if 3 <= duration <= 10:
                text = ' '.join(c['text'].strip() for c in chunks[start:end + 1]).strip()
                if text:
                    windows.append({'start': first, 'end': last, 'text': text})
    windows.sort(key=lambda x: abs(x['end'] - x['start'] - 7))
    selected = []
    for window in windows:
        if all(window['end'] <= old['start'] or window['start'] >= old['end'] for old in selected):
            selected.append(window)
        if len(selected) == 2:
            break
    return selected


config = OmniVoiceGenerationConfig(num_step=32, guidance_scale=1.8,
    denoise=True, preprocess_prompt=True, postprocess_output=True,
    position_temperature=5.0, class_temperature=0.2, pad_duration=0.1, fade_duration=0.1)
report = {'package_version': importlib.metadata.version('omnivoice'),
          'model': 'k2-fsa/OmniVoice', 'sample_rate': model.sampling_rate,
          'model_revision': getattr(model.config, '_commit_hash', None),
          'generation_config': vars(config),
          'gpu': torch.cuda.get_device_name(0), 'texts': TEXTS, 'seeds': SEEDS,
          'clone_permission': 'unknown', 'voices': []}

for number, candidate in enumerate(CANDIDATES, 1):
    folder = DEST / candidate['folder']
    folder.mkdir(exist_ok=True)
    result = {**candidate, 'outputs': [], 'reference_review': 'needs_listening'}
    try:
        if candidate.get('status') != 'preview_downloaded':
            raise ValueError('Preview did not pass local preparation.')
        original = folder / 'preview.mp3'
        if not original.exists():
            parsed = urlsplit(candidate['preview_url'])
            if parsed.scheme != 'https' or parsed.hostname not in {'storage.googleapis.com', 'api.us.elevenlabs.io'}:
                raise ValueError('Unapproved preview URL.')
            class NoRedirect(HTTPRedirectHandler):
                def redirect_request(self, *args, **kwargs):
                    return None
            with build_opener(NoRedirect()).open(Request(candidate['preview_url']), timeout=30) as response:
                data = response.read(25_000_001)
            if not data or len(data) > 25_000_000:
                raise ValueError('Preview file size is invalid.')
            original.write_bytes(data)
        digest = hashlib.sha256(original.read_bytes()).hexdigest()
        if digest != candidate['original_sha256']:
            raise ValueError('Preview changed since preparation; choose a fresh reference.')
        transcription_path = folder / 'transcription.json'
        if transcription_path.exists():
            transcription = json.loads(transcription_path.read_text())
        else:
            transcription = model._asr_pipe(str(original), return_timestamps=True,
                generate_kwargs={'language': 'vi', 'task': 'transcribe'})
            transcription_path.write_text(json.dumps(transcription, ensure_ascii=False, indent=2), encoding='utf-8')
        windows = select_windows(transcription.get('chunks', []))
        if not windows:
            raise ValueError('No complete ASR segment of 3–10s; needs manual reference selection.')
        result['references'] = windows
        for ref_index, window in enumerate(windows, 1):
            ref = folder / f'reference-{ref_index}.wav'
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', str(window['start']),
                '-i', str(original), '-t', str(window['end'] - window['start']),
                '-ac', '1', '-ar', str(model.sampling_rate), '-c:a', 'pcm_s16le', str(ref)], check=True)
            (folder / f'reference-{ref_index}.txt').write_text(window['text'], encoding='utf-8')
            prompt = model.create_voice_clone_prompt(ref_audio=str(ref), ref_text=window['text'])
            prompt.save(str(folder / f'prompt-{ref_index}.pt'))
            for text_index, text in enumerate(TEXTS, 1):
                for seed in SEEDS:
                    out = folder / f'ref-{ref_index}-text-{text_index}-seed-{seed}.wav'
                    started = time.monotonic()
                    if not out.exists():
                        torch.manual_seed(seed)
                        audio = np.asarray(model.generate(text=text, language='vi',
                            voice_clone_prompt=prompt, speed=1.0, generation_config=config)[0])
                        if not audio.size or not np.isfinite(audio).all():
                            raise ValueError('Invalid generated waveform.')
                        sf.write(out, np.clip(audio, -1, 1), model.sampling_rate, subtype='PCM_16')
                    info = sf.info(out)
                    result['outputs'].append({'file': out.name, 'duration': info.duration,
                        'reference': ref_index, 'text_index': text_index, 'seed': seed,
                        'processing_seconds': time.monotonic() - started})
        result['status'] = 'generated_needs_listening'
    except Exception as error:
        result.update(status='failed', error=f'{type(error).__name__}: {error}')
    report['voices'].append(result)
    (folder / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    (DEST / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{number}/{len(CANDIDATES)}: {candidate["name"]} — {result["status"]}', flush=True)

archive = Path('/content/clone-pilot-results.zip')
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
    for path in DEST.rglob('*'):
        if path.is_file() and path.suffix != '.pt':
            bundle.write(path, str(path.relative_to(DEST)))
print('PILOT_COMPLETE', sum(len(v['outputs']) for v in report['voices']), 'WAV outputs', flush=True)
from IPython.display import FileLink, display
display(FileLink(str(archive)))
import gradio as gr
with gr.Blocks(title='Kết quả thử clone') as pilot_results:
    gr.Markdown('# Kết quả thử clone\nTải báo cáo và âm thanh để nghe đối chiếu. Chưa chấm chất lượng giọng.')
    gr.File(value=[str(archive), str(DEST / 'report.json')], label='Tải kết quả', interactive=False)
pilot_results.launch(share=True, debug=False)
