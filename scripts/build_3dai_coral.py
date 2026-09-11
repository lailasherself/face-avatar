"""Rig the selected Coral source; keep originals and the procedural fleet intact."""
import json
import math
from pathlib import Path
import sys

import bpy
import bmesh
from mathutils import Vector, Quaternion

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_avatar_fleet import CHANNELS, Mesh, material, export, clamp

OUT = ROOT / 'assets/3dai/rigged'
OUT.mkdir(parents=True, exist_ok=True)
SOURCE_ID = 'f852429a-8c8c-439a-b073-02fefb4e9421'
EYES = [(-.32, -.467, 2.30), (.32, -.467, 2.30)]
EYE_RADII = (.195, .190, .200)
MOUTH_Z = 1.79


def smoothstep(a, b, x):
    t = clamp((x-a)/(b-a))
    return t*t*(3-2*t)


def create_rig():
    data = bpy.data.armatures.new('Coral body skeleton')
    rig = bpy.data.objects.new('AvatarRig', data)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    def bone(name, start, end, parent=None):
        b = data.edit_bones.new(name)
        b.head, b.tail = start, end
        if parent:
            b.parent = data.edit_bones[parent]
    bone('Root', (0,0,0), (0,0,.25))
    bone('Hips', (0,.28,.80), (0,.23,1.00), 'Root')
    bone('Spine', (0,.23,1.00), (0,.22,1.25), 'Hips')
    bone('Chest', (0,.22,1.25), (0,.20,1.48), 'Spine')
    bone('Neck', (0,.20,1.48), (0,.13,1.67), 'Chest')
    bone('Head', (0,.13,1.67), (0,.13,2.60), 'Neck')
    for side, s in [('L',1),('R',-1)]:
        bone('UpperArm.'+side, (s*.34,.23,1.45), (s*.47,.25,1.04), 'Chest')
        bone('Forearm.'+side, (s*.47,.25,1.04), (s*.48,.20,.69), 'UpperArm.'+side)
        bone('Hand.'+side, (s*.48,.20,.69), (s*.45,.13,.50), 'Forearm.'+side)
        bone('Thigh.'+side, (s*.21,.32,.81), (s*.22,.32,.44), 'Hips')
        bone('Shin.'+side, (s*.22,.32,.44), (s*.22,.30,.14), 'Thigh.'+side)
        bone('Foot.'+side, (s*.22,.30,.14), (s*.22,.10,.08), 'Shin.'+side)
    bpy.ops.object.mode_set(mode='OBJECT')
    rig.show_in_front = True
    rig['sourceTaskId'] = SOURCE_ID
    rig['reference'] = 'nkmqsW'
    rig['bodyRig'] = '18 deform bones; FK limbs; source has mitten hands'
    rig['facialRig'] = 'ARKit morphs, separate sclerae/pupils, spherical lids and oral cavity'
    rig.select_set(False)
    return rig


def body_weights(p):
    x,y,z = p
    side = 'L' if x >= 0 else 'R'
    if z >= 1.63:
        return {'Head': 1}
    if z > 1.45 and (y < -.10 or abs(x) > .57):
        return {'Head': 1}
    arm_inner=.37-.07*smoothstep(1.18,1.45,z)
    arm = smoothstep(arm_inner,.425,abs(x)) * (1-smoothstep(1.42,1.61,z)) * smoothstep(.44,.52,z)
    if arm > .001:
        elbow = 1-smoothstep(.96,1.13,z)
        hand = 1-smoothstep(.63,.76,z)
        w = {'UpperArm.'+side: arm*(1-elbow),
             'Forearm.'+side: arm*elbow*(1-hand), 'Hand.'+side: arm*elbow*hand}
    else:
        w = {}
    torso = 1-arm
    if z < .82:
        knee = 1-smoothstep(.36,.52,z)
        foot = 1-smoothstep(.13,.23,z)
        hips = smoothstep(.68,.82,z)
        w.update({'Hips':torso*hips, 'Thigh.'+side:torso*(1-hips)*(1-knee),
                  'Shin.'+side:torso*(1-hips)*knee*(1-foot),
                  'Foot.'+side:torso*(1-hips)*knee*foot})
    else:
        levels = [(.84,'Hips'),(1.05,'Spine'),(1.32,'Chest'),(1.51,'Neck'),(1.65,'Head')]
        if z <= levels[0][0]:
            w['Hips'] = torso
        else:
            for (a,na),(b,nb) in zip(levels,levels[1:]):
                if z <= b:
                    t = smoothstep(a,b,z)
                    w[na] = torso*(1-t)
                    w[nb] = torso*t
                    break
    return {n:v for n,v in w.items() if v > 1e-8}


