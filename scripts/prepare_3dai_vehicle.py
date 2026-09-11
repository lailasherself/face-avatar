"""Fit an optimized copy of the existing silver vehicle to the installation."""
from pathlib import Path
import sys
import bpy
import bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
(ROOT/'assets/3dai/rigged').mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'scripts'))
from build_avatar_fleet import stage, export

bpy.ops.wm.read_factory_settings(use_empty=True)
source='987d6edd-f31d-4c5e-bff3-53ca15dd4188'
bpy.ops.import_scene.gltf(filepath=str(ROOT/'assets/3dai/originals'/(source+'.glb')))
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
obj.name='SilverVehicle'
bpy.context.view_layer.objects.active=obj
obj.select_set(True)
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
for v in obj.data.vertices:
    v.co=Vector((v.co.x*3,v.co.y*3,(v.co.z+.2349637)*3+.10))
bm=bmesh.new();bm.from_mesh(obj.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
bm.to_mesh(obj.data);bm.free()
modifier=obj.modifiers.new('Vehicle topology reduction','DECIMATE')
modifier.ratio=50000/len(obj.data.polygons)
bpy.ops.object.modifier_apply(modifier=modifier.name)
for p in obj.data.polygons:p.use_smooth=True
for image in bpy.data.images:
    if max(image.size)>2048:
        image.scale(2048,2048)
        image.pack()
obj['sourceTaskId']=source
obj['assetRole']='shared-vehicle'
anchor=bpy.data.objects.new('SeatAnchor',None)
bpy.context.collection.objects.link(anchor)
anchor.location=(0,0,.82)
export(ROOT/'assets/3dai/rigged/silver-vehicle.glb',[obj,anchor])
camera=stage();camera.location=(3.8,-7,3.3)
camera.rotation_euler=(Vector((0,0,.85))-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.ortho_scale=3.8
scene=bpy.context.scene;scene.cycles.samples=16
scene.render.resolution_x=900;scene.render.resolution_y=700
scene.render.filepath=str(ROOT/'.context/qa/3dai/silver-vehicle.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/3dai/silver-vehicle.blend'))
bpy.ops.render.render(write_still=True)
print('VEHICLE',len(obj.data.vertices),len(obj.data.polygons),flush=True)
