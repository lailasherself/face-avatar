# T4 — Ergonomics (gorilla-arm) + Embodiment/Installation Case Studies

Research draft. Inline source URLs throughout. Concrete numbers captured where available.
Single-source claims are flagged **[single-source]**. PDF-only sources are cited but not
full-text parsed (flagged **[PDF — full text blocked]**).

---

## 1. Gorilla-arm fatigue and the "Consumed Endurance" (CE) metric

### The gorilla-arm effect
Mid-air interaction fatigues the shoulder and upper arm, producing a feeling of heaviness
known as the "gorilla-arm effect." Designers historically lacked a quantitative way to
assess it before building an interface.
- Overview: http://hci.cs.umanitoba.ca/projects-and-research/details/ce
- ACM DL entry: https://dl.acm.org/doi/10.1145/2556288.2557130

### Consumed Endurance (CE) — Hincapié-Ramos, Guo, Moghadasian, Irani, CHI 2014
CE is a metric "derived from the biomechanical structure of the upper arm" that quantifies
the gorilla-arm effect. Key validated facts:
- CE is computed from **shoulder torque** produced by the arm's mass/posture versus the
  arm's **endurance/strength**, captured non-intrusively with an off-the-shelf
  camera-based skeleton tracker (e.g., Kinect). It expresses the fraction of available
  endurance consumed by a gesture over time.
- CE **correlates strongly with the Borg CR10 scale** of perceived exertion — this is the
  paper's central validation claim.
- Sources: project page http://hci.cs.umanitoba.ca/projects-and-research/details/ce ;
  publication record http://hci.cs.umanitoba.ca/publications/details/consumed-endurance-a-metric-to-quantify-arm-fatigue-of-mid-air-interactions ;
  paper PDF https://hci.cs.umanitoba.ca/assets/publication_files/Consumed_Endurance_-_CHI_2014.pdf **[PDF — full text blocked]** ;
  Semantic Scholar https://www.semanticscholar.org/paper/416cebc00d038e5e11457c9d71e35025cd9a4829

### CE design guidelines (the actionable output of the paper)
From summaries of the CHI 2014 paper (corroborated across the UManitoba pages and search
metadata):
- **Least endurance is consumed when the arm is bent and operating on an interaction plane
  located roughly midway between the shoulder and the waist** — i.e., keep the working
  plane low, around mid-torso, not up at shoulder/eye level. **[single-source — appears in
  paper summary; verify exact wording against the PDF]**
- **Dwell selection has the lowest CE among single-hand selection techniques.**
- **Menu items should be located toward the bottom of the UI** (so the hand rests lower).
  Source (guideline summary): http://hci.cs.umanitoba.ca/projects-and-research/details/ce
  and search metadata for the CHI 2014 paper.
- The team released the open-source **Consumed Endurance Workbench** (real-time CE from
  skeleton tracking) and a fatigue-optimized mid-air text layout called **SEATO** as a
  demonstration.
  Workbench: https://dl.acm.org/doi/10.1145/2556288.2557130 (associated) ;
  https://www.academia.edu/17696164/ **[PDF — full text blocked]**

### Follow-up / refined models
- **Jang, Stuerzlinger, Ambike, Ramani — "Modeling Cumulative Arm Fatigue in Mid-Air
  Interaction," CHI 2017** (Purdue/SFU). Estimates maximum shoulder torque from a mid-air
  pointing task and builds a *cumulative* fatigue model (CE is more of a single-gesture/
  session snapshot). Reported accuracy: cumulative subjective-fatigue estimation error
  **~15% (vs ~35% for prior methods)**; arm-strength estimate error **8.4% with a depth
  camera vs 6.2% with lab equipment costing tens of thousands of dollars**.
  Experiment used shoulder- and waist-level screen heights; participants did **four
  one-minute target-touching segments with random 5–20 s rests**; strength test held
  **5-lb (male) / 3-lb (female) dumbbells** to exhaustion, n=24.
  - ACM DL: https://dl.acm.org/doi/10.1145/3025453.3025523
  - Purdue lay summary (numbers above): https://www.purdue.edu/newsroom/archive/releases/2017/Q2/study-researches-gorilla-arm-fatigue-in-mid-air-computer-usage.html
  - Author page: https://sites.google.com/site/sujinjang11/research/modeling-cumulative-arm-fatigue-in-mid-air-interactions
- **NICER (New and Improved Consumed Endurance + Recovery), ACM TOG 2024** — adds an
  empirical muscle-contraction term and a **recovery factor** modeling fatigue decay during
  rest; reports mean RMSE for endurance-time prediction dropping from **41.08 s to 19.11 s**
  vs prior models. Relevant for kiosks with short bursts + rest between users.
  https://dl.acm.org/doi/10.1145/3658230

**Takeaway for a kiosk:** keep the primary interaction plane low (mid-torso, bent elbow),
prefer dwell for selection, put menus/targets low in the frame, and design short
interactions with rest — cumulative fatigue and recovery both matter.

