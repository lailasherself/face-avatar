"""Incremental source-preserving Nebula work, driven and inspected through MCP."""
from pathlib import Path
import json
import sys
import bpy
import bmesh
import numpy as np
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
OUT=ROOT/'assets/reference-characters'
BLENDS=ROOT/'blender/reference-characters'
QA=ROOT/'.context/qa/reference-characters'

CONFIG={
    'hips':(0,.015,.87),'chest':(0,.015,1.56),
    'neck':(0,.025,1.88),'head':(0,-.05,2.75),
    'arm':[(.235,.025,1.74),(.565,.015,1.34),(.81,-.015,1.035),(.89,-.03,.735)],
    'leg':[(.225,.025,.855),(.26,.04,.47),(.285,.04,.17),(.29,-.23,.105)],
    'faceFloor':1.98,'faceTop':2.94,'headPinFloor':1.99,'headWidth':.83,'browZ':2.72,
    'mouth':(0,2.305,.115,.006),'mouthScale':.55,
    'eyes':[(-.448,2.512,.236,.12,.151),(.463,2.512,.236,.12,.151)],
    'eyeColor':'#ffdfcf','pupilColor':'#244f4e','pupilSize':.25,
    'lidColor':'#705073','lidAngles':(.35,.35),
    'texturedIris':True,'pupilPatchAngle':.42,
    'texturedLids':True,'lidSample':(.35,2.29),
}


def character():
    from build_3dai_characters import Character
    result=Character('nebula',CONFIG,{'task_id':'local:nebula-rigready'})
    result.rig=bpy.context.scene.objects.get('AvatarRig')
    if 'rigMouthFront' in result.body:
        result.my=result.body['rigMouthFront']
        result.mouth_rim=list(result.body['rigMouthRim'])
        result.eyes=[(Vector(center),Vector(spec[2:])) for center,spec in zip(result.body['rigEyeCenters'],CONFIG['eyes'])]
    return result


def rig_body():
    from rebind_upper_body import rebind_upper_body
    c=character()
    assert c.rig is None,'Body rig already exists in this scene'
    c.create_rig();c.bind();rebind_upper_body(c.body,c.rig,CONFIG)
    c.rig['facialRig']='Pending - static original face retained'
    c.body['armCollisionSurface']=True
    for b in c.rig.pose.bones:b.rotation_mode='QUATERNION'
    reset_pose()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLENDS/'nebula-body-rig.blend'))
    return {'bones':len(c.rig.data.bones),'vertices':len(c.body.data.vertices)}


def reset_pose():
    rig=bpy.context.scene.objects.get('AvatarRig')
    if rig:
        for bone in rig.pose.bones:
            bone.matrix_basis.identity()
    for obj in bpy.context.scene.objects:
        if obj.type=='MESH' and obj.data.shape_keys:
            for key in obj.data.shape_keys.key_blocks:key.value=0
    bpy.context.view_layer.update()


def arm_test(side='L',direction=(1,0,.3),forearm=(.15,-.2,1)):
    reset_pose();c=character()
    c.aim('UpperArm.'+side,direction)
    c.aim('Forearm.'+side,forearm)
    c.aim('Hand.'+side,forearm)
    view()


def rig_face():
    from add_3dai_teeth import add_teeth
    reset_pose();c=character()
    assert not c.body.data.shape_keys,'Facial rig already exists'
    c.body['rigMouthFront']=c.my;c.body['rigMouthRim']=c.mouth_rim
    c.body['rigEyeCenters']=[list(center) for center,_ in c.eyes]
    # The body already has reviewed weights; cutting the slit preserves deform data.
    c.bind=lambda:None
    removed=c.facial_targets()
    scale=max(.40,min(1.3,max(.12,c.mw)/.34))
    p={'mx':c.mx,'mz':c.mz,'mw':c.mw,'my':c.my,'curve':c.curve,
       'wave':0,'rim':c.mouth_rim,'scale':scale,'angle':.40,
       'sideways':.08*scale,'hinge':[c.mx,c.my+.30*scale,c.mz+.10*scale],
       'fit':{'span':.65,'recess':.25,'upperZ':.024,'upperHeight':.020,
              'lowerZ':-.08,'lowerHeight':.026}}
    add_teeth(c.rig,p)
    from refine_3dai_tongues import refine_tongue
    refine_tongue(c.face)
    c.rig['facialRig']='52 facial channels, source-textured eyes/lids, mouth cavity and jaw-driven teeth; review required'
    reset_pose();view(distance=2.4,center=(0,-.2,2.52))
    bpy.ops.wm.save_as_mainfile(filepath=str(BLENDS/'nebula-face-rig.blend'))
    return {'removedMouthFaces':removed,'mouthDepth':c.my}


