"""Incremental Orbit/Coral source rework, invoked through the live Blender MCP."""
import json
import math
import shutil
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Vector
from build_avatar_fleet import Mesh, material
from articulated_hands import smooth
from refine_3dai_rigs import pose

ROOT=Path(__file__).resolve().parents[1]
REFERENCES={
    'orbit':'.context/attachments/DuooAb/lailasherself_purple_alien_from_atlanta_--ar_34_--sref_httpss_77004502-1809-4f55-895b-87757aedf540_1 (1).png',
    'coral':'.context/attachments/FMFGrL/lailasherself_add_a_body_--ar_11_--edit_httpss.mj.runuvJVp0ni_da9be720-1394-41cb-abb8-cb0c68dc0d38_0.png',
}


def name():return bpy.context.scene['referenceRework']
def qa():return ROOT/'.context/qa'/(name()+'-rework')
def rig():return bpy.context.scene.objects['AvatarRig']
def body():return bpy.context.scene.objects[name().title()+'SourceBody']


def reset(mode='Standing'):
    r=rig()
    if r.animation_data:
        r.animation_data.action=None
        for track in r.animation_data.nla_tracks:track.mute=True
    for o in bpy.context.scene.objects:
        if o.type=='MESH' and o.data.shape_keys:
            for key in o.data.shape_keys.key_blocks:
                if not key.name.startswith('corrective'):key.value=0
    config=json.loads((ROOT/'scripts/rig_3dai_landmarks.json').read_text()).get(name(),{})
    pose(r,name(),config,mode)
    for bone in r.pose.bones:
        if bone.name.startswith(('Thumb','Index','Middle','Ring')):bone.matrix_basis.identity()
    bpy.context.view_layer.update()


def prepare(character):
    assert character in REFERENCES
    assert bpy.context.scene.objects.get(character.title()+'SourceBody')
    s=bpy.context.scene;s['referenceRework']=character
    folder=ROOT/'.context/qa'/(character+'-rework');folder.mkdir(parents=True,exist_ok=True)
    if not (folder/'before.blend').exists():
        bpy.ops.wm.save_as_mainfile(filepath=str(folder/'before.blend'),copy=True)
        shutil.copy2(ROOT/'assets/3dai/refined'/(character+'.glb'),folder/'before.glb')
    for label in ['SilverVehicle','SeatAnchor']:
        o=s.objects.get(label)
        if o:bpy.data.objects.remove(o,do_unlink=True)
    reference=bpy.data.objects.new(character.title()+' supplied reference',None)
    reference.empty_display_type='IMAGE';reference.data=bpy.data.images.load(str(ROOT/REFERENCES[character]),check_existing=True);reference.data.pack()
    reference.empty_display_size=3.1;reference.location=(-2.4,.8,1.65);reference.rotation_euler=(math.pi/2,0,0)
    s.collection.objects.link(reference);reference['purpose']='Comparison only; never projected onto the model'
    s['referenceImage']=REFERENCES[character];s['reworkStatus']='in_progress'
    s.render.engine='CYCLES';s.cycles.samples=20
    s.render.resolution_x=1000;s.render.resolution_y=1100;s.render.resolution_percentage=100
    for o in s.objects:
        o.select_set(False)
        if o.type=='MESH':o.hide_set(False)
    reset();view()
    print('Prepared isolated working scene',character)


def view(close=False,side=False):
    s=bpy.context.scene;camera=s.camera
    center=Vector((.15,0,2.02) if close and name()=='orbit' else (0,0,2.05) if close else (0,0,1.6))
    camera.location=center+Vector((4 if side else 0,-8,.1 if close else .55))
    camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type='ORTHO';camera.data.ortho_scale=1.55 if close else 3.65
    for area in bpy.context.screen.areas if bpy.context.screen else []:
        if area.type=='VIEW_3D':
            area.spaces.active.shading.type='MATERIAL';area.spaces.active.overlay.show_overlays=False
            area.spaces.active.region_3d.view_perspective='CAMERA'


def render(label,close=False,side=False):
    view(close,side);bpy.context.scene.render.filepath=str(qa()/(label+'.png'))
    bpy.ops.render.render(write_still=True)


