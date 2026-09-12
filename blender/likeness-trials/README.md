# Reference Likeness Builds

Coral is temporarily paused in the website manifests. Its revised source, GLB and
textures below are retained, but are not part of the published website bundle.

## Orbit And Coral Reference Paint And Sculpt Revision 4

Current sources and GLBs use `reference_painted_sculpt_4`, revised sequentially
through Blender MCP from the locked original PNGs. Reference pixels now supply
pigment, small-scale relief and variable roughness, with approximate lighting
removal. Broad face volume and body folds are actual vertex changes, propagated
to facial keys. Unseen surfaces use cloned skin samples. These are animated 3D
meshes, not PNG billboards, but single-view materials and hidden shapes remain
approximations, not exact reconstructions or approved final art.

`scripts/paint_reference_surfaces.py` adds explicit prepare, coordinate, sculpt,
material, bake, audit and promotion stages to the preceding exporter. Never bake
already baked shaders or repeat sculpting. Packed maps include separate 2048px
head/body/details color, normal and roughness atlases. Original eye, bulb and oral
detail UVs/materials are retained separately to preserve their finish. Runtime
normal strength is restrained to .60 for Orbit and .40 for Coral.

Topology, weights, bone rests and channel names are unchanged. A local displacement
limiter leaves zero newly reversed neutral head/body triangles versus revision 3.
Eye, teeth and tongue targets are preserved; the cavity follows the revised rim.
The other six characters and runtime tracking are untouched by this art pass.

Before-state backups, candidate sources, geometry audits, expression and angle
renders, and the original/before/after review are in
`.context/qa/reference-painted-v4/`. Hardware acceptance and visual approval are
pending. This does not fix live smile bite or eyelid closure/cross-talk.

## Previous Lip And Surface Revision 3

The preceding `*-image-rig.blend` sources and default GLBs used
`reference_lip_surface_3`. Revised sequentially through Blender MCP against the
locked 8gfKpO and ZWD70v PNGs, with Clay's supplied screenshot as a finish-quality
comparison. Lip contours now have distinct upper/lower shapes, rounded depth,
a near-closed resting seam, and textured blue-charcoal/red surfaces. Head, body
and remaining details each have dedicated packed 2048px color/normal atlases.
Orbit retains pebbled skin and rose folds; Coral retains its striated wax finish.
No reference-image projection or paid generation was used.

`scripts/refine_supplied_likeness.py` provides explicit sculpt, material, bake,
audit and promotion stages. Run one character at a time through Blender MCP;
do not rerun sculpting on an already revised source or bake baked materials.
Audits against the preceding source prove unchanged topology, bone rest matrices,
weights, facial channel sets, and body/eye/teeth/tongue targets. Only the lip and
attached cavity geometry and the surface bakes change. The original six other
characters and all runtime tracking code are untouched by this revision.

Before-state backups, candidate sources, seven-pose actual-export renders,
controls audits and a PNG/before/after review page are under
`.context/qa/supplied-lip-surface-v3/`. Both arm-continuity/collision replays and
portrait/landscape live-render checks pass. Visual approval and physical sensor
acceptance remain pending. This is not a fix for the separate smile bite or
live eyelid cross-talk/closure reports.

## Previous Surface Refinement (Revision 2)

The user rejected the first completed rigs' texture quality and assembled look.
Both were subsequently refined, Orbit then Coral, through live Blender MCP using
the same locked PNG references. The current default GLBs and thumbnails include:

- Orbit: finer pebbled lavender face, irregular stretched body creases instead
  of the repeated knitted pattern, blended rose belly, fuller abdomen, rounded
  hip joins, preserved toes, raised blue-charcoal lip contour and amber tips.
- Coral: burgundy-to-plum wax finish, fine surface marks and localized forehead
  creases, warmer ivory eyes, softer red lip transition and narrower resting
  mouth, rounded lower-body joins and a less exposed dark neck connection.
- Repacked UVs remove the observed Orbit belly color seam. Both use 2048-square
  basecolor and normal atlases; only these two rigs increase normal resolution.

Source files and export URLs remain the `*-image-rig` paths below. Revision:
`reference_material_refinement_2`. Before-state assets, renders and controls
audits are in `.context/qa/{orbit,coral}-surface-refinement/`. The helper is
`scripts/polish_supplied_characters.py`; stages must run explicitly, geometry
and Coral resting-lip refinement only once per source. Do not rebake baked
shaders without restoring their retained procedural materials first.