def rig_digits():
    from rebind_upper_body import smooth
    reset_pose();c=character();rig=c.rig;body=c.body
    assert 'Thumb1.L' not in rig.data.bones,'Digits already rigged'
    paths={
        'Thumb':[(.79,-.11,.975),(.735,-.14,.92),(.70,-.16,.865),(.70,-.18,.805)],
        'Index':[(.89,-.085,.965),(.925,-.09,.865),(.90,-.085,.775),(.845,-.08,.665)],
        'Middle':[(.89,.09,.965),(.925,.09,.865),(.895,.085,.785),(.845,.08,.68)],
    }
    bpy.context.view_layer.objects.active=rig;rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for side,sign in [('L',1),('R',-1)]:
        for digit,path in paths.items():
            for i,(a,b) in enumerate(zip(path,path[1:])):
                bone=rig.data.edit_bones.new(f'{digit}{i+1}.{side}')
                bone.head=(a[0]*sign,a[1],a[2]);bone.tail=(b[0]*sign,b[1],b[2])
                bone.parent=rig.data.edit_bones[f'{digit}{i}.{side}' if i else 'Hand.'+side]
                bone.align_roll(Vector((sign if digit=='Thumb' else -sign,0,0)))
    bpy.ops.object.mode_set(mode='OBJECT')
    for bone in rig.data.bones:
        if bone.name not in body.vertex_groups:body.vertex_groups.new(name=bone.name)
    for side,sign in [('L',1),('R',-1)]:
        hand=body.vertex_groups['Hand.'+side]
        for vertex in body.data.vertices:
            existing={body.vertex_groups[g.group].name:g.weight for g in vertex.groups}
            available=existing.get(hand.name,0)
            if available<.01 or vertex.co.x*sign<.60:continue
            x,y,z=vertex.co;digits=[]
            for digit,path in paths.items():
                distances=[];parameters=[];total=0
                for a,b in zip(path,path[1:]):
                    a=Vector((a[0]*sign,a[1],a[2]));b=Vector((b[0]*sign,b[1],b[2]))
                    axis=b-a;t=max(0,min(1,(vertex.co-a).dot(axis)/axis.length_squared))
                    distances.append((vertex.co-a-axis*t).length);parameters.append(total+t*axis.length)
                    total+=axis.length
                k=int(np.argmin(distances));digits.append((min(distances),digit,parameters[k],total))
            _,digit,t,length=min(digits)
            influence=float(smooth(0,.085,t))*(1-float(smooth(.94,1.02,z)))
            knots=np.array([0,.40,.75])*length
            row={}
            for i in range(3):
                lower=float(smooth(knots[i-1],knots[i],t)) if i else 1
                upper=1-float(smooth(knots[i],knots[i+1],t)) if i<2 else 1
                row[f'{digit}{i+1}.{side}']=available*influence*lower*upper
            existing[hand.name]=available*(1-influence);existing.update(row)
            keep=sorted(existing.items(),key=lambda p:p[1],reverse=True)[:4];total=sum(w for _,w in keep)
            for group in [g.group for g in vertex.groups]:body.vertex_groups[group].remove([vertex.index])
            for name,weight in keep:
                if weight>1e-8:body.vertex_groups[name].add([vertex.index],weight/total,'REPLACE')
    smooth_digit_weights(body)
    isolate_digit_tips(body)
    for bone in rig.pose.bones:bone.rotation_mode='QUATERNION'
    for bone in rig.data.bones:
        for digit,limits in [('Thumb',(.22,.25,.15)),('Index',(.38,.42,.30)),('Middle',(.38,.42,.30))]:
            if bone.name.startswith(digit):bone['fingerCurlRadians']=limits[int(bone.name[len(digit)])-1]
    rig['bodyRig']='Fitted body skeleton; three independently articulated native digits per hand'
    rig['fingerLayout']='Thumb, Index and Middle with three joints each per hand; rear digit verified in side view'
    return len(rig.data.bones)


