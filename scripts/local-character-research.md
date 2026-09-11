# Direct Blender Character Production

## Decision

The six replacement designs can be modeled, textured, skinned and exported in
Blender without an image-to-3D service. The appropriate deliverable is an editable
three-dimensional character with a tested deformation mesh, not a flat image
placed on a plane or a static statue with a skeleton attached. The existing two
characters, Coral and Orbit, should retain their current assets and controls.

For this installation, direct modeling offers control over joint construction
and facial anatomy. Its cost is modeling and review effort: the front references
do not specify the back of the head, all finger surfaces, the mouth interior or
material behavior under arbitrary lighting. Those details require deliberate
design decisions. No workflow can recover them with certainty from a single PNG.

The recommended sequence is silhouette construction, deformation topology,
material authoring, body weights, facial targets, export, and runtime pose review.
The sequence matters: remeshing after building expressions can invalidate the
data those expressions depend on. Blender distinguishes topology cleanup from
the manually directed topology needed for reliable animation.[^1]

## Reference Analysis

The following labels identify working assets, not final character names.

| Asset | Identity Features | Main Modeling Risk | Material Requirement |
|---|---|---|---|
| Cosmic | Squarish purple galaxy head; green antennae; orange and green lids; orange feet | Preserve the sleepy silhouette without eyelid overlap | Mottled purple surface with small gold stars; separate solid-color details |
| Nebula | Wide rounded blue/mauve head; pale horizontal eyes; narrow torso; long arms | Oversized head and narrow neck must not pull the shoulders | Soft blue/mauve variation and sparse pale stars |
| Kudzu | Leaf crown; heavy green lids; long vine-covered limbs | Leaves and vines must follow the correct limb, not stretch between regions | Dark green leaves over a bright speckled green body |
| Clay | Very broad flattened head; small glossy black eyes; tapered body | Neck transition and head mass are disproportionate to the body | Iron-red grain with controlled roughness, not glittering metal |
| Summer | Rounded head projections; compact body; small warm eyes | Head projections need consistent volume and must remain head-bound | Dark surface with gold points and larger soft glowing patches |
| Glass | Large teal dome; oversized glossy eyes; thin translucent limbs | Transparency reveals internal intersections otherwise hidden by opaque skin | Tinted reflective/transmissive material, tested in the actual renderer |

Preserve silhouette before adding small surface detail. A successful texture
cannot compensate for incorrect head width, eye placement, body length or foot
size. Each model needs both a front comparison and a three-quarter comparison;
the latter is essential because the installation camera is not perfectly frontal.

The reference images are rendered illustrations, not orthographic model sheets.
Perspective, depth of field and stylized lighting affect apparent dimensions.
Proportional measurements should therefore be treated as targets for visual
comparison, not a unique geometric reconstruction. A hidden reference object in
each Blender file keeps the original image available without exporting it as part
of the character.

## Geometry And Topology

### Body

A connected body is preferable to disconnected limb cylinders at the shoulder.
Blender's Skin modifier can turn a branching edge structure into a surface; it is
a useful local construction tool, not a guarantee of final animation topology.[^2]
Subdivision can then provide intermediate loops before skin weights are assigned.
The resulting shoulder, armpit, elbow and hip regions must still be inspected.

For these designs, a controlled branching body is a reasonable first construction
pass because the limbs are stylized and the replacement designs do not wear the
complex fused jackets that caused problems in the previous roster. Neck and head
attachment still deserve explicit inspection. Separate overlapping shells may be
acceptable in a toy-like opaque character, but can be obvious in the glass design.

Avoid using a dense voxel remesh as proof of rig readiness. Voxel and automatic
quad remeshing redistribute geometry; neither automatically supplies the desired
edge flow at every joint. The Blender manual specifically distinguishes these
operations from manually directed retopology for deformation.[^1]

### Face

The face needs an actual opening at the lips, an inward mouth wall and a dark
interior. A painted mouth over an unbroken face cannot open convincingly. The lip
boundary should have enough segments to form a smile and a rounded opening, with
several surrounding support loops to distribute the movement.

Dikko's face-retopology demonstration is particularly relevant because its chapter
structure covers initial facial loops, lip construction, eyelid volume, the mouth
bag and joining the head to the body. Its listed chapters place lips at31:00,
eyelid volume at40:28 and the mouth bag at41:45.[^3] These are useful review targets,
not evidence that a generated radial face mesh already has production facial flow.