Control audits confirm identical bone rest matrices, skin weights, topology,
facial channel sets and tongue targets. Shape refinements preserve the existing
geometry/deformation thresholds. Both actual-export browser fixtures, synthetic
arm continuity/response checks and live landscape/portrait checks pass. These
are visual revisions for user review, not a claim of exact reference likeness
or physical ZED/Orin approval. Other six characters and runtime tracking/UI code
were not changed in this refinement pass.

## Orbit And Coral: Live Image-Based Rigs

`orbit-image-rig.blend` and `coral-image-rig.blend` now contain the completed
movement-review rigs, built sequentially through live Blender MCP from the
corrected supplied-image studies. The default cockpit manifest selects their
matching `assets/likeness-trials/<name>-image-rig.glb` exports. Exact reference
paths, SHA256s and deliverable paths are in `scripts/reference-source-lock.json`.
The PNGs are packed comparison empties, not projected skins or billboards; no
old character geometry was reused. Original `*-image-source.blend` studies remain
preserved separately. No generation credits were spent.

Both have baked clay-like materials, glossy eyes, independent arms and eyelids,
52 facial channels, recessed oral cavities, separate upper/lower teeth, and
root-anchored tongues with 0.98 units of additional reach. Orbit has 39 bones,
19 exported mesh primitives, 12 teeth and seven visible native digits with three
joints each (four camera-left, three camera-right, as drawn). Coral has 18 bones,
16 primitives, 16 teeth and two articulated flippers without human fingers.
Neck bridges, shoulder weights and Coral's mouth topology were refined.

Final geometry checks pass 12 combined mouth poses without inverted triangles,
normalized weights with at most four influences, independent arms/digits and
fixed tongue roots. Extreme tested edge-stretch maxima are Orbit 1.76 and Coral
1.77; some deformation remains. These are movement-review rigs, not exact
single-image reconstructions or hardware-approved production assets.

Browser fixtures check the actual GLBs, expression changes, tongue retraction,
arm isolation, native digit curl/point and collision envelopes. The default live
cockpit also passes automatic fake-camera startup, hidden operator panels,
absent vehicle and nonblank landscape/portrait canvas checks. Evidence is in
`.context/qa/{orbit,coral}-complete/` and `.context/qa/live-image-replacements/`.
The staged Blender helper is `scripts/complete_supplied_characters.py`; do not
rerun geometry creation or texture baking blindly on completed sources.

The earlier `orbit-body-rig.blend` old-base rework was rejected by the user.
Do not promote it or mistake its successful numerical rig checks for approval.
That rejected old-base export is not selected by the default cockpit.

## Sequential Roster Pass

Cosmic, Summer, Glass and Kudzu now have isolated, full-body reference builds.
Clay's approved build and Nebula's existing refined source are preserved.
Coral and Orbit's subsequent image-based pass is documented above.
No generation credits were spent.

Each new source is `<name>-body-rig.blend`; the corresponding export is
`assets/likeness-trials/<name>-body-rig.glb`. All include body/facial rigs,
independent eyelids, teeth, a recessed mouth cavity and an anchored long tongue.
Native digits have three joints each, with tested curl limits. The source PNGs
are packed comparison empties, never projected skins or flat character meshes.

| Build | Export Meshes | Bones | Digits Per Hand | Teeth | Added Tongue Reach |
| --- | ---: | ---: | ---: | ---: | ---: |
| Cosmic | 16 | 30 | 2 | 16 | 0.98 |
| Summer | 16 | 30 | 2 | 12 | 0.90 |
| Glass | 10 | 36 | 3 | 12 | 0.90 |
| Kudzu | 23 | 36 | 3 | 16 | 0.98 |

Summer has its own six-lobed silhouette, asymmetrical eye apertures and a dark
star-field material with baked warm emission. Glass has raised aqua eye rims,
transmissive cyan limbs and a reflective dark head; the head is opaque in the
runtime material to prevent the oral interior showing through it. Glass's
appearance remains lighting-dependent, not a pixel-identical copy of the PNG.
Kudzu has a traced, thickened leaf crown, independent leafy brows, conformed
pupils, and surface-bound vines. Small leaves use attachment-point skin weights;
vines interpolate nearby body triangle weights. No cloth physics is added.

Geometry checks cover 12 combined mouth poses, every head expression's maximum
displacement, weight normalization, four-influence limits, degenerate geometry,
independent arms/digits and tongue-root anchoring. Tested extreme arm edge
stretch maxima: Cosmic 1.68, Summer 1.70, Glass 1.63, Kudzu 1.74. Compression and
some stretching remain; these are review rigs, not final deformation guarantees.

Local Playwright checks load the actual exports with the existing arm, finger,
mouth, eyelid and collision modules. They cover curl/point/release, independent
arms, tongue extension/retraction, rendered expression changes, bounded morphs,
four moving-arm envelope poses and wide/portrait/narrow canvas sizes. Display
checks do not add a mobile app or visible operator controls.

