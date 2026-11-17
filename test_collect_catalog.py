import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from collect_elevenlabs_catalog import NoRedirect, collect_ranking, request_page


class CatalogTests(unittest.TestCase):
    def test_pagination_deduplicates_and_keeps_filter(self):
        queries, pages = [], []
        def voice(identity):
            return {'public_owner_id': 'owner', 'voice_id': identity}
        def fetch(key, query):
            queries.append(query)
            return ({'voices': [voice('a')], 'has_more': True} if query['page'] == 0 else
                    {'voices': [voice('a'), voice('b')], 'has_more': False})
        voices, reason = collect_ranking('secret', 'trending', 'vi', 10,
                                         lambda q, r: pages.append(q), fetch)
        self.assertEqual([v['voice_id'] for v in voices], ['a', 'b'])
        self.assertEqual([q['page'] for q in queries], [0, 1])
        self.assertTrue(all(q['language'] == 'vi' for q in queries))
        self.assertEqual(reason, 'end_of_results')

    def test_requested_limit(self):
        fetch = lambda key, query: {'voices': [{'public_owner_id': 'x', 'voice_id': '1'}], 'has_more': True}
        voices, reason = collect_ranking('secret', 'trending', None, 1, lambda q, r: None, fetch)
        self.assertEqual(len(voices), 1)
        self.assertEqual(reason, 'requested_limit')

    def test_auth_failure_does_not_echo_secret_or_response(self):
        with patch('collect_elevenlabs_catalog.build_opener') as opener:
            opener.return_value.open.side_effect = HTTPError('https://api.elevenlabs.io', 401, 'SECRET', {}, None)
            with self.assertRaises(RuntimeError) as caught:
                request_page('SECRET', {'page': 0})
        self.assertNotIn('SECRET', str(caught.exception))

    def test_redirect_refused(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.example'))


if __name__ == '__main__':
    unittest.main()
