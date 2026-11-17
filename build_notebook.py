"""Bundle the editable UI source into the standalone Colab notebook."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent
path = root / 'colab_nam-cong-nghe-ban-rieng.ipynb'
notebook = json.loads(path.read_text(encoding='utf-8'))
startup = (root / 'studio_startup.py').read_text(encoding='utf-8')
notebook['cells'][0]['source'] = [
    '# cracksteam456 Voice Studio\n',
    '\n',
    'Phát triển và duy trì bởi [cracksteam456](https://github.com/cracksteam456/voice-studio).\n',
    '\n',
    '150 giọng hot · lọc nhóm/ngôn ngữ · tải giọng mẫu riêng · TXT · WAV/MP3 · ZIP từng đoạn.\n',
    '\n',
    '1. Chọn **Runtime → Change runtime type → T4 GPU**.\n',
    'Nếu chỉ có CPU, notebook vẫn chạy nhưng tạo giọng sẽ chậm hơn.\n',
    '2. Chạy ô cài đặt, rồi chọn **Runtime → Restart session**.\n',
    '3. Chạy ô khởi động model, rồi ô giao diện cuối cùng.\n',
    'Bộ 150 giọng tải từ GitHub Release của cracksteam456: đặt GITHUB_TOKEN trong Colab Secrets (quyền đọc repo private), hoặc chọn ZIP từ máy.\n',
    '4. Nhập nội dung, chọn giọng, bấm **Tạo giọng nói** và tải kết quả.\n',
    '\n',
    'Mỗi phiên chỉ tải model một lần. Khi đổi giọng hoặc tốc độ, dùng giao diện, không chạy lại ô model.\n',
    'Giữ Colab hoạt động khi dùng link giao diện. Các file âm thanh là file tạm; tải về trước khi ngắt phiên.\n',
]
notebook['cells'][3]['source'] = startup.splitlines(keepends=True)
setup = ''.join(notebook['cells'][1]['source']).split('from pathlib import Path')[0]
setup += "\nprint('Đã cài thư viện. Chọn Runtime → Restart session, rồi chạy ô khởi động model.')\n"
notebook['cells'][1]['source'] = setup.splitlines(keepends=True)
notebook['metadata']['authors'] = [{'name': 'cracksteam456'}]
notebook['cells'] = notebook['cells'][:4]
notebook['cells'].extend([
    {'cell_type': 'markdown', 'metadata': {}, 'source': ['## Mở Voice Studio\n', 'Chạy sau khi ô model hoàn tất. Có thể chạy lại ô này để mở lại giao diện mà không tải lại model.']},
    {'cell_type': 'code', 'metadata': {}, 'execution_count': None, 'outputs': [],
     'source': ("if 'demo' in globals():\n    demo.close()\n\n" + (root / 'voice_assets.py').read_text(encoding='utf-8') + '\n\n' + (root / 'voice_studio.py').read_text(encoding='utf-8')).splitlines(keepends=True)},
])
for cell in notebook['cells']:
    if cell['cell_type'] == 'code':
        cell['execution_count'] = None
        cell['outputs'] = []
path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print(f'Bundled {len(notebook["cells"])} cells: {path.name}')
