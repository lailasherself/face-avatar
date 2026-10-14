# ZED camera fix for outdoor air-swipe (2026-10-14)

On the Jetson/ZED installation, air swipes armed but never completed outdoors:
the gesture reached "armed", then the hand vanished the instant it moved. Live
traces and captured frames showed the cause was in the camera server
(`scripts/zed_capture.py`), not the gesture code:

1. **Backlit silhouette.** Outdoors the ZED auto-exposure metered the bright sky,
   rendering the visitor too dark for the hand detector to read (hand found in
   ~2% of frames). Fix: point the auto-exposure/gain ROI at the tracked person's
   head and torso each frame (`set_camera_settings_roi(AEC_AGC_ROI, ...)`),
   resetting to full-frame when no one is selected.
2. **Privacy mask clipped the hand.** The mask that blacks out everyone but the
   selected visitor only extended ~1.2 shoulder-spans past the shoulders. A swipe
   reaches ~2 spans, so the moving hand crossed into the blacked-out region and
   disappeared mid-gesture. Fix: widen the shoulder-based reach to 2.2 spans and
   trust joints at >=.3 confidence (matching the browser-side gesture gate;
   HUMAN_BODY_FAST reports raised wrists at ~.4-.7).

After deploying, swipes completed on camera (orbit -> cosmic -> nebula and on),
past the previous three-character wall, at a normal standing distance. Remaining
sparseness is the HUMAN_BODY_FAST wrist-dropout limit (see memory notes), not
this fix.

## Status / how to land it properly

This change is **live on the Jetson** (`releases/20261008-perf/scripts/zed_capture.py`,
backup `zed_capture.py.before-mask-exposure`) but is **not yet in `main`**. The
deployed `zed_capture.py` is a local-only version ~200 lines ahead of `main`
(the ZED installation work on open PRs #20 `jetson-lean-roster` and #21
`jetson-gesture-wrist-gate`, plus unpushed local edits), so this patch does not
apply to `main`'s `zed_capture.py`.

- `zed_capture-mask-exposure.patch` — the isolated change (unified diff) against
  the currently deployed file.
- `zed_capture-deployed-with-fix.py.reference` — the full deployed file with the
  fix, for reference.

To land it: once the Jetson's `zed_capture.py` base is in the repo (via #20/#21
or a dedicated ZED-deploy PR), apply this patch (or port the two edits in
`visitor_region` and the capture loop) and rebuild the release.
