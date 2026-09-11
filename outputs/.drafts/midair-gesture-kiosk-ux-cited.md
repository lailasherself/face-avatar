# Mid-Air Gesture UX for a Walk-Up Avatar-Embodiment Kiosk — Research Brief

**Context.** A museum/event installation where visitors *swipe in the air* to cycle through
alien avatars and then **embody** the chosen one (face + arms + fingers tracked live; the
visitor's arms drive the avatar's arms). Product decision already made: **live-embody while
browsing** — you drive whichever character is highlighted, and "commit" locks it in.

The hard problem, in one sentence: **the arms are simultaneously the menu controller and the
puppet strings**, so we must tell a deliberate menu gesture apart from expressive
avatar-driving motion — with no physical button and no instructions.

---

## Executive summary

1. **This is the classic "Midas touch" problem** (every hand movement risks being read as a
   command). The long-standing HCI fix is to add a **mode / delimiter** — a gate
   that decides when input "counts," exactly like push-to-talk on a live mic.
2. **When the primary limbs are busy, the gate must be *orthogonal* to continuous motion.**
   The strongest, lowest-risk orthogonal signal is **stillness + a reserved flat-palm pose**:
   expressive puppeteering is fast and never freezes; a deliberately held flat palm does. This
   is why velocity-based gates (a fast "push") are *risky* here and dwell/stillness gates are
   *safe*. **The app's existing `air-swipe.js` already implements exactly this** (raised open
   palm → hold still ~700 ms to "arm" → swipe), so the research validates the current core.
3. **Layer two conditions**, not one (Microsoft MRTK): a single "palm-up" gate false-fires
   because people move their hands unintentionally. The app already layers *flat-open-palm* +
   *held-still* + *only one eligible palm at a time* — good; keep it.
4. **Dwell/hold timing:** ~**600 ms** is the norm for lightweight selection (usable band
   250–1000 ms); AR/VR dwell commonly ~**800 ms**. For the **irreversible commit** ("become
   THIS one"), use a *more* deliberate confirm — a longer hold (~**1–2 s**) and/or a **two-hand
   pose** — because higher intent is worth the cost and it only happens once. (The ~800 ms and
   ~1–2 s figures are single-source/directional — see Reliability note.)
5. **Always show a progress ring for any hold > ~1 s** (Nielsen Norman): visible progress makes
   people willing to wait ~3× longer and prevents premature release.
6. **Teach with a mirror, not text.** Immediately showing the visitor's own image/silhouette is
   the single most evidence-backed way to defeat "interaction blindness" and to teach "you are
   the controller" (field study: **+90%** engagement with a live mirror image, **+47%** with a
   silhouette, vs. a conventional attract/call-to-action sequence — figures single-source, see
   Reliability note).
7. **Ergonomics:** keep held poses **brief** and the interaction plane **low** (mid-torso, bent
   elbow is the least-fatiguing "Consumed Endurance" optimum). **Never require a sustained
   above-shoulder pose.** Dwell is the lowest-fatigue single-hand selection technique.
8. **Best in-the-wild precedent (Ideum "Chow Time"):** selection *is* a body pose — strike a
   pose, raise hands to pick one of three from a 3-D carousel. Their earlier exhibit that mixed
   a **touchscreen with body control was later called "a design flaw."** Keep the public display
   **all-gesture** — don't mix modalities.

---

## Findings by theme

### 1. Disambiguation / the Midas-touch problem (the crux)
- **Definition & fix.** Midas touch = involuntary movements get interpreted as selections,
  "causing unwanted actions." The canonical remedy is a *moded* approach — add an explicit
  engage/disengage delimiter (Istance et al., "Snap Clutch"). [T1]
- **Kinect "engagement":** raise an *open* hand slowly to engage; engagement can also key off
  proximity and a facing pose — i.e., a spatial+postural gate, not raw motion. [T1]
- **Ultraleap:** prevent accidental activation via a **taught pose** or a **palm button**;
  screen-*edge* menu zones caused accidental hits when hands were otherwise busy (argues against
  edge triggers here). [T1]
- **MRTK hand menu:** palm-up alone false-fires; **require a flat (fully-opened) palm** and
  optionally **require gaze** as a second gate; keep any hand-summoned menu to ~3 items. [T1]
