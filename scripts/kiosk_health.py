"""Installation health check for the kiosk: verify, self-heal, record, report.

Runs once per invocation (a systemd user timer calls it every minute). It checks
the two user services, the local installation server's /api/health, the kiosk
page (through the browser debug port when enabled, otherwise through the server's
view of whether the page is still requesting frames), the display, and the
system (memory, swap, temperature, disk). It restarts a service only after the
same failure repeats, logs every run to ~/.face-avatar/health.log, and posts a
heartbeat row to the cloud table that the GitHub monitor workflow reads.

Standard library only; the Jetson virtualenv has no extra packages.
"""
import argparse
import base64
import json
import os
import socket
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

HOME = Path(os.environ.get('FACE_AVATAR_HOME', str(Path.home() / '.face-avatar')))
CONFIG_FILE = HOME / 'health.json'
STATE_FILE = HOME / 'health-state.json'
LOG_FILE = HOME / 'health.log'
DEFAULTS = {
    'station': 'atl-downtown',
    'installationPort': 8014,
    'debugPort': 9222,
    'services': ['face-avatar-installation.service', 'face-avatar-browser.service'],
    'browserService': 'face-avatar-browser.service',
    'installationService': 'face-avatar-installation.service',
    'restartAfterFailures': 3,
    'restartCooldownSeconds': 300,
    'pageIdleSeconds': 20,
    'minAvailableMB': 400,
    'maxTemperatureC': 90,
    'minDiskFreeGB': 2,
    'supabaseUrl': None,
    'supabaseKey': None,
}


def load_config():
    config = dict(DEFAULTS)
    if CONFIG_FILE.is_file():
        config.update(json.loads(CONFIG_FILE.read_text()))
    return config


def run(*args, timeout=10, env=None):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=env)
        return result.returncode, result.stdout
    except (OSError, subprocess.SubprocessError) as error:
        return 127, str(error)


def fetch_json(url, timeout=4):
    with urlopen(Request(url, headers={'Host': url.split('/')[2]}), timeout=timeout) as response:
        return json.loads(response.read(65536))


# ---------------------------------------------------------------- checks ----

def check_services(config, tools):
    details = {}
    for name in config['services']:
        code, out = tools['run']('systemctl', '--user', 'is-active', name)
        details[name] = out.strip() or f'exit {code}'
    inactive = [n for n, s in details.items() if s != 'active']
    return {'ok': not inactive, 'detail': details, 'summary': 'services down: ' + ', '.join(inactive) if inactive else 'services active'}


def check_server(config, tools):
    url = f"http://127.0.0.1:{config['installationPort']}/api/health"
    try:
        health = tools['fetch_json'](url)
    except HTTPError as error:
        if error.code == 404:  # a release that predates /api/health: the server answers, so it is up
            return {'ok': True, 'skipped': True, 'detail': {'note': 'release without /api/health'}, 'summary': 'server up (no health endpoint in this release)'}
        return {'ok': False, 'detail': {'error': f'HTTP {error.code}'}, 'summary': f'installation server error HTTP {error.code}'}
    except (URLError, OSError, ValueError, TimeoutError) as error:
        return {'ok': False, 'detail': {'error': str(error)[:200]}, 'summary': 'installation server not answering'}
    zed = health.get('zed') or {}
    problems = []
    if health.get('zed') is not None:
        if zed.get('error'):
            problems.append('ZED error: ' + str(zed['error'])[:120])
        idle = zed.get('idleSeconds')
        # The page polls the camera continuously while it is alive. A server that
        # has not been asked for a frame in a while means the kiosk page is gone.
        if idle is not None and idle > config['pageIdleSeconds']:
            problems.append(f'kiosk page idle for {idle}s (not requesting frames)')
        elif zed.get('running') and zed.get('frameAgeMs') is not None and zed['frameAgeMs'] > 3000:
            problems.append(f"ZED frames stale ({zed['frameAgeMs']} ms)")
    return {'ok': not problems, 'detail': health, 'summary': '; '.join(problems) if problems else 'server healthy'}


