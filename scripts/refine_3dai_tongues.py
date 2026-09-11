"""Refine only tongueOut on current articulated rigs, preserving the other channels."""
import json
from pathlib import Path
import shutil
import sys
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_avatar_fleet import export
from post_skin_correctives import export_space


def refine_tongue(face):
    if face.get('tongueRigVersion')==5:return
    materials={i for i,m in enumerate(face.data.materials) if m and 'tongue' in m.name.lower()}
    vertices={i for p in face.data.polygons if p.material_index in materials for i in p.vertices}
    assert vertices,(face.name,'no tongue geometry')
    basis=face.data.shape_keys.key_blocks['Basis'];key=face.data.shape_keys.key_blocks['tongueOut']
    front=min(basis.data[i].co.y for i in vertices);back=max(basis.data[i].co.y for i in vertices)
    mouth_front=-.575 if face.name.startswith('Coral') else front-.07
    scale=max(.4,min(1.3,(max(basis.data[i].co.x for i in vertices)-min(basis.data[i].co.x for i in vertices))/.28))
    for i in vertices:
        base=basis.data[i].co;old=key.data[i].co-base
        t=min(1,max(0,(back-base.y)/(back-front)/.85));weight=t*t*(3-2*t)
        forward=(old.y-.80*scale)*weight
        # Clear the lower lip before bending down, rather than cutting through it.
        outside=min(1,max(0,(mouth_front-.07*scale-(base.y+forward))/(.10*scale)))
        bend=max(0,(weight-.35)/.65)
        key.data[i].co=base+Vector((old.x*weight,forward,(old.z+.04*scale)*weight-.55*scale*bend*bend*outside*outside))
    face['tongueRigVersion']=5
    face['tongueRig']='Long cartoon tongue, anchored root, lip clearance and downward-curving tip'


def main():
    backup=ROOT/'.context/before-tongue';backup.mkdir(parents=True,exist_ok=True)
    requested=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    for entry in json.loads((ROOT/'assets/3dai/manifest.json').read_text())['characters']:
        name=entry['id']
        if requested and name not in requested:continue
        blend=ROOT/'blender/3dai/refined'/f'{name}-rigged.blend';glb=ROOT/entry['url']
        for path in [blend,glb]:
            if not (backup/path.name).exists():shutil.copy2(path,backup/path.name)
        bpy.ops.wm.open_mainfile(filepath=str(backup/blend.name));bpy.context.preferences.filepaths.save_version=0
        rig=bpy.data.objects['AvatarRig'];body=bpy.data.objects[name.title()+'SourceBody']
        face=bpy.data.objects[name.title()+'EyesAndMouth'];refine_tongue(face)
        samples=body['correctiveSamples'];objects=[rig]+[o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)]
        drivers=[]
        for obj in objects:
            if obj.type!='MESH' or not obj.data.shape_keys:continue
            keys=obj.data.shape_keys
            if keys.animation_data:
                for driver in keys.animation_data.drivers:drivers.append((driver,driver.mute));driver.mute=True
            for key in keys.key_blocks:key.value=0
        export_space(body,samples,True)
        export(glb,objects,True,morph_normals=True)
        export_space(body,samples,False)
        for driver,mute in drivers:driver.mute=mute
        bpy.context.view_layer.update()
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        print('TONGUE REFINED',name,flush=True)


if __name__=='__main__':main()
