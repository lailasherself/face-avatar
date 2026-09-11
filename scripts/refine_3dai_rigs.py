"""Stage deformation and articulated-hand revisions without overwriting working rigs."""
import json
import math
from pathlib import Path
import shutil
import sys

import bpy
import numpy as np
from mathutils import Quaternion

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_avatar_fleet import export
from build_3dai_characters import Character
from build_3dai_coral import set_pose
from articulated_hands import build_hands,fit_wrist_centers
from pose_correctives import bake_correctives,install_drivers
from refine_clementine_face import rebuild as rebuild_clementine
from refine_eye_rims import refine_eye_rims
from rebind_upper_body import rebind_upper_body
from post_skin_correctives import export_space
from separate_sleeves import separate_sleeves
from refine_3dai_tongues import refine_tongue

QA=ROOT/'.context/qa/refinement'
BACKUP=ROOT/'.context/before-refinement'
OUT=ROOT/'assets/3dai/refined'
BLEND=ROOT/'blender/3dai/refined'


def refit_sprout_arms(rig,config):
    # The source leans forward; its wrists are well ahead of the original fit.
    config={**config,'arm':[[.27,-.08,1.49],[.43,-.40,1.06],[.54,-.67,.80],[.58,-.77,.58]]}
    bpy.context.view_layer.objects.active=rig;rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for side,sign in [('L',1),('R',-1)]:
        points=[(sign*x,y,z) for x,y,z in config['arm']]
        for i,name in enumerate(['UpperArm','Forearm','Hand']):
            bone=rig.data.edit_bones[name+'.'+side];bone.head=points[i];bone.tail=points[i+1]
    bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
    rig['refinedArmLandmarks']=config['arm']
    return config


def rebuild_base_clips(rig,name,config):
    rig.animation_data.action=None
    for track in list(rig.animation_data.nla_tracks):
        actions=[strip.action for strip in track.strips];rig.animation_data.nla_tracks.remove(track)
        for action in actions:
            if action.users==0:bpy.data.actions.remove(action)
    for mode in ['Seated','Standing','T-Pose']:
        pose(rig,name,config,mode)
        for bone in rig.pose.bones:
            for frame in [1,2]:
                bone.keyframe_insert('rotation_quaternion',frame=frame,group=bone.name)
                bone.keyframe_insert('location',frame=frame,group=bone.name)
        action=rig.animation_data.action;action.name=mode
        track=rig.animation_data.nla_tracks.new();track.name=mode;track.strips.new(mode,1,action);track.mute=True
        rig.animation_data.action=None


def pose(rig,name,c,mode,base_pose=None):
    base=base_pose or (mode if mode in ['Seated','Standing','T-Pose'] else 'Seated')
    if name=='coral':set_pose(rig,base)
    else:
        character=Character.__new__(Character);character.name=name;character.c=c;character.rig=rig
        character.pose(base)
    if mode.startswith('Arms'):
        character=Character.__new__(Character);character.rig=rig
        for side,s in [('L',1),('R',-1)]:
            directions={'ArmsUp':[(s*.25,0,1),(0,0,1),(0,-.1,1)],'ArmsOut':[(s,0,0),(s,0,0),(s,0,0)],
                        'ArmsDown':[(s*.1,0,-1),(0,0,-1),(0,0,-1)],'ArmsForward':[(s*.15,-1,-.1),(0,-1,0),(0,-1,0)]}[mode]
            for bone,direction in zip(['UpperArm','Forearm','Hand'],directions):character.aim(bone+'.'+side,direction)
    if mode.startswith('Head'):
        axis,angle={'HeadLeft':[(0,0,1),.55],'HeadRight':[(0,0,1),-.55],'HeadUp':[(1,0,0),.4],'HeadDown':[(1,0,0),-.4]}[mode]
        bone=rig.pose.bones['Head'];basis=bone.bone.matrix_local.to_quaternion()
        bone.rotation_quaternion=basis.inverted()@Quaternion(axis,angle)@basis
        bpy.context.view_layer.update()


