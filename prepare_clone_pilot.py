"""Prepare ten Vietnamese preview references and a standalone Colab pilot."""
import hashlib
import json
from pathlib import Path
import subprocess
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parent
SNAPSHOT = ROOT / 'voice-library/snapshots/20261117T103929553845Z'
PILOT = ROOT / 'pilot'
ALLOWED_HOSTS = {'storage.googleapis.com', 'api.us.elevenlabs.io'}


def validate_url(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in ALLOWED_HOSTS or parsed.username or parsed.password:
        raise ValueError('Preview host is not on the allowlist.')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def download(url, destination):
    validate_url(url)
    with build_opener(NoRedirect()).open(Request(url), timeout=30) as response:
        audio = response.read(25_000_001)
    if not audio or len(audio) > 25_000_000:
        raise ValueError('Preview is empty or exceeds 25 MB.')
    destination.write_bytes(audio)
    return hashlib.sha256(audio).hexdigest()


def probe(path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                             'format=duration:stream=codec_type,sample_rate,channels',
                             '-of', 'json', str(path)], check=True, capture_output=True, text=True)
    info = json.loads(result.stdout)
    if not any(s.get('codec_type') == 'audio' for s in info.get('streams', [])):
        raise ValueError('Preview has no audio stream.')
    return float(info['format']['duration'])


def prepare():
    voices = json.loads((SNAPSHOT / 'shortlists.json').read_text(encoding='utf-8'))['vietnamese_primary_50'][:10]
    PILOT.mkdir(exist_ok=True)
    results = []
    for index, voice in enumerate(voices, 1):
        folder = PILOT / f'voice-{index:02d}'
        folder.mkdir(exist_ok=True)
        record = {**voice, 'folder': folder.name, 'clone_permission': 'unknown',
                  'quality_status': 'not_auditioned', 'reference_selection': 'pending_asr_sentence_boundaries'}
        try:
            original = folder / 'preview.mp3'
            if original.exists():
                validate_url(voice['preview_url'])
                digest = hashlib.sha256(original.read_bytes()).hexdigest()
            else:
                digest = download(voice['preview_url'], original)
            duration = probe(original)
            if not 3 <= duration <= 120:
                raise ValueError(f'Preview duration {duration:.2f}s is outside pilot range 3–120s.')
            record.update(original_sha256=digest, original_duration=duration, status='preview_downloaded')
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            record.update(status='failed', error=str(error))
        (folder / 'metadata.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        results.append(record)
        print(f'{index}/10: {record["status"]}', flush=True)
        (PILOT / 'manifest.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    return results


def build_pilot_notebook(results):
    source = json.loads((ROOT / 'colab_nam-cong-nghe-ban-rieng.ipynb').read_text(encoding='utf-8'))
    setup = source['cells'][1]
    startup = ''.join(source['cells'][3]['source'])
    experiment = (ROOT / 'run_clone_pilot.py').read_text(encoding='utf-8')
    evaluation = (ROOT / 'evaluate_clone_pilot.py').read_text(encoding='utf-8')
    experiment = 'CANDIDATES = ' + repr(results) + '\n\n' + experiment
    notebook = {'cells': [
        {'cell_type': 'markdown', 'metadata': {}, 'source': [
            '# cracksteam456 Voice Studio — Thử nghiệm 10 giọng tiếng Việt\n',
            'Chạy ô cài đặt, Restart session, sau đó chạy ô model và ô thử nghiệm.\n',
            'Dùng preview gốc để đánh giá kỹ thuật; quyền clone ngoài ElevenLabs chưa xác minh. '
            'Kết quả không tự được thêm vào thư viện phát hành. Mẫu được chọn theo mốc câu từ Whisper, cần nghe kiểm tra lại.\n']},
        setup,
        {'cell_type': 'code', 'metadata': {}, 'execution_count': None, 'outputs': [], 'source': startup.splitlines(keepends=True)},
        {'cell_type': 'code', 'metadata': {}, 'execution_count': None, 'outputs': [], 'source': experiment.splitlines(keepends=True)},
        {'cell_type': 'markdown', 'metadata': {}, 'source': ['## Kiểm tra lời đọc bằng Whisper\n', 'Chạy sau bước tổng hợp. WER tự động không phải điểm giống giọng; vẫn cần nghe đối chiếu.']},
        {'cell_type': 'code', 'metadata': {}, 'execution_count': None, 'outputs': [], 'source': evaluation.splitlines(keepends=True)},
    ], 'metadata': source['metadata'], 'nbformat': 4, 'nbformat_minor': 0}
    (ROOT / 'colab_clone_pilot.ipynb').write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


if __name__ == '__main__':
    build_pilot_notebook(prepare())
