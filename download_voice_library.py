"""Resume official shared-catalog discovery and download available preview audio."""
import concurrent.futures
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener

from collect_elevenlabs_catalog import NoRedirect

ROOT = Path(__file__).resolve().parent / 'voice-library' / 'archive'
HOSTS = {'storage.googleapis.com', 'api.us.elevenlabs.io', 'api.elevenlabs.io'}
MAX_FILE = 25_000_000


def safe_url(url):
    parsed = urlsplit(url)
    return (parsed.scheme == 'https' and parsed.hostname in HOSTS
            and parsed.port in (None, 443) and not parsed.username and not parsed.password)


def open_url(url, headers=None):
    if not safe_url(url):
        raise ValueError('unsupported_url')
    return build_opener(NoRedirect()).open(Request(url, headers=headers or {}), timeout=45)


def add_voice(db, voice):
    owner, identity = voice.get('public_owner_id'), voice.get('voice_id')
    if not isinstance(owner, str) or not isinstance(identity, str):
        raise ValueError('Invalid catalog identity')
    metadata = {k: voice.get(k) for k in ('public_owner_id', 'voice_id', 'name', 'language',
        'accent', 'category', 'preview_url', 'verified_languages', 'usage_character_count_1y',
        'usage_character_count_7d', 'cloned_by_count')}
    db.execute('INSERT OR REPLACE INTO voices VALUES(?,?,?)',
               (owner, identity, json.dumps(metadata, ensure_ascii=False)))
    previews = [(voice.get('preview_url'), voice.get('language') or '', '')]
    previews += [(p.get('preview_url'), p.get('language') or '', p.get('model_id') or '')
                 for p in voice.get('verified_languages') or []]
    for url, language, model in previews:
        if not isinstance(url, str) or not url:
            continue
        db.execute('INSERT OR IGNORE INTO downloads(url,status) VALUES(?,?)',
                   (url, 'pending' if safe_url(url) else 'unsupported_url'))
        db.execute('INSERT OR IGNORE INTO links VALUES(?,?,?,?,?)', (owner, identity, url, language, model))


def summary(db, phase, extra=None):
    counts = dict(db.execute('SELECT status,COUNT(*) FROM downloads GROUP BY status'))
    value = {'updated_at': datetime.now(timezone.utc).isoformat(), 'phase': phase,
        'voices': db.execute('SELECT COUNT(*) FROM voices').fetchone()[0],
        'preview_urls': db.execute('SELECT COUNT(*) FROM downloads').fetchone()[0],
        'status_counts': counts,
        'downloaded_bytes': db.execute("SELECT COALESCE(SUM(bytes),0) FROM downloads WHERE status='downloaded'").fetchone()[0],
        'catalog_complete': db.execute("SELECT value FROM state WHERE key='catalog_complete'").fetchone() == ('true',),
        'clone_permission': 'unknown', **(extra or {})}
    temporary = ROOT / 'summary.json.part'
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(ROOT / 'summary.json')
    print(json.dumps(value, ensure_ascii=True), flush=True)


def fetch_audio(url):
    url_id = hashlib.sha256(url.encode()).hexdigest()
    part = ROOT / 'audio' / url_id[:2] / (url_id + '.part')
    part.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open_url(url) as response, part.open('wb') as output:
            content_type = response.headers.get('Content-Type', '').lower()
            digest, size, head = hashlib.sha256(), 0, b''
            while True:
                data = response.read(64 * 1024)
                if not data:
                    break
                size += len(data)
                if size > MAX_FILE:
                    raise ValueError('file_too_large')
                head = (head + data)[:32]
                digest.update(data)
                output.write(data)
        if not size:
            raise ValueError('empty')
        if head.startswith(b'RIFF') and head[8:12] == b'WAVE':
            extension = '.wav'
        elif head.startswith(b'OggS'):
            extension = '.ogg'
        elif head.startswith(b'fLaC'):
            extension = '.flac'
        elif head.startswith(b'ID3') or (head[0] == 255 and len(head) > 1 and head[1] & 224 == 224):
            extension = '.mp3'
        elif 'audio/' in content_type and head[4:8] == b'ftyp':
            extension = '.m4a'
        else:
            raise ValueError('unrecognized_audio')
        sha = digest.hexdigest()
        final = ROOT / 'audio' / sha[:2] / (sha + extension)
        final.parent.mkdir(parents=True, exist_ok=True)
        if final.exists():
            part.unlink()
        else:
            part.replace(final)
        return ('downloaded', str(final.relative_to(ROOT)), size, sha, None)
    except HTTPError as error:
        return ('failed', None, 0, None, f'HTTP {error.code}')
    except (OSError, ValueError, URLError) as error:
        return ('failed', None, 0, None, type(error).__name__ + ': ' + str(error)[:160])
    finally:
        if part.exists():
            part.unlink()