def bind(obj, rig):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True);rig.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    missing=[v for v in obj.data.vertices if sum(g.weight for g in v.groups)<1e-8]
    print('HEAT_BIND',len(obj.data.vertices),'unweighted',len(missing),flush=True)
    assert len(missing)<len(obj.data.vertices)*.05, 'Heat binding failed on a substantial region'
    for v in obj.data.vertices:
        weights=sorted([(g.group,g.weight) for g in v.groups],key=lambda item:item[1],reverse=True)[:4]
        if v.co.z>=1.63 or (v.co.z>1.45 and v.co.y<-.10):
            weights=[(obj.vertex_groups['Head'].index,1)]
        total=sum(w for _,w in weights)
        if total>1e-8:
            for group in [g.group for g in v.groups]:obj.vertex_groups[group].remove([v.index])
            for group,w in weights:obj.vertex_groups[group].add([v.index],w/total,'REPLACE')
        else:
            weights=body_weights(v.co)
            total=sum(weights.values())
            for name,w in weights.items():obj.vertex_groups[name].add([v.index],w/total,'REPLACE')


def skin_delta(p, name, part='skin'):
    x,y,z = p
    d = Vector((0,0,0))
    front = 1-smoothstep(-.34,-.08,y)
    face = smoothstep(1.40,1.62,z)*front
    eye_mask=0
    if part=='skin' and y<-.38:
        eye_mask=max(1-smoothstep(1,1.6,((x-ex)/.21)**2+((z-ez)/.225)**2) for ex,_,ez in EYES)
        face*=1-eye_mask
    if face == 0:
        return d
    side = smoothstep(-.09,.09,x) if name.endswith('Left') else 1-smoothstep(-.09,.09,x) if name.endswith('Right') else 1
    mouth = math.exp(-((x/.42)**6+((z-MOUTH_Z)/.22)**4))*face
    lower = 1-smoothstep(MOUTH_Z-.025,MOUTH_Z+.014,z)
    upper = smoothstep(MOUTH_Z-.005,MOUTH_Z+.05,z)
    corner = clamp(abs(x)/.34)
    # Jaw rotates the chin and lower lip around a hinge behind the mouth.
    curve=MOUTH_Z-.022*(x/.34)**2
    transition=.001+.12*smoothstep(.32,.49,abs(x))+.08*smoothstep(-.40,-.15,y)
    jaw = (1-smoothstep(curve-transition,curve+transition,z))*face
    if part in ['cavity','tongue']:
        mouth = 1
    if name == 'jawOpen':
        q = Quaternion((1,0,0),.37)
        hinge = Vector((0,-.02,1.91))
        d = ((q@(Vector(p)-hinge)+hinge)-Vector(p))*jaw
    elif name == 'mouthClose':
        d = -skin_delta(p,'jawOpen',part)
    elif name in ['jawLeft','jawRight','jawForward']:
        if name == 'jawForward': d.y = -.065*jaw
        else: d.x = (.085 if name == 'jawLeft' else -.085)*jaw
    elif name in ['mouthLeft','mouthRight']:
        d.x = (.085 if name == 'mouthLeft' else -.085)*mouth
    elif name == 'mouthFunnel':
        d.x = -x*.24*mouth; d.y = -.07*mouth
        d.z = (z-MOUTH_Z)*.5*mouth
    elif name == 'mouthPucker':
        d.x = -x*.44*mouth; d.y = -.10*mouth
    elif name.startswith('mouthSmile'):
        d.x = math.copysign(.055,x)*corner*side*mouth
        d.z = .11*corner**1.3*side*mouth
    elif name.startswith('mouthFrown'):
        d.z = -.075*corner*side*mouth
    elif name.startswith('mouthStretch'):
        d.x = math.copysign(.075,x)*corner*side*mouth
    elif name.startswith('mouthDimple'):
        d.y = .05*corner*side*mouth
    elif name.startswith('mouthPress'):
        d.z = -(z-MOUTH_Z)*.4*mouth*side
    elif name.startswith('mouthRoll'):
        w = lower if name.endswith('Lower') else upper
        d.y = .045*w*mouth; d.z = (.018 if name.endswith('Lower') else -.018)*w*mouth
    elif name.startswith('mouthShrug'):
        w = lower if name.endswith('Lower') else upper
        d.z = .055*w*mouth; d.y = -.02*w*mouth
    elif name.startswith('mouthLowerDown'):
        d.z = -.075*lower*mouth*side
    elif name.startswith('mouthUpperUp'):
        d.z = .07*upper*mouth*side
    elif name.startswith('brow'):
        w = math.exp(-((abs(x)-.29)/.29)**4-((z-2.56)/.14)**4)*front*(1-eye_mask)
        if name == 'browInnerUp': d.z = .085*w*(1-smoothstep(.05,.40,abs(x)))
        elif 'OuterUp' in name: d.z = .09*w*side*smoothstep(.10,.43,abs(x))
        else: d.z = -.07*w*side
    elif name == 'cheekPuff':
        w = math.exp(-((abs(x)-.36)/.14)**2-((z-2.04)/.16)**2)*face
        d.y = -.075*w; d.x = math.copysign(.025,x)*w
    elif name.startswith('cheekSquint'):
        w = math.exp(-((abs(x)-.33)/.17)**2-((z-2.05)/.13)**2)*face*side
        d.z = .055*w
    elif name.startswith('noseSneer'):
        w = math.exp(-(x/.19)**2-((z-2.06)/.15)**2)*face*side
        d.z = .05*w; d.y = -.022*w
    if name == 'tongueOut' and part == 'tongue':
        d.y = -.43; d.z = -.035
    return d


