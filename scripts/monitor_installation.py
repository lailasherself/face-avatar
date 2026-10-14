"""Remote installation monitor: live site reachability and kiosk heartbeat freshness.

Runs in GitHub Actions (see .github/workflows/installation-monitor.yml) and can
also be run from any machine: python3 scripts/monitor_installation.py.
Exit code 0 = everything passing, 1 = something needs attention.
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

SITE_FILES = ['cockpit.html', 'fleet.js', 'air-swipe.js', 'assets/3dai/manifest.json', 'vendor/mediapipe/model/hand_landmarker.task']


def get(url, headers=None, timeout=20, limit=4096):
    request = Request(url, headers={'User-Agent': 'face-avatar-monitor', **(headers or {})})
    with urlopen(request, timeout=timeout) as response:
        return response.status, response.read(limit)


def check_site(site, fetch=get):
    problems, detail = [], {}
    for name in SITE_FILES:
        url = f'{site.rstrip("/")}/{name}'
        try:
            status, body = fetch(url, limit=65536 if name.endswith('.html') else 4096)
        except HTTPError as error:
            problems.append(f'{name}: HTTP {error.code}'); continue
        except (URLError, OSError, TimeoutError) as error:
            problems.append(f'{name}: {str(error)[:80]}'); continue
        if status != 200:
            problems.append(f'{name}: HTTP {status}')
        elif body.startswith(b'version https://git-lfs.github.com'):
            problems.append(f'{name}: Git LFS placeholder served instead of the file')
        elif name.endswith('.html') and b'fleet.js' not in body:
            problems.append(f'{name}: unexpected page content')
        detail[name] = status
    return {'ok': not problems, 'problems': problems, 'detail': detail}


def check_heartbeat(url, key, station, max_age_minutes, fetch=get, now=None):
    if not url or not key:
        return {'ok': False, 'problems': ['kiosk heartbeat not configured (SUPABASE_URL / SUPABASE_ANON_KEY repository variables)'], 'detail': {}}
    endpoint = f'{url.rstrip("/")}/rest/v1/kiosk_health?station=eq.{quote(station)}&order=created_at.desc&limit=1&select=created_at,ok,summary,actions,version'
    try:
        status, body = fetch(endpoint, headers={'apikey': key, 'Authorization': 'Bearer ' + key}, limit=65536)
        rows = json.loads(body)
    except (HTTPError, URLError, OSError, TimeoutError, ValueError) as error:
        return {'ok': False, 'problems': ['heartbeat lookup failed: ' + str(error)[:120]], 'detail': {}}
    if not rows:
        return {'ok': False, 'problems': [f'no heartbeat has ever been recorded for station {station}'], 'detail': {}}
    row = rows[0]
    created = datetime.fromisoformat(row['created_at'].replace('Z', '+00:00'))
    now = now or datetime.now(timezone.utc)
    age_minutes = (now - created).total_seconds() / 60
    problems = []
    if age_minutes > max_age_minutes:
        problems.append(f'kiosk silent for {age_minutes:.0f} minutes (last heartbeat {row["created_at"]}): powered off, offline, or the health timer stopped')
    elif not row['ok']:
        problems.append('kiosk reports: ' + (row.get('summary') or 'unknown problem'))
    return {'ok': not problems, 'problems': problems, 'detail': {'lastHeartbeat': row['created_at'], 'ageMinutes': round(age_minutes, 1), 'kioskOk': row['ok'],
                                                               'summary': row.get('summary'), 'actions': row.get('actions'), 'version': row.get('version')}}


def render(results, site, station):
    lines = ['## Installation monitor', '']
    for name, result in results.items():
        icon = '✅' if result['ok'] else ('⏸️' if result.get('skipped') else '❌')
        lines.append(f'### {icon} {name}')
        for problem in result['problems']:
            lines.append(f'- {problem}')
        if result['ok'] and not result['problems']:
            lines.append('- ' + result.get('note', 'passing'))
        if result.get('detail'):
            lines.append('')
            lines.append('```json'); lines.append(json.dumps(result['detail'], indent=1)[:2000]); lines.append('```')
        lines.append('')
    lines.append(f'Site: {site} · Station: {station}')
    lines.append('')
    lines.append('What to do: see scripts/MONITORING.md.')
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--site', default=os.environ.get('SITE', 'https://face-avatar.vercel.app'))
    parser.add_argument('--supabase-url', default=os.environ.get('SUPABASE_URL'))
    parser.add_argument('--supabase-key', default=os.environ.get('SUPABASE_ANON_KEY'))
    parser.add_argument('--station', default=os.environ.get('KIOSK_STATION', 'atl-downtown'))
    parser.add_argument('--max-age-minutes', type=float, default=float(os.environ.get('HEARTBEAT_MAX_AGE_MINUTES', '4')))
    parser.add_argument('--monitor-kiosk', default=os.environ.get('MONITOR_KIOSK', 'on'))
    parser.add_argument('--github-output')
    parser.add_argument('--report')
    args = parser.parse_args(argv)
    results = {'Live site': check_site(args.site)}
    if args.monitor_kiosk.lower() in ('off', 'false', '0', 'no'):
        results['Kiosk heartbeat'] = {'ok': True, 'skipped': True, 'problems': [], 'detail': {}, 'note': 'kiosk monitoring paused (MONITOR_KIOSK=off)'}
    else:
        results['Kiosk heartbeat'] = check_heartbeat(args.supabase_url, args.supabase_key, args.station, args.max_age_minutes)
    status = 'ok' if all(r['ok'] for r in results.values()) else 'failing'
    report = render(results, args.site, args.station)
    print(report)
    if args.report:
        with open(args.report, 'w') as handle:
            handle.write(report)
    if args.github_output:
        with open(args.github_output, 'a') as handle:
            handle.write(f'status={status}\n')
    return 0 if status == 'ok' else 1


if __name__ == '__main__':
    sys.exit(main())
