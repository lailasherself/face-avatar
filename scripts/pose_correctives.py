"""Bake post-skin edge-strain corrections for Blender and the installation runtime."""
import bpy
import numpy as np
from post_skin_correctives import surface_normals,install_post_skin_modifier


def evaluated_points(body):
    evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    points=np.array([v.co[:] for v in mesh.vertices]);evaluated.to_mesh_clear()
    return points


def relax_strain(points,rest,edges,pinned):
    points=points.copy()
    lengths=np.maximum(.006,np.linalg.norm(rest[edges[:,0]]-rest[edges[:,1]],axis=1))
    inverse_mass=(~pinned).astype(float)
    a,b=edges.T;mass=inverse_mass[a]+inverse_mass[b]
    for iteration in range(600):
        vector=points[b]-points[a];distance=np.linalg.norm(vector,axis=1)
        if iteration>=24 and np.max(distance/lengths)<2.02:break
        error=distance-np.clip(distance,lengths*.6,lengths*2)
        correction=vector*(error/np.maximum(distance,1e-8)/np.maximum(mass,1))[:,None]
        total=np.zeros_like(points);count=np.zeros(len(points))
        active=np.abs(error)>1e-6
        np.add.at(total,a,correction*inverse_mass[a,None]);np.add.at(total,b,-correction*inverse_mass[b,None])
        np.add.at(count,a,active);np.add.at(count,b,active)
        points+=total/np.maximum(1,count[:,None])*.7
    return points


def bake_correctives(body,rig,config,set_pose):
    rest=np.array([v.co[:] for v in body.data.vertices]);samples=[];deltas={};normal_deltas={}
    rest_normals=np.array([v.normal[:] for v in body.data.vertices])
    used={tuple(sorted(edge)) for polygon in body.data.polygons for edge in polygon.edge_keys}
    edges=np.array(list(used))
    head_group=body.vertex_groups['Head'].index
    pinned=np.array([any(g.group==head_group and g.weight>.999 for g in v.groups) for v in body.data.vertices])
    pinned&=rest[:,2]>config.get('faceFloor',1.62)+.08
    modes=['Seated','Standing','T-Pose','ArmsUp','ArmsOut','ArmsDown','ArmsForward','HeadLeft','HeadRight','HeadUp','HeadDown']
    for mode in modes:
        for key in body.data.shape_keys.key_blocks:key.value=0
        set_pose(mode);bpy.context.view_layer.update()
        before=evaluated_points(body);after=relax_strain(before,rest,edges,pinned)
        transforms={body.vertex_groups[b.name].index:np.array((b.matrix@b.bone.matrix_local.inverted()).to_3x3()) for b in rig.pose.bones if body.vertex_groups.get(b.name)}
        matrices=np.zeros((len(rest),3,3))
        for v in body.data.vertices:
            for group in v.groups:
                if group.group in transforms:matrices[v.index]+=transforms[group.group]*group.weight
        deltas[mode]=after-before
        skinned_normals=np.einsum('nij,nj->ni',matrices,rest_normals)
        skinned_normals/=np.maximum(1e-8,np.linalg.norm(skinned_normals,axis=1,keepdims=True))
        normal_deltas[mode]=surface_normals(body,after)-skinned_normals
        if mode not in ['Seated','Standing','T-Pose']:
            rig.animation_data.action=None
            for bone in rig.pose.bones:
                for frame in [1,2]:
                    bone.keyframe_insert('rotation_quaternion',frame=frame,group=bone.name)
                    bone.keyframe_insert('location',frame=frame,group=bone.name)
            action=rig.animation_data.action;action.name=mode
            track=rig.animation_data.nla_tracks.new();track.name=mode;track.strips.new(mode,1,action);track.mute=True
            rig.animation_data.action=None
    for mode in modes:
        regions=['L','R'] if mode.startswith('Arms') else ['Head'] if mode.startswith('Head') else ['Base']
        for region in regions:
            delta=deltas[mode].copy();normal=normal_deltas[mode].copy()
            if region!='Base':
                delta-=deltas['Seated']
                normal-=normal_deltas['Seated']
                if region in ['L','R']:
                    mask=np.clip((rest[:,0]*(1 if region=='L' else -1)+.03)/.06,0,1)
                    delta*=mask[:,None]
                    normal*=mask[:,None]
            key=body.shape_key_add(name='corrective'+mode.replace('-','')+('' if region=='Base' else region),from_mix=False)
            key.data.foreach_set('co',(rest+delta).astype(np.float32).ravel());key.value=0
            samples.append({'key':key.name,'clip':mode,'region':region,'basePose':mode if mode in ['Standing','T-Pose'] else 'Seated'})
            attr=body.data.attributes.new(name=f'_PSD_N_{len(samples)-1}',type='FLOAT_VECTOR',domain='POINT')
            attr.data.foreach_set('vector',(normal[:,[0,2,1]]*np.array([1,1,-1])).astype(np.float32).ravel())
    body['correctiveSamples']=samples
    install_post_skin_modifier(body,samples)
    return samples


def install_drivers(body,rig,samples,set_pose):
    """Keep the editable Blender scene responsive to manual FK arm/head posing."""
    rig['correctiveBasePose']=0
    rig.id_properties_ui('correctiveBasePose').update(min=0,max=2,description='0: Seated live corrections; 1: Standing; 2: T-Pose')
    def variable(driver,name,path):
        var=driver.variables.new();var.name=name;var.type='SINGLE_PROP'
        var.targets[0].id=rig;var.targets[0].data_path=path
    for region in ['L','R','Head']:
        bones=['Head'] if region=='Head' else [b+'.'+region for b in ['UpperArm','Forearm','Hand']]
        neighbors=[{'clip':'Seated','key':None}]+[s for s in samples if s['region']==region]
        for i,sample in enumerate(neighbors):
            set_pose(sample['clip']);prop=f'poseScore{region}{i}';rig[prop]=0.
            driver=rig.driver_add(f'["{prop}"]').driver;driver.type='SCRIPTED';terms=[]
            for j,name in enumerate(bones):
                q=rig.pose.bones[name].rotation_quaternion[:]
                for k in range(4):variable(driver,f'q{j}{k}',f'pose.bones["{name}"].rotation_quaternion[{k}]')
                dot='+'.join(f'q{j}{k}*{value:.7f}' for k,value in enumerate(q))
                terms.append(f'(1-min(1,({dot})**2))')
            driver.expression='1/(.0001+('+ '+'.join(terms)+f')/{len(bones)})**2'
        for i,sample in enumerate(neighbors):
            if not sample['key']:continue
            driver=body.data.shape_keys.key_blocks[sample['key']].driver_add('value').driver
            variable(driver,'base','["correctiveBasePose"]')
            for j in range(len(neighbors)):variable(driver,f'w{j}',f'["poseScore{region}{j}"]')
            driver.expression=f'w{i}/('+ '+'.join(f'w{j}' for j in range(len(neighbors)))+') if base==0 else 0'
    for index,mode in enumerate(['Seated','Standing','T-Pose']):
        sample=next(s for s in samples if s['clip']==mode)
        driver=body.data.shape_keys.key_blocks[sample['key']].driver_add('value').driver
        variable(driver,'base','["correctiveBasePose"]');driver.expression=f'1 if base=={index} else 0'
    set_pose('Seated');bpy.context.view_layer.update()