def strain(body):
    points=np.array([v.co[:] for v in body.data.vertices])
    edges=np.array(list({tuple(sorted(edge)) for polygon in body.data.polygons for edge in polygon.edge_keys}))
    original=np.linalg.norm(points[edges[:,0]]-points[edges[:,1]],axis=1)
    evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    moved=np.array([v.co[:] for v in mesh.vertices]);evaluated.to_mesh_clear()
    ratios=np.linalg.norm(moved[edges[:,0]]-moved[edges[:,1]],axis=1)/np.maximum(.006,original)
    return {'max':float(ratios.max()),'over4':int((ratios>4).sum()),'p99':float(np.quantile(ratios,.99))}


def main():
    for folder in [QA,BACKUP,OUT,BLEND]:folder.mkdir(parents=True,exist_ok=True)
    configs=json.loads((ROOT/'scripts/rig_3dai_landmarks.json').read_text())
    requested=[a for a in sys.argv[sys.argv.index('--')+1:] if not a.startswith('--')] if '--' in sys.argv else []
    for name in [*configs,'coral']:
        if requested and name not in requested:continue
        source=ROOT/'blender/3dai'/(name+'-rigged.blend');backup=BACKUP/source.name
        if not backup.exists():shutil.copy2(source,backup)
        bpy.ops.wm.open_mainfile(filepath=str(backup));bpy.context.preferences.filepaths.save_version=0
        rig=bpy.data.objects['AvatarRig'];body=bpy.data.objects[name.title()+'SourceBody'];c=configs.get(name,{})
        rig.animation_data.action=None
        for track in rig.animation_data.nla_tracks:track.mute=True
        before={}
        modes=['Seated','Standing','T-Pose','ArmsUp','ArmsOut','ArmsDown','ArmsForward','HeadLeft','HeadRight','HeadUp','HeadDown']
        for mode in modes:
            pose(rig,name,c,mode);before[mode]=strain(body)
        if name=='clementine':
            c={**c,'mouth':[0,1.985,.075,-.006],'faceFloor':1.90}
            source=next(s for s in json.loads((ROOT/'assets/3dai/selection.json').read_text())['characters'] if s['name']==name)
            rig,body=rebuild_clementine(c,source)
        if name=='sprout':c=refit_sprout_arms(rig,c)
        fit_wrist_centers(body,rig)
        rebuild_base_clips(rig,name,c)
        rebind_upper_body(body,rig,c)
        if name in ['clementine','sprout']:separate_sleeves(body,rig,name,c)
        build_hands(body,rig,name)
        for obj in bpy.context.scene.objects:
            if obj.type=='MESH' and obj.data.shape_keys:
                for key in obj.data.shape_keys.key_blocks:key.value=0
        refine_eye_rims(body,bpy.data.objects[name.title()+'EyesAndMouth'])
        refine_tongue(bpy.data.objects[name.title()+'EyesAndMouth'])
        samples=bake_correctives(body,rig,c,lambda mode:pose(rig,name,c,mode))
        after={}
        for mode in modes:
            for sample in samples:body.data.shape_keys.key_blocks[sample['key']].value=float(sample['clip']==mode or (mode not in ['Seated','Standing','T-Pose'] and sample['clip']=='Seated'))
            pose(rig,name,c,mode);after[mode]=strain(body)
        for sample in samples:body.data.shape_keys.key_blocks[sample['key']].value=0
        pose(rig,name,c,'Seated')
        objects=[rig]+[o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)]
        export_space(body,samples,True)
        export(OUT/(name+'.glb'),objects,True,morph_normals=True)
        export_space(body,samples,False)
        pose(rig,name,c,'Seated')
        install_drivers(body,rig,samples,lambda mode:pose(rig,name,c,mode))
        bpy.ops.wm.save_as_mainfile(filepath=str(BLEND/(name+'-rigged.blend')))
        scene=bpy.context.scene;scene.cycles.samples=12;scene.render.resolution_x=800;scene.render.resolution_y=800
        scene.render.filepath=str(QA/(name+'-seated.png'));bpy.ops.render.render(write_still=True)
        report={'name':name,'before':before,'after':after}
        (QA/(name+'-weights.json')).write_text(json.dumps(report,indent=2)+'\n')
        print('REFINED',json.dumps(report),flush=True)
    manifest=json.loads((ROOT/'assets/3dai/manifest.json').read_text())
    manifest['status']='Articulated refinement; final sculpting and physical target-hardware approval pending'
    for entry in manifest['characters']:
        entry['url']='assets/3dai/refined/'+entry['id']+'.glb'
        entry['bones']=50 if entry['id']=='pearl' else 45 if entry['id']=='fuzz' else 42
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':main()
