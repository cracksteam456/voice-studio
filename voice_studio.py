"""Colab UI; run after loading `model` and `OmniVoiceGenerationConfig`."""
from collections import OrderedDict
from pathlib import Path
import json
import re
import subprocess
import tempfile
import time
import zipfile
from urllib.request import urlretrieve

import gradio as gr
import numpy as np
import soundfile as sf
import torch

VOICES = {
    'Nam công nghệ': 'nam-cong-nghe',
    'Minh Anh': 'minh-anh',
    'Thanh niên tự tin': 'thanh-nien-tu-tin',
    'Nam trầm ấm': 'nam-tram-am',
    'Adam': 'adam',
    'Ngọc Huyền': 'ngoc-huyen',
    'Nhỏ Ngọt Ngào': 'nho-ngot-ngao',
}
LANGUAGES = {'Tiếng Việt': 'vi', 'English': 'en', '日本語': 'ja', '한국어': 'ko',
             '中文': 'zh', 'Français': 'fr', 'Deutsch': 'de', 'Español': 'es'}
SAMPLE_ROOT = Path('samples')
SAMPLE_ROOT.mkdir(exist_ok=True)
PROMPTS = OrderedDict()
SR = model.sampling_rate


def sample_path(name):
    if name not in VOICES:
        raise gr.Error('Chọn một giọng trong danh sách.')
    path = SAMPLE_ROOT / (VOICES[name] + '.mp3')
    if not path.exists():
        urlretrieve('https://raw.githubusercontent.com/doanquangkien/voice-notebooks/main/samples/' + path.name, path)
    return str(path)


def import_text(path):
    if not path:
        raise gr.Error('Chọn file TXT trước.')
    path = Path(path)
    if path.stat().st_size > 1_000_000:
        raise gr.Error('File TXT quá lớn (tối đa 1 MB).')
    try:
        return path.read_text(encoding='utf-8-sig')
    except UnicodeError:
        raise gr.Error('Lưu file TXT bằng UTF-8 rồi thử lại.') from None


def split_text(text, limit):
    """Preserve every word, splitting at blank lines, sentences, then spaces."""
    chunks = []
    for paragraph in re.split(r'\n\s*\n', text.strip()):
        words = paragraph.split()
        current = ''
        for word in words:
            if len(word) > limit:
                raise ValueError('Có một từ quá dài. Hãy thêm khoảng trắng vào văn bản.')
            if current and len(current) + len(word) + 1 > limit:
                chunks.append(current)
                current = ''
            current = (current + ' ' + word).strip()
            if len(current) >= limit * 0.6 and re.search(r'[.!?…。！？][\"\u201d\u2019]?$' , word):
                chunks.append(current)
                current = ''
        if current:
            chunks.append(current)
    return chunks


def get_prompt(name, custom, reference_text):
    reference_text = reference_text or ''
    path = custom if custom else sample_path(name)
    if not Path(path).is_file():
        raise gr.Error('Không tìm thấy file giọng mẫu.')
    if Path(path).stat().st_size > 25_000_000:
        raise gr.Error('Giọng mẫu tối đa 25 MB; nên dùng đoạn sạch dài 3–10 giây.')
    key = (str(path), Path(path).stat().st_mtime_ns, reference_text.strip())
    if key not in PROMPTS:
        kwargs = {'ref_audio': str(path)}
        if reference_text.strip():
            kwargs['ref_text'] = reference_text.strip()
        PROMPTS[key] = model.create_voice_clone_prompt(**kwargs)
        if len(PROMPTS) > 8:
            PROMPTS.popitem(last=False)
    PROMPTS.move_to_end(key)
    return PROMPTS[key]