def facial_targets(body, rig):
    # Remove a narrow strip inside the existing lip borders to expose a real cavity.
    bm = bmesh.new()
    bm.from_mesh(body.data)
    remove = []
    for f in bm.faces:
        x,y,z = f.calc_center_median()
        curve = MOUTH_Z-.022*(x/.34)**2
        slit = y < -.34 and abs(z-curve) < .017*math.sqrt(max(0,1-(x/.34)**2))
        if abs(x) < .335 and slit:
            remove.append(f)
    bmesh.ops.delete(bm, geom=remove, context='FACES')
    # Sculpt the cut boundary onto a smooth lip line after removing its triangles.
    for v in bm.verts:
        x,y,z=v.co
        curve=MOUTH_Z-.022*(x/.34)**2
        if v.is_boundary and abs(x)<.35 and y<-.32 and abs(z-curve)<.065:
            half=.012*math.sqrt(max(0,1-(x/.35)**2))
            v.co.z=curve+math.copysign(half,z-curve)
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()
    bind(body,rig)
    body.shape_key_add(name='Basis',from_mix=False).value=0
    for name in CHANNELS:
        if name.startswith('eye') or name == 'tongueOut':
            continue
        key = body.shape_key_add(name=name,from_mix=False)
        key.value=0
        for v in body.data.vertices:
            key.data[v.index].co = v.co+skin_delta(v.co,name)

    mesh = Mesh()
    sclera = material('Coral ivory sclera','#ece2c7',.3)
    pupil = material('Coral blue pupils','#205d81',.26)
    lid = material('Coral eyelid skin','#b7818b',.65)
    lid.node_tree.nodes['Principled BSDF'].inputs['Coat Weight'].default_value=.04
    dark = material('Oral interior','#260d19',.8)
    dark.node_tree.nodes['Principled BSDF'].inputs['Coat Weight'].default_value=0
    dark.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=.05
    tongue = material('Coral tongue','#b65d70',.55)
    for i,center in enumerate(EYES):
        ex,ey,ez = center
        tag = {'part':'eye','eye':i}
        mesh.ellipsoid(center,EYE_RADII,sclera,tag=tag,n=48,rings=28)
        def pupil_surface(u,v):
            a=2*math.pi*v; t=.001+.225*u
            px=math.sin(t)*math.cos(a); pz=math.sin(t)*math.sin(a)-.30
            return (ex+EYE_RADII[0]*px,
                    ey-(EYE_RADII[1]+.003)*math.sqrt(max(.01,1-px*px-pz*pz)),
                    ez+EYE_RADII[2]*pz)
        mesh.grid(9,32,pupil_surface,pupil,tag={'part':'pupil','eye':i})
        for upper in [True,False]:
            angle=.28 if upper else .32
            def point(u,v):
                t=.001+u*angle; a=2*math.pi*v
                rx,ry,rz=[r+.007 for r in EYE_RADII]
                return (ex+rx*math.sin(t)*math.cos(a),ey+ry*math.sin(t)*math.sin(a),ez+(1 if upper else -1)*rz*math.cos(t))
            def tag(u,v,p):
                return {'part':'lid','eye':i,'u':u,'v':v,'upper':upper}
            mesh.grid(13,48,point,lid,tag=tag)
    def cavity(u,v):
        a=2*math.pi*v; x=.343*math.cos(a)*(1-.25*u)
        z=MOUTH_Z-.022*(x/.34)**2+.026*math.sin(a)*(1+3*u)
        y=-.575+.15*(abs(x)/.34)**2+.35*u
        return (x,y,z)
    mesh.grid(9,64,cavity,dark,tag='cavity')
    mesh.ellipsoid((0,-.18,MOUTH_Z),(.30,.04,.16),dark,tag='cavity',n=24,rings=14)
    mesh.ellipsoid((0,-.30,MOUTH_Z-.035),(.14,.10,.022),tongue,tag='tongue',n=32,rings=14)
    face = mesh.object('CoralEyesAndMouth',rig)
    attr=face.data.attributes.new(name='_LID_INDEX',type='FLOAT',domain='POINT')
    attr.data.foreach_set('value',[tag['eye']+1 if isinstance(tag,dict) and tag['part']=='lid' else 0 for tag in mesh.tags])
    face['eyelidSurfaces']=[{'center':[x,z,-y],'radii':[EYE_RADII[0]+.007,EYE_RADII[2]+.007,EYE_RADII[1]+.007]} for x,y,z in EYES]
    face['sourceTaskId']=SOURCE_ID
    face.shape_key_add(name='Basis',from_mix=False).value=0
    for name in CHANNELS:
        key=face.shape_key_add(name=name,from_mix=False)
        key.value=0
        for j,(p,tag) in enumerate(zip(mesh.v,mesh.tags)):
            delta=Vector((0,0,0))
            if isinstance(tag,dict):
                i=tag['eye']; side='Left' if EYES[i][0]>0 else 'Right'
                if name.endswith(side):
                    if tag['part']=='lid' and name.startswith(('eyeBlink','eyeSquint','eyeWide')):
                        upper=tag['upper']; a=.28 if upper else .32
                        if name.startswith('eyeBlink'): a=1.66 if upper else 1.49
                        elif name.startswith('eyeSquint'): a=.68 if upper else .83
                        else: a=.05
                        t=.001+tag['u']*a; phi=2*math.pi*tag['v']
                        ex,ey,ez=EYES[i]; rx,ry,rz=[r+.007 for r in EYE_RADII]
                        q=Vector((ex+rx*math.sin(t)*math.cos(phi),ey+ry*math.sin(t)*math.sin(phi),ez+(1 if upper else -1)*rz*math.cos(t)))
                        delta=q-Vector(p)
                    elif tag['part']=='pupil' and name.startswith('eyeLook'):
                        ex,ey,ez=EYES[i]; rx,ry,rz=EYE_RADII
                        q=Vector(((p[0]-ex)/rx,(p[1]-ey)/ry,(p[2]-ez)/rz))
                        if 'Up' in name: rot=Quaternion((1,0,0),-.32)
                        elif 'Down' in name: rot=Quaternion((1,0,0),.25)
                        else: rot=Quaternion((0,0,1),(-1 if 'In' in name else 1)*(1 if side=='Left' else -1)*.3)
                        dv=rot@q-q;delta=Vector((dv.x*rx,dv.y*ry,dv.z*rz))
            else:
                delta=skin_delta(p,name,tag)
            key.data[j].co=Vector(p)+delta
    return face, len(remove)