---

## 2. Ergonomic mitigations — vendor/platform guidance (concrete)

### Ultraleap (Leap Motion) — XR design principles & TouchFree
Comfort guidance (direct quotes / paraphrase):
- "Minimise the need for the user to perform large and strenuous movements."
- "Avoid users needing to **hold hand poses for extended periods**."
- "Try not to have users **raise the arm above the shoulder** too often."
- "Keep the need to **fully extend the arm to a minimum**."
- Position frequently accessed objects/UI "within easy reach and in clear view by default."
- **Reserve held hand-poses for high-value actions**, not frequent interactions (fatigue).
- Avoid interactions needing total occlusion (one hand fully covering the other) or
  frequent head-turns away from the hands (hands leave the tracking FOV).
- Tracking envelope numbers: Leap Motion Controller ~**140×120° FOV, ~80 cm range**;
  Stereo IR 170 ~**170×170°, ~100 cm range**; mid-air haptics optimal within a **50 cm
  interaction zone**.
  - https://docs.ultraleap.com/xr-guidelines/Getting%20started/design-principles.html
  - https://support.ultraleap.com/hc/en-us/articles/360004422398-Designing-effective-mid-air-haptics

TouchFree (touchless kiosk) guidance:
- Recommended panel/interaction height: **at eye height, typically 1.35 m–1.8 m
  (4.5–6 ft), and 1.15 m (3.8 ft) for adult wheelchair users.**
- Encourage users to "Stand Back" (use floor stickers) rather than reach toward the screen.
- Onboarding cursor appears on hand initialisation and hides after **2 confirmed
  interactions**; keep tooltips contextual/minimal.
  - https://docs.ultraleap.com/TouchFree/touchless-interfaces/guidance.html
  - Note: TouchFree docs do not publish an explicit dwell-time number here. **[single-source gap]**

### Apple visionOS — gaze + pinch (indirect selection to avoid arm fatigue)
- The pinch "is the new click" and "requires no physical effort — users can rest their
  hands in their lap." Indirect gaze+pinch is explicitly preferred for ergonomics over
  reaching/direct manipulation.
- Keep main content centered in the field of view so users don't move neck/body; minimize
  depth changes to reduce eye fatigue; "tiring postures, such as holding the hands in the
  air, should be used with caution."
  - Apple Q&A: https://developer.apple.com/news/?id=fi8ne6ji
  - Analysis (Pfeuffer, gaze+pinch): https://medium.com/antaeus-ar/design-principles-issues-for-gaze-and-pinch-interaction-a95e251169ae
  - visionOS guide: https://think.design/blog/the-complete-guide-to-designing-for-visionos/

**Cross-source consensus (multi-source):** keep hands low, avoid above-shoulder and
full-extension poses, avoid sustained held poses, and prefer low-effort/indirect selection
(dwell, or gaze+pinch analog). This is echoed by CE (mid-torso plane), Ultraleap, and Apple.

---

## 3. Embodiment / full-body avatar-mirror installations — menu & selection when the body is the controller

### Ideum museum exhibits (richest case-study source)
Ideum's postmortem of full-body Kinect exhibits ("Touchless Gesture-Based Exhibits, Part
Two: Full-Body Interaction") is the most concrete case study found:
https://ideum.com/news/touchless-interaction-public-spaces-part2
- **"Be a Bug":** used a *touch screen* to pick an insect, then switched to full-body
  gesture flight. The team later called the modality switch **"a design flaw"** — mixing
  touch + gesture created friction.
- **"Chow Time" (the fix):** went **fully gesture-based** — the visitor strikes a **pose
  gesture and then raises their hands to select** one of three penguin species from a **3D
  carousel**. This is the pattern to emulate: selection *is* a body pose, no separate menu
  device.
- Working gesture vocabulary in the wild: **arm flapping** (movement), **leaning
  side-to-side** (steering), **hand-raise** (menu select), **pose + lean** (evade).
- Feedback that mattered: **floor vinyl graphics marking the standing spot**, on-screen
  **animated pointers** directing where to move, and a **real-time skeletal outline** so
  the visitor sees they are being tracked.
- **DinoStomp** used an **8 ft × 20 ft wall with three Kinects**, with a custom algorithm
  fusing sensors across the wall's curve and varying visitor distances.
- **Failure mode:** tracking reliability degrades as **more visitors crowd the space**
  (skeleton confusion), though the exhibit's dynamic content masked it for most users.

### Selection mechanics used broadly in Kinect/gesture UIs
- **Dwell / hover-to-select:** cursor pauses over a target longer than a dwell threshold;
  threshold often scaled up with target density. Common in gesture kiosks.
  https://patents.justia.com/patent/20030210227
