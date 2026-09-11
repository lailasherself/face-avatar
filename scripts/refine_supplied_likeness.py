"""Reference-contour lip and material revision, executed one rig at a time via MCP.

Preserves mesh topology, skin weights, facial channel names and the user's hands.
The archived PNGs guide shapes; no reference photograph is projected onto the rig.
"""
import math
import json
import shutil
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
import complete_supplied_characters as rig
import polish_supplied_characters as surfaces
from complete_clay_likeness import smooth, profile

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / '.context/qa/supplied-lip-surface-v3'


def sculpt_lips():
    rig.reset()
    head = rig.obj('Head')
    assert not head.get('referenceLipContourV3'), 'Lip contour already revised'
    source, n, levels, width, opening, drop = rig.face_config()
    start = head['patches']['mouth']['start']
    keys = head.data.shape_keys.key_blocks
    old = np.array([v.co[:] for v in keys['Basis'].data])
    new = old.copy()
    orbit = rig.prefix() == 'Orbit'
    if orbit:
        upper = [(448,600),(467,591),(491,584),(506,587),(521,585),(542,592),(563,600)]
        lower = [(448,601),(468,610),(492,616),(510,617),(534,612),(550,607),(563,601)]
        slit = [(448,600),(474,599),(492,599.5),(509,600),(535,600),(563,601)]
        px_center, px_scale, px_zero = 504, 300, 1150
        half_gap = .0001
    else:
        upper = [(394,531),(416,510),(443,498),(471,499),(495,506),(521,500),(551,500),(577,512),(598,534)]
        lower = [(394,535),(416,550),(450,558),(477,556),(498,554),(526,559),(562,556),(585,548),(598,535)]
        slit = [(394,534),(422,529),(451,526),(479,528),(500,532),(526,528),(555,527),(579,531),(598,534)]
        px_center, px_scale, px_zero = 496, 250, 819
        half_gap = .0002
    for row, t in enumerate(levels):
        for j in range(n):
            i = start + row*n + j
            phi = j*math.tau/n
            q, sn = math.cos(phi), math.sin(phi)
            ix = source.MOUTH.x + width*q
            iz = (px_zero-profile(slit, px_center+width*q*px_scale))/px_scale
            iz += half_gap*sn
            ox = source.MOUTH.x+(width+(.024 if orbit else .035))*q
            oz = (px_zero-profile(upper if sn>=0 else lower, px_center+(ox-source.MOUTH.x)*px_scale))/px_scale
            if t >= .58:
                a = smooth(.58,1,t)
                x,z = ox*(1-a)+ix*a, oz*(1-a)+iz*a
            else:
                a = smooth(.10,.58,t)
                x,z = old[i,0]*(1-a)+ox*a, old[i,2]*(1-a)+oz*a
            depth = lip_depth(source,x,z,t,orbit)
            if t<.14: depth=old[i,1]
            new[i] = (x,depth,z)
    delta = new-old
    for key in keys:
        points=np.array([v.co[:] for v in key.data])+delta
        key.data.foreach_set('co',points.astype(np.float32).ravel())
    # Keep the authored open target, but start it at the newly traced closed lips.
    jaw=keys['jawOpen'];close=keys['mouthClose']
    for i in range(start,len(old)):
        jaw.data[i].co-=Vector(delta[i])
        close.data[i].co=Vector(new[i])*2-jaw.data[i].co
    head.data.vertices.foreach_set('co',new.astype(np.float32).ravel())
    cavity=rig.obj('Oral Cavity')
    for key in cavity.data.shape_keys.key_blocks:
        head_key=keys.get(key.name,keys['Basis'])
        for i,v in enumerate(key.data):
            if i>=13*n:continue
            row,j=divmod(i,n)
            if row==0:
                v.co=head_key.data[start+(len(levels)-1)*n+j].co+Vector((0,.001,0))
            elif row<9:
                v.co+=Vector(delta[start+(len(levels)-1)*n+j])*(1-smooth(.1,.8,row/12))
    for v,b in zip(cavity.data.vertices,cavity.data.shape_keys.key_blocks['Basis'].data):v.co=b.co
    attr=head.data.attributes.get('lip_color') or head.data.attributes.new('lip_color','FLOAT','POINT')
    for i in range(len(new)):
        t=levels[(i-start)//n] if i>=start else 0
        attr.data[i].value=smooth(.20,.48,t)
    for polygon in head.data.polygons:
        if all(i>=start for i in polygon.vertices):
            t=sum(levels[(i-start)//n] for i in polygon.vertices)/len(polygon.vertices)
            polygon.material_index=1 if t>.26 else 0
    head['referenceLipContourV3']=True
    head['neutralLipSealV3']=True
    head.data.update();cavity.data.update();bpy.context.view_layer.update()
    print(rig.prefix(),'reference lip contour revised; topology and all facial channels retained')


def materials():
    orbit=rig.prefix()=='Orbit'
    if orbit:surfaces.orbit_materials()
    else:surfaces.coral_materials()
    lip_mask()
    head=rig.obj('Head');face=head.data.materials[0];nodes=face.node_tree.nodes;p=nodes['Principled BSDF']
    p.inputs['Coat Weight'].default_value=.04 if orbit else .10
    p.inputs['Roughness'].default_value=.58 if orbit else .48
    # Preserve material-space grain, now baked into a dedicated head atlas.
    if not orbit:
        for node in nodes:
            if node.type=='VALTORGB':
                for e in node.color_ramp.elements:
                    if e.color[0]>e.color[1]*1.3:
                        e.color=(e.color[0]*.60,e.color[1]*.48,e.color[2]*.58,1)
    lip=surfaces.Surface('Reference sculpted lips',(.024,.046,.063) if orbit else (.37,.038,.050),.48 if orbit else .43)
    lip.wire(lip.mix(lip.attribute('lip_color'),(.32,.16,.44,1) if orbit else (.13,.038,.065,1),(.026,.052,.069,1) if orbit else (.28,.025,.035,1)),lip.p.inputs['Base Color'])
    coord=lip.node('ShaderNodeVectorMath');coord.operation='MULTIPLY'
    lip.wire(lip.coord,coord.inputs[0]);coord.inputs[1].default_value=(95,95,12) if orbit else (12,12,120)
    lip.bump(lip.noise(1,2,coord.outputs[0]),.003 if orbit else .005,.4)
    lip.bump(lip.noise(90,2),.0015,.3)
    lip.p.inputs['Coat Weight'].default_value=.05 if orbit else .10
    surfaces.assign(head,lip,1)
    body=rig.obj('Body').data.materials[0]
    body.node_tree.nodes['Principled BSDF'].inputs['Coat Weight'].default_value=.06 if orbit else .10
    body.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.57 if orbit else .48
    if orbit:
        s=surfaces.Surface('Reference belly folds',(.32,.16,.44),.56)
        s.wire(s.mix(s.attribute('belly_mask'),(.32,.16,.44,1),(.48,.175,.225,1)),s.p.inputs['Base Color'])
        sep=s.node('ShaderNodeSeparateXYZ');s.wire(s.coord,sep.inputs[0])
        phase=s.math('ADD',s.math('MULTIPLY',sep.outputs['Z'],390),s.math('MULTIPLY',s.noise(15,3),13))
        ridge=s.math('POWER',s.math('ABSOLUTE',s.math('SINE',phase)),4)
        s.bump(s.math('MULTIPLY',ridge,s.attribute('belly_mask')),.008,.36)
        phase=s.math('ADD',s.math('MULTIPLY',s.attribute('sculpt_flow'),320),s.math('MULTIPLY',s.noise(15,3),18))
        folds=s.math('POWER',s.math('ABSOLUTE',s.math('SINE',phase)),5)
        above_feet=s.ramp(sep.outputs['Z'],[(.24,(0,0,0)),(.53,(1,1,1))])
        s.bump(s.math('MULTIPLY',folds,above_feet),.003,.25)
        s.bump(s.noise(155,3),.0025,.25)
        surfaces.assign(rig.obj('Body'),s)
    bpy.context.scene['surfaceRevision']='reference-lip-contour-dedicated-atlas-3'
    print('Reference material finish set; no photograph projection')


def lip_mask():
    head=rig.obj('Head');start=head['patches']['mouth']['start']
    _,n,levels,*_=rig.face_config()
    attr=head.data.attributes.get('lip_color') or head.data.attributes.new('lip_color','FLOAT','POINT')
    for i in range(len(head.data.vertices)):
        t=levels[(i-start)//n] if i>=start else 0
        attr.data[i].value=smooth(.20,.48,t)


def lip_depth(source,x,z,t,orbit):
    a=smooth(.14,1,t)
    seal=source.depth((x,source.MOUTH.y))-(.035 if orbit else .075)
    return source.depth((x,z))*(1-a)+seal*a-(.012 if orbit else .028)*math.sin(math.pi*a)


def round_lip_surface():
    rig.reset();head=rig.obj('Head');source,n,levels,*_=rig.face_config()
    start=head['patches']['mouth']['start'];keys=head.data.shape_keys.key_blocks
    delta=np.zeros((len(head.data.vertices),3))
    for row,t in enumerate(levels):
        if t<.14:continue
        for j in range(n):
            i=start+row*n+j;x,y,z=keys['Basis'].data[i].co
            if not head.get('neutralLipSealV3'):
                delta[i,2]=-(.0013 if rig.prefix()=='Orbit' else .0038)*math.sin(j*math.tau/n)*smooth(.65,1,t)
                z+=delta[i,2]
            delta[i,1]=lip_depth(source,x,z,t,rig.prefix()=='Orbit')-y
    for key in keys:
        if key.name in ['jawOpen','mouthClose']:continue
        points=np.array([v.co[:] for v in key.data])+delta
        key.data.foreach_set('co',points.astype(np.float32).ravel())
    for i in range(start,len(delta)):keys['mouthClose'].data[i].co=keys['Basis'].data[i].co*2-keys['jawOpen'].data[i].co
    cavity=rig.obj('Oral Cavity')
    for key in cavity.data.shape_keys.key_blocks:
        target=keys.get(key.name,keys['Basis'])
        for i,v in enumerate(key.data):
            row,j=divmod(i,n)
            if row==0:v.co=target.data[start+(len(levels)-1)*n+j].co+Vector((0,.001,0))
            elif row<9 and key.name!='jawOpen':v.co+=Vector(delta[start+(len(levels)-1)*n+j])*(1-smooth(.1,.8,row/12))
    for o in [head,cavity]:
        for v,b in zip(o.data.vertices,o.data.shape_keys.key_blocks['Basis'].data):v.co=b.co
        o.data.update()
    head['roundedLipSurfaceV3']=True
    head['neutralLipSealV3']=True
    print('Rounded reference lip cross-section without changing open target')


def audit(before_path=None):
    current={o.name:o for o in rig.meshes()+[rig.obj('AvatarRig')]}
    collections=[getattr(bpy.data,n) for n in ['meshes','armatures','materials','images','node_groups','shape_keys','actions']]
    existing={item for collection in collections for item in collection}
    names=list(current)
    path=before_path or QA/('before-'+rig.prefix().lower()+'-image-rig.blend')
    with bpy.data.libraries.load(str(path),link=False) as (source,target):
        assert set(names)<=set(source.objects)
        target.objects=list(names)
    old=dict(zip(names,target.objects))
    try:
        for name,o in current.items():
            before=old[name]
            if o.type=='ARMATURE':
                assert list(o.data.bones.keys())==list(before.data.bones.keys())
                for b in o.data.bones:assert b.matrix_local==before.data.bones[b.name].matrix_local
                continue
            assert len(o.data.vertices)==len(before.data.vertices)
            assert [tuple(p.vertices) for p in o.data.polygons]==[tuple(p.vertices) for p in before.data.polygons]
            assert list(o.vertex_groups.keys())==list(before.vertex_groups.keys())
            for v,b in zip(o.data.vertices,before.data.vertices):
                assert {g.group:g.weight for g in v.groups}=={g.group:g.weight for g in b.groups}
            if o.data.shape_keys:
                assert list(o.data.shape_keys.key_blocks.keys())==list(before.data.shape_keys.key_blocks.keys())
                for key in o.data.shape_keys.key_blocks:
                    assert all(math.isfinite(c) for v in key.data for c in v.co)
                    if any(s in name for s in ['Tongue','Teeth','Body','Eye']):
                        assert all((v.co-b.co).length<1e-7 for v,b in zip(key.data,before.data.shape_keys.key_blocks[key.name].data))
        report={'bones':len(rig.obj('AvatarRig').data.bones),'topologyPreserved':True,'weightsPreserved':True,'boneRestPreserved':True,'facialChannelsPreserved':True,'tongueTeethBodyEyeTargetsPreserved':True}
        (QA/(rig.prefix().lower()+'-preserved-controls.json')).write_text(json.dumps(report,indent=2))
        print(report)
    finally:
        for o in old.values():bpy.data.objects.remove(o,do_unlink=True)
        bpy.data.batch_remove(ids=[item for collection in collections for item in collection if item not in existing])


def promote():
    audit();name=rig.prefix().lower()
    assert bpy.context.scene.get('surfaceRevision')=='reference-lip-contour-dedicated-atlas-3'
    for label in groups():
        for channel in ['basecolor','normal']:
            filename=name+'-'+label+'-'+channel+'.png'
            destination=ROOT/'assets/likeness-trials'/filename
            shutil.copy2(QA/filename,destination)
            for image in bpy.data.images:
                if image.filepath and Path(image.filepath).name==filename:
                    image.filepath=str(destination);image.pack()
    save_candidate();export_candidate()
    shutil.copy2(QA/(name+'-candidate.glb'),ROOT/'assets/likeness-trials'/(name+'-image-rig.glb'))
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/likeness-trials'/(name+'-image-rig.blend')))
    print('Promoted audited reference lip and dedicated surface revision:',name)


def groups():
    head=[rig.obj('Head'),rig.obj('Neck Bridge')]
    if rig.prefix()=='Coral':head += [rig.obj('Eyelids '+s) for s in ['L','R']]
    body=[rig.obj('Body')]
    rest=[o for o in rig.meshes() if o not in head+body]
    return {'head':(head,2048),'body':(body,2048),'details':(rest,2048)}


def bake_group(label,roughness=False):
    objects,size=groups()[label]
    s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=8
    bpy.ops.object.select_all(action='DESELECT')
    # Local material copies prevent another atlas group from overwriting these textures.
    copies={}
    for o in objects:
        o.hide_set(False);o.select_set(True);o.active_shape_key_index=0
        for i,m in enumerate(list(o.data.materials)):
            if m.name not in copies:copies[m.name]=m.copy()
            o.data.materials[i]=copies[m.name]
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(78),island_margin=.009)
    bpy.ops.object.mode_set(mode='OBJECT')
    materials={m.name:m for o in objects for m in o.data.materials}
    active={}
    for name,m in materials.items():
        m.use_fake_user=True;node=m.node_tree.nodes.new('ShaderNodeTexImage');m.node_tree.nodes.active=node;active[name]=node
    images={}
    channels=[('basecolor','DIFFUSE'),('normal','NORMAL')]
    if roughness:channels.append(('roughness','ROUGHNESS'))
    for channel,kind in channels:
        image=bpy.data.images.new(rig.prefix()+' v3 '+label+' '+channel,width=size,height=size)
        if kind!='DIFFUSE':image.colorspace_settings.name='Non-Color'
        for node in active.values():node.image=image
        if kind=='NORMAL':bpy.ops.object.bake(type=kind,use_clear=False,margin=12,normal_space='TANGENT')
        elif kind=='ROUGHNESS':bpy.ops.object.bake(type=kind,use_clear=False,margin=12)
        else:bpy.ops.object.bake(type=kind,pass_filter={'COLOR'},use_clear=False,margin=12)
        image.filepath_raw=str(QA/(rig.prefix().lower()+'-'+label+'-'+channel+'.png'));image.file_format='PNG';image.save();image.pack();images[channel]=image
    replacements={}
    for name,m in materials.items():
        old=m.node_tree.nodes['Principled BSDF']
        baked=surfaces.plain_material(name+' - Baked PBR',(.5,.5,.5),old.inputs['Roughness'].default_value)
        p=baked.node_tree.nodes['Principled BSDF'];nodes=baked.node_tree.nodes;links=baked.node_tree.links
        for field in ['Metallic','Specular IOR Level','Coat Weight','Coat Roughness','IOR','Transmission Weight']:p.inputs[field].default_value=old.inputs[field].default_value
        color=nodes.new('ShaderNodeTexImage');color.image=images['basecolor'];links.new(color.outputs['Color'],p.inputs['Base Color'])
        tex=nodes.new('ShaderNodeTexImage');tex.image=images['normal'];normal=nodes.new('ShaderNodeNormalMap');links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],p.inputs['Normal'])
        if roughness:
            tex=nodes.new('ShaderNodeTexImage');tex.image=images['roughness'];links.new(tex.outputs['Color'],p.inputs['Roughness'])
        replacements[name]=baked
    for o in objects:
        for i,m in enumerate(list(o.data.materials)):o.data.materials[i]=replacements[m.name]
    s.cycles.samples=32
    print(rig.prefix(),label,'dedicated 2048 atlas baked')


def save_candidate():
    rig.reset()
    bpy.ops.wm.save_as_mainfile(filepath=str(QA/(rig.prefix().lower()+'-candidate.blend')))


def export_candidate():
    rig.reset();bpy.ops.object.select_all(action='DESELECT')
    for o in rig.meshes()+[rig.obj('AvatarRig')]:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=rig.obj('AvatarRig')
    path=QA/(rig.prefix().lower()+'-candidate.glb')
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,use_active_scene=True,export_animations=False,export_skins=True,export_morph=True,export_morph_normal=True,export_extras=True,export_yup=True,export_cameras=False,export_lights=False)
    print('Candidate exported for runtime review:',path)