def orbit_hands():
    assert name()=='orbit'
    reset();r=rig();r.hide_set(False)
    for o in list(bpy.context.scene.objects):
        if o.get('assetRole')=='articulated-hand':bpy.data.objects.remove(o,do_unlink=True)
    skin=material('Orbit native clay hands','#b394c6',.78)
    for side in ['L','R']:
        hand=r.data.bones['Hand.'+side];origin=hand.head_local.copy()
        d=(hand.tail_local-origin).normalized();n=Vector((0,-1,0));n=(n-d*n.dot(d)).normalized()
        w=d.cross(n).normalized()
        if side=='R':w=-w
        length=.32
        def point(x,y,z=0):return origin+(w*x+d*y+n*z)*length
        paths={
            'Index':[(-.28,.40),(-.40,.60),(-.50,.76),(-.58,.91)],
            'Middle':[(0,.46),(.015,.72),(.025,.92),(.03,1.10)],
            'Ring':[(.27,.37),(.40,.56),(.52,.71),(.62,.85)],
            'Thumb':[(-.26,.17),(-.46,.23),(-.64,.31),(-.78,.40)],
        }
        chains={digit:[point(x,y,.012 if i==3 else 0) for i,(x,y) in enumerate(path)] for digit,path in paths.items()}
        bpy.context.view_layer.objects.active=r;r.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
        for digit,points in chains.items():
            for i in range(3):
                bone=r.data.edit_bones[f'{digit}{i+1}.{side}'];bone.head=points[i];bone.tail=points[i+1];bone.align_roll(n)
        bpy.ops.object.mode_set(mode='OBJECT');r.select_set(False)
        mesh=Mesh()
        def ellipsoid(center,scales):
            start=len(mesh.v);mesh.ellipsoid((0,0,0),scales,skin,n=24,rings=16)
            for i in range(start,len(mesh.v)):
                x,y,z=mesh.v[i];mesh.v[i]=tuple(center+w*x+d*y+n*z)
        ellipsoid(point(0,.20),(.38*length,.38*length,.21*length))
        ellipsoid(point(0,-.23),(.32*length,.66*length,.23*length))
        for digit,points in chains.items():
            radius=length*(.14 if digit=='Thumb' else .13)
            mesh.tube(points,[radius,radius*.93,radius*.91,radius],skin,n=20)
            for i,p in enumerate(points):
                radius_here=radius*(1.07 if i==3 else 1)
                mesh.ellipsoid(p,(radius_here,radius_here,radius_here),skin,n=20,rings=14)
        obj=mesh.object('OrbitNativeHand'+side);obj.select_set(True);bpy.context.view_layer.objects.active=obj
        obj.data.remesh_voxel_size=.006;bpy.ops.object.voxel_remesh()
        modifier=obj.modifiers.new('Rounded finger webbing','SMOOTH');modifier.factor=.5;modifier.iterations=4
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        for polygon in obj.data.polygons:polygon.use_smooth=True
        groups={b.name:obj.vertex_groups.new(name=b.name) for b in r.data.bones}
        for vertex in obj.data.vertices:
            p=vertex.co;candidates=[]
            for digit,points in chains.items():
                distance=min((p-a-(b-a)*max(0,min(1,(p-a).dot(b-a)/(b-a).length_squared))).length for a,b in zip(points,points[1:]))
                candidates.append((distance,digit))
            _,digit=min(candidates);points=chains[digit]
            axis=(points[-1]-points[0]).normalized();t=(p-points[0]).dot(axis)/(points[-1]-points[0]).length
            active=smooth(-.14,.18,t);first=1-smooth(.30,.56,t);third=smooth(.64,.9,t)
            weights={'Hand.'+side:1-active,f'{digit}1.{side}':active*first,f'{digit}2.{side}':active*(1-first-third),f'{digit}3.{side}':active*third}
            wrist=(p-origin).dot(d);forearm=(1-smooth(-.10,.015,wrist))*weights['Hand.'+side]
            weights['Hand.'+side]-=forearm;weights['Forearm.'+side]=forearm
            keep=sorted(((k,v) for k,v in weights.items() if v>1e-7),key=lambda x:-x[1])[:4];total=sum(v for _,v in keep)
            for k,v in keep:groups[k].add([vertex.index],v/total,'REPLACE')
        modifier=obj.modifiers.new('Native hand articulation','ARMATURE');modifier.object=r;obj.parent=r
        obj['assetRole']='articulated-hand';obj['handSide']=side;obj['fingerDigits']=['Thumb','Index','Middle','Ring'];obj['referenceAnatomy']='Four splayed rounded digits with broad fingertip pads'
        obj.select_set(False)
        for digit in chains:
            for i,limit in enumerate((.65,.75,.5)):r.data.bones[f'{digit}{i+1}.{side}']['fingerCurlRadians']=limit
    r['bodyRig']='Independent FK arms and four short padded reference digits per hand'
    reset();view();print('Built native Orbit palms and four rounded digits per hand')


