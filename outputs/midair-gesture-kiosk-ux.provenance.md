# Provenance: Mid-air Gesture UX for a Walk-Up Avatar-Embodiment Kiosk

- **Date:** 2026-09-11
- **Rounds:** 1 (4 parallel researcher agents) + 1 verification/review pass
- **Sources consulted:** ~45 across 4 research files (HCI papers, vendor design docs —
  Microsoft Kinect HIG / MRTK, Ultraleap, Apple visionOS — and museum-installation postmortems)
- **Sources accepted:** peer-reviewed/primary (Vogel & Balakrishnan UIST 2004/2005; Müller et al.
  MM 2010 / "Looking Glass"; Wouters DIS 2016; Consumed Endurance CHI 2014; Jang CHI 2017; NICER
  TOG 2024; gaze-dwell ScienceDirect) + authoritative vendor guidance (Kinect HIG, MRTK,
  Ultraleap TouchFree/XR, visionOS) + Ideum full-body exhibit case study.
- **Sources rejected / limited:** several primaries were PDF-only and not full-text parsed
  (cited by URL, flagged); some figures single-source (+90%/+47% Looking Glass; ~2 s min-hold;
  ~800 ms AR/VR dwell; ~230 ms visionOS; CE mid-torso wording) — marked directional. Honeypot
  66.7%/11% is from a VR-simulated study (ecological-validity caveat carried into the brief).
- **Verification:** PASS WITH NOTES. Reviewer pass: 0 FATAL, 0 MAJOR, 4 MINOR — all 4 minors
  (exec-summary caveat placement, honeypot VR caveat, softened "never happens" wording, removed
  unsourced "45 years") fixed and verified on disk (grep confirmed 5 fix markers present).
  Remaining limitation: PDF full-text not parsed per workflow; exact dwell/hold numbers are
  research bands to be tuned on-site.
- **Plan:** outputs/.plans/midair-gesture-kiosk-ux.md
- **Research files:** outputs/.drafts/midair-gesture-kiosk-ux-research-{disambiguation,
  commit-timing,discoverability,ergonomics-cases}.md
- **Draft/cited/verification:** outputs/.drafts/midair-gesture-kiosk-ux-{draft,cited,verification}.md
- **Final:** outputs/midair-gesture-kiosk-ux.md
