"""Stage local mouth constraints and genuinely baked Standing arm correctives."""
import json
from pathlib import Path
import shutil
import sys
import bpy
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_avatar_fleet import export
from refine_3dai_rigs import pose
from pose_correctives import evaluated_points
from post_skin_correctives import export_space,install_post_skin_modifier,surface_normals
from surface_constraints import relax_surface,defects


def mouths(body):
    keys=body.data.shape_keys.key_blocks
    rest=np.array([v.co[:] for v in body.data.vertices])
    edges=np.array([e.vertices[:] for e in body.data.edges]);body.data.calc_loop_triangles()
    triangles=np.array([t.vertices[:] for t in body.data.loop_triangles]);report={}
    targets={key.name:np.array([v.co[:] for v in key.data])-rest for key in keys if key.name.startswith(('mouth','jaw'))}
    mixes=[{'jawOpen':v,'mouthSmileLeft':1,'mouthSmileRight':1} for v in [.3,.65,1]]
    mixes.append({'jawOpen':.8,'mouthLowerDownLeft':.112,'mouthLowerDownRight':.112,
                  'mouthUpperUpLeft':.2275,'mouthUpperUpRight':.2275,'mouthFunnel':.4333333333333333,
                  'mouthPucker':.3666666666666667,'mouthSmileLeft':.16,'mouthSmileRight':.16})
    def mix_score(mix,values):return defects(rest+sum(values[k]*v for k,v in mix.items()),rest,edges,triangles)
    budgets=[mix_score(mix,targets) for mix in mixes]
    for key in keys:
        if not key.name.startswith(('mouth','jaw')) or key.name=='mouthClose':continue
        original=np.array([v.co[:] for v in key.data]);movable=np.linalg.norm(original-rest,axis=1)>1e-7
        if not movable.any():continue
        candidate=relax_surface(original,rest,edges,movable,triangles)
        before=defects(original,rest,edges,triangles);after=defects(candidate,rest,edges,triangles)
        accepted=after['flipped']<=before['flipped'] and after['stretched']<=before['stretched'] and after!=before
        candidate=candidate.astype(np.float32).astype(float)
        trial={**targets,key.name:candidate-rest}
        for mix,budget in zip(mixes,budgets):
            score=mix_score(mix,trial)
            if score['flipped']>budget['flipped'] or score['stretched']>budget['stretched']:accepted=False
        if accepted:key.data.foreach_set('co',candidate.ravel());targets=trial
        report[key.name]={'before':before,'after':after,'accepted':accepted}
    opened=np.array([v.co[:] for v in keys['jawOpen'].data])
    keys['mouthClose'].data.foreach_set('co',(2*rest-opened).astype(np.float32).ravel())
    body['mouthRefinementVersion']=3
    return report


