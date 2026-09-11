# Deep Research Plan: Mid-air Gesture UI for Walk-up Kiosks (embodiment context)

**Date:** 2026-09-11
**Slug:** midair-gesture-kiosk-ux

## Context
Museum/event installation. Visitors swipe in the air to cycle through alien avatars,
then **embody** the chosen one — face + arms + fingers tracked live (arms drive the
avatar's arms). Core tension: the arms are used for BOTH menu navigation AND continuous
puppeteering. Need to disambiguate intent, commit to a choice, and re-enter selection —
all without a physical button, discoverable by the general public with no instructions.

## Key Questions
1. **Midas touch / clutching:** How does HCI disambiguate deliberate menu gestures from
   incidental/continuous motion? Engagement & disengagement gestures, clutch mechanisms,
   "live mic" problem. What works when the user's limbs are already doing a primary task?
2. **Commit/confirm gestures:** Dwell-to-select (recommended ms ranges), push/press,
   grab/pinch, two-hand/clasp. False-activation rates and fatigue tradeoffs of each.
3. **Mode switching without a button:** browse-mode ↔ engaged/embodied-mode. Reserved
   poses, held stillness, two-hand gestures, timeouts, spatial zones.
4. **Discoverability / self-teaching:** palm cursor, progress rings, affordances, attract
   loops, onboarding for zero-instruction public use (Kinect-era + modern findings).
5. **Ergonomics / gorilla-arm:** fatigue of held/raised-hand gestures; interaction-plane
   height, duration limits, consumed-endurance metric; design mitigations.

## Evidence Needed
- HCI papers/surveys: mid-air interaction, clutching, engagement gestures, dwell timing.
- Concrete dwell-time numbers (ms) from studies / vendor guidance (Kinect, Leap Motion,
  HoloLens/MRTK, Vision Pro, Xbox NUI, public-display research).
- Gorilla-arm / "consumed endurance" research (Hincapié-Ramos et al.).
- Public-display & museum installation case studies; "honeypot"/attract-loop effect,
  "immediate usability" / "interaction blindness" literature (Vogel & Balakrishnan,
  Müller et al.).
- Design-system guidance: MRTK, Apple visionOS HIG, Leap Motion/Ultraleap design guides.

## Scale Decision
Broad, multi-faceted (5 sub-domains) → **4 researcher subagents** + lead synthesis.
Not a "what is X" explainer; multi-agent decomposition clearly helps.

## Task Ledger
- **T1 — Disambiguation & clutching:** Midas touch, engagement/disengagement, clutch,
  reserved poses, continuous-vs-deliberate separation, mode switching without buttons.
- **T2 — Commit gestures & timing:** dwell-to-select ms recommendations, push/grab/pinch/
  two-hand confirm, false-trigger + fatigue tradeoffs, vendor design guidance.
- **T3 — Discoverability & self-teaching:** palm cursor/hand-mirror, progress rings,
  affordances, attract loops, interaction blindness, zero-instruction onboarding.
- **T4 — Ergonomics + embodiment/installation case studies:** gorilla-arm/consumed
  endurance, interaction-plane ergonomics, Kinect/AR-mirror/avatar-puppeteering museum
  installations and their gesture-vocabulary choices.

Owner: lead writes per-task briefs (T1..T4.md), spawns 4 researchers (concurrency 4,
failFast false), then synthesizes, cites (verifier), reviews (reviewer), delivers.

## Verification Log
- (to fill) URL reachability, dwell-ms claims cross-checked across ≥2 sources,
  single-source critical claims flagged.

## Decision Log
- 2026-09-11: Chose subagent scale (4) over direct search: 5 distinct sub-domains,
  each needs its own source set. Browse style fixed by user = "live embody while
  browsing" — so findings should weight solutions that work while arms are busy.
- 2026-09-11: PDF full-text parsing avoided per workflow; use abstracts/HTML/docs.
