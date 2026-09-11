# T3 — Discoverability & Self-Teaching for Zero-Instruction Midair Gesture Kiosks

Research draft. Focus: how walk-up visitors with NO instructions notice a touchless gesture
display, realize it is interactive, and learn the gestures in the moment. Inline source URLs
provided. Claims resting on a single source are flagged **[single-source]**. PDF-only sources
are cited by URL and marked **[PDF full-text blocked]** (not parsed per workflow rules).

---

## 1. Interaction blindness & immediate usability

**Display blindness / interaction blindness.** Müller et al. frame *display blindness* by analogy
to banner blindness: passers-by deliberately avoid looking at displays because they expect low-value
advertising. *Interaction blindness* is the related failure to realize a display can be interacted
with at all. Interactivity itself gives pedestrians a reason to attend — it makes them stop, gesture,
and dwell longer, and it seeds the honeypot effect.
- Müller, Alt, Michelis, Schmidt, "Requirements and Design Space for Interactive Public Displays"
  (ACM MM 2010): http://www.florian-alt.org/unibw/wp-content/publications/mueller2010mm.pdf
  **[PDF full-text blocked]** — cited from search metadata/abstract.
- Dalton et al., "Display Blindness? Looking Again at the Visibility of Situated Displays":
  https://oro.open.ac.uk/42236/1/pn236-dalton.pdf **[PDF full-text blocked]**

**Making the system "look strange" reduces blindness.** Houben & Weichel (2013) found display and
interaction blindness can be reduced by making the system look unusual/strange enough to break the
"it's just an ad" expectation. **[single-source]** (surfaced via search summary of Müller-line
literature; primary not directly fetched — verify before citing as load-bearing.)

**The honeypot effect.** Defined by Brignull & Rogers (2003): "people notice someone already looking
at the display and are thereby prompted to look themselves." It is a three-way dynamic — display,
an initial active user, and influenced bystanders. People already interacting passively stimulate
others to observe, approach, and engage. Critically, display blindness stems from insufficient
*initial* awareness, so the core design problem is attracting that **first** user, after whom
attention cascades.
- Wouters et al., "Uncovering the Honeypot Effect: How Audiences Engage with Public Interactive
  Systems" (DIS 2016): https://www.semanticscholar.org/paper/763a3b4d8cee373084a62d460855f3618601b19d
  and https://www.researchgate.net/publication/298397007 **[PDF full-text blocked]**
- Frontiers in Virtual Reality (2025), "Honey-pot effect on pedestrian attention to public displays
  in a virtual environment" (HTML, fetched):
  https://www.frontiersin.org/journals/virtual-reality/articles/10.3389/frvir.2025.1714725/full

**Quantified behavioral cascade (Frontiers 2025 VR study).** How a bystander behaves near a display
drives whether newcomers turn to look:
- Bystander *stops/approaches* the display → **66.7%** of participants turned to look (p < 0.01).
- Bystander merely *head-turns while walking* → **16.7%** (rising to 33.3% when approaching from the
  opposite direction, 0% same-direction).
- Bystander *walks past* → **11.1%** (no better than baseline).
- Content recall tracked attention: Approach 46.7% vs. Attention 33.3% vs. Walking-past 0%; a single
  1–2 s glance rarely forms short-term memory.
- No significant German vs. Japanese cultural difference (20.8% vs. 37.5% head-turns overall).
- Design implication: **a stopped, actively-engaged body is the strongest attractor**; visually
  striking design and sound recruit the critical first user. (Note: VR-simulated environment —
  ecological validity caveat.)

---

## 2. Attract loops / attract modes

An **attract loop** is content that auto-plays when the kiosk is idle past a timeout, designed to
draw people in and hand off into interaction. Attracting, engaging, and motivating the user are the
central design issues for public displays (Müller et al. 2010). Practical guidance:
- Include a **clear call-to-action** ("touch to…", "step up", or a QR code).
- Loop duration long enough to catch attention but short enough to avoid boredom/annoyance.
- Works for unattended/semi-attended stations, drawing visitors without staff.
- Sources: SiteKiosk, "How to Create an Engaging Attract Loop" (HTML):
  https://sitekiosk.us/attract-kiosk-users/ ; GWD, "Donation Station Attract Loop":
  https://gwd.team/blog/what-is-the-donation-station-attract-loop/ **[single-source each — vendor/
  practitioner blogs, not peer-reviewed; treat as best-practice not evidence]**
