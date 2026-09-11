# 3D AI Studio Source Selection

Inspected all nine supplied references and all 22 existing 3D library previews on 2026-09-07.
No generation, conversion, texturing, or other paid jobs were submitted.

The source GLBs have textures but no skins, armatures, animations, or morph targets.
They must not be presented as production-ready avatars. Rigged outputs, when validated,
will live separately from these originals and from the existing procedural fleet.

| Character | Reference | Source / Preview | Selection Reason |
| --- | --- | --- | --- |
| orbit | Jy8yzW | [32162e04-483e-4d62-82b3-984296472ce0](https://www.3daistudio.com/Dashboard?openFile=32162e04-483e-4d62-82b3-984296472ce0) / [preview](../../assets/3dai/previews/32162e04-483e-4d62-82b3-984296472ce0.png) | Original retains purple skin and dark lips; retexture changes lips to orange. |
| pearl | kMxwme | [1d7d7a55-79a5-41d7-b840-c2b85577625b](https://www.3daistudio.com/Dashboard?openFile=1d7d7a55-79a5-41d7-b840-c2b85577625b) / [preview](../../assets/3dai/previews/1d7d7a55-79a5-41d7-b840-c2b85577625b.png) | Original retains iridescent eye, orange lips and fingertips; tail silhouette needs inspection. |
| juno | bjWgsy | [cd161e78-226d-49ed-84bb-57d764dda6f7](https://www.3daistudio.com/Dashboard?openFile=cd161e78-226d-49ed-84bb-57d764dda6f7) / [preview](../../assets/3dai/previews/cd161e78-226d-49ed-84bb-57d764dda6f7.png) | Hunyuan version retains pink upper body, orange legs, yellow single eye and black antenna tips. |
| fuzz | UnGowG | [f133eee2-d6db-4ec6-b341-940d7aad2fcb](https://www.3daistudio.com/Dashboard?openFile=f133eee2-d6db-4ec6-b341-940d7aad2fcb) / [preview](../../assets/3dai/previews/f133eee2-d6db-4ec6-b341-940d7aad2fcb.png) | Hunyuan version retains ribbed limbs and yellow sneakers; sculpted hair is solid geometry. |
| clementine | zF0uXa | [1536b59f-56ba-4096-9823-eda7cf44d099](https://www.3daistudio.com/Dashboard?openFile=1536b59f-56ba-4096-9823-eda7cf44d099) / [preview](../../assets/3dai/previews/1536b59f-56ba-4096-9823-eda7cf44d099.png) | Original retains lilac knit hat, orange jacket and two-tone sneakers; retexture changes footwear. |
| coral | nkmqsW | [f852429a-8c8c-439a-b073-02fefb4e9421](https://www.3daistudio.com/Dashboard?openFile=f852429a-8c8c-439a-b073-02fefb4e9421) / [preview](../../assets/3dai/previews/f852429a-8c8c-439a-b073-02fefb4e9421.png) | Original matches the rose crowned character and retains the blue pupils. Best first facial construction candidate. |
| sprout | 8KA2yn | [5220d255-53e9-4679-9347-75eb310f6994](https://www.3daistudio.com/Dashboard?openFile=5220d255-53e9-4679-9347-75eb310f6994) / [preview](../../assets/3dai/previews/5220d255-53e9-4679-9347-75eb310f6994.png) | Original retains black pupils, cracked skin and beanie lettering; retexture loses key details. |
| atl | ppDO39 | [68b47717-cbeb-4987-b9e2-c3306e38c161](https://www.3daistudio.com/Dashboard?openFile=68b47717-cbeb-4987-b9e2-c3306e38c161) / [preview](../../assets/3dai/previews/68b47717-cbeb-4987-b9e2-c3306e38c161.png) | Full-body version matches baseball uniform, cap and green skin. |
| vehicle | 4B64Zq | [987d6edd-f31d-4c5e-bff3-53ca15dd4188](https://www.3daistudio.com/Dashboard?openFile=987d6edd-f31d-4c5e-bff3-53ca15dd4188) / [preview](../../assets/3dai/previews/987d6edd-f31d-4c5e-bff3-53ca15dd4188.png) | Retextured version has metallic/roughness and normal maps, silver hull and tinted windshield. |
| vehicle_original | 4B64Zq | [c179f298-5af8-4a53-9877-0ca0a6403bdd](https://www.3daistudio.com/Dashboard?openFile=c179f298-5af8-4a53-9877-0ca0a6403bdd) / [preview](../../assets/3dai/previews/c179f298-5af8-4a53-9877-0ca0a6403bdd.png) | Original vehicle alternate, useful for shape and material comparison. |

Full library metadata: [library.json](../../assets/3dai/library.json).
Selected source paths: [selection.json](../../assets/3dai/selection.json).

The three-character source `aea70bc8-1bb3-4763-aef8-e51dbbf3bd5b` is a generated
multi-figure composition and is unsuitable for a single-character rig. The older
`5b48e6ba-74eb-4c09-ba00-2b5a4ecb6674` head is not one of these full-body references.

## Connection Recovery

The shell resolves Codex 0.137.0, while Conductor bundles 0.153.2. The current MCP
connection initially failed with missing OAuth authorization-server issuer metadata.
Reauthentication using Conductor's bundled executable succeeded, after which the
same session could list the library and retrieve all 22 existing asset records.
Blender's live MCP add-on was unreachable; isolated background Blender processes
are used for inspection and editing, preserving any interactive Blender session.

## Preservation

The shared-car architecture, camera startup, air swipes and eyelid correction remain
in the existing installation. Originals are never rewritten by the rigging pipeline.
The runtime remains local; downloaded GLBs embed their textures.

## Source-Based Review Fleet

All eight selected source characters now have separate editable rigs and runtime
GLBs. `assets=3dai` selects the full source-based roster and the matching shared car;
the default fleet and all ten downloaded originals remain unchanged.

| Character | Body Bones | Editable Scene | Runtime Preview |
| --- | ---: | --- | --- |
| Orbit | 18 | [Blender](orbit-rigged.blend) | [Preview](http://localhost:8014/cockpit.html?setup&assets=3dai&character=orbit) |
| Pearl | 26 | [Blender](pearl-rigged.blend) | [Preview](http://localhost:8014/cockpit.html?setup&assets=3dai&character=pearl) |
| Juno | 18 | [Blender](juno-rigged.blend) | [Preview](http://localhost:8014/cockpit.html?setup&assets=3dai&character=juno) |
| Fuzz | 21 | [Blender](fuzz-rigged.blend) | [Preview](http://localhost:8014/cockpit.html?setup&assets=3dai&character=fuzz) |
| Clementine | 18 | [Blender](clementine-rigged.blend) | [Preview](http://localhost:8014/cockpit.html?setup&assets=3dai&character=clementine) |
| Coral | 18 | [Blender](coral-rigged.blend) | [Preview](http://localhost:8014/cockpit.html?setup&assets=3dai&character=coral) |
| Sprout | 18 | [Blender](sprout-rigged.blend) | [Preview](http://localhost:8014/cockpit.html?setup&assets=3dai&character=sprout) |
| ATL | 18 | [Blender](atl-rigged.blend) | [Preview](http://localhost:8014/cockpit.html?setup&assets=3dai&character=atl) |

Every rig has genuinely deforming 52-channel facial controls and Seated, Standing,
and T-Pose clips. Pearl and Juno have one physical eye: the existing runtime averages
the two tracking signals and applies only the left-channel alias, avoiding additive
double closure. Pearl has eight tail bones, Fuzz three. The hands move as units;
individual finger articulation and animator-facing IK handles are not implemented.

Joint and facial landmarks are fitted separately in
`scripts/rig_3dai_landmarks.json`. Bone-heat weights are constrained to nearby skeleton
joints, relaxed over welded mesh topology, and normalized to four influences. Source
eyes are recessed behind fitted sclerae, pupils and geometric lids. Eye-local texture
bakes preserve Pearl's iridescent eye, ATL's painted eye detail, and sampled lid skin
without interpolating across the original UV atlas seams. Oral openings are cut into
the source mesh with cavities and tongues behind them. No external jobs are used.

### Teeth

All eight review rigs now include separate `UpperTeeth` and `LowerTeeth` meshes,
weighted to the head. The lower row follows `jawOpen`, `mouthClose`, `jawLeft`,
`jawRight` and `jawForward`; the upper row stays fixed to the skull. Each row has
six teeth for the small mouths or eight for the larger mouths. Clementine's very
small opening has a narrower, shorter dental fit. The existing source skin,
eyelids, facial deltas and skin-weight buffers are unchanged by this pass.

After rebuilding a base rig, run Blender with
`--background --python scripts/add_3dai_teeth.py` (optionally `-- orbit coral` to
select characters). This adds teeth to the current editable scenes and re-exports
the GLBs without rebuilding the body. Pre-teeth files are retained under
`.context/before-teeth/`. The pass can be rerun; it replaces only its own dental
meshes. Verify with `python3 scripts/validate_3dai_teeth.py`. Close-up renders and
export/browser validation reports are under `.context/qa/teeth/`.

**These are review rigs, not production-approved character sculpts.** The generated
meshes have fused clothing/limb regions and no deformation-oriented edge loops.
Extreme arm poses still stretch clothing around the armpits, and neck/chin transitions
need corrective sculpting. Small-mouth shapes, lid rims, extreme facial combinations,
and source likeness need an artistic pass. Numeric nonzero deltas and bone counts do
not prove deformation quality. The pose-strain reports record these limitations;
they are diagnostics, not a passing artistic certification. Real-camera participants
and GEEKOM/Orin performance have not been tested.

The process on 8013 still owns that port but stopped responding to requests. A new
instance of the same versioned, no-cache installation server runs on 8014. No existing
server process was killed. Remove `setup` from a preview URL to hide the operator
controls; the camera now starts automatically in both modes. Arm tracking also
accepts this bundled MediaPipe version's coordinate-only landmarks instead of
rejecting every joint for missing optional confidence metadata. Explicit low
confidence, invalid coordinates and out-of-frame joints are still rejected.

## Articulated Refinement

### Tongues And Tracking Timing

All eight current articulated rigs have revised `tongueOut` shapes with anchored
roots and tips that extend forward and bend down. `scripts/refine_3dai_tongues.py`
backs up the current files under `.context/before-tongue/` and rebuilds from those
snapshots. `scripts/validate_3dai_tongues.py` compares every unrelated mesh attribute
and morph against those backups; teeth, hands, eyes, body and pose data are retained.

The installation now runs an additional local image-based tongue detector because
the bundled MediaPipe face output has no tongueOut coefficient. The 2MB FoxyFace
ONNX model and WASM runtime are bundled with licenses and pinned provenance in
`vendor/tongue/` and `vendor/onnxruntime/`. It shares the existing camera, runs in a
dedicated worker, and uploads nothing. Model loss retracts the tongue; model failure
leaves face/arm tracking running. The mouth leaves clearance during extension.

Arm processing now preserves capture time, rejects stale/reordered frames, emits
pose results before finger inference and samples up to30Hz. Joint smoothing is
performed together in world space to avoid cascading forearm lag. The mirrored
side mapping remains unchanged. All eight rigs passed injected rapid arm changes;
physical GEEKOM/Orin motion, tongue accuracy and performance still need testing.

QA scripts and image-fixture renders: `scripts/test_tongue_*.cjs`,
`scripts/test_motion_timing*`, `.context/qa/tongue/`.

### Rig Details

The local installation selects the articulated revisions at
`http://localhost:8014/cockpit.html?assets=3dai`.
The previous manifest is preserved in `.context/before-refinement/manifest.json`.
This enables the functional improvements; final artistic approval is pending.

Editable revisions live in `blender/3dai/refined/`; corresponding embedded GLBs
and the preview manifest are in `assets/3dai/refined/`. The original working rigs,
shared car and downloaded source files are preserved. No generation credits were
spent. One-time input snapshots are under `.context/before-refinement/`.

- Each hand has a thumb and three fingers, each with three independently weighted
  joints. The human ring/little fingers drive the alien's outer finger together.
  This adds 24 finger bones: 42 total normally, 50 for Pearl and 45 for Fuzz.
- `finger-motion.js` derives joint curls from the local Hand Landmarker world
  coordinates and matches hands to the pose wrists. `finger-retarget.js` applies
  bounded, smoothed curls and relaxes them after tracking loss. Pointing keeps
  the index independent of the other fingers.
- Fifteen corrective morphs cover seated/standing/T-pose bases, independent
  left/right arm sample poses, and head turns. Runtime interpolation is active
  for the seated installation; standing/T-pose use their static corrections.
  Extreme mixed poses are not guaranteed by the sample-based interpolation.
- Wrist centers are fitted to the source cuff cross-sections, with rebuilt poses.
  Sprout has corrected forward-leaning arm landmarks. Source hand fragments are
  removed; all sixteen replacement hands are continuous, closed manifold meshes.
- Upper-body weights now use smooth arm/torso fields with a locked face region.
  Clementine and Sprout have separated, capped sleeve/body seams to stop their
  fused clothing from dragging the jacket fronts during raised-arm poses.
- Blender scenes include editable FK finger joints and pose-correction drivers.
  `AvatarRig["correctiveBasePose"]` selects 0: seated, 1: standing, 2: T-pose.
  Automatic pose following is enabled in the seated mode. There are no IK handles.
- Corrective deltas are applied AFTER skinning: Geometry Nodes in Blender, and
  `post-skin-correctives.js` in the installation (positions, normals, depth and
  CPU vertex queries). GLBs require this metadata-aware runtime; ordinary GLTF
  viewers applying every morph before skinning will not reproduce the corrections.
- Source eyelid boundary vertices were locally faired without changing existing
  eye filtering or ellipsoid reprojection. Clementine's mouth was rebuilt below
  the nose on denser local geometry, and the dental fit was adjusted.

**Remaining polish:** visible cuff seams and pointed sleeve corners; rough source
mouth/lid edges and expression combinations, especially Clementine and Juno.
The long Clementine jacket stretch has been removed in the tested poses, but
passing numeric/control tests is not final artistic approval. Fuzz retains one
4.46x edge-strain outlier in an intermediate arm pose. Arbitrary mixed poses and
physical participant motion still require review.

Rebuild with Blender `--background --python scripts/refine_3dai_rigs.py`.
Optional names after `--` select characters. The pass reloads its input snapshots
and writes only the separate refinement outputs. It exports morph normals and
installs Blender drivers after exporting so runtime morph defaults stay neutral.

Checks: `scripts/validate_refined_rigs.py`, `scripts/validate_refined_blender.py`,
`scripts/test_finger_motion.mjs`,
`scripts/test_refined_rigs_browser.cjs`, `scripts/test_finger_tracking_browser.cjs`.
Browser checks use `NODE_PATH=.context/qa/node_modules` and the server on 8014.
Reports and pose screenshots are under `.context/qa/refinement/`. Finger tracking
integration uses injected landmarks with the real worker initialized, not a human
participant. GEEKOM/Orin performance and physical-camera approval are outstanding.

The current pass passes all 22 unit checks, all-eight structural, finger pipeline,
pose-driver, rendered-control and visible dental checks. Original source hashes
and original working Blender scene hashes are unchanged. Clementine/Sprout sampled
maximum strain is about 2.02x, versus old overhead maxima of 34.52x/12.76x.
All seven tested runtime states have p99 strain below 2.1x. These are regression
measurements, not a claim of final sculpting or target-hardware readiness.

## Preserved Coral Rig Details

The first review build is Coral, using the selected original source mesh and its
4K texture. The neutral crown, ears, nose, lip form and body silhouette remain from
that source. Its body uses Blender bone-heat binding, normalized to four influences
per vertex, with the head fixed to the head bone so the reconstructed eyes stay
attached during head motion. The source has mitten hands, not articulated fingers.

- [Editable Coral and shared-car scene](coral-rigged.blend).
- [Runtime Coral GLB](../../assets/3dai/rigged/coral.glb).
- [Optimized shared car](../../assets/3dai/rigged/silver-vehicle.glb).
- [Rendered preview](../../assets/3dai/rigged/coral.png).
- [Local operator preview](http://localhost:8014/cockpit.html?setup&assets=3dai&character=coral).
- [Local installation preview](http://localhost:8014/cockpit.html?assets=3dai&character=coral).

Coral's existing rig and builder were preserved while the other seven characters
were added. The default URL continues to use the original fleet. Both modes keep
the same camera, motion and eyelid code.

Coral exports 18 body bones, Seated / Standing / T-Pose clips and 52 facial channels
across the skin, eyelids, pupils and mouth. It has reconstructed moving pupils,
independent eyelids, an opening in the original lips, an oral cavity and a tongue.
`mouthClose` cancels the jaw-opening delta. Half-blinks retain the existing runtime
ellipsoid projection; Blender review renders apply the same projection temporarily.

This is a review rig, not final artistic approval. Extreme simultaneous facial
combinations and live human expressions still need corrective review. The source
car's windshield is opaque textured geometry. Fine limb creases, baked lighting in
the original texture and source asymmetry remain visible. No target-PC performance
claim is made, and real-camera participant testing remains outstanding.

## Source Inspection

All ten downloaded GLBs were imported into Blender. Each has one mesh and no
armature, skin, action or facial shape key. All textures are embedded at 4096 square.
The retextured car includes color, normal and metallic/roughness maps; the original
character selections each supply a color texture. The exported source meshes have
UV-split boundaries, so the raw nonmanifold-edge count is not a retopology verdict.
The working copies weld coincident vertices before reduction.

| Source | Source Triangles | Source Exported Vertices |
| --- | ---: | ---: |
| Orbit | 1,466,548 | 751,818 |
| Pearl | 500,000 | 272,311 |
| Juno | 500,000 | 275,714 |
| Fuzz | 499,462 | 274,353 |
| Clementine | 1,485,140 | 759,541 |
| Coral | 1,438,218 | 736,413 |
| Sprout | 500,150 | 288,997 |
| ATL | 500,000 | 280,787 |
| Silver car, retextured | 1,432,042 | 737,527 |
| Silver car, original | 1,432,160 | 737,350 |

Only GLB formats were reported for these existing library entries. No paid format
conversion was requested. Detailed source statistics and SHA-256 hashes are in
`.context/qa/3dai/source-inspection.json`.

## Rebuild

Run these in order from the workspace root:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python scripts/prepare_3dai_coral.py
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python scripts/prepare_3dai_vehicle.py
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python scripts/build_3dai_coral.py
python3 scripts/validate_3dai_coral.py
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python scripts/prepare_3dai_characters.py
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python scripts/build_3dai_characters.py
python3 scripts/validate_3dai_characters.py
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python scripts/inspect_3dai_poses.py
```

The numerical validator reads exported buffers, checks neutral weights, real channel
deltas, independent blinks, normalized skin weights, embedded textures and original
file hashes. The render checks and browser screenshots live in `.context/qa/3dai`.
`verify-characters.cjs` checks all eight source rigs, visible expression changes,
cyclops mapping, body poses, one shared car, offline requests, and simulated camera
startup in landscape and portrait installation viewports. `verify-motion.cjs` reuses
the existing installation motion regression tests with the source assets enabled.

## Verification Results

The seven new exported rigs and the preserved Coral pass numeric skin/morph checks.
All ten original source hashes are unchanged, and the original procedural fleet
validator still passes. All 10 gesture/body mapping unit tests pass. The full-roster
browser test passes jaw, smile, half/full blink and brow pixel changes for every
character, cyclops aliasing, body poses, shared-car identity, local-only asset
requests, and synthetic automatic camera at 1920x1080 and 800x1280. The motion
regression passes independent arms, all-eight retargeting, held-palm gated swipes,
camera restart, and model failure recovery, with no browser/shader errors.

The artistic diagnostics remain separate: seated-pose maximum edge stretch is
approximately 6-19x at small generated mesh joins. Clementine's fused jacket/arms
need particular attention in corrective retopology. These numerical and browser
passes are not a production-quality deformation signoff or a hardware benchmark.
