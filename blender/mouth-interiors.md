# Mouth interiors, September 11

Local revision of Clay, Nebula and Glass only. Coral remains paused; Orbit,
Cosmic, Kudzu and Summer have not been re-exported in this pass.

## Tutorial reference

Dikko, [Modeling for Animation 06 - Retopologising the Face!](https://www.youtube.com/watch?v=SwM19PgSdCM),
has a mouth-bag chapter at [41:45](https://www.youtube.com/watch?v=SwM19PgSdCM&t=2505s).
The primary YouTube chapter listing was verified. This is not a claim to have
watched or transcribed the complete video. The implementation uses its general
mouth-bag/connected-lip topology approach, adapted to the existing morph rigs.

## Implementation

`scripts/refine_mouth_interiors.py` runs in staged Blender MCP calls, one source
at a time. It replaces the shallow interiors with head-skinned, closed-back
cavities. The open front ring follows the source lip morphs; deeper rings relax
toward the rear cavity. The lining has a dark red depth falloff and high roughness.
Clay gets separately shaped crowns, a curved dental arch and recessed gums.
Gums follow the runtime dental bite correction without influencing its bounds.
Nebula resamples only the two innermost lip rings, retaining corner colors and
explicitly interpolating every facial target. Its outer cheek topology stays put.
Resting tongues are recessed; fully extended shape coordinates remain unchanged.

Broad subdivision trials introduced pinching and were rejected. Source backups,
candidates, preservation audits and renders are in `.context/qa/mouth-interiors/`.
Do not rerun authoring operations on an already revised source. `promote()` runs
the preservation audit before copying the candidate to its existing live path.

## Verification and limits

Audits compare bone rests, original skin weights, nonoral geometry/facial targets
and full tongue-extension endpoints. Cavities have one open lip boundary, a
closed rear and normalized head weights. Browser tests render actual `driveFace`
with measured-photo smile scores, closure, talking, tongue and rotated views.
They count both visible dental rows and test that runtime bite fitting leaves
the neutral pose unchanged. They do not prove anatomical accuracy, absence of
all extreme-pose intersections, or physical camera/ZED performance.

Review: http://localhost:8014/.context/qa/mouth-interiors/review.html
Glass remains dark, and Nebula retains original cheek faceting. Visual approval
and a real visitor smile test remain pending. No paid generation was used.
