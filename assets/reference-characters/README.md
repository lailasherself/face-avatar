# Reference Character Work In Progress

`nebula-review.glb` is a source-preserving rigging study, not an approved replacement.
It is deliberately absent from the installation manifest.

- Source: `assets/3dai/rigready/atliens-nebula.blend`, left unchanged.
- Editable review: `blender/reference-characters/nebula-review.blend`.
- Builder: `scripts/rig_reference_nebula.py`, used incrementally through Blender MCP.
- Validation: `node --test scripts/test_reference_nebula.mjs`.
- Visual QA and deformation report: `.context/qa/reference-characters/`.

The v2 rig has independent body chains, three articulated native digits per hand,
52 facial channels, teeth, and an anchored extending tongue. Side-view inspection
revealed the rear digit missed in v1. All 18 finger joints now have tested curl
limits; existing installation characters retain their default ranges.

The eye sockets have localized surface and texture cleanup. The mouth patch has
six connected quad rings. Five tested mouth combinations have no inverted patch
triangles; curling the middle digit produces zero drift in the index fingertip.
These are focused regressions, not complete deformation or likeness approval.
Eyelid and lip material transitions still need artistic polish. No physical
ZED/Orin or live-user camera timing validation has been performed on this rig.
The other five new characters remain unfinished.

Rebuild from the separate `nebula-body-rig.blend` stage through Blender MCP:
`rig_face()`, `rig_digits()`, then `refine_reference_face.refine()`,
`blend_pupil_edges()`, `retopologize_mouth()`, `validate()`, `save_review()`.
Open the Blender stage in a separate MCP call before running build functions.

Run the browser export check with:
`NODE_PATH=.context/qa/node_modules node scripts/test_reference_nebula_browser.cjs`.
It uses an ephemeral test page, not new installation UI, and captures landscape
and portrait display layouts. `REVIEW_ORIGIN` defaults to `http://localhost:8014`.
