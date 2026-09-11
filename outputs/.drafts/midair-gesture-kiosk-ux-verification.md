# Verification pass — midair-gesture-kiosk-ux-cited.md

Scope: traceability of quantitative claims and named studies to T1–T4; correct flagging of
single-source / PDF-not-parsed figures; no invented URLs; no overreach in "Recommended design."

Result: **0 FATAL, 0 MAJOR, 4 MINOR.**

---

## FATAL
None.

- All named studies in the brief trace to a research file: Istance "Snap Clutch" (T1),
  Kinect HIG / MRTK hand-menu (T1), Ultraleap TouchFree/XR principles (T1/T3/T4), Vogel &
  Balakrishnan UIST 2004/2005 (T1/T2/T3), Bolt "put-that-there" (T1 §5), ScienceDirect
  S0141938221000123 + Majaranta & MacKenzie (T2), arXiv 2204.08156 (T2/T3), Pfeuffer/visionOS
  (T2/T4), Springer 978-3-030-05532-5_25 (T2), NN/g progress-indicators + clickable-elements
  (T2/T3), Müller "Looking Glass"/Goncalves CHI13 (T3), Wouters DIS 2016 + Frontiers VR 2025
  (T3), Consumed Endurance CHI 2014 (T4), Jang 2017 + NICER 2024 (T4), Ideum full-body
  postmortem (T3/T4), Apple visionOS Q&A (T2/T4). No untraceable study found.
- All quantitative figures trace: 250–1000 ms band / 600 ms preferred / 450–900 ms eye-typing
  (T2 §1); ~800 ms AR/VR dwell (T2/T3); ~230 ms visionOS (T2 §1); ~2 s min-hold (T2 §4);
  ~3× wait tolerance + "<1 s no indicator" (T2 §5); +90%/+47% mirror/silhouette (T3 §2);
  66.7% vs ~11% honeypot (T3 §1); mid-torso/bent-elbow CE optimum + Borg CR10 + dwell-lowest-CE
  (T4 §1); ~3-button hand menu (T1). No fabricated number.
- No invented citation URLs: every URL in the Sources section of the cited brief appears
  verbatim in one of T1–T4.

## MAJOR
None.

- Every figure the research files flag as single-source or PDF-not-parsed is flagged somewhere
  in the brief: the +90%/+47%, ~2 s, ~800 ms, ~230 ms, and CE mid-torso-wording items are all
  called out in Findings §2/§3 and again in "Open questions / to validate" and the closing
  "Reliability" note. None is presented as a bare hard fact throughout the document.
- The "Recommended design" numbers (browse-arm ~600–800 ms, commit ~1.2–1.5 s, re-entry
  ~800 ms) all sit inside the evidence bands in T2; the two-hand + longer-hold commit is
  directly supported by T2 §4; the stillness-over-velocity gate is directly supported by
  T1 §5. No design recommendation exceeds the evidence.

## MINOR

1. **Exec-summary figures stated without inline caveat.** Executive-summary item 6
   ("field study: +90% ... +47% ...") and item 4 ("AR/VR dwell commonly ~800 ms") present
   these as hard facts at the top of the doc. They are single-source / PDF-not-parsed per
   T3 §2 and T2/T3 (arXiv 2204.08156) and ARE flagged later (Findings, Open questions,
   Reliability), so this is a placement issue, not an unsupported claim. Consider adding a
   parenthetical "(single-source)" at first mention.

2. **Honeypot 66.7% vs ~11% omits the ecological-validity caveat.** Findings §3 cites the
   figures as behavioral fact. T3 §1 explicitly notes the source (Frontiers VR 2025) is a
   **VR-simulated** environment with an ecological-validity caveat; the brief drops that
   qualifier. Numbers themselves match T3 (66.7% stop/approach; 11.1% walk-past).

3. **Slight amplification in "Recommended design / core answer."** The brief states stillness
   "essentially never happens by accident while someone is animatedly being an alien." T1 §5's
   supported wording is weaker: continuous performance "rarely goes perfectly still." The
   conclusion is sound but stated more absolutely than the source.

4. **"45 years of HCI" is not sourced.** Exec-summary item 1's "the canonical fix in 45 years
   of HCI" — the "45 years" span appears in none of T1–T4 (rhetorical framing). Harmless but
   not traceable.