def soften_socket_edges():
    reset();o=body();rest=np.array([v.co[:] for v in o.data.vertices]);points=rest.copy()
    edges=np.array([e.vertices[:] for e in o.data.edges]);degree=np.bincount(edges.ravel(),minlength=len(rest))
    face=bpy.context.scene.objects[name().title()+'EyesAndMouth'];mask=np.zeros(len(rest))
    for surface in face['eyelidSurfaces']:
        x,z,negative_y=surface['center'];rx,rz,ry=surface['radii'];y=-negative_y
        radial=np.hypot((rest[:,0]-x)/rx,(rest[:,2]-z)/rz)
        ring=np.clip((radial-.85)/.23,0,1)*np.clip((1.7-radial)/.42,0,1)*(rest[:,1]<y+ry*.2)
        mask=np.maximum(mask,ring)
    for _ in range(36):
        total=np.zeros(len(rest));np.add.at(total,edges[:,0],points[edges[:,1],1]);np.add.at(total,edges[:,1],points[edges[:,0],1])
        points[:,1]+=(total/np.maximum(1,degree)-points[:,1])*mask*.42
    delta=np.zeros_like(points);delta[:,1]=np.clip(points[:,1]-rest[:,1],-.022,.022)
    for key in o.data.shape_keys.key_blocks:
        values=np.array([p.co[:] for p in key.data])+delta;key.data.foreach_set('co',values.astype(np.float32).ravel())
    o.data.vertices.foreach_set('co',(rest+delta).astype(np.float32).ravel());o.data.update()
    o['referenceSocketCleanup']='Depth-only fairing; original silhouette, UVs and all target deltas preserved'
    for m in face.data.materials:
        p=m.node_tree.nodes.get('Principled BSDF')
        if any(part in m.name for part in ['sclera','pupil']):
            p.inputs['Roughness'].default_value=.16 if 'sclera' in m.name else .07
            p.inputs['Coat Weight'].default_value=.8;p.inputs['Coat Roughness'].default_value=.06
        elif 'lid' in m.name:
            p.inputs['Roughness'].default_value=.8;p.inputs['Coat Weight'].default_value=0
    print('Locally faired socket depth',int(np.count_nonzero(np.abs(delta[:,1])>1e-7)))