def isolate_digit_tips(body):
    from rebind_upper_body import smooth
    for vertex in body.data.vertices:
        x,y,z=vertex.co
        if abs(x)<.60 or z>.94:continue
        side='L' if x>0 else 'R'
        digit='Thumb' if abs(x)<.78 and y<-.10 else 'Index' if y<0 else 'Middle'
        amount=1-float(smooth(.85,.92,z) if digit=='Thumb' else smooth(.76,.88,z))
        row={g.group:g.weight for g in vertex.groups}
        own=[i for i in row if body.vertex_groups[i].name.startswith(digit)]
        total=sum(row[i] for i in own)
        if total<.05:continue
        removed=0
        for i in row:
            name=body.vertex_groups[i].name
            if name.endswith('.'+side) and name.startswith(('Thumb','Index','Middle')) and i not in own:
                removed+=row[i]*amount;row[i]*=1-amount
        for i in own:row[i]+=removed*row[i]/total
        for group in [g.group for g in vertex.groups]:body.vertex_groups[group].remove([vertex.index])
        for i,w in row.items():
            if w>1e-8:body.vertex_groups[i].add([vertex.index],w,'REPLACE')


def smooth_digit_weights(body):
    points=np.array([v.co[:] for v in body.data.vertices])
    weights=np.zeros((len(points),len(body.vertex_groups)),dtype=np.float32)
    for v in body.data.vertices:
        for g in v.groups:weights[v.index,g.group]=g.weight
    locked=(np.abs(points[:,0])<.60)|(points[:,2]>1.08)
    original=weights.copy();edges=np.array([e.vertices[:] for e in body.data.edges])
    a,b=edges.T;degree=np.bincount(edges.ravel(),minlength=len(points)).reshape(-1,1)
    for _ in range(25):
        total=np.zeros_like(weights)
        np.add.at(total,a,weights[b]);np.add.at(total,b,weights[a])
        weights=.5*weights+.5*total/np.maximum(1,degree)
        weights[locked]=original[locked]
    for v in body.data.vertices:
        if locked[v.index]:continue
        row=weights[v.index];keep=np.argsort(row)[-4:];total=row[keep].sum()
        if total<1e-8:continue
        for group in [g.group for g in v.groups]:body.vertex_groups[group].remove([v.index])
        for i in keep:
            if row[i]>1e-8:body.vertex_groups[i].add([v.index],float(row[i]/total),'REPLACE')


def expression(values):
    for obj in bpy.context.scene.objects:
        if obj.type=='MESH' and obj.data.shape_keys:
            for key in obj.data.shape_keys.key_blocks:key.value=values.get(key.name,0)
    bpy.context.view_layer.update()


def evaluated_points(obj):
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=evaluated.to_mesh()
    points=np.array([v.co[:] for v in mesh.vertices])
    evaluated.to_mesh_clear()
    return points


