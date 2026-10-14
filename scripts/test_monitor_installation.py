"""Remote monitor unit tests with a fake fetcher; no network required."""
import unittest
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError

import monitor_installation as mi


class MonitorTests(unittest.TestCase):
    def test_live_site_passes_when_every_file_is_served(self):
        fetch = lambda url, headers=None, timeout=20, limit=4096: (200, b'<html><script src="fleet.js"></script>' if url.endswith('.html') else b'binary')
        result = mi.check_site('https://example.test', fetch)
        self.assertTrue(result['ok'], result)

    def test_live_site_reports_missing_files_and_lfs_placeholders(self):
        def fetch(url, headers=None, timeout=20, limit=4096):
            if url.endswith('hand_landmarker.task'): return 200, b'version https://git-lfs.github.com/spec/v1\noid sha256:abc'
            if url.endswith('air-swipe.js'): raise HTTPError(url, 404, 'Not Found', {}, None)
            return 200, b'<html>fleet.js</html>'
        result = mi.check_site('https://example.test', fetch)
        self.assertFalse(result['ok'])
        self.assertEqual(len(result['problems']), 2)
        self.assertTrue(any('Git LFS placeholder' in p for p in result['problems']))
        self.assertTrue(any('air-swipe.js: HTTP 404' in p for p in result['problems']))

    def test_heartbeat_fresh_and_ok_passes(self):
        now = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
        row = [{'created_at': (now - timedelta(minutes=1)).isoformat(), 'ok': True, 'summary': 'all good', 'actions': [], 'version': 'v'}]
        fetch = lambda url, headers=None, timeout=20, limit=4096: (200, __import__('json').dumps(row).encode())
        result = mi.check_heartbeat('https://db.test', 'key', 'atl-downtown', 4, fetch, now)
        self.assertTrue(result['ok'], result)

    def test_stale_or_failing_heartbeat_is_reported(self):
        import json
        now = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
        stale = [{'created_at': (now - timedelta(minutes=30)).isoformat(), 'ok': True, 'summary': 'all good', 'actions': [], 'version': None}]
        result = mi.check_heartbeat('https://db.test', 'key', 's', 4, lambda *a, **k: (200, json.dumps(stale).encode()), now)
        self.assertFalse(result['ok']); self.assertIn('kiosk silent for 30 minutes', result['problems'][0])
        failing = [{'created_at': (now - timedelta(minutes=1)).isoformat(), 'ok': False, 'summary': 'no monitor detected', 'actions': ['restarted x'], 'version': None}]
        result = mi.check_heartbeat('https://db.test', 'key', 's', 4, lambda *a, **k: (200, json.dumps(failing).encode()), now)
        self.assertFalse(result['ok']); self.assertIn('kiosk reports: no monitor detected', result['problems'][0])
        result = mi.check_heartbeat('https://db.test', 'key', 's', 4, lambda *a, **k: (200, b'[]'), now)
        self.assertFalse(result['ok']); self.assertIn('no heartbeat has ever been recorded', result['problems'][0])
        result = mi.check_heartbeat(None, None, 's', 4, None, now)
        self.assertFalse(result['ok']); self.assertIn('not configured', result['problems'][0])

    def test_report_renders_every_section(self):
        text = mi.render({'Live site': {'ok': True, 'problems': [], 'detail': {'a': 200}}, 'Kiosk heartbeat': {'ok': False, 'problems': ['kiosk silent'], 'detail': {}}}, 'https://s', 'atl')
        self.assertIn('✅ Live site', text); self.assertIn('❌ Kiosk heartbeat', text); self.assertIn('- kiosk silent', text); self.assertIn('MONITORING.md', text)


if __name__ == '__main__':
    unittest.main()