def bake_hand_grain():
    assert name()=='orbit';reset()
    hands=[o for o in bpy.context.scene.objects if o.get('assetRole')=='articulated-hand']
    bpy.ops.object.select_all(action='DESELECT')
    for o in hands:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=hands[0]
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.025)
    bpy.ops.object.mode_set(mode='OBJECT')
    mat=hands[0].data.materials[0];nodes=mat.node_tree.nodes;links=mat.node_tree.links;p=nodes['Principled BSDF']
    p.inputs['Roughness'].default_value=.8;p.inputs['Coat Weight'].default_value=0;p.inputs['Specular IOR Level'].default_value=.2
    noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=115;noise.inputs['Detail'].default_value=2.5
    bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.4;bump.inputs['Distance'].default_value=.009
    links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],p.inputs['Normal'])
    editable=mat.copy();editable.name='Orbit native hand clay - editable';editable.use_fake_user=True
    image=bpy.data.images.new('Orbit native hand grain normal',width=1024,height=1024);image.colorspace_settings.name='Non-Color'
    texture=nodes.new('ShaderNodeTexImage');texture.image=image;nodes.active=texture
    bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT',use_clear=False,margin=8)
    image.filepath_raw=str(ROOT/'assets/likeness-trials/orbit-hand-normal.png');image.file_format='PNG';image.save();image.pack()
    normal=nodes.new('ShaderNodeNormalMap');links.new(texture.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],p.inputs['Normal'])
    for m in body().data.materials:
        if 'wrist closure' in m.name:
            q=m.node_tree.nodes['Principled BSDF'];q.inputs['Base Color'].default_value=p.inputs['Base Color'].default_value;q.inputs['Roughness'].default_value=.8;q.inputs['Coat Weight'].default_value=0
    print('Baked clay hand grain, original body pigments preserved')


def orbit_eye_contour():
    assert name()=='orbit';reset();face=bpy.context.scene.objects['OrbitEyesAndMouth']
    surfaces=[(list(f['center']),list(f['radii'])) for f in face['eyelidSurfaces']]
    for o in [body(),face]:
        rest=np.array([v.co[:] for v in o.data.vertices]);mask_by_eye=[]
        for i,(center,radii) in enumerate(surfaces):
            x,z,negative_y=center;rx,rz,ry=radii;y=-negative_y
            radial=np.hypot((rest[:,0]-x)/rx,(rest[:,2]-z)/rz)
            mask=np.clip((1.8-radial)/.5,0,1)*(rest[:,1]<y+ry*1.1)
            if o==face:
                mask[:]=0
                for polygon in o.data.polygons:
                    if polygon.material_index<4:
                        for v in polygon.vertices:
                            if abs(rest[v,0]-x)<rx*1.1:mask[v]=1
            mask_by_eye.append(mask)
        for key in o.data.shape_keys.key_blocks:
            points=np.array([p.co[:] for p in key.data]);after=points.copy()
            for i,((center,radii),mask) in enumerate(zip(surfaces,mask_by_eye)):
                x,z,_=center;rx,rz,_=radii;angle=(-1 if i==0 else 1)*.22
                u=(points[:,0]-x)/rx;v=(points[:,2]-z)/rz
                after[:,0]+=((u*math.cos(angle)-v*math.sin(angle))*rx+x-points[:,0])*mask
                after[:,2]+=((u*math.sin(angle)+v*math.cos(angle))*rz+z-points[:,2])*mask
            key.data.foreach_set('co',after.astype(np.float32).ravel())
        values=np.array([p.co[:] for p in o.data.shape_keys.key_blocks['Basis'].data]);o.data.vertices.foreach_set('co',values.astype(np.float32).ravel());o.data.update()
    bpy.context.scene.view_settings.view_transform='Standard'
    print('Matched inward-sloping eyelid contour; closed/open targets transformed together')


def reference_pose():
    reset()
    if name()=='orbit':
        for b in rig().pose.bones:
            if b.name.startswith(('UpperArm','Forearm','Hand')):b.matrix_basis.identity()
    bpy.context.view_layer.update()


