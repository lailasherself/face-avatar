"""Incremental Cosmic repairs executed in the live Blender MCP scene."""
import math
import bpy
from mathutils import Vector


def oral_motion():
    face=bpy.context.scene.objects['CosmicFace']
    keys=face.data.shape_keys.key_blocks;basis=keys['Basis'];jaw=keys['jawOpen']
    cavity=sorted({i for p in face.data.polygons if face.data.materials[p.material_index].name=='Cosmic cavity' for i in p.vertices})
    assert len(cavity)>=512
    for offset,i in enumerate(cavity):
        amount=max(0,-math.sin(2*math.pi*(offset%64)/64))**.4 if offset<512 else 0
        depth=1-(offset//64)/7 if offset<512 else 0
        jaw.data[i].co=basis.data[i].co+Vector((0,-.012*amount*depth,-.15*amount*depth))
    teeth=bpy.context.scene.objects['Teeth'];keys=teeth.data.shape_keys.key_blocks
    if not teeth.get('oralTravelRefined'):
        for key in keys:
            for p in key.data:p.co.x*=.82
    for i,p in enumerate(keys['jawOpen'].data):
        rest=keys['Basis'].data[i].co
        lower=p.co.z<rest.z-.05
        p.co=rest+Vector((0,-.010,-.105)) if lower else rest
    teeth['oralTravelRefined']=True
    for p,v in zip(teeth.data.vertices,keys['Basis'].data):p.co=v.co
    face.data.update();teeth.data.update();bpy.context.view_layer.update()
    return {'cavityVertices':len(cavity),'lowerDentalTravel':.105,'backwallJawTravel':0}


def save():
    from build_reference_cosmic import ROOT,reset,validate,validate_export
    rig=bpy.context.scene.objects['AvatarRig']
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.parent==rig]
    reset(rig,objects);print(validate(rig,objects));reset(rig,objects)
    bpy.ops.object.select_all(action='DESELECT')
    for o in [rig,*objects]:o.select_set(True)
    bpy.context.view_layer.objects.active=rig
    path=ROOT/'assets/reference-characters/cosmic-review.glb'
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,use_active_scene=True,export_animations=False,export_extras=True,export_attributes=True,export_morph=True,export_morph_normal=True)
    print(validate_export(path))
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/reference-characters/cosmic-review.blend'))