- **Orthogonal channels for busy limbs** (ranked fit): voice delimiter ("put-that-there"
  model), gaze/head direction, a **distinct static held pose + dwell**, a bimanual
  non-dominant-hand quasimode, or a spatial engagement zone. **Stillness/dwell gating is safer
  than velocity gating here because expressive avatar motion can itself be fast.** [T1 §5]

### 2. Commit / confirm gestures & dwell timing (concrete numbers)
- **Gaze dwell norm ~600 ms**, usable band **250–1000 ms** (600 ms preferred across object
  types); classic eye-typing used 450–900 ms. [T2, ScienceDirect / Majaranta]
- **AR/VR dwell ~800 ms** with a wrist/target progress bar is a common starting point (not a
  universal optimum). [T2, single-source arXiv 2204.08156]
- **visionOS:** ~**230 ms** hover-feedback fade-in; never show a raw gaze cursor. [T2,
  single-source]
- **Push / air-tap** has a *higher* recognition-error rate than a physical click and suffers
  depth ambiguity / recoil — avoid as the primary confirm. [T2]
- **Pinch / dwell / second-hand** are the lowest-fatigue confirms (Consumed Endurance: reach/push
  "gorilla arm" is worst). [T2/T4]
- **Two-hand / minimum-hold confirm:** pairing a gesture with a **~2 s minimum hold** substantially
  cut unintentional selections in a display-confirmation study; a two-step "detect intent → confirm"
  is an explicit low-false-positive pattern. Reserve this for the irreversible commit. [T2,
  single-source for the 2 s figure]
- **Progress feedback:** NN/g — no indicator < 1 s, animated indicator ~1–10 s; a moving feedback
  bar makes users tolerate ~**3×** longer waits; show a filling ring that snaps/changes color on
  completion and lets the user cancel by moving away. [T2/T3]

### 3. Discoverability / self-teaching (zero instructions)
- **Interaction blindness** is the core failure — people don't realize a display is interactive.
  Making it **live-mirror the viewer** is the strongest fix (**+90%** image / **+47%** silhouette
  vs. attract/CTA; Müller et al. "Looking Glass"). [T3, verify exact figures vs. primary]
- **Honeypot effect:** a **stopped, actively-engaged body** recruits newcomers far better
  (**66.7%** turn to look vs. ~**11%** for someone walking past; from a VR-simulated study, so
  treat as directional). Engineer for landing the *first* user; others cascade. [T3]
- **Palm cursor + real-time skeletal outline** teaches "you are the controller" wordlessly
  (Kinect model; standard museum practice per Ideum). [T3]
- **Use poses sparingly** (Ultraleap): reserve a pose for one high-value action and teach it
  explicitly (persistent ghost-hand/label); prefer direct-manipulation metaphors over abstract
  symbolic gestures. [T3]
- **Ghost-hand demo:** animate the gesture in one region and its result in another; fade the hand
  to dots + directional arrows. For the call-to-action text itself, evidence suggests
  text > icon, color > greyscale, static > animated. [T3, verify vs. primary]

### 4. Ergonomics & installation case studies
- **Consumed Endurance (CHI 2014):** quantifies gorilla-arm; correlates with Borg CR10 perceived
  exertion. Guidance: **keep the interaction plane low (mid-torso, bent elbow)**, put targets
  toward the bottom of the frame, and **dwell has the lowest fatigue of single-hand selection
  techniques.** [T4]
- **Cumulative fatigue accrues and recovers** between users (Jang 2017; NICER 2024) — design for
  short bursts + rest, which a walk-up kiosk naturally provides. [T4]
- **Multi-source consensus:** avoid sustained above-shoulder and fully-extended poses; keep held
  poses brief; prefer low-effort/indirect selection. [T4: CE + Ultraleap + Apple]
- **Ideum full-body exhibits (the key precedent):**
  - "Chow Time": **pose + raise hands to pick one of three from a 3-D carousel** — selection *is*
    a body pose, no separate menu device. **Emulate this.**
  - "Be a Bug": mixing a **touchscreen with body-gesture control was later judged "a design
    flaw."** → keep the public display all-gesture.
  - Feedback that mattered: **floor vinyl marking the standing spot**, animated directional
    pointers, and a **real-time skeletal outline** proving the visitor is tracked.
  - **Failure mode:** tracking degrades as more visitors crowd the space (skeleton confusion). [T4]