def fit_orbit_wrists():
    assert name()=='orbit';reset();o=body();rest=np.array([v.co[:] for v in o.data.vertices]);delta=np.zeros_like(rest)
    for side in ['L','R']:
        hand=rig().data.bones['Hand.'+side];origin=np.array(hand.head_local)
        d=(hand.tail_local-hand.head_local).normalized();n=Vector((0,-1,0));n=(n-d*n.dot(d)).normalized();w=d.cross(n).normalized()
        d,n,w=np.array(d),np.array(n),np.array(w);offset=rest-origin;along=offset@d;u=offset@w;v=offset@n
        owned=np.array([sum(g.weight for g in vertex.groups if o.vertex_groups[g.group].name in ['UpperArm.'+side,'Forearm.'+side,'Hand.'+side]) for vertex in o.data.vertices])
        influence=np.array([smooth(-.38,-.18,t) for t in along])*(along<-.17)*(owned>.9)
        factor=.4
        delta+=((u*(factor-1))[:,None]*w+(v*(factor-1))[:,None]*n)*influence[:,None]
    edges=np.array([e.vertices[:] for e in o.data.edges]);degree=np.bincount(edges.ravel(),minlength=len(rest))
    points=rest+delta;mask=np.clip(np.linalg.norm(delta,axis=1)/.02,0,1)
    for _ in range(45):
        total=np.zeros_like(points);np.add.at(total,edges[:,0],points[edges[:,1]]);np.add.at(total,edges[:,1],points[edges[:,0]])
        points+=(total/np.maximum(1,degree[:,None])-points)*mask[:,None]*.4
    delta=points-rest
    for key in o.data.shape_keys.key_blocks:
        points=np.array([p.co[:] for p in key.data])+delta;key.data.foreach_set('co',points.astype(np.float32).ravel())
    o.data.vertices.foreach_set('co',(rest+delta).astype(np.float32).ravel());o.data.update()
    o['nativeWristFit']='Old broad hand stubs tapered into oval reference wrists'
    bpy.context.scene.view_settings.exposure=-1.2
    print('Refitted old wrist stubs',int(np.count_nonzero(np.linalg.norm(delta,axis=1)>1e-6)))


def trim_orbit_old_palms():
    assert name()=='orbit';reset();o=body();bm=bmesh.new();bm.from_mesh(o.data)
    deform=bm.verts.layers.deform.active
    for side in ['L','R']:
        hand=rig().data.bones['Hand.'+side];origin=hand.head_local.copy();d=(hand.tail_local-origin).normalized()
        groups={o.vertex_groups[n+'.'+side].index for n in ['UpperArm','Forearm','Hand']}
        def owns(face):return sum(sum(v[deform].get(g,0) for g in groups) for v in face.verts)/len(face.verts)>.9
        local=[f for f in bm.faces if owns(f) and (f.calc_center_median()-origin).length<.6]
        edges={e for f in local for e in f.edges};verts={v for f in local for v in f.verts}
        bpy.context.view_layer.objects.active=o
        bpy.context.scene['wristCut']= -.18
        bmesh.ops.bisect_plane(bm,geom=[*local,*edges,*verts],dist=.000001,plane_co=origin-d*.18,plane_no=d)
        remove=[f for f in bm.faces if owns(f) and (f.calc_center_median()-origin).dot(d)>-.179999 and (f.calc_center_median()-origin).length<.7]
        deleted=set(remove);seam={e for f in remove for e in f.edges if any(n not in deleted for n in e.link_faces)}
        bmesh.ops.delete(bm,geom=remove,context='FACES_ONLY')
        caps=bmesh.ops.holes_fill(bm,edges=[e for e in seam if e.is_valid and e.is_boundary],sides=0)['faces']
        for f in caps:f.material_index=1 if side=='L' else 2;f.smooth=True
        if caps:bmesh.ops.triangulate(bm,faces=caps)
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3]);bm.to_mesh(o.data);bm.free();o.data.update()
    assert all(len(k.data)==len(o.data.vertices) for k in o.data.shape_keys.key_blocks)
    assert all(len(a.data)==len(o.data.vertices) for a in o.data.attributes if a.domain=='POINT')
    bpy.context.scene.view_settings.exposure=-1.2
    print('Removed complete old palm/cuff remnants, preserving all deform layers',len(o.data.vertices))


def meshes():
    return [o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig() for m in o.modifiers)]


def normalize_weights():
    for o in meshes():
        for v in o.data.vertices:
            keep=sorted(((g.group,g.weight) for g in v.groups if g.weight>1e-8),key=lambda pair:-pair[1])[:4]
            total=sum(w for _,w in keep);assert total>0,(o.name,v.index)
            if len(v.groups)<=4 and abs(total-1)<1e-7:continue
            for index in [g.group for g in v.groups]:o.vertex_groups[index].remove([v.index])
            for index,weight in keep:o.vertex_groups[index].add([v.index],weight/total,'REPLACE')


