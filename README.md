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
- MediaPipe FaceLandmarker for face tracking
- Gaussian Splats 3D for SPZ world rendering
- Vanilla JavaScript (no build tools required)

## Usage

1. Start a local server:
   ```bash
   python3 -m http.server 8000
   ```

2. Open `http://localhost:8000` in Chrome

3. Allow webcam access when prompted

4. Your alien avatar will track your face movements!

## Controls

- **Alien 1 / Alien 2 buttons** - Switch between avatar models
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
