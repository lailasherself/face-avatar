# Reference-Inspired Avatar Fleet

Eight editable prototype characters, one shared vehicle, and a camera-driven preview.
These are procedural interpretations of the supplied artwork, not reconstructed copies
or production-approved likenesses. Clothing and hair are simplified exportable geometry;
the original images' fine skin and textile textures have not been recreated.

Launch locally with `python3 scripts/run_installation.py`. `cockpit.html` defaults to
an installation display with automatic camera startup and no studio controls. Use
`cockpit.html?setup` only for operator inspection. The main `index.html`
links to this view through **Full-body Fleet**. The existing kiosk remains available.

## Files

- `blender/fleet/*.blend`: editable character, vehicle, lighting, and camera scenes.
- `assets/fleet/*.glb`: runtime characters. Each contains one body skeleton and facial targets.
- `assets/fleet/silver-vehicle.glb`: the common car, with a `SeatAnchor` node.
- `assets/fleet/*.png`: rendered previews.
- `assets/fleet/manifest.json`: character names, source-reference IDs, assets, and channels.
- `scripts/build_avatar_fleet.py`: reproducible Blender source.
- `scripts/validate_fleet.py`: exported-buffer validation, independent of the build.

## Character Mapping

| Working Name | Reference |
| --- | --- |
| Orbit | Purple alien, four orange-tipped antennae (`Jy8yzW`) |
| Pearl | Pale pink cyclops, orange lips (`kMxwme`) |
| Juno | Pink cyclops, jester antennae, orange lower body (`bjWgsy`) |
| Fuzz | Lavender hair, ribbed limbs, yellow sneakers (`UnGowG`) |
| Clementine | Orange head and jacket, lilac beanie (`zF0uXa`) |
| Coral | Rose skin and coral-like crown (`nkmqsW`) |
| Sprout | Purple skin, green eyes, orange beanie and shirt (`8KA2yn`) |
| ATL | Green alien in an Atlanta-inspired baseball outfit (`ppDO39`) |

Names are working labels, not assumed final character names.

## Rig Contract

`AvatarRig` has 28 deform bones: root, hips, spine, chest, neck, head, arms, hands,
four single-joint fingers per hand, thighs, shins, feet, and toes. This is an FK rig;
there are no IK handles, physics, or secondary antenna simulation. Body geometry is
weighted at elbows and knees. `Head` moves the face and head accessories together.

`Face` has a neutral `Basis` and 52 nonempty ARKit-named relative shape keys. These
include geometric eyelids, pupil gaze, mouth opening, smiles, cheek/brow/nose motion,
teeth, a recessed oral cavity, and a tongue. Facial motion is through shape keys,
not a separate facial bone rig. The browser's **All facial controls** selector exposes
each channel. The export uses zero default facial weights.

The animation clips `Seated`, `Standing`, and `T-Pose` are static body poses. Playing
`Seated` places the character at the common vehicle origin. GLB uses Y up and faces +Z.
Models must not be independently recentered or normalized when swapping them.
In Blender, all NLA tracks are muted for manual editing and the saved pose is seated.
Choose an action to inspect its keyed pose. Finger and toe geometry stays editable.

`Face` also exports a `_LID_INDEX` vertex attribute and `eyelidSurfaces` metadata.
The installation shader projects interpolated lids back onto the eye's outer surface
and recomputes their normals. This prevents linear shape interpolation from cutting
through the eyeball during partial blinks. Other runtimes need this same correction.

The browser loads the car once. Swapping disposes the old character and replaces only
its scene. Cyclops eye channels are averaged and applied once to the single eye.
Blink suppresses simultaneous squint/wide deltas. Head rotation affects only `Head`.

## Camera and Limits

Camera access starts automatically in installation mode, after the assets load.
Initial browser/OS permission is still required. MediaPipe runs locally using the
existing bundled runtime and model. Camera frames are not uploaded or recorded.
The camera pauses while the page is hidden and resumes on return. Disconnections
retry automatically; permission denial shows a retry action. The operator view
starts its camera on demand. Calibration averages 30 detected neutral-face frames.

MediaPipe provides 52 scores including a neutral category; it does **not** provide
the ARKit `tongueOut` signal. That channel can be inspected manually or supplied by
another tracker. Shape key names alone do not guarantee Memoji-quality tracking.
Extreme combinations and individual likenesses still require artistic review and
corrective sculpting. Live expression fidelity must be checked with a real person.

The preview is a separate studio view. Existing kiosk capture, attract-loop behavior,
and anamorphic camera projection have not been ported into it.

## Rebuild and Validate

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python scripts/build_avatar_fleet.py
python3 scripts/validate_fleet.py
```

For one character, append `-- --only orbit`. This rebuilds that character but does not
rewrite the fleet manifest. `--no-render` skips thumbnails. No paid addons or external
generation services are used by the script.

## Bringing in 3D AI Studio Assets

Existing textured full-body GLB/FBX files would improve reference fidelity. Inspect
their topology, separate eye geometry, actual mouth opening, skin weights, and facial
targets in Blender first. A generated body skeleton is not a complete facial rig.
Keep the car separate. Preserve neutral reference meshes before remeshing or rigging.
Imported models need fitting and retargeting to the seat contract; changing a file
path alone will not adapt arbitrary proportions or skeletons.

The supplied MCP endpoint was added to the local Codex configuration and OAuth
sign-in completed. No 3D AI Studio assets have been generated or charged for.

References: [Blender glTF export](https://docs.blender.org/manual/en/5.1/addons/import_export/scene_gltf2.html),
[MediaPipe blendshape enum](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/python/vision/face_landmarker.py),
[3D AI Studio rigging](https://docs.3daistudio.com/processing/rigging),
[3D AI Studio MCP](https://www.3daistudio.com/MCP).
