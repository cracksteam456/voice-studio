"""Bundle the editable UI source into the standalone Colab notebook."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent
path = root / 'colab_nam-cong-nghe-ban-rieng.ipynb'
notebook = json.loads(path.read_text(encoding='utf-8'))
startup = ''.join(notebook['cells'][3]['source']).split('def generate_voice(text):')[0]
startup = startup.split('generation_config = OmniVoiceGenerationConfig(')[0]
startup = startup.split("voice_prompt = model.create_voice_clone_prompt(")[0]
if "if 'model' not in globals():" not in startup:
    startup = startup.replace(
        "model = OmniVoice.from_pretrained('k2-fsa/OmniVoice', device_map=device, dtype=torch.float16, load_asr=True)",
        "if 'model' not in globals():\n    model = OmniVoice.from_pretrained('k2-fsa/OmniVoice', device_map=device, dtype=torch.float16, load_asr=True)",
    )
notebook['cells'][0]['source'] = [
    '# Voice Studio — Bản riêng\n',
    '\n',
    '7 giọng có sẵn · tải giọng mẫu riêng · nhập TXT · chỉnh tốc độ và khoảng nghỉ · WAV/MP3 · ZIP từng đoạn.\n',
    '\n',
    '1. Chọn **Runtime → Change runtime type → T4 GPU**.\n',
    '2. Chạy ô cài đặt, rồi chọn **Runtime → Restart session**.\n',
    '3. Chạy ô khởi động model, rồi ô giao diện cuối cùng.\n',
    '4. Nhập nội dung, chọn giọng, bấm **Tạo giọng nói** và tải kết quả.\n',
    '\n',
    'Mỗi phiên chỉ tải model một lần. Khi đổi giọng hoặc tốc độ, dùng giao diện, không chạy lại ô model.\n',
    'Giữ Colab hoạt động khi dùng link giao diện. Các file âm thanh là file tạm; tải về trước khi ngắt phiên.\n',
]
notebook['cells'][3]['source'] = startup.splitlines(keepends=True)
notebook['cells'] = notebook['cells'][:4]
notebook['cells'].extend([
    {'cell_type': 'markdown', 'metadata': {}, 'source': ['## Mở Voice Studio\n', 'Chạy sau khi ô model hoàn tất. Có thể chạy lại ô này để mở lại giao diện mà không tải lại model.']},
    {'cell_type': 'code', 'metadata': {}, 'execution_count': None, 'outputs': [],
     'source': ("if 'demo' in globals():\n    demo.close()\n\n" + (root / 'voice_studio.py').read_text(encoding='utf-8')).splitlines(keepends=True)},
])
for cell in notebook['cells']:
    if cell['cell_type'] == 'code':
        cell['execution_count'] = None
        cell['outputs'] = []
path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print(f'Bundled {len(notebook["cells"])} cells: {path.name}')
