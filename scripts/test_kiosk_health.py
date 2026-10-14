"""Kiosk health check unit tests with fake tools; no services or network required."""
import json
import unittest
from urllib.error import HTTPError

import kiosk_health as kh


def tools(**overrides):
    base = {
        'run': lambda *args, **kw: (0, 'active\n') if 'is-active' in args else (0, 'Monitors: 1\n 0: +*DP-0 1920/0x1080/0+0+0 DP-0\n') if 'xrandr' in args else (0, ''),
        'fetch_json': lambda url, timeout=4: {'ok': True, 'version': 'abc', 'zed': {'running': True, 'error': None, 'frameAgeMs': 40, 'idleSeconds': 0, 'peopleCount': 1}} if url.endswith('/api/health') else (_ for _ in ()).throw(OSError('refused')),
        'cdp': None,
        'read': lambda path: 'MemTotal: 7800000 kB\nMemFree: 1000000 kB\nMemAvailable: 3000000 kB\nSwapTotal: 3900000 kB\nSwapFree: 3900000 kB\n' if path.endswith('meminfo') else '61000',
        'glob': lambda pattern: ['/sys/devices/virtual/thermal/thermal_zone0/temp'],
        'disk_usage': lambda path: type('U', (), {'free': 20e9, 'total': 57e9, 'used': 37e9})(),
        'urlopen': None,
    }
    base.update(overrides)
    return base


CONFIG = dict(kh.DEFAULTS, restartAfterFailures=3, restartCooldownSeconds=300)


class KioskHealthTests(unittest.TestCase):
    def test_healthy_kiosk_reports_ok_without_actions(self):
        payload = kh.run_once(CONFIG, {}, tools(), now=1000)
        self.assertTrue(payload['ok'], payload)
        self.assertEqual(payload['actions'], [])
        self.assertEqual(payload['summary'], 'all good')
        self.assertTrue(payload['checks']['page']['ok'])  # debug port off is not a failure
        self.assertEqual(payload['version'], 'abc')

    def test_dead_page_restarts_browser_only_after_repeated_failures_and_respects_cooldown(self):
        calls = []
        def run(*args, **kw):
            calls.append(args)
            if 'is-active' in args: return 0, 'active\n'
            if 'xrandr' in args: return 0, 'Monitors: 1\n'
            return 0, ''
        def idle(url, timeout=4):
            if url.endswith('/api/health'): return {'ok': True, 'zed': {'running': True, 'error': None, 'frameAgeMs': 30, 'idleSeconds': 95}}
            raise OSError('refused')
        state = {}
        for i in range(3):
            payload = kh.run_once(CONFIG, state, tools(run=run, fetch_json=idle), now=1000 + i * 60)
            self.assertFalse(payload['ok'])
            self.assertIn('kiosk page idle', payload['summary'])
        restarts = [c for c in calls if 'restart' in c]
        self.assertEqual(restarts, [('systemctl', '--user', 'restart', 'face-avatar-installation.service')])
        self.assertIn('restarted face-avatar-installation.service', payload['actions'][0])
        # Still failing right after: the cooldown prevents a restart storm.
        for i in range(3):
            payload = kh.run_once(CONFIG, state, tools(run=run, fetch_json=idle), now=1200 + i * 60)
        self.assertEqual(len([c for c in calls if 'restart' in c]), 1)
        # After the cooldown another restart is allowed.
        for i in range(3):
            payload = kh.run_once(CONFIG, state, tools(run=run, fetch_json=idle), now=1700 + i * 60)
        self.assertEqual(len([c for c in calls if 'restart' in c]), 2)

    def test_inactive_service_is_started_immediately(self):
        calls = []
        def run(*args, **kw):
            calls.append(args)
            if 'is-active' in args: return 3, 'inactive\n' if 'browser' in args[-1] else 'active\n'
            if 'xrandr' in args: return 0, 'Monitors: 1\n'
            return 0, ''
        payload = kh.run_once(CONFIG, {}, tools(run=run), now=1000)
        self.assertFalse(payload['ok'])
        self.assertIn(('systemctl', '--user', 'start', 'face-avatar-browser.service'), calls)
        self.assertEqual(payload['actions'], ['started face-avatar-browser.service'])

    def test_old_release_without_health_endpoint_is_not_a_failure_but_a_dead_server_is(self):
        def missing(url, timeout=4):
            raise HTTPError(url, 404, 'Not Found', {}, None)
        payload = kh.run_once(CONFIG, {}, tools(fetch_json=missing), now=1000)
        self.assertTrue(payload['ok'])
        self.assertTrue(payload['checks']['server'].get('skipped'))
        def refused(url, timeout=4):
            raise OSError('connection refused')
        payload = kh.run_once(CONFIG, {}, tools(fetch_json=refused), now=1000)
        self.assertFalse(payload['ok'])
        self.assertIn('installation server not answering', payload['summary'])

    def test_missing_monitor_low_memory_and_heat_are_reported(self):
        def run(*args, **kw):
            if 'is-active' in args: return 0, 'active\n'
            if 'xrandr' in args: return 0, 'Monitors: 0\n'
            return 0, ''
        read = lambda path: 'MemAvailable: 200000 kB\nSwapTotal: 100 kB\nSwapFree: 0 kB\n' if path.endswith('meminfo') else '95000'
        payload = kh.run_once(CONFIG, {}, tools(run=run, read=read), now=1000)
        self.assertFalse(payload['ok'])
        for text in ('no monitor detected', 'low memory', 'hot (95 C)'):
            self.assertIn(text, payload['summary'])
        self.assertEqual(payload['checks']['system']['detail']['availableMB'], 195)

    def test_dry_run_never_heals(self):
        calls = []
        def run(*args, **kw):
            calls.append(args)
            if 'is-active' in args: return 3, 'failed\n'
            return 0, 'Monitors: 1\n'
        payload = kh.run_once(CONFIG, {}, tools(run=run), now=1000, dry_run=True)
        self.assertFalse(payload['ok'])
        self.assertEqual(payload['actions'], [])
        self.assertFalse(any('start' in c for c in calls))

    def test_a_crashing_check_does_not_hide_the_others(self):
        def boom(url, timeout=4):
            raise RuntimeError('unexpected')
        payload = kh.run_once(CONFIG, {}, tools(fetch_json=boom), now=1000)
        self.assertFalse(payload['ok'])
        self.assertIn('server check crashed', payload['summary'])
        self.assertTrue(payload['checks']['system']['ok'])

    def test_payload_is_json_serialisable_and_bounded(self):
        payload = kh.run_once(CONFIG, {}, tools(), now=1000)
        encoded = json.dumps(payload)
        self.assertLess(len(encoded), 16000)
        self.assertEqual(payload['station'], 'atl-downtown')


if __name__ == '__main__':
    unittest.main()
