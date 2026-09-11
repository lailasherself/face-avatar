"""Preserve the source texture while preparing an editable Coral working mesh."""
from pathlib import Path
import sys
import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_avatar_fleet import stage

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT / 'assets/3dai/originals/f852429a-8c8c-439a-b073-02fefb4e9421.glb'))
obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
obj.name = 'CoralSourceBody'
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for v in obj.data.vertices:
    v.co = Vector((v.co.y * 3.2, -v.co.x * 3.2, (v.co.z + .5) * 3.2))
bm = bmesh.new()
bm.from_mesh(obj.data)
bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=.00001)
bm.to_mesh(obj.data)
bm.free()
decimate = obj.modifiers.new('Working topology reduction', 'DECIMATE')
decimate.ratio = 60000 / len(obj.data.polygons)
bpy.ops.object.modifier_apply(modifier=decimate.name)
for p in obj.data.polygons:
    p.use_smooth = True
obj['sourceTaskId'] = 'f852429a-8c8c-439a-b073-02fefb4e9421'
obj['reference'] = 'nkmqsW'
obj['rigStatus'] = 'unrigged working copy'
camera = stage()
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 12
scene.render.resolution_x = 800
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
camera.data.ortho_scale = 3.7
for label, location, target, scale in [
    ('front', (0,-8,1.6), (0,0,1.6), 3.7),
    ('side', (8,0,1.6), (0,0,1.6), 3.7),
    ('face', (0,-8,2.3), (0,-.15,2.3), 1.65),
]:
    camera.location = location
    camera.rotation_euler = (Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale = scale
    scene.render.filepath = str(ROOT / '.context/qa/3dai' / ('coral-source-'+label+'.png'))
    bpy.ops.render.render(write_still=True)
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.context.view_layer.objects.active=obj
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'blender/3dai/coral-prepared.blend'))
print('PREPARED', len(obj.data.vertices), len(obj.data.polygons), flush=True)