Evidence: `.context/qa/<name>-complete/`, especially `runtime-validation.json`,
`geometry-validation.json`, `final-neutral.png`, `final-tongue-blink.png` and
`runtime-*.png`. Intermediate failed studies are not final assets.

**Active in the local cockpit for movement review.** Visual acceptance, actual ZED capture,
tracking latency, hand visibility and Orin performance still require hardware
checks. Single-view hidden anatomy and material response are interpretations.
Camera autostart, hidden visitor UI, swipe, tracking and the absent vehicle
remain preserved. The later Orbit/Coral pass also refined shared arm-collision
transitions; all eight now pass the existing synthetic continuity thresholds.
Nebula's original mesh was not newly reconstructed from PNG.

New-scene rebuild stages (live Blender MCP only):

- Summer: `scene`, `head`, `projections`, `body`, `skin`, `skeleton`,
  `smooth_weights(650)`, `facial`, `bake_material`, `validate`, `export_runtime`.
- Glass: `scene`, `head`, `projections`, `body`, `skin`, `skeleton`, `facial`,
  `bake_material`, `validate`, `export_runtime`.
- Kudzu: `scene`, `head`, `body`, `eyes`, `galaxy`, then `kudzu_foliage.crown`
  and `brows`, `skeleton`, `facial`, `kudzu_foliage.body_foliage`,
  `bake_material`, `validate`, `export_runtime`.

Helpers are `scripts/complete_<name>_likeness.py`, `reference_body_tools.py`,
`reference_rig_checks.py` and `kudzu_foliage.py`. Never rerun geometry creation
on a completed source. Save only the active character scene as a standalone file.
Always initialize expression targets from Basis (`from_mix=False`). Cosmic's
earlier inherited brow/cheek targets were caught, rebuilt and revalidated.

## Cosmic Body And Rig

`cosmic-body-rig.blend` is a new, isolated reference-contour build made through
live Blender MCP. The original PNG is a comparison empty, not a projected skin.
The squared head, colored eyelids, antennae, squat body, two-digit hands and
orange feet follow the supplied reference. Unseen depth remains inferred.

16 meshes, 30 bones, 52 expression channels, 16 teeth, a closed-back mouth cavity
and an anchored tongue with 0.98 units of additional reach. Each native digit has
three fitted joints with bounded curl metadata. The purple star-field material
is authored in 3D and baked to a 2048 base-color and 1024 tangent-normal atlas;
the procedural material is retained in the Blender source.

Validation passes after four-influence runtime conversion: 12 mouth combinations
without projected triangle inversions, normalized weights, no degenerate faces,
independent arms/fingers and zero tongue-root drift. Four extreme joint tests
record max edge stretch 1.68, 99th percentile 1.28. Local runtime checks cover
rendered expressions, tongue retraction, native finger curl/point/release and
four collision-envelope poses with no measured penetration. These are not
physical ZED tracking, latency, exact mesh collision or Orin performance tests.

Runtime: `assets/likeness-trials/cosmic-body-rig.glb`.
Evidence: `.context/qa/cosmic-complete/`, including `final-neutral.png`,
`final-tongue-blink.png`, `neck-leg-check.png`, `runtime-*.png`,
`geometry-validation.json` and `runtime-validation.json`.

```sh
LIKENESS_ASSET=cosmic NODE_PATH=.context/qa/node_modules node scripts/test_clay_likeness_browser.cjs
```

Staged helper: `scripts/complete_cosmic_likeness.py`. Start a NEW scene, never
rerun geometry on the completed file. Final sequence: scene, head, body,
fuse_body, eyes, galaxy, skeleton, smooth_shoulders(900), runtime_weights,
facial, bake_material, validate, export_runtime. Use Standard view transform
for the reference-matched renders. Export uses active-scene isolation.
The default roster and installation behavior are unchanged.

## Active Movement-Test Roster

On 2026-09-11 the user explicitly requested replacing the default old roster,
not a separate opt-in preview. `assets/3dai/manifest.json` now selects Cosmic,
Nebula, Kudzu, Clay, Summer and Glass alongside the existing Orbit and Coral.
The ordinary `cockpit.html?assets=3dai` uses these rigs and the unchanged live
tracking pipeline. Orbit/Coral reworks are pending. Original assets are preserved;
the old default manifest is backed up in `.context/before-live-roster/manifest.json`.
Historical "not installed" notes below describe the initial authoring stages,
not the current active roster. Visual/hardware acceptance remains pending.

## Cosmic Material Review Revision