- Goncalves et al., "Exploring Visual Signals to Entice Interaction on Public Displays" (CHI 2013):
  https://www.jorgegoncalves.com/docs/chi13.pdf **[PDF full-text blocked]** — search-surfaced
  findings below (§5) on text vs. icon, color vs. greyscale, static vs. animated.

**Key evidence — mirror image beats a traditional attract/CTA sequence (Müller et al., "Looking
Glass", CHI 2012).** A field deployment (shop window, ~502 sessions over three weeks) found
significantly more passers-by interacted when the display **immediately showed the user's mirrored
image (+90%)** or **silhouette (+47%)** versus a conventional attract sequence with a call-to-action.
Companion lab study: mirrored user image/silhouette beat avatar-like representations; and for the
CTA signal itself, **text > icons, color > greyscale, static > animated**. This is the strongest
single result for kiosk attract design: prioritize a live self-image over animated instructions.
- Surfaced via: https://www.researchgate.net/publication/303903346 (Sartor et al., "Comparing two
  methods to overcome interaction blindness on public displays") and CHI13 Goncalves paper metadata.
  **[PDF full-text blocked; +90%/+47% figures are from search summary of the Looking Glass work —
  verify exact numbers against the primary CHI 2012 paper before publication.]**

---

## 3. Hand/body mirror & palm cursor ("you are the controller")

Showing the user's own hand, silhouette, or skeleton as a live cursor teaches — with zero words —
that their motion is being tracked. This is the mechanism behind the mirror-image attract results in
§2 and is standard museum practice.
- **Kinect model:** a `KinectRegion` shows a hand cursor mirroring the user's hand; the user's
  silhouette highlights (green) at the top of the screen; users move the hand cursor and "push"
  forward to press an active control ("push-to-press"). Xbox positioned this as the natural user
  interface where you control without a controller.
  - Microsoft Learn, "Hand gestures to control Windows mouse cursor – Kinect for Windows":
    https://learn.microsoft.com/en-us/archive/blogs/msgulfcommunity/hand-gestures-to-control-windows-mouse-cursor-kinect-for-windows
  - Kinect 2 Hands-On Lab 10: https://kinect.github.io/tutorial/lab10/index.html
- **Museum practice (Ideum, fetched HTML):** a small **skeletal-outline inset** shown in real time
  confirms the system sees the visitor; **avatars/insets that mirror movement improve social
  acceptance and give continuous feedback**; **animated pointers** show which direction to move;
  **vinyl floor graphics** act as a physical affordance marking the tracked standing spot. Blob
  tracking (gross movement) can suffice when experience design compensates — precision is not always
  required.
  - Ideum, "Touchless Gesture-Based Exhibits, Part Two: Full-Body Interaction":
    https://ideum.com/news/touchless-interaction-public-spaces-part2
  - MCT master's thesis, "Designing Gesture-based Interactive Museum Exhibit":
    https://mct-master.github.io/masters-thesis/2021/06/20/simonrs-gestures.html (corroborates that
    avatars mirroring users aid social acceptance and continuous feedback, and that everyday-derived
    gesture sets allow interaction "without introduction or guidance").

---

## 4. Progress rings / radial fill / dwell feedback

For hold-to-confirm and dwell selection, a filling ring/bar communicates "keep holding," arming, and
completion, and prevents premature release.
- **Fill representations & semantics:** selection progress can be shown as thin-bar, full-button,
  radial, or linear fill; a **radial fill can start as a dot at the cursor and grow outward** as an
  enlarging circle from 0→100%. (Patent, "Visual feedback for level of gesture completion,"
  US 9,383,894 — cited by URL only): https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9383894
  **[PDF full-text blocked]**
- **Dwell timing:** AR/VR dwell selection commonly uses ~**800 ms** thresholds, auto-confirming on
  reaching the threshold, with a **progress bar (e.g., over the wrist) giving feedback on dwell
  time**. Source: "Interaction Design of Dwell Selection Toward Gaze-based AR/VR Interaction":
  https://arxiv.org/pdf/2204.08156 **[PDF full-text blocked]** — arxiv abstract/HTML basis; treat
  800 ms as a starting point, not a universal optimum. **[single-source for the specific number]**
- **Completion feedback on release:** releasing a pinch can trigger confirmation feedback (haptic to
  palm in equipped systems); relevant for signaling "action committed." Source: RingGesture
  (arxiv 2410.18100, HTML): https://arxiv.org/html/2410.18100v1
- **Practitioner ring semantics** (visual reference only): Stagetimer progress-ring element docs:
  https://stagetimer.io/docs/output-elements/progress-ring/