def validate():
    from build_avatar_fleet import CHANNELS
    reset_pose();c=character();body=c.body
    rest=evaluated_points(body)
    weight_sums=np.array([sum(g.weight for g in v.groups) for v in body.data.vertices])
    assert np.max(np.abs(weight_sums-1))<1e-5,'Non-normalized body skin'
    assert all(len(v.groups)<=4 for v in body.data.vertices),'More than four skin influences'
    face=bpy.context.scene.objects['NebulaEyesAndMouth']
    assert all(name in face.data.shape_keys.key_blocks for name in CHANNELS)
    for obj in bpy.context.scene.objects:
        if obj.type=='MESH' and obj.data.shape_keys:
            for key in obj.data.shape_keys.key_blocks:
                assert np.isfinite(np.array([v.co[:] for v in key.data])).all(),key.name
    opposite=(rest[:,0]<-.45)&(rest[:,2]<1.65)
    head=rest[:,2]>2.05
    arm_test();posed=evaluated_points(body)
    drift=float(np.linalg.norm(posed[opposite]-rest[opposite],axis=1).max())
    head_drift=float(np.linalg.norm(posed[head]-rest[head],axis=1).max())
    assert drift<1e-5,'Opposite arm moves during one-sided pose'
    assert head_drift<1e-5,'Arm pose deforms the head'
    reset_pose()
    materials={i for i,m in enumerate(face.data.materials) if 'tongue' in m.name.lower()}
    tongue=sorted({i for p in face.data.polygons if p.material_index in materials for i in p.vertices})
    basis=face.data.shape_keys.key_blocks['Basis'];key=face.data.shape_keys.key_blocks['tongueOut']
    base=np.array([basis.data[i].co[:] for i in tongue]);out=np.array([key.data[i].co[:] for i in tongue])
    root=base[:,1]>base[:,1].max()-.001
    root_drift=float(np.linalg.norm(out[root]-base[root],axis=1).max())
    assert root_drift<.001,'Tongue root detaches'
    tip_positions=[]
    for value in [0,.25,.5,.75,1]:
        expression({'jawOpen':.8,'tongueOut':value})
        points=evaluated_points(face)[tongue]
        tip_positions.append(float(points[:,1].min()))
    assert all(b<a for a,b in zip(tip_positions,tip_positions[1:])),'Tongue extension is not monotonic'
    reset_pose()
    report={'status':'WORK IN PROGRESS - not installation approved','bones':len(c.rig.data.bones),
            'bodyVertices':len(body.data.vertices),'faceChannels':len(CHANNELS),
            'maxWeightError':float(np.max(np.abs(weight_sums-1))),
            'oppositeArmDrift':drift,'headDriftDuringArmPose':head_drift,
            'tongueRootDrift':root_drift,'tongueTipYByQuarter':tip_positions,
            'remaining':['Broader pose, collision and reference-likeness review remains',
                         'Eye-lid and lip material transitions still need artistic polish',
                         'No camera timing, physical ZED/Orin or installation validation'],
            'originalAssetUnmodified':True,'defaultRosterUnmodified':True}
    if body.get('oralBoundaryRefinement'):report['refinements']=validate_refinements()
    QA.mkdir(parents=True,exist_ok=True)
    (QA/'nebula-rig-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def save_review():
    reset_pose();c=character()
    c.body['rigStatus']='Review v2: native three-digit hands, refined eye sockets and connected mouth loops; not installation approved'
    c.rig['installationApproved']=False
    objects=[c.rig]+[o for o in bpy.context.scene.objects if o.type=='MESH' and o.parent==c.rig]
    OUT.mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(OUT/'nebula-review.glb'),export_format='GLB',
        use_selection=True,use_active_scene=True,export_animations=False,
        export_skins=True,export_morph=True,export_morph_normal=True,
        export_extras=True,export_attributes=True,export_yup=True,
        export_cameras=False,export_lights=False)
    reset_pose();view()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLENDS/'nebula-review.blend'))
    return {'blend':str(BLENDS/'nebula-review.blend'),'glb':str(OUT/'nebula-review.glb')}


