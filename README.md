# Face Avatar

A web-based AR face tracking app that animates 3D alien avatars using your webcam.

## Features

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

### On-site operator shortcuts

- **S** — open/close the Installation Setup panel (pick camera, avatar, toggles, clear gallery)
- **K** — toggle kiosk chrome (show/hide the demo controls)
- **F** — toggle fullscreen

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