- **T-pose / reset pose + timeout to an attract loop** is the standard state-control convention
  when the body is the controller (you can't "click away"). [T4]

---

## Recommended design for this app (fleet.js), grounded in the findings

A clean state machine with **two gesture primitives** (plus a distinct one-time commit). The
app already has the hardest piece built (`air-swipe.js`), so most of this is *gating and
transitions* rather than new tracking.

### The core answer to your question
> *"How do they change avatars with their arms while their arms are busy being the character?"*

**Ride an orthogonal channel: a reserved flat-open-palm pose held STILL.** Expressive
puppeteering is motion; the change gesture is the *absence* of motion in a specific pose.
Continuous performance rarely goes perfectly still, so a held, flat-palm dwell is very unlikely
to fire by accident while someone is animatedly being an alien — which is precisely why the research prefers dwell/stillness over
velocity gates when the limbs are already busy [T1 §5], and why MRTK layers *flat palm* on top
[T1]. `air-swipe.js` already does this (flat palm + hold-still-to-arm + single-eligible-palm).

### State machine
1. **ATTRACT** — no body detected. Immediately **mirror the visitor** (camera/silhouette +
   idle avatar) and show "Step up." (Mirror > instructions; honeypot.) [T3]
2. **BROWSE (live-embody)** — visitor drives the centered avatar; roster strip + name + a small
   palm-cursor hint visible. **Raise one flat palm, hold still ~700 ms** (ring arms) **→ swipe
   L/R** to change. This is the *only* state where swipe is active. (Existing code.)
3. **COMMIT ("step forward")** — **raise both open palms and hold ~1.2 s** (ring fills). Avatar
   **dollies forward**, roster/chrome fade, "You're now NAME." Two-hand + longer hold = a
   deliberate, low-false-trigger confirm reserved for the one irreversible action. [T2]
4. **EMBODIED** — full free puppeteering, chrome hidden, with a persistent low "✋ Hold to change"
   hotspot. To change: **raise one flat palm, hold still ~800 ms** → avatar **steps back**,
   chrome/roster return → BROWSE. Stillness+flat-palm keeps it from firing during performance. [T1]
5. **Timeout** — no body for N seconds → back to ATTRACT.

### Refinements from the evidence (concrete)
- **Keep every hold short and always show the ring** (browse-arm ~600–800 ms; commit ~1.2–1.5 s).
  Ring fills from the hand-cursor position, snaps + color-changes + sound on completion, cancels
  by moving/dropping. [T2/T3]
- **Don't require a *sustained* above-shoulder pose.** The current `raisedPalmBodySide` requires
  the palm above the shoulder; that's fine for a *momentary* ~700 ms arm, but don't make people
  hold it up. Consider relaxing toward chest/shoulder height (CE mid-torso optimum) *if* it stays
  distinguishable from puppeteering in testing. [T4]
- **Palm cursor + live skeletal/mirror feedback**, and after a few idle seconds in BROWSE play a
  **ghost-hand swipe demo**. Reserve poses for these few high-value actions and label them. [T3]
- **Keep the public display all-gesture** — no touch prompts mixed in (Ideum "design flaw"). [T4]
- **Floor marker** for the standing spot to hold users in the tracking envelope. [T4]

### Why not the alternatives
- *Velocity "push" to change while embodied:* expressive arm motion is fast → false triggers +
  gorilla-arm fatigue. [T1/T2/T4]
- *Screen-edge hot-zones:* accidental hits when hands are busy. [T1]
- *A separate touch/button for the menu:* mixing modalities was a documented design flaw. [T4]

---

## Open questions / to validate on-site
- Exact dwell/hold values (research gives bands, not app-specific optima) — tune with real,
  energetic visitors, especially kids.
- Whether "one flat palm held still" stays reliably distinct from your users' puppeteering given
  your tracker's stillness threshold — the existing single-eligible-palm + stillness logic is the
  right lever; stress-test it.
- The above-shoulder vs. fatigue trade-off for the re-entry gesture.
- Crowd/multi-body tracking robustness (Ideum's reported failure mode). [T4]
- Several primary figures (+90%/+47%; the 2 s and 800 ms dwell numbers; 230 ms) are
  single-source or from PDFs not full-text parsed — treat as directional, not exact.

---

## Sources

Bracketed [T1]–[T4] map to the four research files under `outputs/.drafts/`
(`-research-disambiguation`, `-research-commit-timing`, `-research-discoverability`,
`-research-ergonomics-cases`), which hold the full inline citations and reliability flags.
Key primary sources:

**Disambiguation / clutching / modes [T1]**
- Istance et al., "Snap Clutch, a moded approach to solving the Midas touch problem" (PDF, not parsed) — https://www.academia.edu/117119052/
- Kinect for Windows Human Interface Guidelines v2.0 (PDF) — https://download.microsoft.com/download/6/7/6/676611b4-1982-47a4-a42e-4cf84e1095a8/kinecthig.2.0.pdf
- Microsoft MRTK "Hand menu" (anti-false-activation: flat palm + gaze) — https://learn.microsoft.com/en-us/windows/mixed-reality/design/hand-menu
- Ultraleap XR design principles — https://docs.ultraleap.com/xr-guidelines/Getting%20started/design-principles.html
- Ultraleap TouchFree interaction types (AirPush / TouchPlane / Hover & Hold) — https://docs.ultraleap.com/TouchFree/touchless-interfaces/interactions.html
- Vogel & Balakrishnan, "Distant Freehand Pointing and Clicking…" UIST 2005 (PDF) — https://www.dgp.toronto.edu/~ravin/papers/uist2005_distantpointing.pdf

**Commit gestures & dwell timing [T2]**
- Dwell-time usability for gaze selection (~600 ms preferred; 250–1000 ms band) — https://www.sciencedirect.com/science/article/pii/S0141938221000123
- Majaranta & MacKenzie, feedback & dwell time in eye typing — https://www.yorku.ca/mack/uais2006.html
- "Interaction Design of Dwell Selection…" (~800 ms) arXiv — https://arxiv.org/pdf/2204.08156
- Pfeuffer, gaze+pinch design (visionOS ~230 ms hover) — https://www.shapesxr.com/articles/eye-gaze-the-next-wave-of-user-interfaces-led-by-the-apple-vision-pro
- "Analyzing Mid-Air Hand Gestures to Confirm Selections on Displays" (~2 s min hold) — https://link.springer.com/chapter/10.1007/978-3-030-05532-5_25
- Nielsen Norman Group, progress indicators — https://www.nngroup.com/articles/progress-indicators/

**Discoverability / self-teaching [T3]**
- Müller et al., "Requirements and Design Space for Interactive Public Displays" MM 2010 (PDF) — http://www.florian-alt.org/unibw/wp-content/publications/mueller2010mm.pdf
- Wouters et al., "Uncovering the Honeypot Effect" DIS 2016 — https://www.researchgate.net/publication/298397007
- Frontiers in Virtual Reality 2025, honeypot attention study — https://www.frontiersin.org/journals/virtual-reality/articles/10.3389/frvir.2025.1714725/full
- Müller et al., "Looking Glass" (mirror +90% / silhouette +47%) — via Goncalves CHI 2013 (PDF) https://www.jorgegoncalves.com/docs/chi13.pdf
- Ideum, "Touchless Gesture-Based Exhibits, Part Two: Full-Body Interaction" — https://ideum.com/news/touchless-interaction-public-spaces-part2
- Vogel & Balakrishnan, ambient-display interaction zones, UIST 2004 (PDF) — https://www.dgp.toronto.edu/~ravin/papers/uist2004_ambient.pdf
- NN/g, "Beyond Blue Links: Making Clickable Elements Recognizable" — https://www.nngroup.com/articles/clickable-elements/

**Ergonomics & case studies [T4]**
- Hincapié-Ramos et al., "Consumed Endurance…" CHI 2014 — http://hci.cs.umanitoba.ca/projects-and-research/details/ce
- Jang et al., "Modeling Cumulative Arm Fatigue in Mid-Air Interaction" CHI 2017 — https://www.purdue.edu/newsroom/archive/releases/2017/Q2/study-researches-gorilla-arm-fatigue-in-mid-air-computer-usage.html
- NICER, ACM TOG 2024 — https://dl.acm.org/doi/10.1145/3658230
- Apple visionOS spatial design Q&A (gaze+pinch ergonomics) — https://developer.apple.com/news/?id=fi8ne6ji
- Ultraleap TouchFree guidance (panel height, stand-back) — https://docs.ultraleap.com/TouchFree/touchless-interfaces/guidance.html

**Reliability:** figures flagged single-source or PDF-not-parsed in the research files
(+90%/+47%; ~2 s; ~800 ms; ~230 ms; CE mid-torso guideline wording) are directional and
should be confirmed against primaries before being treated as load-bearing. No sources fabricated.
