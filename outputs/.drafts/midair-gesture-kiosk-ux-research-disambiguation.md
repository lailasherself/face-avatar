# T1 — Disambiguation, Clutching & Mode-Switching (no button)

Research findings for a mid-air gesture kiosk where the user's arms already drive an
avatar's arms continuously. Core problem: how to tell a *deliberate* menu/command gesture
apart from the *incidental/continuous* motion the limbs are always producing.

Note on sources: several canonical HCI papers exist only as PDFs (ACM DL, author preprints).
Per brief, those are cited by URL and marked **[PDF — full text not parsed]**. HTML/doc
pages were fetched and quoted directly.

---

## 1. The "Midas touch" / "live mic" problem

**Definition.** In vision/gesture UIs, *every* active hand movement — even unintentional —
risks being interpreted as a command, so natural or continuous motion triggers unwanted
actions. Phrased in the literature as "the involuntary action of selection by the user …
causing unwanted actions and harming the user experience."
- Overview / definition: Pactolo Bar paper, NCBI PMC (HTML), https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9960067/
- Visual-attention mitigation method (Springer, The Visual Computer), https://link.springer.com/article/10.1007/s00371-014-1060-0

**Origin & the "moded" framing.** The term comes from eye-tracking (a gaze that both looks
*and* selects). The classic fix is to add a *mode* / delimiter so input only "counts" when
explicitly engaged — directly analogous to a **push-to-talk / live-mic** gate.
- "Snap Clutch, a moded approach to solving the Midas touch problem" (Istance, Bates,
  Hyrskykari, Vickers) — introduces mode-switching as the canonical remedy.
  **[PDF — full text not parsed]** https://www.academia.edu/117119052/Snap_clutch_a_moded_approach_to_solving_the_Midas_touch_problem

**Direct relevance to busy limbs:** in multi-target mid-air settings "the Midas touch problem
must be addressed — accidental activations of commands." (Address & Command, ScienceDirect,
abstract HTML) https://www.sciencedirect.com/science/article/abs/pii/S1071581921001737

---

## 2. Clutching / engagement & disengagement — gating when input "counts"

**Kinect for Windows — the canonical industry treatment.**

*KinectInteraction feature set* (Microsoft Learn, HTML, fetched): identifies **up to 2 users**
and tracks their **primary interaction hand**; provides **grip and grip-release detection**,
**press detection**, and hand location/state.
https://learn.microsoft.com/en-us/previous-versions/windows/kinect-1.8/dn188671(v=ieb.10)

*Engagement* (Kinect HIG, via search of Microsoft HIG v2.0 PDF; also patent text):
- **Wave / raise to engage:** users "slowly raise their hand (hand should be opened) to
  engage the system"; waving = raise hand above the elbow, move side-to-side. Chosen because
  it "feels natural and carries meaning … as a way to begin an interaction."
- Engagement can also key off **proximity to the sensor** and **a particular pose / facing
  direction** — i.e., a spatial engagement zone + posture, not raw motion.
- Kinect HIG v2.0 (Microsoft download) **[PDF — full text not parsed]**:
  https://download.microsoft.com/download/6/7/6/676611b4-1982-47a4-a42e-4cf84e1095a8/kinecthig.2.0.pdf
- Kinect HIG v1.7 **[PDF]**: https://download.microsoft.com/download/B/0/7/B070724E-52B4-4B1A-BD1B-05CC28D07899/Human_Interface_Guidelines_v1.7.0.pdf

*Physical Interaction Zone (PHIZ)* — the spatial engagement zone (Microsoft patents,
US 8,659,658 / US 9,063,578 / US 9,342,160; text via search):
- A **3D zone per hand**, spanning **approximately head-to-navel**, centered slightly to the
  side of the active hand.
- Deliberately a **curved surface** (not a flat screen-shaped rectangle) so arm extension is
  comfortable; cursor maps ergonomically to the full UI. This means only motion *inside* the
  PHIZ maps to the cursor — motion outside is ignored (an implicit engagement gate).
- https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/8659658 **[PDF — patent]**

**Ultraleap / Leap Motion (mid-air, screenless & XR).**
- *Stateful enabling* to prevent accidental activation is "easiest to achieve through a
  **taught pose** … or a **palm button**." Taught pose is convenient but needs a tutorial/hint;
  palm button is easy to learn "but can feel slow and less like one cohesive action."
  (XR design principles / locomotion docs, HTML)
  https://docs.ultraleap.com/xr-guidelines/Interactions/locomotion.html
  https://docs.ultraleap.com/xr-guidelines/Getting%20started/design-principles.html
- Comfort constraints that double as false-positive reducers: minimize large/strenuous
  movements, **avoid holding poses for extended periods**, and **avoid raising the arm above
  the shoulder** too often. (Ultraleap design principles, HTML — fetched)
