# Face Avatar

A local face-avatar installation for a GEEKOM mini PC or NVIDIA Orin Nano. A
connected camera animates the character on the installation's display.

## Team Checkout

This snapshot includes the local application, all model exports, Blender sources
and earlier model iterations. Large binaries use Git LFS. Install Git LFS before
cloning, then fetch the binaries on the checked-out branch:

```sh
git lfs install
git lfs pull
python3 scripts/run_installation.py --serve-only --port 8014
```

Open `http://localhost:8014/cockpit.html?assets=3dai&character=orbit` on that
computer. Use `character=coral` for Coral. Allow camera access when prompted.
Requirements: Git LFS, Python 3 and Chrome/Chromium. The complete authoring history
requires several GB of disk space. `node --test scripts/test_*.mjs` runs the core
regression tests with Node.js installed. Corrected Orbit/Coral reference PNGs are
archived in `assets/references/` with hashes in `scripts/reference-source-lock.json`.
Conductor's `.context/`, local credentials and generated caches are not included.
Some historical Blender/QA scripts still refer to their original local context;
the saved Blender sources have packed reference images and textures.

A GitHub branch is a source snapshot, not a hosted preview. A localhost link only
works on the computer running the server. Native ZED capture still requires the
local SDK/hardware setup described in `scripts/ZED_INSTALLATION.md`.

## Vercel Team Preview

The hosted preview opens `cockpit.html`, with the same automatic webcam startup
and hidden operator UI as the local installation. Native ZED SDK capture still
requires the local installation; Vercel only hosts the browser files.

In the Vercel project's **Settings > Git**, enable **Git LFS**, then redeploy.
Without it, model and WebAssembly URLs contain Git LFS text placeholders, causing
`WebAssembly.instantiate(): expected magic word` and character-loading failures.
The build now rejects those placeholders instead of publishing a broken preview.

`node scripts/build_web_preview.mjs` validates and packages the cockpit, bundled
libraries and manifest-referenced assets into `dist/`. Blender sources, unused
model iterations, local context and scripts are not published. The original
head-only `index.html` remains available locally; hosted `/` and `/index.html`
redirect to the cockpit. Merge preview changes into the Vercel production branch
(`main`) to publish them. Revalidate cached assets on reload; no camera images
are uploaded by the preview.

## Local Installation

Run `python3 scripts/run_installation.py` (`py -3 scripts/run_installation.py` on
Windows) on the installation computer. It opens the locally bundled renderer in a
dedicated fullscreen Chromium/Chrome kiosk, with automatic camera startup and no
studio interface. Nothing is hosted externally. It requires Python 3, a graphical
desktop, a supported browser, and a connected camera. This has not been benchmarked
on GEEKOM or Orin Nano hardware yet.

For first-time camera permission, run the launcher with `--setup` and select Allow
when the camera starts automatically. Operator mode also starts the camera; it no
longer requires a Start click. The dedicated browser profile remembers permission. Keep
the same port and profile for unattended launches. Then close the setup browser and
launcher, and run the normal launch command. The app retries disconnected cameras.

`cockpit.html?setup` exposes operator-only calibration and model inspection controls.
The installation defaults to Orbit, Cosmic, Nebula, Kudzu, Clay, Coral, Summer,
and Glass, with 52 facial controls each. The new roster is active for movement
testing, not hardware-approved. Orbit and Coral now use their new supplied-image
rigs, including teeth, long tongues and articulated native hands/flippers.
Left/right arrows change characters.
The vehicle is not loaded; its original files are preserved. The authoritative
roster is `assets/3dai/manifest.json`; it selects the current GLBs without merging
in old character IDs. New sources are in `blender/likeness-trials/`, with Nebula
in the reference-character files. Orbit/Coral's completed sources are
`blender/likeness-trials/{orbit,coral}-image-rig.blend`; their original form
studies and previous refined models are preserved separately.
See [the new rig notes](blender/likeness-trials/README.md).
Open `http://localhost:8014/cockpit.html?assets=3dai&character=cosmic` on the running
local server to test the new set. No setup or review flag is needed. The previous
GLBs remain on disk, and `?assets=3dai&rigs=refined` selects the previous roster.
The earlier procedural fleet remains available explicitly with `--assets fleet`.
The older head-only installation remains available at `index.html`.

