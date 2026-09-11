# Movement References And Verification

## Live Pipeline Follow-Up

The visitor still reported poor movement, tongue timing and contorted mouths after
the synthetic direction tests below. The follow-up changes the execution pipeline,
not the arm smoothing constants:

- Face inference now runs in `face-tracking-worker.js`, with GPU/CPU fallback and
  bounded frame ownership in `face-tracking.js`. MediaPipe's official guidance
  explicitly documents blocking detection calls and recommends workers:
  https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/web_js
- Pose runs independently of finger inference in a nested local worker. Pose
  completion releases capture immediately; late finger results cannot release a
  different in-flight pose. Fingers/swipes use the pose from their captured image.
- Tongue sampling is capped at30Hz, one frame in flight. After the visitor's
  recording confirmed lag, the old face-returned bitmap path was removed from
  the installation: it serialized face and tongue pixel age whenever face took
  over100ms. Fresh camera pixels now use a bounded <=180ms recent face crop;
  duplicate frames and delayed bitmap creation are rejected.
  Strong scores >=.8 activate immediately; ambiguous >=.55 scores still need two
  samples; <.35 retracts. Tongue morph smoothing is45/s instead of17/s.
- Real-model slow-face regression (110ms injected face work): previous scheduling
  median tongue pixel age at result146.1ms, fresh scheduling13.1ms. Run
  `test_tongue_freshness_browser.cjs`; `TONGUE_LEGACY_FRAMES=1` recreates the previous
  fallback through test-only page routing. No model outputs are substituted.
  This isolates scheduling, not human gesture latency or classifier accuracy.
- The classifier still estimates presence, NOT tip position or physical extension
  length. Photo-fixture end-to-end transitions measured roughly150-300ms on the
  development Mac. These switch between different faces, so include reacquisition
  and are NOT proof of accurate physical visitor pacing. No tip-tracking claim.
- `mouth-signals.js` resolves competing controls, limits compounded opening and
  narrowing, and prevents lip controls from deforming the oral cavity/tongue.
  Blender mouth target v2 smooths only displacement fields where bind-space
  fold/stretch checks improve. Neutral vertices, skin, eyes, fingers, long tongue,
  body correctives and topology are unchanged. Source lip creases remain.

`test_worker_pacing_browser.cjs` adds150ms of face-worker CPU work and150ms delay
to finger results: 151 renders,50 pose results,10 finger results in about2.5s;
95th-percentile render interval16.8ms. This tests thread isolation, not GEEKOM/Orin
certification. Read-only QA adds face frames/latency/delegate and pose frames.

Mouth fixtures:32 cases across8 characters. Combined talking changed from767 to99
triangles with reversed normals relative to neutral, and1546 to176 triangles with
an edge stretched over2x. These are deformation diagnostics, not zero-defect or
production-rig claims. Rendered examples: `.context/qa/mouth-combinations/final/`.

Rebuild mouth pass: `Blender -b --python scripts/refine_mouth_targets.py`, after
full rig/tongue rebuilds. It starts from `.context/before-mouth-cleanup/`, preserving
the immediately preceding v5 tongues. Existing deterministic older rebuild scripts
start from older snapshots: do not run them over these outputs without reapplying
the mouth pass. `validate_mouth_preservation.py` checks the final stage's exact
unrelated data preservation; the older tongue-only validator expects pre-mouth
data and is not the final-stage preservation check.

## Earlier References

Reviewed September 8, 2026. YouTube titles/channels verified through YouTube
oEmbed and the creators' linked pages. Video playback/transcripts were not
available here; implementation decisions use the primary written guidance and
reference source code below, not a claim to have watched the videos.

## YouTube

- Gery Casiez: "1 Euro Filter: A Simple Speed-based Low-pass Filter for Noisy
  Input in Interactive Systems (CHI 2012)"
  https://www.youtube.com/watch?v=ybZR4WRjkpM
  Author's comparison video, linked on https://gery.casiez.net/1euro/.
  The accompanying guidance distinguishes stationary jitter from fast-motion
  latency. We use the author's verified JavaScript implementation, vendored
  locally with its BSD license, rather than increasing constant smoothing.
- Rokoko: "Rokoko Studio Live Plugin for Blender - including Retargeting tool
  for Motion Capture animations"
  https://www.youtube.com/watch?v=HitTDDCfhJg
  Official accompanying guide:
  https://support.rokoko.com/hc/en-us/articles/4410463481489-Retarget-an-animation-in-Blender
  Check source/target bone mapping, proportions and matching calibration poses.
  Existing alien rest calibration is retained, separate from the collision-safe
  idle pose. No Rokoko service, subscription or suit is required by this app.

## Local Changes

- Camera-time One Euro filtering: unit directions, 1.5Hz minimum cutoff,
  beta 4, derivative cutoff 1Hz, independent axes/joints/sides. Repeated or old
  samples do not advance history; a 400ms gap resets that side.
- Retargeting maintains its own rotation state, isolated from collision output.
  Continuous shortest-arc transport avoids ambiguous bone roll near the opposite
  rest direction; slow twist recentering only operates while moving and away from
  that singularity, so a held arm does not continue untwisting.
- Collision solving retains the previous feasible route, refines escape paths,
  and evaluates alternate directions for continuity. Consistent joint radii leave
  elbow clearance. Forearm queries reserve hand reach; wrists retain their bend
  relative to a deflected forearm. These are convex contact constraints, not a
  ragdoll, cloth simulation, anatomical IK solver, or swept collision guarantee.
- Tongue presence is binary after two-frame confirmation and hysteresis, not a
  confidence-based length estimate. Existing facial smoothing animates full
  extension/retraction. Tongue morph v5 is substantially longer, root anchored,
  and curved down. Early jaw opening clears the lower lip during extension.

## Checks

`test_arm_fluidity_browser.cjs` compares filtered/unfiltered input using the SAME
current collision and retargeting code. At 30Hz synthetic camera / 60Hz rig steps,
stationary hand jitter falls about 79-83%; the continuous noisy sweep stays below
5 degrees per frame on all eight rigs. This is not a whole-application live-camera
latency benchmark. Unit tests also cover the rest-axis antipode and collision
feedback isolation. Scripted camera tests retain independent arms and fast changes.

Tongue tests cover all eight rendered rigs at zero/half/full extension, quantify
length and canvas pixel visibility, and run actual local face/tongue inference
on positive/neutral camera fixtures. Exact GLB comparisons preserve all base mesh
attributes and unrelated morphs. Original and preceding v4 assets remain backed
up. Fixtures do not establish detection accuracy for every visitor or lighting
condition. Physical GEEKOM/Orin performance remains unverified.