def set_pose(rig, name):
    for b in rig.pose.bones:
        b.rotation_mode='QUATERNION';b.rotation_quaternion=(1,0,0,0);b.location=(0,0,0)
    def swing(name, axis, angle):
        b=rig.pose.bones[name];q=b.bone.matrix_local.to_quaternion()
        b.rotation_quaternion=q.inverted()@Quaternion(axis,angle)@q
    if name=='Seated':
        root=rig.pose.bones['Root']
        root.location=root.bone.matrix_local.to_quaternion().inverted()@Vector((0,0,.10))
        for side in ['L','R']:
            swing('Thigh.'+side,(1,0,0),-math.pi/2)
            swing('Shin.'+side,(1,0,0),math.pi/2)
            swing('UpperArm.'+side,(1,0,0),-.62)
            swing('Forearm.'+side,(1,0,0),-.62)
    elif name=='T-Pose':
        for side,s in [('L',1),('R',-1)]:
            swing('UpperArm.'+side,(0,1,0),-s*1.27)
    bpy.context.view_layer.update()


def actions(rig):
    for name in ['Seated','Standing','T-Pose']:
        rig.animation_data_create();rig.animation_data.action=None
        set_pose(rig,name)
        for b in rig.pose.bones:
            for f in [1,2]:
                b.keyframe_insert('rotation_quaternion',frame=f,group=b.name)
                b.keyframe_insert('location',frame=f,group=b.name)
        action=rig.animation_data.action;action.name=name
        track=rig.animation_data.nla_tracks.new();track.name=name
        track.strips.new(name,1,action);track.mute=True
    rig.animation_data.action=None
    set_pose(rig,'Seated')