For a local preview without launching a kiosk window, use
`python3 scripts/run_installation.py --serve-only --port 8013`, not a plain
`python3 -m http.server`. The installation server disables HTTP caching for all
files and sends current bytes even for conditional requests. Its root URL opens
`cockpit.html`, redirected to a versioned `/_build/.../cockpit.html` path. Relative
modules, workers, models, and styles inherit that versioned path, preventing old
module-cache entries from being reused. Reloading an old build URL redirects to
the current version when runtime files change. To refresh an older server's page, open
`http://localhost:8013/cockpit.html?refresh=1` once; the cache-only reset preserves
saved user data and permissions in supporting browsers. Versioned paths provide
the cache bypass even when a browser retains imported modules after a cache clear.

### Arms And Character Switching

Body and hand tracking start automatically with face tracking in `cockpit.html`.
The alien's upper arms, elbows, and hands mirror the visitor's movement. Both arms
work independently, including with closed fists. Keep shoulders, elbows, and wrists
visible to the camera. Uncertain or lost arm tracking eases back to a collision-safe
neutral pose. The default pose is standing. Available fingers curl/point
independently according to each alien's native anatomy; Clay and Coral have flippers rather
than separate fingers. The lower-body pose controls only affect rigs with clips.

Local Rapier contact queries guard the torso/head against arm capsules, with elbow
and wrist limits and fixed bone lengths. This is constrained camera animation, not
a gravity-driven ragdoll. Collision bounds are approximate: clothing, finger and
arm-to-arm intersections can remain, especially at extreme poses. Existing
upper-body deformation corrections are rebased for the standing runtime.
Collision-induced pose transitions are bounded for small tracking changes when
an intermediate pose remains clear; large deliberate input changes bypass that
transition limiter. All eight rigs pass the synthetic continuity and response
checks, but this does not measure physical camera-to-display latency.

Normal arm movement does not change characters. To switch, hold ONE open palm
toward the camera at shoulder height or higher, steadily for 0.7 seconds. The hand
indicator fills and arrows appear when ready. Then swipe horizontally across about
a quarter of the camera view in under two-thirds of a second. From the visitor's
perspective, left selects the next alien and right selects the previous alien.
Readiness expires after two seconds. Lower/close the hand to cancel or to rearm
after a swap; each hold permits one swap. Your other hand can stay visible and
lowered. Two raised open palms cannot arm switching.
The lower-body pose stays fixed throughout.

The bundled MediaPipe Hand Landmarker and Pose Landmarker Lite run locally in a
separate worker, capped at 30 samples per second with one frame in flight.
No camera images are uploaded. `body-motion.js` maps the observed limb directions;
`arm-retarget.js` applies smoothed rotations, followed by `arm-collisions.js`.
Tests: `node --test scripts/test_air_swipe.mjs scripts/test_arm_collisions.mjs`. Real-camera sensitivity and
GEEKOM/Orin performance still need on-site verification.

Live eyes reject isolated camera-tracking spikes before smoothing. Blinks stay
independent and override competing squint/wide signals; brief face-detection gaps
retain the last expression. Tests: `node --test scripts/test_eye_signals.mjs`.

## Legacy Head-Only App

The following sections describe `index.html`, not the full-body installation launcher.

### Features

- **Real-time face tracking** using MediaPipe FaceLandmarker
- **Head rotation tracking** (pitch, yaw, roll)
- **Procedural facial animation** for jaw, eyes, and brows
- **AR mode** - avatar only appears when face is detected
- **Multiple avatars** - switch between different alien models
- **Gaussian splat background** - immersive 3D world using World Labs SPZ format
- **Responsive design** - works on desktop and mobile