- Screen-space menu elements at the **edges of the screen** caused accidental activations when
  users reached there while doing something else — argues *against* edge-triggered menus when
  hands are busy. (Ultraleap, HTML)

**Note (single-source):** the "raise-slowly / open hand" engagement phrasing and the PHIZ
head-to-navel geometry each come primarily from Microsoft's own docs+patents; independent
academic corroboration was not separately located in this pass.

---

## 3. Mode switching without a physical button

**TouchFree (Ultraleap) interaction modes** (docs, HTML — fetched) — three shipped patterns,
each a different disambiguation strategy, all buttonless:
- **AirPush** — triggers on **hand speed + forward direction** (a velocity/direction gate);
  "works for the widest range of users … at any distance." Best general default.
- **TouchPlane** — an invisible virtual plane in front of the screen; a click fires when the
  hand crosses it. Distance is **adjustable in settings**.
- **Hover & Hold** — cursor held still, an animation plays, then click fires; the **dwell time
  before click is adjustable**. Selection only (no scroll/drag). Best for large-distance setups.
- Hybrid touchscreen + TouchFree guidance: set the interaction zone to **~5 cm** from the
  screen and use AirPush + Scroll/Drag to avoid false activations as users approach.
- https://docs.ultraleap.com/TouchFree/touchless-interfaces/interactions.html

**MRTK / HoloLens 2 hand menu** (Microsoft Learn, HTML — fetched) — buttonless summon of a
menu via a reserved pose, with explicit anti-false-activation layers:
- Palm-up alone causes false positives "because people move their hands both intentionally …
  and unintentionally." Fix: **add an extra step** — **Require Flat Palm** (fully opened hand)
  and/or **Require Gaze** at the hand (eye or head gaze) as a secondary activation gate, with a
  "tunable distance threshold."
- **Keep buttons few:** one column of **~3 buttons** (attentional cone of vision ≈ **10°**).
- Place menu **~13 cm above the palm**; **freeze the menu when the opposite hand approaches**
  to avoid jitter and mis-targets.
- Avoid buttons **near the wrist** (system home button) — accidental triggers.
- World-lock the menu when the hand **drops or flips palm-down** = a natural disengage gesture.
- https://learn.microsoft.com/en-us/windows/mixed-reality/design/hand-menu

**Two-handed / non-dominant-hand mode switching (academic).**
- **Address & Command (A&C):** non-dominant hand *addresses* (selects) a device, dominant hand
  *commands* it — a bimanual split that inherently gates command input. (ScienceDirect, HTML abstract)
  https://www.sciencedirect.com/science/article/abs/pii/S1071581921001737