On 2026-09-11, Cosmic received a material-only revision through live Blender MCP:
matte clay skin (roughness .88), two-scale baked surface grain, and separate
polished black eyes (roughness .028, clearcoat 1). The existing purple/star
base-color atlas is unchanged. Orange and green exterior parts are also matte.
Mesh positions, UVs, weights, expression targets and bone rests have matching
before/after hashes. Other characters and the installation roster are unchanged.

The editable grain material and packed normal atlas are in the final .blend.
For reconstruction, after the original Cosmic stages, run
`refine_cosmic_clay_material.checkpoint()` then `materials()` through the live
MCP, followed by `complete_cosmic_likeness.export_runtime()`. Do not rerun
geometry stages or rebake over the final material as part of opening the file.

Evidence: `.context/qa/cosmic-material-review/` contains the pre-change backup,
material validation and close-up. The approval sheet uses refreshed renders.
The runtime exports real reflective eyes, but the stock overhead environment
puts its bright reflections behind the narrow neutral lids. Eye-level lighting
is still needed for consistently visible neutral-pose catchlights in the
installation. No painted highlights, altered lids or production lighting changes
were used to mask that limitation. Visual approval remains pending.

## Completed Body And Rig

`clay-body-rig.blend` continues the user-approved head into a full character.
It is separate from the installation roster. The original unrigged head remains
unchanged in `clay-head-unrigged.blend`.

- Connected head, neck and pear-shaped torso, independent flippers and flared feet.
- 18 body bones: independent shoulders, elbows, wrists, hips, knees, ankles, neck and head.
- 52 expression channels across the meshes, including independent blinks and tongue extension.
- 12 teeth, recessed oral cavity, anchored tongue with 0.88 units of additional reach.
- Iron-red mineral material, baked 2048px base color and 1024px tangent normal maps.
- Runtime export: `assets/likeness-trials/clay-body-rig.glb` (paths relative to the workspace).

The flippers have no human fingers because none are present in the reference.
Unseen anatomy remains an interpretation of one PNG, not a verified reconstruction.
The broad head was retained; the small mouth region was retopologized for animation.

Validation: 12 mouth combinations with no projected triangle inversions; normalized
weights; isolated arms and anchored tongue root; local-runtime textured rendering,
expression changes, full tongue extension/retraction, independent arms, and four
moving-arm collision scenarios. The collision tests use envelopes, not exact
mesh self-collision. Extreme elbow bends retain local skin compression/stretch
(recorded max edge stretch about 1.48, 99th percentile about 1.30).

This is **not yet a live ZED/Orin acceptance test or an installation replacement**.
Camera, tracking, swipe, hidden visitor UI and retained character selection are unchanged.
Clay opts into `UpperArm` bone metadata `armCollisionRestContact=true`; the runtime
allows its authored resting contact but still constrains moving arms. Other rigs
retain the default behavior without that metadata.

Evidence: `.context/qa/clay-complete/`, particularly `final-reference-comparison.png`,
`final-neutral.png`, `final-tongue-blink.png`, `geometry-validation.json` and
`runtime-validation.json`. Tests:

```sh
node --test scripts/test_*.mjs
NODE_PATH=.context/qa/node_modules node scripts/test_clay_likeness_browser.cjs
```

The staged MCP helper is `scripts/complete_clay_likeness.py`. It is not an automatic
background generator. Start from the original approved head, and do not rerun
geometry stages on the final file. The final stage order is prepare, body, skeleton,
mineral_material, finish_body, facial, refine_blinks_tongue, retopologize_mouth,
stabilize_mouth_topology, finalize_mouth_contour, fit_oral_clearance, clean_oral_cap,
bake_material, export_runtime, validate_geometry. Earlier experimental helpers
refine_mouth, solve_mouth_patch and conform_mouth_depth are not final stages.

## Original Head Trial

`clay-head-unrigged.blend` is the **user-approved, unrigged form study**, not an
installation character. Built through Blender MCP on 2026-09-11.

- Manually traced silhouette, eye openings, and mouth from the supplied Clay PNG.
- Solid head volume with an inferred back; separate static eyes and mouth recess.
- Source image appears beside the head as an image empty, never as skin texture.
- Plain materials deliberately leave out the source's mineral grain.
- Triangulated face with quad aperture and perimeter loops, not final animation topology.

The reference supplies one view. The trial matches that projection and does not
establish accurate unseen anatomy. Mouth corners and depth need further review.
No body, rig, teeth, tongue, or working facial expressions are included yet.
Its head likeness was approved before the body continuation above.

Comparison and front/angled renders: `.context/qa/clay-likeness-trial/` in the
workspace. Modeling helper: `.context/clay-head-trial.py`.