A radial mouth-to-head surface is a controllable prototype. It needs further
eye-loop refinement if cheek movements stretch long strips around the eyes. Do
not call such a prototype artist-approved merely because the channel count is52.

### Hands

The references range from mitten-like hands to visible separated digits. A
four-digit alien hand can retain the runtime's thumb/index/middle/outer-digit
mapping without pretending it is a five-finger human hand. Each digit needs
several joints and enough lengthwise segments for curling. A palm and several
overlapping tubes are an intermediate construction, not finished finger webbing.

Dikko's hand-retopology tutorial specifically addresses animation-efficient hand
topology.[^4] Its applicability here is the placement of deforming regions and
webbing, rather than literal adoption of realistic human proportions. Finger
separation, thumb opposition and palm volume must be checked during a fist,
pointing pose, open palm and wrist rotation.

## Body Rig And Weights

Use the current runtime names for Root, Hips, Spine, Chest, Neck, Head, UpperArm,
Forearm and Hand, including left/right suffixes. Retaining that contract allows
the existing tracking and smoothing pipeline to drive the new assets. The body
sensor does not need to know which visual character is loaded.

Weights should be normalized, limited to supported influence counts, and inspected
for cross-body contamination. Blender provides normalization, smoothing and
influence-limiting tools for this purpose.[^5] The first practical tests are an
isolated left-arm raise and an isolated right-arm raise. A vertex on one shoulder
must not receive meaningful weight from the opposite arm.

Do not use bone translation or scale to hide a bad elbow. Bone lengths should
remain fixed while joint rotations change. Add corrective shapes only after the
underlying weights are satisfactory, and keep left/right corrective regions
independent. A corrective shape should represent measured useful displacement,
not an empty marker inserted to satisfy a test.

The current torso/head contact guards are approximate collision constraints.
They should be supplied with the new body and head surfaces explicitly. Collision
guards can keep a tracked forearm away from a head envelope, but cannot repair
stretching topology, pinched armpits or poor finger webbing.

## Face, Eyelids And Tongue

### Expression Targets

The installation already consumes named facial channels. New characters should
map those signals to actual vertex motion rather than introduce another facial
tracking system. Channel existence and channel usefulness are separate checks:
an empty jawOpen key technically exists but does not animate a mouth.

Keep upper teeth attached to the upper face and lower teeth coupled to the jaw.
Use a neutral mouth gap small enough to resemble the reference, but avoid exposing
large tooth rows while the mouth is closed. The interior should stay dark during
smiles, lateral mouth motion and jaw opening. Excessive additive displacement is
a common reason individually acceptable expressions become contorted together.

Royal Skies demonstrates a workflow that derives facial shape keys after facial
rigging.[^6] The relevant lesson is that expression generation needs a meaningful
face rig underneath; automatic creation of named channels does not eliminate the
modeling and combination-review work.

### Eyelids

An eyelid moves around an eyeball rather than straight through it. Model upper and
lower lids on a slightly larger enclosing surface, with sufficient coverage at
full blink and a narrow overlap that avoids cracks. Preserve the existing runtime
eyelid surface correction and blink arbitration.

Pierrick Picaut's cartoon-eye tutorial addresses non-spherical eyes and preserving
the iris shape. Its listed sections include driver-based and modifier-based eye
rigging.[^7] The installation uses exportable geometry and morph targets instead
of assuming Blender-only drivers survive export. This is especially relevant to
Nebula's flattened eyes and Glass's tall eyes.

Check gaze at the same time as blinking: a pupil that looks correct in the neutral
pose can slide off the visible eyeball during diagonal gaze. Surface constraints
and bounded gaze ranges are preferable to arbitrary XY translations.

### Tongue

Use an anchored root, an extensible middle and a tip that clears the lower lip
before curving downward. A whole tongue translated forward creates a floating
object; an unanchored scale operation can expose the back of the mouth. Keep the
root within the oral cavity across jaw-open and tongue-out combinations.

The existing camera pipeline estimates tongue presence, not tongue-tip position
or physical extension length. A long stylized extension can respond to that
signal, but it is not a measurement of the visitor's exact tongue length. Better
geometry does not prove a latency problem is fixed. Geometry validation and
end-to-end capture timing must remain separate tests.

## Materials And Export

Author galaxy variation, clay grain and glowing points as reusable surface
materials, not as the original picture projected across the entire mesh. The
picture contains lighting and background that would otherwise remain fixed when
the character rotates. Keep solid-colored eyelids, antennae, leaves, eyes, teeth
and tongues independently controllable.