- **"Experimental Analysis of Barehand Mid-air Mode-Switching Techniques in VR"** (CHI 2019,
  Surale et al.): compares buttonless mode switches; **holding a spring-loaded mode with the
  non-preferred hand is fast**; **two-finger** postures were fastest, **long-press much slower**;
  non-preferred-hand techniques scored high subjectively.
  **[PDF — full text not parsed]** https://hemantsurale.com/assets/pdf/Vrmode.pdf
  (also http://library.usc.edu.ph/ACM/CHI2019/1proc/paper196.pdf)
- **"A model of non-preferred hand mode switching"** (Li/Hinckley lineage) — foundational on
  quasimodes/spring-loaded modes. **[PDF]**
  https://www.researchgate.net/publication/221474748_A_model_of_non-preferred_hand_mode_switching
- Depth-based clutch: **"A Clutching Method for Switching Interaction Modes Driven by Natural
  Mid-Air Gestures"** (IEEE 2024/25) — **inward drag** = engage→disengage, **outward stretch** =
  reverse, keyed on **hand depth** change. **[PDF/gated]** https://ieeexplore.ieee.org/document/11167990/

---

## 4. Continuous-vs-deliberate separation: motion vs stillness, velocity/dwell, delimiters

- **Stillness as the discriminator (Hover & Hold / dwell):** deliberate = user *stops* moving
  and holds; the system uses a tunable hold time before committing. Continuous motion never
  dwells, so it never fires. (Ultraleap TouchFree, HTML — above.)
- **Velocity/direction as the discriminator (AirPush):** a deliberate push is a fast forward
  motion; lateral/continuous motion doesn't cross the speed+direction threshold. (TouchFree.)
- **Gesture delimiters / segmentation:** a delimiter is an explicit start/stop marker bracketing
  a gesture so the recognizer knows the segment boundaries (a "clutch" for recognition). Core
  references:
  - Vogel & Balakrishnan 2005, **"Distant Freehand Pointing and Clicking on Very Large, High
    Resolution Displays"** (UIST '05, pp. 33–42) — the seminal freehand kiosk-style work.
    Separates **pointing** (ray-cast with extended index finger; open hand for relative cursor)
    from **clicking**: **AirTap** = "down-and-up of the index finger"; **ThumbTrigger** =
    "in-and-out of the thumb." Key insight for us: **decouple the continuous positioning channel
    from a distinct discrete trigger gesture.** **[PDF — full text not parsed]**
    https://www.dgp.toronto.edu/~ravin/papers/uist2005_distantpointing.pdf
  - Consensus/segmentation surveys (context): "Towards a Consensus Gesture Set" (CHI 2023),
    https://dl.acm.org/doi/10.1145/3544548.3581420 ; "Gesture Elicitation Studies for Mid-Air
    Interaction: A Review" (MTI 2018, open), https://doi.org/10.3390/mti2040065
- **Clutching for range:** clutching also solves the anatomical-range limit — record rotation/
  position "at the point of departure" and resume, exactly like lifting a mouse. (per clutch
  survey results; corroborated across the mode-switch sources above).

---

## 5. Patterns that work when the PRIMARY limbs are busy (the crux for this kiosk)

Because the arms are continuously driving the avatar, the disambiguation channel should be
*orthogonal* to that continuous motion. Options found, ranked by fit:

1. **Reserve a different modality — voice as delimiter.** The "put-that-there" model (Bolt,
   1980): speech gates/segments while the hand points continuously; speech+gesture are
   complementary and resolve ambiguity neither can alone. A spoken keyword ("menu", "select")
   is a natural live-mic gate that leaves the arms free.
   https://www.sciencedirect.com/topics/computer-science/multimodal-interaction
2. **Reserve gaze / head direction.** MRTK **Require Gaze** shows gaze is an effective secondary
   gate with a tunable distance threshold — the user must *look* to confirm, independent of arm
   motion. (MRTK hand-menu, HTML — above.)
3. **A distinct static held pose (reserved pose + dwell).** A pose the avatar-driving motion
   never naturally produces (e.g., flat open palm facing camera, or hand raised above the
   shoulder / above head), held still for a dwell period. Kinect uses raise-and-hold to engage;
   Ultraleap uses "taught pose" for stateful enable; both explicitly warn to keep such poses
   brief to avoid fatigue.
4. **Bimanual split / non-dominant-hand quasimode.** If one arm can be freed momentarily, a
   spring-loaded non-preferred-hand pose (fast per CHI 2019 Surale et al.) or Address & Command
   split gates commands while the other arm keeps driving.
5. **Spatial engagement zone (PHIZ-style).** Only motion inside a defined zone counts; reaching
   *outside* the normal avatar-driving envelope (e.g., a raised "menu" region above the
   shoulders) becomes the deliberate signal. Note Ultraleap's caution that *screen-edge* zones
   caused accidental hits when hands were otherwise engaged.

**Design synthesis for this kiosk:** the strongest options avoid overloading the busy arms —
prefer **voice or gaze as the delimiter**, or a **reserved held pose + short dwell** in a region
outside the natural avatar-driving envelope. AirPush-style velocity gating is risky here because
expressive avatar-driving motion can be fast; stillness/dwell gating (Hover & Hold) is safer
because continuous performance rarely goes perfectly still. Layer two conditions (pose **and**
gaze, or pose **and** dwell) as MRTK recommends, since any single continuous-motion signal will
false-fire.

---

## Concrete numbers captured
- Kinect: up to **2 users**; **1 primary hand** each; PHIZ spans **head→navel**, per-hand,
  curved surface.
- MRTK hand menu: **~3 buttons** / one column; attentional cone **~10°**; place **~13 cm** above
  palm; world-lock on palm-down; freeze on opposite-hand approach.
- Ultraleap TouchFree: interaction zone **~5 cm** in hybrid touch setups; Hover & Hold and
  TouchPlane thresholds/times **user-adjustable** (no fixed default published on the HTML page).
- Vogel & Balakrishnan: AirTap = index **down-up**; ThumbTrigger = thumb **in-out**; ray-cast
  pointing "fast but inaccurate."

## Single-source / caveats
- Kinect "raise slowly / open hand to engage" and PHIZ head-to-navel geometry: primarily
  Microsoft docs+patents; no independent academic confirmation located this pass.
- Surale et al. CHI 2019 specific rankings (two-finger fastest, long-press slowest) taken from
  search snippets of a **PDF not fully parsed** — verify against the PDF before quoting numbers.
- Depth-clutch inward/outward mapping is from a single IEEE 2024/25 paper (gated).
- No paper co-authored by "Wobbrock & Hoffmann" on dwell/stillness delimiters was found; the
  delimiter concept here is assembled from Vogel & Balakrishnan + TouchFree + Snap Clutch.