def render_checks(rig,body,face):
    scene=bpy.context.scene;camera=scene.camera
    for obj in scene.objects:
        if obj.get('assetRole')=='shared-vehicle':obj.hide_render=True
    camera.location=(.15,-8,2.28)
    camera.rotation_euler=(Vector((0,-.2,2.28))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=1.85
    cases={'neutral':{},'jaw':{'jawOpen':1},'smile':{'mouthSmileLeft':1,'mouthSmileRight':1,'jawOpen':.2},
           'blink-left':{'eyeBlinkLeft':1},'blink-half':{'eyeBlinkLeft':.5,'eyeBlinkRight':.5},
           'blink-both':{'eyeBlinkLeft':1,'eyeBlinkRight':1},
           'brows':{'browInnerUp':1,'browOuterUpLeft':1,'browOuterUpRight':1},
           'gaze':{'eyeLookOutLeft':1,'eyeLookInRight':1}}
    if '--quick' in sys.argv:
        cases={name:cases[name] for name in ['neutral','jaw']}
    set_pose(rig,'Standing')
    for name,weights in cases.items():
        for obj in [body,face]:
            for key in obj.data.shape_keys.key_blocks:
                key.value=weights.get(key.name,0)
        # Match the browser's post-morph lid projection for Blender review renders.
        corrections=[]
        for key in face.data.shape_keys.key_blocks:
            if key.value and key.name.startswith('eyeBlink') and key.value<1:
                corrections.append((key,key.value,[v.co.copy() for v in key.data]))
        for key,value,original in corrections:
            for j,tag in enumerate(face.data.attributes['_LID_INDEX'].data):
                if tag.value==0: continue
                center=Vector(EYES[int(tag.value)-1]);radii=Vector(tuple(r+.007 for r in EYE_RADII))
                base=face.data.vertices[j].co
                mixed=base.lerp(key.data[j].co,value)
                delta=mixed-center
                radial=Vector((delta.x/radii.x,delta.y/radii.y,delta.z/radii.z)).normalized()
                projected=center+Vector((radial.x*radii.x,radial.y*radii.y,radial.z*radii.z))
                key.data[j].co=base+(projected-base)/value
        scene.render.filepath=str(ROOT/'.context/qa/3dai'/('coral-'+name+'.png'))
        bpy.ops.render.render(write_still=True)
        # Restore shape coordinates after the temporary review correction.
        for key,value,original in corrections:
            for point,co in zip(key.data,original):point.co=co
            key.value=0


def main():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/3dai/coral-prepared.blend'))
    body=bpy.data.objects['CoralSourceBody']
    bpy.ops.object.select_all(action='DESELECT')
    rig=create_rig()
    face,removed=facial_targets(body,rig)
    actions(rig)
    export(OUT/'coral.glb',[rig,body,face],True)
    for obj in [body,face]:
        for key in obj.data.shape_keys.key_blocks:key.value=0
    rig.animation_data.action=None
    for track in rig.animation_data.nla_tracks:track.mute=True
    set_pose(rig,'Seated')
    bpy.ops.import_scene.gltf(filepath=str(OUT/'silver-vehicle.glb'))
    scene=bpy.context.scene;camera=scene.camera
    camera.location=(3.8,-7,3.3)
    camera.rotation_euler=(Vector((0,0,1.6))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=4.2
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True);rig.select_set(True)
    bpy.context.view_layer.objects.active=body
    bpy.context.scene['rigReview']='Source-based Coral. Original preserved. Body/FK and facial morph review required.'
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/3dai/coral-rigged.blend'))
    scene.render.filepath=str(OUT/'coral.png')
    bpy.ops.render.render(write_still=True)
    print('CORAL RIG',json.dumps({'bones':len(rig.data.bones),'source_vertices':len(body.data.vertices),'mouth_faces_removed':removed}),flush=True)
    render_checks(rig,body,face)


if __name__=='__main__':main()
