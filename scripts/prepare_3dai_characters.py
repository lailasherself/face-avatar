"""Prepare selected static sources for landmark fitting without changing originals."""
import json
from pathlib import Path
import sys

import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_avatar_fleet import stage


def prepare(entry, model):
    name = entry['name']
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.import_scene.gltf(filepath=str(ROOT / entry['original']))
    obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
    obj.name = name.title() + 'SourceBody'
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    low = min(v.co.z for v in obj.data.vertices)
    height = max(v.co.z for v in obj.data.vertices) - low
    scale = 3.2 / height
    for v in obj.data.vertices:
        x, y, z = v.co
        # Prism faces +X; Hunyuan's GLB front becomes -Y in Blender.
        v.co = Vector((y * scale, -x * scale, (z-low)*scale)) if 'Prism' in model else Vector((x*scale, y*scale, (z-low)*scale))
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=.00001)
    bm.to_mesh(obj.data)
    bm.free()
    decimate = obj.modifiers.new('Working topology reduction', 'DECIMATE')
    decimate.ratio = min(1, 60000 / len(obj.data.polygons))
    bpy.ops.object.modifier_apply(modifier=decimate.name)
    for p in obj.data.polygons:
        p.use_smooth = True
    obj['sourceTaskId'] = entry['task_id']
    obj['reference'] = entry['reference']
    obj['rigStatus'] = 'unrigged working copy'
    camera = stage()
    scene = bpy.context.scene
    scene.cycles.samples = 8
    scene.render.resolution_x = 700
    scene.render.resolution_y = 700
    for label, location in [('front', (0,-8,1.6)), ('side', (8,0,1.6))]:
        camera.location = location
        camera.rotation_euler = (Vector((0,0,1.6))-camera.location).to_track_quat('-Z','Y').to_euler()
        camera.data.ortho_scale = 3.6
        scene.render.filepath = str(ROOT / '.context/qa/3dai' / (name+'-source-'+label+'.png'))
        bpy.ops.render.render(write_still=True)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'blender/3dai' / (name+'-prepared.blend')))
    print('PREPARED', name, len(obj.data.vertices), flush=True)


if __name__ == '__main__':
    selections = json.loads((ROOT/'assets/3dai/selection.json').read_text())['characters']
    models = {item['task_id']: item['model'] for item in json.loads((ROOT/'assets/3dai/library.json').read_text())['items']}
    requested = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    for entry in selections:
        if entry['name'] in ['coral', 'vehicle', 'vehicle_original']:
            continue
        if requested and entry['name'] not in requested:
            continue
        prepare(entry, models[entry['task_id']])