Blender's glTF exporter supports recognized PBR materials, skinning and morph
targets. Exportable image textures and standard material inputs are the reliable
boundary; arbitrary shader-node networks and rig controls should not be assumed
to transfer automatically.[^8] A packed GLB should be reloaded in the installation
to check the actual material result, rather than judged only in a Blender render.

For Glass, use restrained transmission and reflections first. A high-transmission
body can expose intersecting shells and add rendering cost. A beautiful offline
Cycles image does not demonstrate acceptable Orin performance. Keep editable
material parameters so physical-hardware review can adjust this without changing
the character mesh.

The first export should retain the runtime skeleton names, named expression
targets, standing pose, fingers and contact-envelope metadata. Store editable
Blender files separately from runtime GLBs. Never overwrite the source roster as
a side effect of rebuilding an experimental character.

## Acceptance Matrix

| Check | Method | Required Evidence |
|---|---|---|
| Reference fidelity | Front/three-quarter comparison | Head silhouette, eyes, limbs and distinguishing details reviewed |
| Structural rig | Blender and GLB inspection | Expected bones, normalized weights, nonempty expressions, finite coordinates |
| Arm independence | Drive only one side | Opposite chain unchanged; no cross-body weights |
| Joint deformation | Down/out/forward/overhead poses | Stable length, bounded strain, no visible shoulder holes |
| Fingers | Open/fist/point | Independent digit motion, acceptable webbing and wrist transition |
| Eyes | Blink/gaze/squint/wide combinations | No exposed eye edge, pupil escape or tracking-induced flicker |
| Mouth | Jaw/smile/pucker/close combinations | Dark cavity retained, lips do not invert, correct tooth attachment |
| Tongue | Extension with several jaw values | Root retained, lip cleared, return follows the existing signal |
| Runtime | Landscape and portrait screenshots | Nonblank canvas, no clipping, no operator UI restored |
| Installation regression | Current automated suites | Camera autostart, swipe, old assets, fingers and ZED interface preserved |
| Hardware | Physical ZED and Orin trial | Measured capture-to-render delay and sustained frame rate |

Numeric tests are necessary but not visual approval. Edge-strain bounds detect
gross regressions but cannot judge likeness or a subtly pinched eyelid. Likewise,
a screenshot cannot certify native sensor timing. Keep status explicit until both
technical checks and the relevant visual/hardware review have passed.

## Sources

[^1]: Blender Foundation. [Remeshing and Retopology, Blender5.0 Manual](https://docs.blender.org/manual/id/5.0/modeling/meshes/retopology.html). Describes the limits of automatic remeshing for animation topology.
[^2]: Blender Foundation. [Skin Modifier, Blender4.5 LTS Manual](https://docs.blender.org/manual/en/4.5/modeling/modifiers/generate/skin.html). Reference for edge-based surface construction.
[^3]: Dikko. [Modeling for Animation06: Retopologising the Face](https://www.youtube.com/watch?v=SwM19PgSdCM), July2,2020. Public chapter listing and description; Blender UI shown is older than the local5.1 installation.
[^4]: Dikko. [Best Tips for Retopologising ANY Kind of Hand](https://www.youtube.com/watch?v=zF61xM6fiDw). Public title and description identify its animation-topology scope; full transcript not available in this research.
[^5]: Blender Foundation. [Weight Paint, Blender5.2 Manual](https://docs.blender.org/manual/en/5.2/sculpt_paint/weight_paint/index.html). Normalization, smoothing, transfer and influence-limit tool inventory; local Blender is5.1.2, so confirm exact operator behavior locally.
[^6]: Royal Skies. [FREE-AUTOMATIC Facial MoCap Shapekeys](https://www.youtube.com/watch?v=61QUzH34l1I), February24,2022. Public description of generating52 shape keys after facial rigging.
[^7]: Pierrick Picaut. [Simplified Cartoon Eye Rig in Blender](https://www.youtube.com/watch?v=hHDkD9UVYVE), June23,2020. Public description and chapter listing; demonstrated in Blender2.83.
[^8]: Blender Foundation. [glTF2.0, Blender4.5 LTS Manual](https://docs.blender.org/manual/sl/4.5/addons/import_export/scene_gltf2.html). Exported material and animation support. Source is an official localized manual with English technical sections.

Additional tutorial: Dikko, [Ultimate Character Modelling, Part5: Face Topology](https://www.youtube.com/watch?v=dl-JOScRCI8), February23,2025. A newer companion reference for efficient animation topology; do not treat a video title or description as full tutorial verification.
