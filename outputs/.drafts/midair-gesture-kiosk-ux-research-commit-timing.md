# T2 — Commit / Confirm Gestures & Dwell Timing (research findings)

Scope: reliable ways to CONFIRM a mid-air selection on a public kiosk, with concrete
timing (ms) and false-trigger vs fatigue tradeoffs. Sources are inline. Numbers seen in
only ONE source are marked **[single-source]**. PDF-only sources are marked
**[PDF full-text blocked]** — cited from search/metadata only, not parsed.

---

## 1. Dwell / hover-to-select timing (concrete ms)

### Gaze dwell (eye-tracking) norms
- **250–1000 ms** rated potentially useful for gaze object selection; **600 ms** was the
  preferred dwell across object types. Study tested **200, 400, 800, 1000, 1200 ms**.
  Source: Usability of various dwell times for eye-gaze-based object selection (Kyushu U. /
  ScienceDirect) — https://www.sciencedirect.com/science/article/pii/S0141938221000123 and
  https://kyushu-u.elsevierpure.com/en/publications/usability-of-various-dwell-times-for-eye-gaze-based-object-select/
- Classic eye-typing dwell values: **900 ms** (early studies) vs **450 ms** (short-dwell
  study); short dwell is faster but needs simplified feedback and raises double-entry
  errors. Adjustable-dwell longitudinal study: novices went 6.9 → 19.9 wpm over 10
  sessions as dwell shortened.
  Source: Majaranta & MacKenzie, "Effects of feedback and dwell time on eye typing speed
  and accuracy" — https://www.yorku.ca/mack/uais2006.html
  (HTML fetch blocked by TLS cert error; numbers taken from search abstract + Semantic
  Scholar https://www.semanticscholar.org/paper/a9dd025f3814d83a41cf053be8e939b258b22a0e);
  "Fast Gaze Typing with an Adjustable Dwell Time" (Majaranta CHI'09,
  https://homepages.tuni.fi/oleg.spakov/publications/Majaranta_CHI_09.pdf) **[PDF full-text blocked]**.
- General dwell-pointing summary values cited across HCI: a few hundred ms up to ~800 ms,
  with **500 ms** and **300–800 ms** and **400–600 ms** commonly recommended; some apps use
  **~750 ms** **[single-source]** (only surfaced in one aggregated search summary, no clean
  primary citation — treat as soft).
  Source (aggregated): search results incl.
  https://www.researchgate.net/publication/221054246_Dwell-Based_Pointing_in_Applications_of_Human_Computer_Interaction

### VR/AR task-specific dwell (GazeIntent)
- Pilot-tuned static dwell: **300 ms** (circle selection), **1200 ms** (sliding puzzle),
  **1500 ms** (arithmetic). Adaptive intent model gave up to **273% more selections** vs
  baseline and F1 0.94 for intent prediction. **[single-source]** for these exact ms values.
  Source: GazeIntent (arXiv HTML) — https://arxiv.org/html/2404.13829v1

### visionOS gaze-hover feedback timing
- **230 ms** recommended fade-in for gaze hover feedback: faster feels self-conscious,
  slower causes eye strain / "stare to activate" feeling. Also warns NEVER show a raw gaze
  cursor (offset feedback loop). Min target **60 pt (~3° visual angle)**.
  **[single-source]** for the 230 ms figure.
  Source: Ken Pfeuffer, "Design Principles & Issues for Gaze and Pinch Interaction"
  (Antaeus AR / ShapesXR) —
  https://www.shapesxr.com/articles/eye-gaze-the-next-wave-of-user-interfaces-led-by-the-apple-vision-pro
  (companion Medium article returned 403:
  https://medium.com/antaeus-ar/design-principles-issues-for-gaze-and-pinch-interaction-a95e251169ae)

### Ultraleap "Hover & Hold" (touchless kiosk)
- Interaction has TWO configurable durations: a start/enter hold before the timed
  animation begins, and a second hold to fire the click. Ultraleap says defaults are
  research-based and advises caution changing them, and advises AGAINST maximum cursor
  responsiveness with Hover & Hold (jitter → false/mis-triggers). No public numeric default
  is published on these pages.
  Sources: https://docs.ultraleap.com/touchless-interfaces/interaction-types/hover-and-hold
  (returned 403 direct);
  https://docs.ultraleap.com/TouchFree/touchfree-user-manual/interaction-settings.html;
  https://docs.ultraleap.com/TouchFree/touchless-interfaces/interactions.html

### Tradeoff (dwell)
- Longer dwell → fewer false selections but eye/arm fatigue and frustration; shorter dwell
  → Midas-touch false positives. This speed/accuracy tradeoff is the consistent finding
  across the gaze sources above.

---

## 2. Push / press ("air tap", press-to-select)

- HoloLens air-tap = "ready → pressed" state transition detected by depth camera; air taps
  have a learning curve and a **higher recognition-error rate than a physical button
  click**. Pinch detection flips on a threshold, so hovering near the threshold causes
  chatter.
  Sources: https://github.com/microsoft/MixedRealityToolkit-Unity/issues/7998 ;
  https://localjoost.github.io/Getting-raw-air-taps-and-their-positions-with-MRTK3/
- Distant freehand pointing: Vogel & Balakrishnan proposed **AirTap** (index finger down-up)
  and **ThumbTrigger** (thumb in-out) as click gestures; ray-cast pointing is fast but
  inaccurate, and the core problem is the lack of a physical plane for a clean on/off action
  — i.e., depth ambiguity and recoil/drift on the press.
  Source (UIST'05) — https://www.dgp.toronto.edu/~ravin/papers/uist2005_distantpointing.pdf
  **[PDF full-text blocked]**

---

## 3. Grab / pinch / clasp

- visionOS model: eyes are the pointer, **pinch (thumb+index) confirms** — near-zero
  physical effort (hands can rest in lap), which is the main fatigue advantage over
  push/reach gestures. Hover triggers on look; select on pinch.
  Sources: https://developer.apple.com/news/?id=fi8ne6ji (Apple Q&A spatial design);
  https://applemagazine.com/apple-vision-pro-gestures/
- Arm-fatigue evidence (Consumed Endurance metric): **click outperforms all selection
  methods on endurance; dwell and second-hand use consume similarly little** — reach/push
  ("gorilla arm") is the worst. Supports low-effort confirm (pinch/dwell/second-hand) for
  sustained use.
  Sources: Consumed Endurance (CHI'14) —
  http://hci.cs.umanitoba.ca/publications/details/consumed-endurance-a-metric-to-quantify-arm-fatigue-of-mid-air-interactions
  (PDF: https://hci.cs.umanitoba.ca/assets/publication_files/Consumed_Endurance_-_CHI_2014.pdf
  **[PDF full-text blocked]**);
  gorilla-arm overview https://phys.org/news/2017-05-gorilla-arm-fatigue-mid-air-usage.html

---

## 4. Two-hand / symmetric & deliberate confirms

- Study of confirmation gestures on displays: compared several confirm gestures; **hover
  was found best for confirming a selection** (all felt reasonably intuitive). Pairing
  dwell time with a gesture cut unintentional selections (Midas touch); introducing a
  **minimum hold of ~2 seconds** substantially reduced misinterpretation errors.
  **[single-source]** for the 2 s figure.
  Source: "Analyzing Mid-Air Hand Gestures to Confirm Selections on Displays" (Springer;
  direct link auth-gated) —
  https://link.springer.com/chapter/10.1007/978-3-030-05532-5_25
- Public-display elicitation (Kinect, n=10): point-and-dwell perceived MORE accurate, but
  **push was preferred for selecting** and grab-and-pull for navigation — i.e., users
  trade some accuracy for a more deliberate/expressive confirm.
  Source: touchless gestural interaction for a university public display (arXiv) —
  https://arxiv.org/pdf/2011.09749 **[PDF full-text blocked]**
- Multi-stage / two-step confirm ("detect intent, then confirm/deny") is an explicit
  low-false-positive pattern.
  Source: https://link.springer.com/chapter/10.1007/978-3-030-05532-5_25
- Discoverability: mid-air two-hand/symmetric gestures score well on deliberateness but
  poorly on discoverability/memorability without onscreen affordances — recurring caveat.
  Source: Gesture Elicitation Studies review —
  https://www.researchgate.net/publication/328036083_Gesture_Elicitation_Studies_for_Mid-Air_Interaction_A_Review

---

## 5. Comparative + progress-ring feedback

- No single method wins both axes: dwell/pinch/second-hand minimize FATIGUE; a deliberate
  push or a short hold minimizes accidental FALSE TRIGGERS. For a short one-shot public
  interaction the low-friction pattern is **gaze/point + dwell (~600 ms) with a visible
  progress ring**, or **point + short hold** — and a **deliberate two-hand or hold confirm
  reserved only for the irreversible "become THIS avatar" commit** (higher intent, worth
  the extra cost since it happens once).
- Mid-air method comparison (Push/Tap/Dwell/Pinch, Fitts'-law + ultrasonic haptics):
  relevant head-to-head, but **[PDF full-text blocked]** — numbers not parsed.
  Source: MacKenzie et al., ISS 2022 — http://www.yorku.ca/mack/iss2022.html
  (direct fetch failed on TLS cert)

### Progress-ring / feedback effect on perceived wait
- NN/g response-time thresholds: **<1 s** no indicator; looped spinner for **~2–10 s**;
  **percent-done indicator for ≥10 s**. A moving feedback bar made users willing to wait on
  average **~3× longer** and raised satisfaction. Percent-done is most informative;
  inconsistent speed hurts satisfaction.
  Source: https://www.nngroup.com/articles/progress-indicators/
- Dwell UIs: shrinking symbol / filling target on focus gives users confidence and a chance
  to cancel before commit; progress bars beat countdowns/static icons/no-feedback for
  reducing perceived wait and anxiety (sense of control/predictability).
  Sources: eye-typing feedback work (https://www.yorku.ca/mack/uais2006.html, TLS-blocked);
  perceived-wait visual-feedback review
  https://www.iieta.org/journals/ts/paper/10.18280/ts.390423

---

## Practical takeaways for the avatar kiosk
- Browse/hover selection: gaze/point + dwell around **600 ms** (norm band 250–1000 ms) with
  a filling progress ring; keep dwell short enough to avoid fatigue, long enough to dodge
  Midas touch.
- Irreversible commit ("become THIS avatar"): use a MORE deliberate confirm — longer hold
  (toward ~1–2 s) or a two-hand/pinch gesture — because the higher false-trigger cost
  justifies extra intent, and it's a one-time action so fatigue is negligible.
- Always show progress feedback during any hold >1 s (NN/g), and allow cancel-by-moving-away.
- Avoid pure reach/push for repeated actions (gorilla arm); pinch/dwell/second-hand are
  lowest-endurance-cost.

## Numbers flagged as single-source (verify before quoting)
- **230 ms** visionOS hover fade-in (ShapesXR/Antaeus only).
- **300 / 1200 / 1500 ms** GazeIntent task dwells and 273% figure (that paper only).
- **~750 ms** generic dwell (aggregated search summary, no clean primary source).
- **~2 s** minimum hold to cut confirm errors (Springer confirm-selections chapter only).

## Sources where full text was blocked (cited, not parsed)
- MacKenzie ISS 2022 (Push/Tap/Dwell/Pinch): http://www.yorku.ca/mack/iss2022.html (TLS)
- Majaranta UAIS 2006 & CHI 2009: https://www.yorku.ca/mack/uais2006.html (TLS),
  https://homepages.tuni.fi/oleg.spakov/publications/Majaranta_CHI_09.pdf (PDF)
- Vogel & Balakrishnan UIST 2005: https://www.dgp.toronto.edu/~ravin/papers/uist2005_distantpointing.pdf (PDF)
- Consumed Endurance CHI 2014: https://hci.cs.umanitoba.ca/assets/publication_files/Consumed_Endurance_-_CHI_2014.pdf (PDF)
- University public display: https://arxiv.org/pdf/2011.09749 (PDF)
- Springer confirm-selections chapter: auth-gated (303 redirect to idp.springer.com)
- Ultraleap Hover & Hold page: 403 on direct fetch (content recovered via related docs pages)
- Interaction Design of Dwell Selection (ETRA'22): https://arxiv.org/pdf/2204.08156 (PDF), DOI 10.1145/3517031.3531628