Design takeaway: a radial ring that fills from the cursor/hand position, auto-completes at a fixed
dwell, and visibly snaps/changes color on completion gives novices an unambiguous "hold until full"
signifier and avoids accidental early release.

---

## 5. Affordances & signifiers for gestures (ghost hands, demos, icons, labels)

**Signifiers vs. affordances (Norman / NN/g).** Affordances are the actual possible actions;
**signifiers are the perceivable cues that advertise them**. Gestures are invisible by default, so
they need strong explicit signifiers.
- NN/g, "Beyond Blue Links: Making Clickable Elements Recognizable" (fetched): color, shape,
  borders, consistency, placement, and (historically) 3-D depth make elements look interactive; one
  early study saw clicks rise **416%** switching flat→3-D buttons; "life is too short to click on
  things you don't understand." https://www.nngroup.com/articles/clickable-elements/
- NN/g research (via search): **flat design costs users ~22% more time locating interactive
  elements** than designs with visual depth. **[single-source, search-surfaced — verify exact NN/g
  article]**
- IxDF, "What is Gesture-Based Interaction?": https://ixdf.org/literature/topics/gesture-interaction
  and IxDF signifiers: https://ixdf.org/literature/topics/signifiers

**Gesture onboarding & ghost-hand demonstrations.** Because gestures are hidden and easily missed,
animated demonstrations are the standard teaching device:
- Show the **gesture being performed in one region and the resulting action in another**, synchronized
  (hand performing gesture + object responding). A demo **hand can fade out leaving only dots/
  touch-points**; **arrows appear/move/grow** to show direction and order of motion. (Apple patent,
  "Gesture movies," US 8,413,075 — URL only): https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/8413075
  **[PDF full-text blocked]**
- Practitioner guidance corroborating: Fireart, "How to Design Gesture-Driven UI"
  (https://fireart.studio/blog/how-to-design-gesture-driven-ui/); Boldist, "Understanding Gestures
  for UI Design" (https://boldist.co/design/gesture-based-interfaces/). **[practitioner blogs —
  best-practice, not evidence]**

**Ultraleap XR design guidelines (fetched HTML) — most directly applicable to hand-tracked midair:**
- **Use hand poses sparingly.** "Ultraleap recommend using poses sparingly. They are rarely suitable
  for applications where users will have little time to onboard… They work best… for actions which
  are valuable to users… Poses… must always be taught by using a help panel or similar tutorial
  content." → For a walk-up kiosk with no onboarding, minimize distinct poses; reserve any pose for a
  single high-value action and teach it explicitly.
- **Physical realism minimizes teaching:** "When objects look three-dimensional and behave as one
  would expect from the real world, users will naturally manipulate objects… without needing to learn
  or memorise new interactions." → Prefer direct-manipulation metaphors (push, grab, poke) over
  abstract symbolic gestures.
- **Rich state feedback:** components should "provide extra visual and audio feedback… reacting to
  proximity of the hand, to focus and activation states with clear colour changes and sounds";
  3-D buttons that visibly depress reduce novice cognitive load.
- **Keep targets in view/reach; keep hands and content co-located** (avoid making users look away
  from their hands). Respect the **interaction zone** (Leap controller ~140×120°, up to ~80 cm;
  Stereo IR 170 ~170×170°, up to ~100 cm).
- Sources: https://docs.ultraleap.com/xr-guidelines/Getting%20started/design-principles.html ;
  https://docs.ultraleap.com/xr-guidelines/ ; virtual hands:
  https://docs.ultraleap.com/xr-guidelines/Getting%20started/virtual-hands.html ; design
  considerations: https://docs.ultraleap.com/xr-guidelines/Getting%20started/DesignConsiderations.html

**Signal-design specifics (Goncalves CHI 2013, via search).** For the CTA/signifier itself:
**text > icons, color > greyscale, static > animated** at enticing interaction — a useful counter to
the instinct to use animated icon-only prompts. https://www.jorgegoncalves.com/docs/chi13.pdf
**[PDF full-text blocked — verify direction of each comparison against primary.]**

---

## 6. Spatial framework & best practices for one-shot, high-throughput public use