class CDP:
    """Minimal Chrome DevTools Protocol client over a raw websocket (no deps)."""

    def __init__(self, ws_url, timeout=4):
        _, rest = ws_url.split('://', 1)
        host, path = rest.split('/', 1)
        hostname, port = host.split(':')
        self.sock = socket.create_connection((hostname, int(port)), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f'GET /{path} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
                           f'Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n').encode())
        header = b''
        while b'\r\n\r\n' not in header:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise OSError('websocket handshake failed')
            header += chunk
        if b' 101 ' not in header.split(b'\r\n', 1)[0]:
            raise OSError('websocket upgrade refused')
        self.buffer = header.split(b'\r\n\r\n', 1)[1]
        self.next_id = 0

    def send(self, payload):
        data = json.dumps(payload).encode()
        mask = os.urandom(4)
        head = bytearray([0x81])
        if len(data) < 126:
            head.append(0x80 | len(data))
        elif len(data) < 65536:
            head.append(0x80 | 126); head += len(data).to_bytes(2, 'big')
        else:
            head.append(0x80 | 127); head += len(data).to_bytes(8, 'big')
        self.sock.sendall(bytes(head) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def recv_frame(self):
        def need(n):
            while len(self.buffer) < n:
                chunk = self.sock.recv(65536)
                if not chunk:
                    raise OSError('websocket closed')
                self.buffer += chunk
        need(2)
        opcode = self.buffer[0] & 0x0f
        length = self.buffer[1] & 0x7f
        offset = 2
        if length == 126:
            need(4); length = int.from_bytes(self.buffer[2:4], 'big'); offset = 4
        elif length == 127:
            need(10); length = int.from_bytes(self.buffer[2:10], 'big'); offset = 10
        need(offset + length)
        payload = self.buffer[offset:offset + length]
        self.buffer = self.buffer[offset + length:]
        return opcode, payload

    def call(self, method, params=None, session=None):
        self.next_id += 1
        message = {'id': self.next_id, 'method': method, 'params': params or {}}
        if session:
            message['sessionId'] = session
        self.send(message)
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            opcode, payload = self.recv_frame()
            if opcode != 1:
                continue
            reply = json.loads(payload)
            if reply.get('id') == self.next_id:
                if 'error' in reply:
                    raise OSError(reply['error'].get('message', 'CDP error'))
                return reply.get('result', {})
        raise OSError('CDP timeout')

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


PAGE_PROBE = """(async()=>{const f0=window.fleetQA?window.fleetQA.renderFrame:null;let frames=0;const t0=performance.now();
await new Promise(r=>{const tick=()=>{frames++;if(performance.now()-t0<500)requestAnimationFrame(tick);else r();};requestAnimationFrame(tick);});
const q=window.fleetQA;const dt=(performance.now()-t0)/1000;return JSON.stringify({url:location.pathname+location.search,ready:document.readyState,qa:!!q,
 rafFps:+(frames/dt).toFixed(1),renderFps:q&&f0!==null?+((q.renderFrame-f0)/dt).toFixed(1):null,camera:q?q.cameraActive:null,
 character:q?q.character:null,loaded:q?q.loadedCharacters:null,person:q?q.zedPersonId:null,hand:q?.handDiagnostics?.status??null,
 faceFrames:q?q.faceTrackingFrames:null,notice:document.getElementById('notice')?.textContent||'',loading:!(document.getElementById('loading')?.hidden??true)});})()"""


def check_page(config, tools):
    """Look inside the kiosk page through the browser debug port when it is enabled."""
    base = f"http://127.0.0.1:{config['debugPort']}"
    try:
        version = tools['fetch_json'](base + '/json/version', timeout=2)
    except (URLError, HTTPError, OSError, ValueError, TimeoutError):
        return {'ok': True, 'skipped': True, 'detail': {}, 'summary': 'page inspection unavailable (debug port off)'}
    try:
        client = tools['cdp'](version['webSocketDebuggerUrl'])
        try:
            targets = [t for t in client.call('Target.getTargets')['targetInfos'] if t['type'] == 'page']
            if not targets:
                return {'ok': False, 'detail': {}, 'summary': 'browser has no page open'}
            page = next((t for t in targets if 'cockpit.html' in t['url']), targets[0])
            session = client.call('Target.attachToTarget', {'targetId': page['targetId'], 'flatten': True})['sessionId']
            result = client.call('Runtime.evaluate', {'expression': PAGE_PROBE, 'awaitPromise': True, 'returnByValue': True}, session)
            probe = json.loads(result['result']['value'])
        finally:
            client.close()
    except (OSError, KeyError, ValueError, TypeError) as error:
        return {'ok': False, 'detail': {'error': str(error)[:200]}, 'summary': 'page inspection failed: ' + str(error)[:120]}
    problems = []
    if 'cockpit.html' not in probe['url']:
        problems.append('kiosk shows ' + probe['url'][:60])
    if probe['rafFps'] < 5:
        problems.append(f"page frozen ({probe['rafFps']} fps)")
    if probe['qa'] and probe['camera'] is False:
        problems.append('camera inactive in page')
    if probe['notice']:
        problems.append('page notice: ' + probe['notice'][:100])
    return {'ok': not problems, 'detail': probe, 'summary': '; '.join(problems) if problems else 'page alive'}


def check_display(config, tools):
    env = dict(os.environ, DISPLAY=os.environ.get('DISPLAY', ':0'))
    code, out = tools['run']('xrandr', '--listmonitors', env=env)
    if code != 0:
        return {'ok': True, 'skipped': True, 'detail': {'error': out[:120]}, 'summary': 'display check unavailable'}
    monitors = 0
    for line in out.splitlines():
        if line.startswith('Monitors:'):
            monitors = int(line.split(':')[1].strip() or 0)
    return {'ok': monitors > 0, 'detail': {'monitors': monitors, 'xrandr': out.strip()[:200]},
            'summary': 'no monitor detected (DisplayPort hot-plug missed; re-seat the cable)' if monitors == 0 else f'{monitors} monitor'}


def check_system(config, tools):
    detail, problems = {}, []
    try:
        meminfo = dict(line.split(':', 1) for line in tools['read']('/proc/meminfo').splitlines() if ':' in line)
        available = int(meminfo['MemAvailable'].split()[0]) // 1024
        swap_used = (int(meminfo['SwapTotal'].split()[0]) - int(meminfo['SwapFree'].split()[0])) // 1024
        detail.update(availableMB=available, swapUsedMB=swap_used)
        if available < config['minAvailableMB']:
            problems.append(f'low memory ({available} MB available)')
    except (OSError, KeyError, ValueError):
        pass
    temps = []
    for zone in tools['glob']('/sys/devices/virtual/thermal/thermal_zone*/temp'):
        try:
            temps.append(int(tools['read'](zone).strip()) / 1000)
        except Exception:  # offline zones on the Jetson return nothing readable
            continue
    if temps:
        detail['maxTemperatureC'] = max(temps)
        if max(temps) > config['maxTemperatureC']:
            problems.append(f'hot ({max(temps):.0f} C)')
    try:
        usage = tools['disk_usage']('/')
        free_gb = usage.free / 1e9
        detail['diskFreeGB'] = round(free_gb, 1)
        if free_gb < config['minDiskFreeGB']:
            problems.append(f'disk almost full ({free_gb:.1f} GB free)')
    except OSError:
        pass
    try:
        detail['load1'] = round(os.getloadavg()[0], 2)
    except OSError:
        pass
    return {'ok': not problems, 'detail': detail, 'summary': '; '.join(problems) if problems else 'system fine'}


CHECKS = [('services', check_services), ('server', check_server), ('page', check_page), ('display', check_display), ('system', check_system)]


# ------------------------------------------------------------- healing ----

def heal(config, checks, state, tools, now):
    """Restart a service only after the same failure repeats, with a cooldown."""
    actions = []
    failing = {name for name, result in checks.items() if not result['ok']}
    # With no monitor attached, Chrome throttles the invisible page to a few
    # frames per second. That is not a frozen page and restarting the browser
    # would not help, so the page check is reported but never healed then.
    display = checks.get('display', {})
    if not display.get('ok', True) and not display.get('skipped'):
        failing.discard('page')
        state.setdefault('streaks', {}).pop('page', None)
    streaks = state.setdefault('streaks', {})
    for name in list(streaks):
        if name not in failing:
            del streaks[name]
    for name in failing:
        streaks[name] = streaks.get(name, 0) + 1
    cooldown_until = state.get('restartCooldownUntil', 0)
    for name, service in (('services', None), ('server', config['installationService']), ('page', config['browserService'])):
        if name not in failing:
            continue
        if name == 'services':
            down = [s for s, status in checks['services']['detail'].items() if status != 'active']
            for s in down:
                tools['run']('systemctl', '--user', 'start', s, timeout=60)
                actions.append(f'started {s}')
            continue
        if streaks[name] >= config['restartAfterFailures'] and now >= cooldown_until:
            tools['run']('systemctl', '--user', 'restart', service, timeout=60)
            actions.append(f'restarted {service} after {streaks[name]} failed checks: ' + checks[name]['summary'])
            state['restartCooldownUntil'] = now + config['restartCooldownSeconds']
            streaks[name] = 0
    return actions


# ----------------------------------------------------------- reporting ----

def report(config, payload, tools):
    if not config.get('supabaseUrl') or not config.get('supabaseKey'):
        return 'cloud report not configured'
    request = Request(config['supabaseUrl'].rstrip('/') + '/rest/v1/kiosk_health', data=json.dumps(payload).encode(), method='POST',
                      headers={'apikey': config['supabaseKey'], 'Authorization': 'Bearer ' + config['supabaseKey'],
                               'Content-Type': 'application/json', 'Prefer': 'return=minimal'})
    try:
        with tools['urlopen'](request, timeout=8) as response:
            return f'reported ({response.status})'
    except HTTPError as error:
        return f'report rejected ({error.code})'
    except (URLError, OSError, TimeoutError) as error:
        return 'report failed: ' + str(error)[:100]


def append_log(line):
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        if LOG_FILE.exists() and LOG_FILE.stat().st_size > 5_000_000:
            LOG_FILE.replace(LOG_FILE.with_suffix('.log.1'))
        with LOG_FILE.open('a') as handle:
            handle.write(line + '\n')
    except OSError:
        pass


def default_tools():
    import glob
    import shutil
    return {'run': run, 'fetch_json': fetch_json, 'cdp': CDP, 'read': lambda p: Path(p).read_text(),
            'glob': glob.glob, 'disk_usage': shutil.disk_usage, 'urlopen': urlopen}


def run_once(config, state, tools, now=None, dry_run=False):
    now = time.time() if now is None else now
    checks = {}
    for name, check in CHECKS:
        try:
            checks[name] = check(config, tools)
        except Exception as error:  # a broken check must never hide the others
            import traceback
            where = traceback.extract_tb(error.__traceback__)[-1]
            checks[name] = {'ok': False, 'detail': {'error': str(error)[:200], 'at': f'{where.name}:{where.lineno}'}, 'summary': f'{name} check crashed: {error}'[:160]}
    actions = [] if dry_run else heal(config, checks, state, tools, now)
    ok = all(result['ok'] for result in checks.values())
    summary = 'all good' if ok else '; '.join(result['summary'] for result in checks.values() if not result['ok'])
    server = checks['server']['detail'] if isinstance(checks['server'].get('detail'), dict) else {}
    payload = {'station': config['station'], 'ok': ok, 'summary': summary[:500], 'version': (server.get('version') or '')[:64] or None,
               'checks': {name: {'ok': r['ok'], 'summary': r['summary'], **({'skipped': True} if r.get('skipped') else {}),
                                 **({'detail': r['detail']} if isinstance(r.get('detail'), dict) else {})} for name, r in checks.items()},
               'actions': actions}
    return payload


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--dry-run', action='store_true', help='Check only: no restarts, no cloud report')
    parser.add_argument('--print', action='store_true', help='Print the full payload as JSON')
    args = parser.parse_args(argv)
    config = load_config()
    state = {}
    if STATE_FILE.is_file():
        try:
            state = json.loads(STATE_FILE.read_text())
        except ValueError:
            state = {}
    tools = default_tools()
    payload = run_once(config, state, tools, dry_run=args.dry_run)
    sent = 'dry run' if args.dry_run else report(config, payload, tools)
    if not args.dry_run:
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            STATE_FILE.write_text(json.dumps(state))
        except OSError:
            pass
    line = json.dumps({'at': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'ok': payload['ok'], 'summary': payload['summary'], 'actions': payload['actions'], 'report': sent})
    append_log(line)
    print(json.dumps(payload, indent=1) if args.print else line)
    return 0 if payload['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
