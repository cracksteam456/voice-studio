"""Watch archive progress; return on a milestone, new errors or a stall."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sqlite3
import time

ROOT = Path(__file__).resolve().parent / 'voice-library/archive'


def snapshot():
    with sqlite3.connect('file:' + (ROOT / 'inventory.sqlite').as_posix() + '?mode=ro',
                         uri=True, timeout=10) as db:
        counts = dict(db.execute('SELECT status,COUNT(*) FROM downloads GROUP BY status'))
        return {'updated_at': datetime.now(timezone.utc).isoformat(),
                'voices': db.execute('SELECT COUNT(*) FROM voices').fetchone()[0],
                'catalog_state': dict(db.execute('SELECT key,value FROM state')),
                'counts': counts,
                'bytes': db.execute("SELECT COALESCE(SUM(bytes),0) FROM downloads WHERE status='downloaded'").fetchone()[0],
                'errors': db.execute("SELECT error,COUNT(*) FROM downloads WHERE status='failed' GROUP BY error ORDER BY COUNT(*) DESC LIMIT 5").fetchall(),
                'free_gb': round(shutil.disk_usage(ROOT).free / 1024**3, 2)}


def main():
    baseline = previous = snapshot()
    started = last_progress = time.monotonic()
    while True:
        time.sleep(30)
        try:
            current = snapshot()
        except (OSError, sqlite3.Error) as error:
            print(json.dumps({'reason': 'monitor_read_failed', 'error': type(error).__name__}), flush=True)
            return
        now = time.monotonic()
        current['files_per_minute'] = round((current['counts'].get('downloaded', 0) - baseline['counts'].get('downloaded', 0)) * 60 / (now - started), 1)
        current['mb_per_minute'] = round((current['bytes'] - baseline['bytes']) / 1_000_000 * 60 / (now - started), 2)
        if current['counts'].get('downloaded', 0) != previous['counts'].get('downloaded', 0):
            last_progress = now
        reason = None
        if current['free_gb'] < 12:
            reason = 'disk_low'
        elif current['counts'].get('failed', 0) > baseline['counts'].get('failed', 0):
            reason = 'new_download_errors'
        elif current['counts'].get('pending', 0) == 0 and current['catalog_state'].get('catalog_complete') == 'true':
            reason = 'finished'
        elif now - last_progress >= 180:
            reason = 'audio_stalled_3_minutes'
        elif current['counts'].get('downloaded', 0) - baseline['counts'].get('downloaded', 0) >= 5000:
            reason = '5000_more_files'
        elif now - started >= 600:
            reason = '10_minute_update'
        current['notification_reason'] = reason
        temporary = ROOT / 'monitor.json.part'
        temporary.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(ROOT / 'monitor.json')
        if reason:
            print(json.dumps(current, ensure_ascii=True), flush=True)
            return
        previous = current


if __name__ == '__main__':
    main()
