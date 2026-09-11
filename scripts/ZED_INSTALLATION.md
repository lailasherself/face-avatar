# Local ZED / Orin Installation

The ZED path is implemented but has NOT been tested on a physical ZED or Orin.
Do not treat simulated packet tests as hardware approval. Exact ZED model and
JetPack/SDK versions still need confirmation. The original ZED and monocular
ZED X One models do not support the SDK body-tracking module.

## Setup On The Orin

1. Install a ZED SDK release compatible with the Orin's installed JetPack, the
   matching `pyzed` Python package, and OpenCV (`cv2`). Use the SDK's own Python
   installation instructions. Do not install an unrelated package named `zed`.
2. Connect the supported ZED camera. USB models and GMSL ZED X models have different
   connection/driver requirements; identify the camera before choosing a driver.
3. Run Stereolabs' native Body Tracking sample once. Confirm independent arm
   movement, usable depth, and successful AI model optimization. SDK installation
   and initial model provisioning may require internet; runtime data stays local.
4. From this repository run:

```sh
python3 scripts/run_installation.py --tracking zed --port 8014 --check
python3 scripts/run_installation.py --tracking zed --port 8014
```

`--check` verifies imports/files without opening the camera. It does not verify
GPU inference, camera connection, or sustained performance. Use `--zed-serial`
to select one of several connected cameras. Use a free port if 8014 is occupied.
`--setup` exposes the existing operator controls; automatic capture remains on.

## Data Flow

`pyzed.sl.Camera` is the sole device owner. It retrieves a fitted BODY_34 skeleton
and the left RGB image from the same grab. It uses meters, OpenGL Y-up coordinates,
and the CAMERA reference frame. FAST body inference and no prediction or additional
SDK skeleton smoothing keep the existing arm filter in control of smoothing.

The loopback server stores only the latest sample, not a frame queue. An atomic
JPEG response carries its skeleton, session, sequence and native sample age in
`X-Zed-Sample`. The renderer subtracts native age plus request/decode duration
from its local clock; delayed samples are not restamped as current. Samples over
250ms old are rejected. Face/tongue have their existing stricter acceptance bounds.

The renderer uses depth-derived arm directions, not uncalibrated SDK local bone
quaternions: the alien skeleton axes/rest poses differ from the SDK T-pose.
Existing per-side smoothing, collision guards and pose correctives remain active.

The same RGB stream feeds separate local face, tongue and finger workers. ZED mode
does NOT open `getUserMedia` or load the MediaPipe pose model. Finger tracking and
held-palm air swipes use the selected ZED visitor's projected shoulders/wrists.
Visitor IDs are retained across brief occlusions; other people are masked outside
the selected bounding rectangle to reduce cross-person expression pickup. This
rectangle is not segmentation: overlapping people can still confuse face/hands.

## Hand Detail And Diagnostics

### Camera Framing

Open `http://localhost:8014/cockpit.html?framing&assets=3dai&tracking=zed`
on a freshly launched native ZED server. The operator's Camera Framing button
opens the same view. Development webcam preview omits `tracking=zed`.
Framing alone does not enable operator panels. Old `setup&framing` links are
normalized to framing-only before the first paint. Closing the dialog removes
the framing flag, leaving the avatar-only installation even after refresh.
The dialog shows the entire delivered image, mirrored like the installation,
with independent left/right arm edge indicators. It reads the same camera stream;
opening/closing it does not create another capture or stop tracking. The default
public display is unchanged. The small operator preview also uses contain instead
of cover, so a16:9 stream is no longer visually cropped into its4:3 box.

Webcam capture now prefers1280x720 at30fps and requests native `resizeMode: none`
when supported, avoiding browser crop-and-scale. This does not turn a narrow lens
into a wide lens or disable camera-driver/OS auto-framing. Native ZED capture
already uses the SDK's full delivered left image and is not a getUserMedia source.
Its selected-person mask now includes confident arm joints and extra wrist reach
margin instead of relying only on the body's bounding box; it remains a rectangle,
not segmentation, and overlapping people can still share visible pixels.

With both arms fully extended, both hands need to stay inside the actual camera
frame, preferably with room to move. Reposition the camera or standing mark if
they do not. Keep checking facial detail at the resulting distance; do not assume
that a full-body picture guarantees enough tongue/finger pixels. Display zoom and
software crops cannot recover anatomy outside the physical camera view.