- **Press-and-hold ("Holding" event):** Kinect fires a hold event once a time threshold is
  crossed while the hand cursor stays on a UI element — the standard Kinect confirm.
  https://learn.microsoft.com/en-us/previous-versions/windows/kinect/dn759207(v=ieb.10) ;
  https://pterneas.com/2014/01/27/implementing-kinect-gestures/
- **Kinect skeleton tracking** provides joint positions **~30×/second**; a gesture = joints
  reaching relative positions for a set duration. (No single canonical dwell-second value
  surfaced across sources — implementations vary; **flagged gap**.)
- **T-pose / calibration pose:** standard "enter/reset" convention in motion-capture and
  Kinect systems — actor assumes a T-pose to start tracking; reusable as a reserved
  "reset/attract" pose. https://en.wikipedia.org/wiki/T-pose

### Reserved-pose / reset / timeout patterns (design conventions, not one paper)
When the body is the controller you cannot "click away," so installations rely on:
- **Reserved poses** (raise-both-hands, T-pose) for select/confirm/reset — distinct from
  natural movement so they aren't triggered accidentally.
- **Timeouts back to an attract loop** when no skeleton is detected (drives the "watch
  others to learn" onboarding Ideum describes).
- **Secondary modality only as a last resort** — Ideum's data argues *against* mixing touch
  with body control (the "Be a Bug" design flaw).
- **[single-source for the specific attribution]** — these are widely-used conventions;
  Ideum is the concrete documented case, T-pose from Wikipedia/mocap practice.

---

## 4. Synthesis — concrete guidance for the kiosk

1. **Keep the interaction plane low** — mid-torso, bent elbow (CE optimum), not shoulder/eye
   height. Put selectable items toward the bottom of the frame.
2. **Never require above-shoulder or fully-extended sustained poses** (CE, Ultraleap, Apple
   all agree — multi-source).
3. **Prefer dwell for selection** (lowest CE single-hand technique) with a visible
   progress/hover indicator; keep the required hold short. Reserve held/strenuous poses for
   rare high-value confirms only (Ultraleap).
4. **Make selection a body pose, not a separate menu device** — avoid mixing touch + gesture
   (Ideum "Be a Bug" flaw); the "Chow Time" pose+raise carousel is the model.
5. **Strong real-time feedback:** skeletal outline / cursor, floor marker for the standing
   spot, directional prompts (Ideum).
6. **Design for short bursts + rest** — cumulative fatigue accrues and recovers between
   users (Jang 2017, NICER 2024).
7. **Reserved reset pose (T-pose / both-hands) + timeout to attract loop** for state control.
8. **If a mounted screen kiosk:** panel at 1.35–1.8 m, wheelchair 1.15 m; "stand back" floor
   cue (Ultraleap TouchFree).

---

## Source list
- Consumed Endurance project: http://hci.cs.umanitoba.ca/projects-and-research/details/ce
- Consumed Endurance publication: http://hci.cs.umanitoba.ca/publications/details/consumed-endurance-a-metric-to-quantify-arm-fatigue-of-mid-air-interactions
- Consumed Endurance PDF **[blocked]**: https://hci.cs.umanitoba.ca/assets/publication_files/Consumed_Endurance_-_CHI_2014.pdf
- Consumed Endurance ACM DL: https://dl.acm.org/doi/10.1145/2556288.2557130
- Jang et al. 2017 cumulative fatigue, ACM DL: https://dl.acm.org/doi/10.1145/3025453.3025523
- Jang et al. 2017 — Purdue summary: https://www.purdue.edu/newsroom/archive/releases/2017/Q2/study-researches-gorilla-arm-fatigue-in-mid-air-computer-usage.html
- NICER (TOG 2024): https://dl.acm.org/doi/10.1145/3658230
- Ultraleap XR design principles: https://docs.ultraleap.com/xr-guidelines/Getting%20started/design-principles.html
- Ultraleap TouchFree guidance: https://docs.ultraleap.com/TouchFree/touchless-interfaces/guidance.html
- Ultraleap mid-air haptics: https://support.ultraleap.com/hc/en-us/articles/360004422398-Designing-effective-mid-air-haptics
- Apple visionOS spatial design Q&A: https://developer.apple.com/news/?id=fi8ne6ji
- Gaze+pinch analysis (Pfeuffer): https://medium.com/antaeus-ar/design-principles-issues-for-gaze-and-pinch-interaction-a95e251169ae
- Ideum full-body exhibit postmortem: https://ideum.com/news/touchless-interaction-public-spaces-part2
- Ambient Interactive gesture exhibits (thin): https://www.ambientinteractive.com/gesture-based-interactive-digital-exhibits/
- Kinect gesture settings (press/hold): https://learn.microsoft.com/en-us/previous-versions/windows/kinect/dn759207(v=ieb.10)
- Kinect gesture implementation: https://pterneas.com/2014/01/27/implementing-kinect-gestures/
- Dwell-time patent: https://patents.justia.com/patent/20030210227
- T-pose (mocap calibration convention): https://en.wikipedia.org/wiki/T-pose