**Vogel & Balakrishnan spatial interaction framework (UIST 2004).** Interaction with a public display
transitions through **four continuous distance zones**: (1) *ambient display* (public, no user), (2)
*implicit interaction* (system reacts to body orientation/position — attracts and signals
responsiveness), (3) *subtle/explicit interaction* (simple hand gestures), (4) *personal interaction*
(close, detailed, e.g. touch). Design should support **fluid transitions** implicit→explicit and
public→personal, and handle multiple users.
- Primary: https://www.dgp.toronto.edu/~ravin/papers/uist2004_ambient.pdf **[PDF full-text blocked]**
- HTML notes summarizing it: https://medium.com/shengzhis-mdes-thesis/notes-for-interactive-public-ambient-displays-transitioning-from-implicit-to-explicit-public-to-e2dbd6e37dd5
- Semantic Scholar record: https://www.semanticscholar.org/paper/28285dc9bdbd58074f01520c88b6b8be495a8b6d

Applied to the kiosk: use the **implicit zone** to react to an approaching body (mirror the person as
they get close) — this both attracts (honeypot) and proves responsiveness before any deliberate
gesture, then escalates to explicit dwell/pose actions.

**High-throughput / museum best practices (Ideum + guides).**
- Design for **short cycles or parallel stations** where queuing space is limited.
- **Pose-based parallel selection** (e.g., raise a hand to pick one of three options) beats
  sequential menus for throughput (Ideum "Penguin Chill").
- Every interaction must be **immediately clear/intuitive** in free-choice environments or visitors
  leave; custom cursors, on-screen displays, and LEDs were "key to success."
- **Multi-user detection** (several people gesturing at once) is a real engineering constraint;
  sensor calibration/fusion needed. Social visibility of others gesturing doubles as the attract loop.
- Sources: Ideum Part 2 (fetched, above); Ideum Part 3 "Touchless.Design":
  https://ideum.medium.com/touchless-gesture-based-exhibits-part-three-touchless-design-2b12aaaa0f81 ;
  STQRY museum-kiosk guide: https://www.stqry.com/blog/museum-kiosk/ ; Workinman:
  https://workinman.com/trade-show-museum-kiosk-design-development/ **[practitioner sources]**

---

## Synthesis — actionable recommendations for a zero-instruction midair-gesture kiosk

1. **Lead with a live mirror, not instructions.** Immediately reflecting the user's image/silhouette
   is the single most evidence-backed attractor (+90% image / +47% silhouette in the Looking Glass
   field study) and simultaneously teaches "you are the controller." (§2, §3)
2. **Exploit the honeypot, engineer for the first user.** A stopped, engaged body is the strongest
   recruiter (66.7% vs. ~11%); make interacting bodies highly visible and use striking visuals/sound
   to land the first participant. (§1)
3. **Use an implicit→explicit escalation** (Vogel & Balakrishnan): react to approach, then invite a
   simple explicit gesture. (§6)
4. **Prefer direct-manipulation metaphors over symbolic poses;** if a pose is required, keep it to one
   high-value action and teach it with a persistent ghost-hand/label. (§5, Ultraleap)
5. **Give a palm/hand cursor plus rich proximity/focus/activation feedback** (color + sound + depress).
   (§3, §5)
6. **For confirmation use a dwell ring** that fills from the hand position, ~800 ms auto-complete,
   with a clear completion state to prevent premature release. (§4)
7. **Teach in the moment with ghost-hand animations** showing gesture + result together, with fading
   hands, dots, and directional arrows; for the CTA text, remember text/color/static may outperform
   icon/greyscale/animated. (§5)
8. **Design for throughput:** short cycles or parallel pose-selection; floor graphics to place users
   in the tracking zone; plan for multi-user detection. (§6)

---

## Source reliability notes
- **Peer-reviewed / primary (strongest):** Vogel & Balakrishnan UIST 2004; Müller et al. MM 2010;
  Wouters et al. DIS 2016; Goncalves et al. CHI 2013; Frontiers VR 2025; Dwell-selection arxiv.
  Several are **PDF-only and were not full-text parsed** — figures quoted come from search summaries
  and abstracts and are flagged for verification.
- **The +90%/+47% Looking Glass figures and the text>icon/color>greyscale/static>animated ordering**
  are search-surfaced from secondary summaries; confirm against the primary CHI 2012 ("Looking
  Glass") and CHI 2013 papers before treating as load-bearing.
- **Vendor/practitioner blogs** (SiteKiosk, GWD, Ideum, STQRY, Workinman, Fireart, Boldist) are
  best-practice guidance, not empirical evidence — used for concrete tactics, not proof.
- **Patents** (gesture completion visual feedback; gesture movies) cited for design-pattern
  descriptions only, by URL, PDF not parsed.
- No sources were fabricated; every claim above links to a real search-returned or fetched URL.
