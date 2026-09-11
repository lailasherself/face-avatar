"""Smooth discontinuous sleeve weights, then rebake corrections for that binding."""
import json
from pathlib import Path
import sys
import bpy
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_avatar_fleet import export
from refine_3dai_rigs import pose
from pose_correctives import bake_correctives,install_drivers
from post_skin_correctives import export_space


def smooth_elbows(body):
    size=len(body.data.vertices);edges=np.array([e.vertices[:] for e in body.data.edges])
    points=np.array([v.co[:] for v in body.data.vertices]);a,b=edges.T
    strength=1/np.maximum(.004,np.linalg.norm(points[a]-points[b],axis=1))
    degree=np.zeros(size);np.add.at(degree,a,strength);np.add.at(degree,b,strength)
    for side in ['L','R']:
        groups=[body.vertex_groups[name+'.'+side] for name in ['UpperArm','Forearm','Hand']]
        indices={g.index:i for i,g in enumerate(groups)};old=np.zeros((size,3))
        for vertex in body.data.vertices:
            for g in vertex.groups:
                if g.group in indices:old[vertex.index,indices[g.group]]=g.weight
        total=old.sum(axis=1)
        # Preserve the attached shoulder, wrist and torso boundary. Only diffuse
        # the mixed elbow band on vertices wholly owned by this arm.
        movable=(total>.999)&(old[:,0]>.01)&(old[:,1]>.01)&(old[:,2]<.01)
        values=old.copy()
        for _ in range(90):
            average=np.zeros_like(values)
            np.add.at(average,a,values[b]*strength[:,None]);np.add.at(average,b,values[a]*strength[:,None])
            candidate=.5*values+.5*average/np.maximum(1,degree[:,None])
            values[movable]=candidate[movable]
            values[:,2]=old[:,2]
            scale=(total-values[:,2])/np.maximum(1e-10,values[:,:2].sum(axis=1))
            values[:,:2]*=scale[:,None]
        for vertex in np.flatnonzero(movable):
            for i,g in enumerate(groups):g.add([int(vertex)],float(values[vertex,i]),'REPLACE')
    body['elbowWeightRefinementVersion']=1


def main():
    requested=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    configs=json.loads((ROOT/'scripts/rig_3dai_landmarks.json').read_text())
    out=ROOT/'assets/3dai/clothing-cleanup';out.mkdir(parents=True,exist_ok=True)
    blend_out=ROOT/'blender/3dai/clothing-cleanup';blend_out.mkdir(parents=True,exist_ok=True)
    for entry in json.loads((ROOT/'assets/3dai/manifest.json').read_text())['characters']:
        name=entry['id']
        if requested and name not in requested:continue
        bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/3dai/mouth-cleanup'/f'{name}-rigged.blend'))
        bpy.context.preferences.filepaths.save_version=0
        body=bpy.data.objects[name.title()+'SourceBody'];rig=bpy.data.objects['AvatarRig'];c=configs.get(name,{})
        if name=='clementine':c={**c,'faceFloor':1.90}
        rig.animation_data.action=None
        for track in list(rig.animation_data.nla_tracks):
            if track.name not in ['Seated','Standing','T-Pose']:
                actions=[s.action for s in track.strips];rig.animation_data.nla_tracks.remove(track)
                for action in actions:
                    if action.users==0:bpy.data.actions.remove(action)
            else:track.mute=True
        for driver in list(rig.animation_data.drivers):
            if driver.data_path.startswith('["poseScore'):rig.driver_remove(driver.data_path)
        body.modifiers.remove(body.modifiers['Post-skin pose corrections'])
        for key in list(body.data.shape_keys.key_blocks):
            if key.name.startswith('corrective'):body.shape_key_remove(key)
            else:key.value=0
        for attr in list(body.data.attributes):
            if attr.name.startswith('_PSD_'):body.data.attributes.remove(attr)
        smooth_elbows(body)
        samples=bake_correctives(body,rig,c,lambda mode:pose(rig,name,c,mode))
        for sample in samples:body.data.shape_keys.key_blocks[sample['key']].value=0
        pose(rig,name,c,'Seated')
        objects=[rig]+[o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)]
        export_space(body,samples,True);export(out/f'{name}.glb',objects,True,morph_normals=True);export_space(body,samples,False)
        install_drivers(body,rig,samples,lambda mode:pose(rig,name,c,mode))
        rig['correctiveBasePose']=1;pose(rig,name,c,'Standing')
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_out/f'{name}-rigged.blend'))
        print('STAGED ELBOW WEIGHTS',name,flush=True)


if __name__=='__main__':main()
