# T2 — Commit / Confirm Gestures & Dwell Timing

## Focus
Reliable ways to CONFIRM a mid-air selection, with concrete timing and false-trigger /
fatigue tradeoffs. Here: confirm "I want to become THIS avatar" and "step back to browse."

## Sub-questions
1. **Dwell / hover-to-select:** recommended dwell times in **milliseconds** from studies
   and vendor guides. Ranges for public displays, Kinect, Leap, HoloLens/MRTK, eye/gaze
   dwell, gaze+pinch. Tradeoff: too short = false positives; too long = fatigue/frustration.
2. **Push / press ("air tap", press-to-select):** accuracy, the "recoil"/drift problem,
   depth ambiguity.
3. **Grab / pinch / clasp:** pinch-to-select (visionOS), grab gestures, two-hand clasp as
   a deliberate confirm; false-activation resistance.
4. **Two-hand / symmetric gestures** as high-intent confirmations ("this one!"), and their
   discoverability.
5. Comparative: which confirm methods minimize false triggers AND fatigue for a short,
   one-shot public interaction. Progress-ring feedback effect on perceived wait.

## Evidence to find
- Dwell-time HCI literature (pointing + selection, gaze dwell ~400–1000ms norms).
- Ultraleap "how to design" (dwell/hover, timing), MRTK interaction guidance,
  Apple visionOS Human Interface Guidelines (gaze + pinch).
- Kinect press/grip selection guidance; public-display selection studies.

## Output
Write findings to `outputs/.drafts/midair-gesture-kiosk-ux-research-commit-timing.md`.
WebSearch several angles + WebFetch reachable HTML/docs. Avoid PDF parsing; cite PDF URLs
and mark blocked if only PDF. Record concrete ms numbers with source URLs; flag any number
that appears in only one source. Return a one-line summary.
