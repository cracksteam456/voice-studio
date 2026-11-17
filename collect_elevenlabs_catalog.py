"""Read-only official Voice Library inventory. No audio downloads or TTS calls."""
import argparse
from datetime import datetime, timezone
from getpass import getpass
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward the API key to a redirect target.


def request_page(key, query):
    request = Request('https://api.elevenlabs.io/v1/shared-voices?' + urlencode(query),
                      headers={'xi-api-key': key, 'Accept': 'application/json'})
    try:
        with build_opener(NoRedirect()).open(request, timeout=30) as response:
            payload = response.read(10_000_001)
        if len(payload) > 10_000_000:
            raise RuntimeError('API response exceeded 10 MB.')
        data = json.loads(payload)
    except HTTPError as error:
        messages = {
            401: 'API key is missing, invalid or lacks access. Check the key in ElevenLabs.',
            403: 'Access denied. Check API key permissions and account plan.',
            429: 'API rate limit reached. Saved progress is retained; try later.',
        }
        raise RuntimeError(messages.get(error.code, f'ElevenLabs returned HTTP {error.code}.')) from None
    except (URLError, TimeoutError):
        raise RuntimeError('Could not connect to ElevenLabs. Check the network and try later.') from None
    except (ValueError, UnicodeError):
        raise RuntimeError('ElevenLabs returned invalid JSON.') from None
    if (not isinstance(data, dict) or not isinstance(data.get('voices'), list)
            or not isinstance(data.get('has_more'), bool)):
        raise RuntimeError('Unexpected API response: missing voices/has_more.')
    for voice in data['voices']:
        if not isinstance(voice, dict) or not all(isinstance(voice.get(k), str) and voice[k]
                                              for k in ('public_owner_id', 'voice_id')):
            raise RuntimeError('Unexpected voice record: missing owner/voice ID.')
    return data


def collect_ranking(key, sort, language, limit, save_page, fetch=request_page):
    voices, seen = [], set()
    for page in range(100):
        query = {'sort': sort, 'page': page, 'page_size': min(limit, 100)}
        if language:
            query['language'] = language
        response = fetch(key, query)
        save_page(query, response)
        added = 0
        for voice in response['voices']:
            identity = (voice['public_owner_id'], voice['voice_id'])
            if identity not in seen:
                seen.add(identity)
                voices.append(voice)
                added += 1
            if len(voices) >= limit:
                return voices, 'requested_limit'
        if not response['has_more']:
            return voices, 'end_of_results'
        if not added:
            raise RuntimeError('Pagination repeated or returned an empty page with has_more=true.')
    raise RuntimeError('Stopped at the 100-page safety limit.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ask-key', action='store_true', help='Prompt for a hidden key in this terminal')
    parser.add_argument('--limit', type=int, default=50, help='Maximum records per ranking (default 50)')
    args = parser.parse_args()
    if not 1 <= args.limit <= 1000:
        parser.error('--limit must be between 1 and 1000')
    key = os.environ.get('ELEVENLABS_API_KEY') or os.environ.get('ELEVEN_API_KEY')
    if args.ask_key and not key:
        key = getpass('ElevenLabs API key (hidden, not saved): ').strip()
    if not key:
        print('Missing ELEVENLABS_API_KEY. Run with --ask-key in your own terminal.')
        return 2
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder = Path(__file__).parent / 'voice-library' / 'snapshots' / stamp
    folder.mkdir(parents=True, exist_ok=False)
    catalog, rankings = {}, []
    try:
        for label, sort, language in [('trending-global', 'trending', None),
                                      ('usage-global', 'usage_character_count_1y', None),
                                      ('trending-vi', 'trending', 'vi')]:
            def save_page(query, response):
                # Store only catalog fields, not account state, links to social profiles or raw bodies.
                fields = ('public_owner_id', 'voice_id', 'name', 'language', 'locale', 'accent',
                          'gender', 'age', 'description', 'use_case', 'category', 'preview_url',
                          'verified_languages', 'usage_character_count_1y', 'usage_character_count_7d',
                          'cloned_by_count', 'free_users_allowed', 'notice_period')
                safe = [{k: v[k] for k in fields if k in v} for v in response['voices']]
                response['voices'] = safe
                (folder / f'{label}-page-{query["page"]:03d}.json').write_text(
                    json.dumps({'query': query, 'response': response}, ensure_ascii=False, indent=2), encoding='utf-8')
            voices, stopped = collect_ranking(key, sort, language, args.limit, save_page)
            rankings.append({'label': label, 'count': len(voices), 'stopped': stopped})
            for rank, voice in enumerate(voices, 1):
                identity = (voice['public_owner_id'], voice['voice_id'])
                if identity not in catalog:
                    catalog[identity] = {**voice, 'clone_permission': 'unknown', 'rankings': []}
                catalog[identity]['rankings'].append({'list': label, 'rank': rank})
            print(f'{label}: {len(voices)} voices ({stopped})')
    except RuntimeError as error:
        print(str(error))
        print(f'Partial metadata saved to: {folder}')
        return 1
    (folder / 'catalog.json').write_text(json.dumps(list(catalog.values()), ensure_ascii=False, indent=2), encoding='utf-8')
    (folder / 'summary.json').write_text(json.dumps({'fetched_at': stamp, 'rankings': rankings,
        'unique_voices': len(catalog), 'audio_downloaded': False}, indent=2), encoding='utf-8')
    print(f'Done: {len(catalog)} unique voices. No audio downloads or TTS charges.')
    print(f'Results: {folder}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