def main():
    key = os.environ.get('ELEVENLABS_API_KEY')
    ROOT.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(ROOT / 'inventory.sqlite')
    db.executescript('''
      CREATE TABLE IF NOT EXISTS voices(owner TEXT,id TEXT,metadata TEXT,PRIMARY KEY(owner,id));
      CREATE TABLE IF NOT EXISTS downloads(url TEXT PRIMARY KEY,status TEXT,path TEXT,bytes INTEGER DEFAULT 0,sha256 TEXT,error TEXT);
      CREATE TABLE IF NOT EXISTS links(owner TEXT,id TEXT,url TEXT,language TEXT,model TEXT,PRIMARY KEY(owner,id,url,language,model));
      CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY,value TEXT);
    ''')
    if not db.execute('SELECT 1 FROM voices LIMIT 1').fetchone():
        original = ROOT.parent / 'snapshots/20261117T103929553845Z/catalog.json'
        for voice in json.loads(original.read_text(encoding='utf-8')):
            add_voice(db, voice)
        db.commit()
    done = db.execute("SELECT value FROM state WHERE key='catalog_complete'").fetchone() == ('true',)
    if not done:
        if not key:
            summary(db, 'needs_api_key')
            return 2
        page_row = db.execute("SELECT value FROM state WHERE key='next_page'").fetchone()
        page = int(page_row[0]) if page_row else 0
        for _ in range(1000):
            query = urlencode({'page': page, 'page_size': 100, 'sort': 'created_date'})
            try:
                with open_url('https://api.elevenlabs.io/v1/shared-voices?' + query, {'xi-api-key': key}) as response:
                    payload = response.read(10_000_001)
                if len(payload) > 10_000_000:
                    raise ValueError('Catalog page too large')
                data = json.loads(payload)
                if not isinstance(data.get('voices'), list) or not isinstance(data.get('has_more'), bool):
                    raise ValueError('Invalid catalog response')
                if not data['voices'] and data['has_more']:
                    raise ValueError('Empty page with has_more=true')
                for voice in data['voices']:
                    add_voice(db, voice)
                page += 1
                db.execute("INSERT OR REPLACE INTO state VALUES('next_page',?)", (str(page),))
                if not data['has_more']:
                    db.execute("INSERT OR REPLACE INTO state VALUES('catalog_complete','true')")
                db.commit()
                if page % 10 == 0 or not data['has_more']:
                    summary(db, 'catalog', {'next_page': page, 'api_total_at_page': data.get('total_count')})
                if not data['has_more']:
                    break
                time.sleep(0.2)
            except HTTPError as error:
                summary(db, 'stopped', {'reason': f'Catalog HTTP {error.code}', 'next_page': page})
                return 1
        else:
            summary(db, 'stopped', {'reason': '1000-page safety bound'})
            return 1
    summary(db, 'audio')
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        while True:
            if shutil.disk_usage(ROOT).free < 10 * 1024**3:
                summary(db, 'stopped', {'reason': 'Less than 10 GiB free space'})
                return 1
            rows = db.execute("SELECT url FROM downloads WHERE status='pending' LIMIT 30").fetchall()
            if not rows:
                break
            futures = {pool.submit(fetch_audio, row[0]): row[0] for row in rows}
            stop = None
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                db.execute('UPDATE downloads SET status=?,path=?,bytes=?,sha256=?,error=? WHERE url=?',
                           (*result, futures[future]))
                if result[4] in ('HTTP 401', 'HTTP 403', 'HTTP 429'):
                    stop = result[4]
            db.commit()
            summary(db, 'audio')
            if stop:
                summary(db, 'stopped', {'reason': stop + '; no account rotation or automatic bypass'})
                return 1
    summary(db, 'finished')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