Constraint reference: [W3C Media Capture and Streams](https://www.w3.org/TR/mediacapture-streams/).

Camera capture for the hand path now retains up to960 pixels of width (without
upscaling a smaller input). In development webcam mode, only the body worker's
copy is reduced to480 pixels; the independent finger worker receives the larger
image. Native ZED mode uses the same retained RGB detail directly.

`hand-crops.js` locates square crops around the two projected wrists, using
forearms, shoulder span and optional ZED palm hints for coverage. A fixed640x320
two-tile image feeds the existing single HandLandmarker model, one inference per
frame. Coordinates are mapped back to the camera before wrist matching and swipe
recognition. Overlapping duplicate detections and landmarks crossing tile edges
are rejected. Missing wrist hints fall back to the full frame; no selected native
body skips inference. Crop/full-frame transitions can require reacquisition.
The model still runs on CPU; this is not a TensorRT/GPU hand pipeline.

The existing QA view (`?qa&assets=3dai&tracking=zed`) exposes
`fleetQA.handDiagnostics`: status, source dimensions, crop bounds, raw detections,
mapped/matched hands, inference duration, capture-to-result age, last-result age,
and separate late-capture, late-result, missing-detection and wrist-match counters.
Statuses distinguish `tracking`, `not-detected`, `crop-rejected`, `no-wrist`,
`wrist-unmatched`, `no-body`, `late`, `late-capture` and `out-of-order`.
These diagnostics stay off the public installation display. They do not record
camera images. Results over250ms old still cannot drive fingers or switching.

Real-model crop regression uses Google's hand test photo (development only):

```sh
curl -fL https://storage.googleapis.com/mediapipe-assets/right_hands.jpg -o .context/qa/right_hands.jpg
node --test scripts/test_hand_crops.mjs
NODE_PATH=.context/qa/node_modules node scripts/test_hand_crops_browser.cjs
```

Fixture provenance: [MediaPipe's hand-landmarker tests](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/python/test/vision/hand_landmarker_test.py).
This checks real model inference with simulated body hints, not a physical ZED,
visitor recognition rate, or Orin throughput. Cropping cannot recover finger
detail absent from the camera image or see a hand hidden behind the body.

Camera stop/retry also stops/restarts native capture. Loss of the local client
expires the capture lease after ten seconds. Frames are never recorded to disk
or sent to a remote service. Endpoints reject cross-site requests and non-loopback
Host headers. Camera control POSTs require the installation's custom header.

## Limits And Acceptance

- Tongue detection still classifies presence; it does not measure tongue-tip
  position or physical extension length. Do not promise exact length matching.
- Face/tongue detail depends on face pixel size, light, pose and camera distance.
  The shared RGB stream is 960 pixels wide, preserving aspect ratio. Validate at
  the actual visitor distance rather than assuming full-body framing is sufficient.
- Measure end-to-end latency and sustained performance with rendering, depth,
  body fitting, face, tongue and fingers all running on the actual Orin.
- Test left/right-only raises, forward reach, elbows bent, fingers, tongue hold
  and retract, face loss, body occlusion, visitor changes, unplug/replug and restart.
- The remaining mouth/clothing surface defects are a separate rig-quality issue.

Development regression commands (no physical ZED):

```sh
python3 scripts/test_zed_capture.py
node --test scripts/test_zed_motion.mjs scripts/test_zed_hand_identity.mjs scripts/test_face_tracking.mjs
NODE_PATH=.context/qa/node_modules node scripts/test_zed_browser.cjs
```

## Primary References

- [SDK body API](https://www.stereolabs.com/docs/development/zed-sdk/modules/body-tracking/using-the-api)
- [Official Python body sample](https://github.com/stereolabs/zed-sdk/blob/master/body%20tracking/body%20tracking/python/body_tracking.py)
- [Python API joint enums](https://github.com/stereolabs/zed-python-api/blob/master/src/pyzed/sl.pyx)
- [Coordinate systems](https://docs.stereolabs.com/docs/development/zed-sdk/modules/positional-tracking/coordinate-frames)
- [Jetson SDK installation](https://docs.stereolabs.com/docs/development/zed-sdk/linux/work-with-nvidia-jetson)