## Tech Stack

- Three.js for 3D rendering
- MediaPipe FaceLandmarker for face tracking (runs 100% on-device — no cloud)
- Vanilla JavaScript (no build tools required)

## Runs Offline

All dependencies (Three.js, the MediaPipe runtime + face model, and the font) are
bundled locally in `vendor/`. The app makes **no external network requests** — it runs
with the internet completely off, which is what you want for an unattended storefront
mini PC. Face recognition happens entirely on the device; no image ever leaves the PC.

To serve it, run a local web server on the mini PC (camera access requires
`http://localhost`, not a `file://` path):

```bash
python3 -m http.server 8000
```

Then point Chrome (ideally `--kiosk`) at `http://localhost:8000`.

## Usage

1. Start a local server:
   ```bash
   python3 -m http.server 8000
   ```

2. Open `http://localhost:8000` in Chrome

3. Allow webcam access when prompted

4. Your alien avatar will track your face movements!

## Installation / Kiosk Mode

This runs as an unattended storefront installation: a monitor in a window fed by a
camera. Someone walks up, sees themselves transformed into the character in real time,
and when nobody is present the screen cycles through snapshots of previous participants
to draw people in.

- **Kiosk mode is on by default** — all demo chrome (buttons, status, webcam preview) is
  hidden so the screen shows only the avatar experience.
- **Attract loop** — after ~6s with no face, a full-screen "Step Up" invitation appears,
  cross-fading through previously captured participants.
- **Auto-capture** — when a visitor is tracked steadily for ~2.5s, a snapshot is saved
  locally (on the mini PC, in browser storage) and added to the attract-loop gallery.

### Avatars

- **Alien 1 / Alien 2** — stylized alien heads. These have *no facial rig*, so only head
  movement is truly tracked; mouth/eyes are approximated procedurally.
- **Character (stylized)** — `avatar-character.glb`, a cartoon Ready-Player-Me-style head
  with the full 52 ARKit blendshapes. This is the **Memoji-style avatar**: the character
  genuinely mirrors the visitor's expressions (smile, blink, jaw, brows…). Full-body
  avatars are auto-framed as a floating head (body meshes hidden). Swap in the artist's own
  character the same way — export any avatar with `?morphTargets=ARKit` and drop the `.glb`
  in `vendor/`.
- **Face (realistic)** — `facecap.glb`, Apple's ARKit face-capture head. Same rig, realistic
  look. Useful as a reference/fallback.

MediaPipe blendshape names (`eyeBlinkLeft`) are mapped to whatever naming a model uses
(`eyeBlink_L`), so any ARKit-rigged avatar animates without renaming.

### On-site operator shortcuts

- **S** — open/close the Installation Setup panel (pick camera, avatar, toggles, clear gallery)
- **K** — toggle kiosk chrome (show/hide the demo controls)
- **F** — toggle fullscreen
- **?preview** — add to the URL (`…/index.html?preview`) to show the avatar without a live
  face, for setup and avatar checks

For a true kiosk, launch Chrome with `--kiosk` pointed at the page. The selected camera
auto-recovers if the feed drops (useful for an external/outdoor motion-capture camera).

## Controls (setup / debug)

- **Alien 1 / Alien 2 buttons** - Switch between avatar models (hidden in kiosk mode; use the setup panel)
- **Mouse drag** - Rotate camera view
- **Scroll** - Zoom in/out

## Files

- `index.html` - Main application
- `alien.glb` - Pink alien model
- `alien2.glb` - Green alien with cap model
- `cosmic-voyage.spz` - World Labs gaussian splat background

## Future Improvements

- Add blendshapes to alien models for full facial expressions (tongue out, smile, etc.)
- More avatar options
- Custom background upload

## Credits

- Alien models from Meshy AI
- Background from World Labs
- Built with Claude Code