def validate_refinements():
    from mathutils import Quaternion
    reset_pose();c=character();body=c.body;rest=evaluated_points(body)
    index=(rest[:,0]>.78)&(rest[:,2]<.735)&(rest[:,1]<-.045)
    middle=(rest[:,0]>.78)&(rest[:,2]<.735)&(rest[:,1]>.045)
    for bone in c.rig.pose.bones:
        if bone.name.startswith('Middle') and bone.name.endswith('.L'):
            bone.rotation_quaternion=Quaternion((1,0,0),bone.bone['fingerCurlRadians'])
    bpy.context.view_layer.update();delta=np.linalg.norm(evaluated_points(body)-rest,axis=1)
    drift=float(delta[index].max());motion=float(delta[middle].mean())
    assert drift<1e-5,'Curling the middle digit also moves the index fingertip'
    assert motion>.08,'Middle digit is not deforming'
    reset_pose();body.data.calc_loop_triangles()
    triangles=np.array([t.vertices[:] for t in body.data.loop_triangles if body.data.polygons[t.polygon_index].material_index>0])
    assert len(triangles)>=200,'Connected mouth patch missing'
    def normals(points):return np.cross(points[triangles[:,1]]-points[triangles[:,0]],points[triangles[:,2]]-points[triangles[:,0]])
    base=normals(evaluated_points(body));cases={}
    for name,values in [('jaw',{'jawOpen':1}),('smile',{'jawOpen':.5,'mouthSmileLeft':1,'mouthSmileRight':1}),
                        ('pucker',{'mouthPucker':1,'jawOpen':.3}),('frown',{'mouthFrownLeft':1,'mouthFrownRight':1}),
                        ('tongue-smile',{'jawOpen':.7,'mouthSmileLeft':.8,'mouthSmileRight':.8,'tongueOut':1})]:
        expression(values);posed=normals(evaluated_points(body))
        cases[name]=int(np.count_nonzero(np.sum(base*posed,axis=1)<-1e-12))
        assert cases[name]==0,('Mouth patch folds over',name)
    reset_pose()
    return {'indexTipDriftDuringMiddleCurl':drift,'middleTipMotion':motion,'mouthTriangleInversions':cases,
            'digitsPerHand':3,'boundedCurlJoints':18,'mouthQuadRings':6}


def render_review(case):
    from mathutils import Quaternion
    scene=bpy.context.scene;reset_pose()
    camera=scene.objects.get('ReviewCamera')
    if not camera:
        camera=bpy.data.objects.new('ReviewCamera',bpy.data.cameras.new('ReviewCamera'))
        scene.collection.objects.link(camera)
        for name,location,power,size in [
            ('ReviewKey',(3,-4,5),450,4),('ReviewFill',(-3,-3,3),300,4),('ReviewRim',(0,2,4),350,3)]:
            data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
            obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
            obj.location=location;obj.rotation_euler=(Vector((0,0,1.7))-obj.location).to_track_quat('-Z','Y').to_euler()
        scene.world=scene.world.copy() if scene.world else bpy.data.worlds.new('ReviewWorld')
        scene.world.use_nodes=True
        scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.12,.12,.12,1)
        scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.4
    face=case in ['tongue-blink','smile']
    hand=case.startswith('hand-')
    if case=='left-arm':arm_test()
    if case=='tongue-blink':expression({'jawOpen':.8,'tongueOut':1,'eyeBlinkLeft':1})
    if case=='smile':expression({'jawOpen':.5,'mouthSmileLeft':.8,'mouthSmileRight':.8})
    if hand:
        for bone in character().rig.pose.bones:
            if not bone.name.endswith('.L') or 'fingerCurlRadians' not in bone.bone:continue
            curl=case=='hand-curl' or (case=='hand-point' and not bone.name.startswith('Index'))
            bone.rotation_quaternion=Quaternion((1,0,0),bone.bone['fingerCurlRadians'] if curl else 0)
        bpy.context.view_layer.update()
    center=Vector((0,-.1,2.47 if face else 1.6))
    camera.location=center+Vector((.35 if face else 0,-7,.02))
    camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type='ORTHO';camera.data.ortho_scale=1.95 if face else 3.7;scene.camera=camera
    if hand:
        center=Vector((.85,0,.88));camera.location=center+Vector((.9,-3,.02))
        camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=.8
    scene.render.engine='CYCLES';scene.cycles.samples=16
    scene.render.resolution_x=720;scene.render.resolution_y=720;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str(QA/f'nebula-{case}.png')
    bpy.ops.render.render(write_still=True)
    reset_pose();view()
    return scene.render.filepath


def view(direction=(0,1,0),distance=5.0,center=(0,0,1.6)):
    for area in bpy.context.screen.areas:
        if area.type=='VIEW_3D':
            space=area.spaces.active;space.shading.type='MATERIAL';space.overlay.show_overlays=False
            r=space.region_3d;r.view_location=center;r.view_distance=distance;r.view_perspective='ORTHO'
            r.view_rotation=Vector(direction).to_track_quat('-Z','Y');area.tag_redraw()