def synthesize(text, name, custom, reference_text, language, speed, pause,
               steps, guidance, denoise, seed, chunk_size, mp3, progress=gr.Progress()):
    text = (text or '').strip()
    if not text:
        raise gr.Error('Nhập văn bản hoặc nạp file TXT trước.')
    if len(text) > 100_000:
        raise gr.Error('Tối đa 100.000 ký tự mỗi lần; hãy chia kịch bản thành nhiều lượt.')
    try:
        chunks = split_text(text, int(chunk_size))
    except ValueError as error:
        raise gr.Error(str(error)) from error
    if language not in LANGUAGES:
        raise gr.Error('Chọn ngôn ngữ trong danh sách.')
    progress(0, desc='Chuẩn bị giọng mẫu…')
    started = time.monotonic()
    try:
        prompt = get_prompt(name, custom, reference_text)
        config = OmniVoiceGenerationConfig(
            num_step=int(steps), guidance_scale=float(guidance), denoise=bool(denoise),
            preprocess_prompt=True, postprocess_output=True,
            position_temperature=5.0, class_temperature=0.2,
            pad_duration=0.1, fade_duration=0.1,
        )
        output = Path(tempfile.mkdtemp(prefix='voice-studio-'))
        audio_parts, manifest, segment_files = [], [], []
        cursor = 0.0
        with torch.random.fork_rng():
            if int(seed) >= 0:
                torch.manual_seed(int(seed))
            for index, chunk in enumerate(chunks):
                progress(index / len(chunks), desc=f'Đang đọc đoạn {index + 1}/{len(chunks)}')
                audio = np.asarray(model.generate(
                    text=chunk, voice_clone_prompt=prompt, language=LANGUAGES[language],
                    speed=float(speed), generation_config=config,
                )[0], dtype=np.float32).reshape(-1)
                if not audio.size or not np.isfinite(audio).all():
                    raise RuntimeError(f'Âm thanh đoạn {index + 1} không hợp lệ.')
                audio = np.clip(audio, -1, 1)
                segment = output / f'doan-{index + 1:03d}.wav'
                sf.write(segment, audio, SR, subtype='PCM_16')
                segment_files.append(segment)
                duration = len(audio) / SR
                manifest.append({'segment': index + 1, 'text': chunk, 'start': cursor, 'end': cursor + duration})
                audio_parts.append(audio)
                cursor += duration
                if index < len(chunks) - 1:
                    silence = np.zeros(round(SR * float(pause)), dtype=np.float32)
                    audio_parts.append(silence)
                    cursor += len(silence) / SR
        wav = output / 'giong-doc.wav'
        sf.write(wav, np.concatenate(audio_parts), SR, subtype='PCM_16')
        (output / 'kich-ban.txt').write_text(text, encoding='utf-8')
        (output / 'cac-doan.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        settings = dict(voice='Giọng riêng' if custom else name, language=language, speed=speed,
                        pause=pause, steps=steps, guidance=guidance, denoise=denoise,
                        seed=seed, chunk_size=chunk_size, sample_rate=SR)
        (output / 'thiet-lap.json').write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding='utf-8')
        downloads = [str(wav)]
        export_notice = ''
        if mp3:
            mp3_path = output / 'giong-doc.mp3'
            try:
                subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(wav), '-b:a', '192k', str(mp3_path)],
                               check=True, capture_output=True, timeout=120)
                downloads.append(str(mp3_path))
            except (OSError, subprocess.SubprocessError):
                export_notice = ' Chưa xuất được MP3; WAV và ZIP vẫn dùng được.'
        archive = output / 'goi-giong-doc.zip'
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
            for path in segment_files + [output / 'kich-ban.txt', output / 'cac-doan.json', output / 'thiet-lap.json']:
                bundle.write(path, path.name)
        downloads.append(str(archive))
        progress(1, desc='Hoàn tất')
        return str(wav), downloads, f'Đã tạo {cursor:.1f} giây • {len(chunks)} đoạn • {time.monotonic() - started:.1f} giây xử lý.{export_notice}'
    except torch.cuda.OutOfMemoryError:
        torch.cuda.empty_cache()
        raise gr.Error('GPU hết bộ nhớ. Giảm độ dài mỗi đoạn hoặc khởi động lại phiên.') from None


