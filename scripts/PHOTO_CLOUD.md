# Public QR Photos

The permanent visitor URL is:
`https://face-avatar.vercel.app/photo.html?station=atl-downtown`

Visitors use their own network. The active camera station sends heartbeats and
captures to the public HTTPS API; no inbound camera port or public tunnel is needed.
The QR contains no operator credential and never links to a public photo gallery.
The permanent QR stays visible on the Spaceship tab even while the camera is
offline. Its status identifies the offline station, and the phone disables capture
until the paired camera is ready. Viewing or scanning the QR needs no private link.

## Camera Station

The public website cannot claim the camera station. An operator opens the private
launch link, which stores a station credential in that browser and removes it from
the address bar. Only one tab can operate the station at a time. Close the existing
tab and wait 10 seconds before moving to another browser. Clear the
`alien-photo-owner` localStorage key to unpair a browser. Do not share the operator
link with visitors. Use the Spaceship tab for the visitor QR.

On the provisioning Mac the private link is `.context/photo-station-launch.html`.
The credential is also in macOS Keychain, service `face-avatar.photo-owner`.
The webcam path works on the public site. Native ZED capture still requires the
local SDK installation and its existing local frame endpoint; opening Vercel does
not give a website native ZED SDK access. Do not claim physical ZED delivery until
the local station's cloud transport is configured and tested on that device.

## Private Storage

Dedicated Supabase project: `ysxjztjiajszyvxfzfhn` (`face-avatar`, US East).
Bucket `alien-photos` is private; anonymous/authenticated roles cannot access the
station or object registry. Server-only service credentials are Vercel production
environment variables `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.
Never put the service key in client JavaScript or the QR.

Each phone has an independent random session token in sessionStorage. The API
checks that token before returning JPEG bytes; it does not publish signed URLs.
Photos are inaccessible after 24 hours. The authenticated `photo-cleanup` Edge
Function runs each minute through Supabase Cron and deletes expired objects using
the Storage API. Physical removal can lag expiry by one cleanup interval (or a
service outage); downloads are still denied immediately after expiry. Delete and
Retake revoke access immediately and attempt immediate physical deletion, with
cron retries if storage is unavailable. The privacy notice appears before capture.
No automatic social posting or face-identification database is created.

Session state changes use optimistic concurrency in `photo_commit`; conflicting
requests retry instead of overwriting an active capture. There is a 700 KiB image
limit, one active capture per station, 256 retained sessions, and creation limits.
At high event throughput monitor Supabase quotas and tune these bounds explicitly.

## Verification

`node --test scripts/test_photo_cloud.mjs` tests state/auth/expiry transitions.
`node scripts/test_photo_supabase.mjs` uses authenticated CLI access to the
dedicated project for synthetic upload/download, competing captures, RLS,
cross-visitor isolation and physical deletion/cleanup. Run only while the station
is idle; it temporarily acquires the operator lease.

The browser test uses a public fixture and actual face inference. It is not a
physical-visitor or ZED test. A staff member must validate framing and capture at
the installed window before public launch.
