# Installation Monitoring

You get told when something goes wrong in two ways:

1. **GitHub issue + email.** The `Installation monitor` workflow runs every
   10 minutes. When a check fails it opens (or updates) an issue titled
   **🚨 Installation alert** in this repository and the run fails, which makes
   GitHub email the repository owner. When everything passes again the issue is
   closed automatically with a "Recovered" comment. Turn on GitHub mobile
   notifications for this repository to get it on your phone.
2. **The kiosk heals itself first.** On the Jetson a health check runs every
   minute (`scripts/kiosk_health.py`). It restarts a service only after the same
   failure repeats three times, waits five minutes between restarts, and logs
   every run to `~/.face-avatar/health.log` on the Jetson.

## What is checked

| Where | Check | Alert text you will see |
|---|---|---|
| Live site | `cockpit.html`, `fleet.js`, `air-swipe.js`, the roster manifest and a tracking model are served, and none is a Git LFS placeholder | `<file>: HTTP 404` / `Git LFS placeholder served` |
| Kiosk | A heartbeat reached the cloud in the last 4 minutes | `kiosk silent for N minutes` |
| Kiosk | Both user services active | `services down: …` (auto-started) |
| Kiosk | Installation server answers `/api/health`, ZED has no error, page keeps requesting frames | `installation server not answering`, `ZED error`, `kiosk page idle for Ns` (auto-restart after 3) |
| Kiosk | Page inspection through the browser debug port, when enabled: cockpit URL loaded, not frozen, camera active, no on-screen notice | `page frozen`, `kiosk shows …`, `page notice: …` |
| Kiosk | A monitor is attached and recognised by X | `no monitor detected` |
| Kiosk | Memory, temperature, disk | `low memory`, `hot`, `disk almost full` |

## What to do when an alert arrives

- **kiosk silent** – the Jetson is off, has no network, or the health timer
  stopped. Check power and the Wi-Fi/Ethernet cable. Once on the network:
  `ssh laila@100.108.8.87` then `systemctl --user status face-avatar-health.timer`.
  If the kiosk is intentionally off, set the repository variable
  `MONITOR_KIOSK` to `off` (Settings → Secrets and variables → Actions →
  Variables) and back to `on` when it returns.
- **no monitor detected** – the Jetson missed the DisplayPort hot-plug. Re-seat
  the cable or power-cycle the TV. The avatar keeps running underneath.
- **kiosk page idle / page frozen** – the browser is stuck. The check restarts it
  automatically; if alerts continue, `systemctl --user restart face-avatar-browser.service`.
- **installation server not answering / ZED error** – the capture server is down
  or the camera is unplugged. Check the ZED USB cable, then
  `systemctl --user restart face-avatar-installation.service` (this also restarts the browser).
- **Live site file problems** – a deploy broke the hosted preview. Open the
  latest Vercel deployment; if the alert mentions Git LFS, re-enable LFS in the
  Vercel project settings and redeploy.
- **low memory / hot** – close the other project's `ripple.py` if it is running,
  check airflow around the Jetson.

## Checking by hand

- Latest kiosk status from anywhere:
  `python3 scripts/monitor_installation.py` with `SUPABASE_URL` and
  `SUPABASE_ANON_KEY` set (the values are repository variables).
- On the Jetson: `python3 ~/.local/share/face-avatar/kiosk_health.py --dry-run --print`
  runs every check without restarting anything, and `tail ~/.face-avatar/health.log`
  shows the recent history.
- Trigger the GitHub workflow immediately: Actions → Installation monitor → Run workflow.

## How it is wired

- Jetson timer: `scripts/jetson/face-avatar-health.timer` runs
  `~/.local/share/face-avatar/kiosk_health.py` every minute. Its configuration
  is `~/.face-avatar/health.json` (station name, Supabase URL and anon key).
- Heartbeats land in the Supabase table `kiosk_health`
  (`supabase/migrations/202610140001_kiosk_health.sql`); rows older than seven
  days are purged automatically, and a station can write at most one row every
  20 seconds.
- `scripts/run_installation.py` serves `/api/health` (local only) so the check
  can see the ZED capture state and whether the page is still polling frames.
- Enabling the browser debug port on the kiosk (the `FACE_AVATAR_DIAGNOSTICS=1`
  path in `scripts/run_jetson_kiosk.py`) adds in-page checks (frame rate, camera,
  on-screen notices). Without it the page is judged by its frame requests.