with gr.Blocks(title='Voice Studio — Giọng đọc tiếng Việt') as demo:
    gr.Markdown('# Voice Studio\nTạo lời thuyết minh cho video · 7 giọng có sẵn hoặc giọng mẫu của bạn')
    with gr.Row():
        with gr.Column(scale=3, min_width=280):
            script = gr.Textbox(label='Kịch bản', lines=12, placeholder='Dán nội dung cần đọc. Dùng dòng trống để tách đoạn.')
            with gr.Row():
                text_file = gr.File(label='Nhập kịch bản TXT (UTF-8)', file_types=['.txt'], type='filepath')
                load_text = gr.Button('Nạp văn bản')
            with gr.Row():
                create = gr.Button('Tạo giọng nói', variant='primary')
                clear = gr.ClearButton([script], value='Xóa văn bản')
            status = gr.Textbox(label='Trạng thái', value='Sẵn sàng. Chọn giọng, nhập văn bản rồi bấm tạo.', interactive=False)
            result = gr.Audio(label='Nghe kết quả', type='filepath', format='wav')
            files = gr.File(label='Tải WAV / MP3 / ZIP từng đoạn', file_count='multiple', interactive=False)
        with gr.Column(scale=2, min_width=280):
            voice = gr.Dropdown(list(VOICES), value='Nam công nghệ', label='Giọng có sẵn')
            preview = gr.Button('Nghe giọng mẫu')
            sample = gr.Audio(label='Giọng mẫu có sẵn', interactive=False)
            with gr.Accordion('Dùng giọng mẫu riêng', open=False):
                gr.Markdown('Tải đoạn giọng sạch dài khoảng 3–10 giây. Khi có file, giọng riêng sẽ được ưu tiên. Xóa file để quay lại giọng có sẵn.')
                custom = gr.Audio(label='Giọng mẫu của bạn', sources=['upload'], type='filepath')
                ref_text = gr.Textbox(label='Lời nói trong mẫu (không bắt buộc)', lines=2,
                                      placeholder='Để trống để tự nhận dạng; điền đúng lời giúp giảm thời gian chuẩn bị.')
            lang = gr.Dropdown(list(LANGUAGES), value='Tiếng Việt', label='Ngôn ngữ đọc')
            speed = gr.Slider(0.6, 1.5, value=0.95, step=0.05, label='Tốc độ đọc (1 = bình thường)')
            pause = gr.Slider(0, 2, value=0.3, step=0.1, label='Khoảng nghỉ giữa các đoạn (giây)')
            mp3 = gr.Checkbox(value=True, label='Xuất thêm MP3')
            with gr.Accordion('Chất lượng và văn bản dài', open=False):
                steps = gr.Radio([16, 32, 64], value=32, label='Số bước (16 nhanh · 32 cân bằng · 64 chậm hơn)')
                guidance = gr.Slider(1, 4, value=1.8, step=0.1, label='Guidance — mức bám giọng mẫu')
                denoise = gr.Checkbox(value=True, label='Giảm nhiễu giọng đọc')
                chunk_size = gr.Slider(150, 1000, value=400, step=50, label='Độ dài tối đa mỗi đoạn (ký tự)')
                seed = gr.Number(value=-1, precision=0, label='Seed (-1 = ngẫu nhiên; cùng seed giúp tái tạo)')
    gr.Markdown('ZIP gồm WAV từng đoạn, kịch bản, thiết lập và mốc thời gian từng đoạn (không phải phụ đề theo từ). '
                'File tạo ra nằm tạm trên Colab; tải về trước khi phiên kết thúc.')
    preview.click(sample_path, voice, sample, queue=False)
    load_text.click(import_text, text_file, script, queue=False)
    create.click(synthesize, [script, voice, custom, ref_text, lang, speed, pause, steps, guidance,
                             denoise, seed, chunk_size, mp3], [result, files, status], concurrency_limit=1)

demo.queue(default_concurrency_limit=1, max_size=10)
demo.launch(share=True, debug=False)