def standing(body,rig,name,config):
    samples=[dict(s.items()) for s in body['correctiveSamples']]
    rest=np.array([v.co[:] for v in body.data.vertices]);edges=np.array([e.vertices[:] for e in body.data.edges])
    positions=[np.array([v.vector[:] for v in body.data.attributes[f'_PSD_P_{i}'].data]) for i in range(len(samples))]
    base=positions[next(i for i,s in enumerate(samples) if s['clip']=='Standing')]
    body.modifiers.remove(body.modifiers['Post-skin pose corrections'])
    upper=np.zeros(len(rest));pinned=np.zeros(len(rest),dtype=bool)
    groups={g.index:g.name for g in body.vertex_groups}
    for vertex in body.data.vertices:
        upper[vertex.index]=sum(g.weight for g in vertex.groups if groups[g.group].startswith(('Spine','Chest','Neck','Head','UpperArm','Forearm','Hand')))
        pinned[vertex.index]=any(groups[g.group] in ('Head','Hand.L','Hand.R') and g.weight>.8 for g in vertex.groups)
    movable=(upper>.5)&~pinned
    for mode in ['ArmsUp','ArmsOut','ArmsDown','ArmsForward']:
        pose(rig,name,config,mode,base_pose='Standing');bpy.context.view_layer.update()
        before=evaluated_points(body)+base
        after=relax_surface(before,rest,edges,movable,stretch=1.6,iterations=400)
        delta=after-before;normal=surface_normals(body,after)-surface_normals(body,before)
        clip='Standing'+mode
        for bone in rig.pose.bones:
            for frame in [1,2]:
                bone.keyframe_insert('rotation_quaternion',frame=frame,group=bone.name)
                bone.keyframe_insert('location',frame=frame,group=bone.name)
        action=rig.animation_data.action;action.name=clip
        track=rig.animation_data.nla_tracks.new();track.name=clip;track.strips.new(clip,1,action);track.mute=True
        rig.animation_data.action=None
        for region,sign in [('L',1),('R',-1)]:
            mask=np.clip((rest[:,0]*sign+.03)/.06,0,1)*upper
            key='corrective'+clip+region;body.shape_key_add(name=key,from_mix=False)
            sample={'key':key,'clip':clip,'region':region,'basePose':'Standing'}
            index=len(samples);samples.append(sample);positions.append(delta*mask[:,None])
            attr=body.data.attributes.new(name=f'_PSD_N_{index}',type='FLOAT_VECTOR',domain='POINT')
            values=normal*mask[:,None]
            attr.data.foreach_set('vector',(values[:,[0,2,1]]*np.array([1,1,-1])).astype(np.float32).ravel())
    for attr in list(body.data.attributes):
        if attr.name.startswith('_PSD_P_'):body.data.attributes.remove(attr)
    for sample,delta in zip(samples,positions):body.data.shape_keys.key_blocks[sample['key']].data.foreach_set('co',(rest+delta).astype(np.float32).ravel())
    body['correctiveSamples']=samples;body['standingCorrectiveVersion']=1
    install_post_skin_modifier(body,samples)
    # Mirror the runtime neighborhood in the editable Blender scene.
    for region in ['L','R']:
        neighbors=[{'clip':'Standing','key':None}]+[s for s in samples if s['basePose']=='Standing' and s['region']==region]
        for i,s in enumerate(neighbors):
            mode=s['clip'].replace('Standing','') or 'Standing'
            pose(rig,name,config,mode,base_pose='Standing')
            prop=f'standingScore{region}{i}';rig[prop]=0.
            driver=rig.driver_add(f'["{prop}"]').driver;terms=[]
            for j,part in enumerate(['UpperArm','Forearm','Hand']):
                bone=rig.pose.bones[part+'.'+region];q=bone.rotation_quaternion[:]
                for k in range(4):
                    var=driver.variables.new();var.name=f'q{j}{k}';var.type='SINGLE_PROP'
                    var.targets[0].id=rig;var.targets[0].data_path=f'pose.bones["{bone.name}"].rotation_quaternion[{k}]'
                dot='+'.join(f'q{j}{k}*{v:.7f}' for k,v in enumerate(q));terms.append(f'(1-min(1,({dot})**2))')
            driver.expression='1/(.0001+('+ '+'.join(terms)+')/3)**2'
        for i,s in enumerate(neighbors):
            if s['key'] is None:continue
            driver=body.data.shape_keys.key_blocks[s['key']].driver_add('value').driver
            for j in range(len(neighbors)):
                var=driver.variables.new();var.name=f'w{j}';var.type='SINGLE_PROP';var.targets[0].id=rig;var.targets[0].data_path=f'["standingScore{region}{j}"]'
            var=driver.variables.new();var.name='base';var.type='SINGLE_PROP';var.targets[0].id=rig;var.targets[0].data_path='["correctiveBasePose"]'
            driver.expression=f'w{i}/('+ '+'.join(f'w{j}' for j in range(len(neighbors)))+') if base==1 else 0'
    return samples


def main():
    backup=ROOT/'.context/before-review-surfaces';backup.mkdir(parents=True,exist_ok=True)
    mouth_only='--mouth-only' in sys.argv
    folder='mouth-cleanup' if mouth_only else 'cleanup'
    out=ROOT/'assets/3dai'/folder;out.mkdir(parents=True,exist_ok=True)
    blend_out=ROOT/'blender/3dai'/folder;blend_out.mkdir(parents=True,exist_ok=True)
    configs=json.loads((ROOT/'scripts/rig_3dai_landmarks.json').read_text())
    requested=[v for v in sys.argv[sys.argv.index('--')+1:] if not v.startswith('--')] if '--' in sys.argv else []
    for entry in json.loads((ROOT/'assets/3dai/manifest.json').read_text())['characters']:
        name=entry['id']
        if requested and name not in requested:continue
        blend=ROOT/'blender/3dai/refined'/f'{name}-rigged.blend'
        for path in [blend,ROOT/entry['url']]:
            if not (backup/path.name).exists():shutil.copy2(path,backup/path.name)
        bpy.ops.wm.open_mainfile(filepath=str(backup/blend.name));bpy.context.preferences.filepaths.save_version=0
        rig=bpy.data.objects['AvatarRig'];body=bpy.data.objects[name.title()+'SourceBody']
        rig.animation_data.action=None
        for track in rig.animation_data.nla_tracks:track.mute=True
        for obj in bpy.context.scene.objects:
            if obj.type=='MESH' and obj.data.shape_keys:
                if obj.data.shape_keys.animation_data:
                    for d in obj.data.shape_keys.animation_data.drivers:d.mute=True
                for key in obj.data.shape_keys.key_blocks:key.value=0
        report=mouths(body)
        samples=[dict(s.items()) for s in body['correctiveSamples']] if mouth_only else standing(body,rig,name,configs.get(name,{}))
        for d in body.data.shape_keys.animation_data.drivers:d.mute=True
        for key in body.data.shape_keys.key_blocks:key.value=0
        pose(rig,name,configs.get(name,{}),'Standing')
        objects=[rig]+[o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)]
        export_space(body,samples,True);export(out/f'{name}.glb',objects,True,morph_normals=True);export_space(body,samples,False)
        for d in body.data.shape_keys.animation_data.drivers:d.mute=False
        rig['correctiveBasePose']=1
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_out/blend.name))
        (out/f'{name}-report.json').write_text(json.dumps(report,indent=2)+'\n')
        print('STAGED REVIEW SURFACES',name,flush=True)


if __name__=='__main__':main()
