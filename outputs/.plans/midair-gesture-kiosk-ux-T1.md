# T1 — Disambiguation, Clutching & Mode-Switching (no button)

## Focus
How HCI separates *deliberate* menu/command gestures from *incidental or continuous*
motion — especially when the user's limbs are ALREADY doing a primary continuous task
(here: their arms drive an avatar's arms in real time). This is the core question.

## Sub-questions
1. The "Midas touch" / "live mic" problem in gesture UIs — definition, canonical sources.
2. Clutching / engagement & disengagement gestures: how systems gate when input "counts."
   Reserved poses, held stillness, spatial engagement zones, timeouts, explicit
   start/stop gestures, hand raised above shoulder, "engagement" in Kinect for Windows.
3. Mode switching without a physical button: how to toggle browse-mode vs engaged-mode.
   Two-hand gestures, T-pose/timeout, "menu palm," push-to-menu, edge/zone triggers.
4. Continuous-vs-deliberate separation: motion vs stillness as a discriminator; velocity/
   dwell thresholds; "delimiters" for gesture segmentation (start/stop of a gesture).
5. Specifically: patterns that work when the primary limbs are busy (e.g. reserve a
   different limb, a held static pose, voice, gaze, foot, lean, or a distinct 2-hand pose).

## Evidence to find
- Kinect for Windows Human Interface Guidelines (engagement, "grip"/press, Midas touch).
- Academic: gesture delimiters/segmentation, clutching in mid-air, Vogel & Balakrishnan
  distant freehand pointing (2005), Walter/Müller engagement on public displays.
- Ultraleap / Leap Motion, Microsoft MRTK guidance on avoiding accidental activation.

## Output
Write findings to `outputs/.drafts/midair-gesture-kiosk-ux-research-disambiguation.md`.
Use WebSearch (several angles) + WebFetch on reachable HTML/doc pages. Avoid PDF
full-text parsing — cite PDF URLs from search metadata and mark as blocked if only a PDF.
Capture concrete numbers (thresholds, times), source URLs inline, and note single-source
claims. Return a one-line summary.