def evaluated(o):
    e=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh()
    values=np.array([v.co[:] for v in m.vertices]);e.to_mesh_clear();return values


def validate():
    from mathutils import Quaternion
    reset();report={'name':name(),'meshes':[],'armChecks':[],'digitChecks':[],'visualApproval':False,'physicalHardwareTested':False}
    for o in meshes():
        errors=[abs(sum(g.weight for g in v.groups)-1) for v in o.data.vertices]
        assert max(errors,default=0)<1e-5,(o.name,'weights')
        assert all(len(v.groups)<=4 for v in o.data.vertices),(o.name,'too many weights')
        bm=bmesh.new();bm.from_mesh(o.data);open_edges=sum(not e.is_manifold for e in bm.edges);bm.free()
        if o.get('assetRole') in ['articulated-hand','native-flipper']:assert open_edges==0,(o.name,'open native hand')
        assert np.isfinite(evaluated(o)).all(),o.name
        report['meshes'].append({'name':o.name,'vertices':len(o.data.vertices),'nonmanifoldEdges':open_edges,'weightError':max(errors,default=0)})
    for side,other in [('L','R'),('R','L')]:
        reset();before={o.name:evaluated(o) for o in meshes()}
        for label,angle in [('UpperArm',.65),('Forearm',.9)]:rig().pose.bones[label+'.'+side].rotation_quaternion=Quaternion((1,0,0),angle)
        bpy.context.view_layer.update();worst=0
        for o in meshes():
            after=evaluated(o)
            pinned=np.array([any(o.vertex_groups[g.group].name in ['UpperArm.'+other,'Forearm.'+other,'Hand.'+other,'Head'] and g.weight>.999 for g in v.groups) for v in o.data.vertices])
            if pinned.any():worst=max(worst,float(np.linalg.norm(after[pinned]-before[o.name][pinned],axis=1).max()))
        assert worst<.01,('opposite arm/head drift',side,worst)
        report['armChecks'].append({'side':side,'otherSideAndHeadMaxDrift':worst})
    for o in meshes():
        if o.get('assetRole')!='articulated-hand':continue
        side=o['handSide']
        for digit in o['fingerDigits']:
            reset();before=evaluated(o)
            for i in range(3):
                b=rig().pose.bones[f'{digit}{i+1}.{side}'];b.rotation_quaternion=Quaternion((1,0,0),b.bone.get('fingerCurlRadians',.5))
            bpy.context.view_layer.update();movement=float(np.linalg.norm(evaluated(o)-before,axis=1).max())
            assert movement>.025,(digit,side,'no motion')
            report['digitChecks'].append({'side':side,'digit':digit,'movement':movement})
    reset();(qa()/'validation.json').write_text(json.dumps(report,indent=2));print(report)
    return report


def export_review():
    from post_skin_correctives import export_space
    reset();o=body();samples=o['correctiveSamples'];drivers=[]
    for mesh in meshes():
        if mesh.data.shape_keys:
            keys=mesh.data.shape_keys
            if keys.animation_data:
                for driver in keys.animation_data.drivers:drivers.append((driver,driver.mute));driver.mute=True
            for key in keys.key_blocks:key.value=0
    out=ROOT/'assets/likeness-trials'/(name()+'-body-rig.glb')
    try:
        export_space(o,samples,True)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in [rig(),*meshes()]:obj.hide_set(False);obj.select_set(True)
        bpy.context.view_layer.objects.active=rig()
        bpy.ops.export_scene.gltf(filepath=str(out),export_format='GLB',use_selection=True,use_active_scene=True,
            export_animations=True,export_animation_mode='ACTIONS',export_nla_strips=True,export_skins=True,
            export_morph=True,export_morph_normal=True,export_extras=True,export_attributes=True,
            export_yup=True,export_cameras=False,export_lights=False)
    finally:
        export_space(o,samples,False)
        for driver,mute in drivers:driver.mute=mute
    reset();view();bpy.context.scene['reworkStatus']='exported_pending_runtime_checks'
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/likeness-trials'/(name()+'-body-rig.blend')))
    rig().hide_set(True)
    print('Saved',out)