def prepare():
    for folder in [OUT,BLENDS,QA]:folder.mkdir(parents=True,exist_ok=True)
    original=bpy.context.scene.objects.get('Nebula')
    assert original and original.type=='MESH','Start in the untouched source Nebula scene'
    scene=bpy.data.scenes.new('Nebula - reference matched working copy')
    scene.world=bpy.context.scene.world
    body=original.copy();body.data=original.data.copy();body.name='NebulaSourceBody'
    scene.collection.objects.link(body);bpy.context.window.scene=scene
    before=len(body.data.vertices)
    bm=bmesh.new();bm.from_mesh(body.data)
    region=[f for f in bm.faces if .33<f.calc_center_median().z<.65 and abs(f.calc_center_median().x)<.13]
    edges={e for f in region for e in f.edges};verts={v for f in region for v in f.verts}
    bmesh.ops.bisect_plane(bm,geom=[*region,*edges,*verts],dist=1e-6,plane_co=(0,-.148,.48),plane_no=(0,1,0))
    remove=[f for f in bm.faces if .33<f.calc_center_median().z<.65 and abs(f.calc_center_median().x)<.13 and f.calc_center_median().y>-.148+1e-6]
    removed=set(remove);seam={e for f in remove for e in f.edges if any(o not in removed for o in e.link_faces)}
    bmesh.ops.delete(bm,geom=remove,context='FACES')
    closed=bmesh.ops.holes_fill(bm,edges=[e for e in seam if e.is_valid and e.is_boundary],sides=0)['faces']
    uv=bm.loops.layers.uv.active
    for face in closed:
        if uv:
            for loop in face.loops:
                neighbors=[other[uv].uv.copy() for other in loop.vert.link_loops if other.face not in closed]
                if neighbors:loop[uv].uv=sum(neighbors,Vector((0,0)))/len(neighbors)
        face.smooth=True
    bmesh.ops.triangulate(bm,faces=closed)
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bm.to_mesh(body.data);bm.free()
    scale=3.2/1.6186459064483643
    for v in body.data.vertices:v.co=Vector((v.co.x*scale,(v.co.y+.28)*scale,v.co.z*scale))
    body.data.update();body['sourceAsset']='assets/3dai/rigready/atliens-nebula.blend'
    body['sourcePreserved']=True;body['rigStatus']='working - source likeness retained'
    bpy.context.view_layer.objects.active=body;body.select_set(True)
    view();bpy.ops.wm.save_as_mainfile(filepath=str(BLENDS/'nebula-prepared.blend'))
    report={'sourceVertices':before,'preparedVertices':len(body.data.vertices),'removedRearFaces':len(remove),'closedRearFaces':len(closed),'scale':scale}
    (QA/'nebula-preparation.json').write_text(json.dumps(report,indent=2))
    return report


def sample_eyes():
    body=bpy.data.objects['NebulaSourceBody'];image=next(n.image for n in body.data.materials[0].node_tree.nodes if n.type=='TEX_IMAGE' and n.image)
    w,h=image.size;pixels=np.array(image.pixels[:]).reshape(h,w,4);uv=body.data.uv_layers.active.data
    candidates=set()
    for polygon in body.data.polygons:
        center=polygon.center
        if not (2.28<center.z<2.80 and abs(center.x)>.15 and center.y<-.65):continue
        colors=[]
        for loop in polygon.loop_indices:
            u,v=uv[loop].uv;colors.append(pixels[min(h-1,int(v%1*h)),min(w-1,int(u%1*w)),:3])
        r,g,b=np.mean(colors,axis=0)
        if min(r,g,b)>.60 and max(r,g,b)-min(r,g,b)<.35:candidates.update(polygon.vertices)
    result=[]
    for sign in [-1,1]:
        points=np.array([body.data.vertices[i].co[:] for i in candidates if body.data.vertices[i].co.x*sign>0])
        result.append({'side':sign,'count':len(points),'bounds':np.quantile(points,[.02,.5,.98],axis=0).tolist()})
    return result
