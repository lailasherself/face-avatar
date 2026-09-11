"""Isolated Cosmic review build. Run with Blender --background --python this_file.

Reference-scaled geometry and cleaned reference projection; no background plane
or image-based geometry is exported. Original assets and shared helpers untouched.
"""
import json
import math
import struct
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector, Quaternion

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_avatar_fleet import Mesh, material, export
from build_local_characters import face, smooth, bind

OUT = ROOT / 'assets/reference-characters'
BLEND = ROOT / 'blender/reference-characters'
QA = ROOT / '.context/qa/reference-characters'
REF = ROOT / '.context/attachments/kioMh1/lailasherself_cosmic_alien_creature_made_of_a_swirling_star-f_80d4b03e-6e0a-42a9-9dff-fa782902333e_3.png'
PI = math.pi
C = dict(head=(.715,.43,.655), hz=2.20, power=.61,
         eyes=(.319,.085,.318,.175,.296), eye='#031007', pupil='#020803',
         upper='#ff7800', lower='#119500', sleep=1.477,
         mouth=(.305,-.392,.010))


def make_materials():
    m = {k: material('Cosmic ' + k, v, .51) for k,v in {
        'skin':'#541765', 'lip':'#46124e', 'eye':C['eye'], 'pupil':C['pupil'],
        'upper':C['upper'], 'lower':C['lower'], 'cavity':'#150714',
        'tongue':'#d66387', 'teeth':'#fff0d7', 'green':'#128d09', 'shoe':'#ff7300',
    }.items()}
    original = bpy.data.images.load(str(REF)); original.pack()
    w,h = original.size
    pixels = np.array(original.pixels[:], dtype=np.float32).reshape(h,w,4)
    rgb = pixels[:,:,:3]
    # Dilate genuine purple skin into eyes, backdrop and shoes before projection.
    # This also provides coherent purple material for unseen surfaces.
    mask = ((rgb[:,:,0] > rgb[:,:,1]*1.24) & (rgb[:,:,2] > rgb[:,:,1]*1.24)
            & (rgb.max(2)-rgb.min(2) > .10))
    yy,xx=np.mgrid[0:h,0:w];photo_y=h-1-yy
    eyes=(((xx-340)/103)**2+((photo_y-510)/96)**2<1)|(((xx-534)/105)**2+((photo_y-508)/96)**2<1)
    mask &= ~eyes
    cleaned = rgb.copy()
    # Fill removed features with actual forehead artwork rather than stretching
    # eyelid/boundary colors across the reconstructed eye sockets and side walls.
    source_x=(330+(xx+photo_y*.07)%210).astype(int)
    source_y=(h-1-(362+photo_y%49)).astype(int)
    cleaned[~mask]=rgb[source_y[~mask],source_x[~mask]]
    # Preserve stars within a small neighborhood of confirmed purple skin.
    near=mask.copy()
    for dy in range(-2,3):
        for dx in range(-2,3):near |= np.roll(mask,(dy,dx),(0,1))
    stars=near & (~eyes) & (rgb[:,:,0]>.60) & (rgb[:,:,1]>.37) & (rgb[:,:,2]<.35)
    cleaned[stars]=rgb[stars]
    mouth_distance=((xx-448)/110)**2+((photo_y-651)/39)**2
    blend=np.clip((1-mouth_distance)*1.35,0,1)[:,:,None]
    cleaned=cleaned*(1-blend)+np.array([.235,.046,.277])*blend
    rgba=np.ones_like(pixels);rgba[:,:,:3]=cleaned
    texture=bpy.data.images.new('Cosmic cleaned reference galaxy',width=w,height=h)
    texture.pixels.foreach_set(rgba.ravel());texture.update()
    texture.filepath_raw=str(OUT/'cosmic-reference-texture.png');texture.file_format='PNG';texture.save();texture.pack()
    for key in ['skin','lip']:
        mat=m[key];p=mat.node_tree.nodes.get('Principled BSDF')
        tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=texture
        mat.node_tree.links.new(tex.outputs['Color'],p.inputs['Base Color'])
        mat.node_tree.links.new(tex.outputs['Color'],p.inputs['Emission Color'])
        p.inputs['Emission Strength'].default_value=.075
        p.inputs['Roughness'].default_value=.63
        p.inputs['Coat Weight'].default_value=.025
        p.inputs['Specular IOR Level'].default_value=.15
    for key in ['eye','pupil']:
        p=m[key].node_tree.nodes.get('Principled BSDF');p.inputs['Roughness'].default_value=.085;p.inputs['Coat Weight'].default_value=.65
    for key in ['shoe','green','upper','lower']:
        p=m[key].node_tree.nodes.get('Principled BSDF');p.inputs['Roughness'].default_value=.62;p.inputs['Coat Weight'].default_value=0
        p.inputs['Specular IOR Level'].default_value=.15
    return m


def projection(obj):
    uv=obj.data.uv_layers.active or obj.data.uv_layers.new(name='ReferenceProjection')
    for loop in obj.data.loops:
        p=obj.data.vertices[loop.vertex_index].co
        # Front matches reference landmarks. Side/rear repeat cleaned forehead.
        u=(448+p.x*290)/896;v=(169+p.z*290)/1344
        if p.y>.04:
            blend=smooth(.04,.28,p.y)
            u=u*(1-blend)+(.35+.25*(.5+.5*math.sin(p.x*3+p.y*4)))*blend
            v=v*(1-blend)+(.68+.04*math.sin(p.z*4+p.y*2))*blend
        uv.data[loop.index].uv=(u,v)


def skeleton():
    data=bpy.data.armatures.new('Cosmic reference skeleton');rig=bpy.data.objects.new('AvatarRig',data)
    bpy.context.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    def bone(name,a,b,parent=None):
        v=data.edit_bones.new(name);v.head=a;v.tail=b
        if parent:v.parent=data.edit_bones[parent]
        v.align_roll(Vector((0,-1,0)))
    bone('Root',(0,0,0),(0,0,.20))
    bone('Hips',(0,0,.64),(0,0,.85),'Root');bone('Spine',(0,0,.85),(0,0,1.12),'Hips')
    bone('Chest',(0,0,1.12),(0,0,1.43),'Spine');bone('Neck',(0,0,1.43),(0,0,1.59),'Chest')
    bone('Head',(0,0,1.59),(0,0,2.58),'Neck')
    chains={}
    for side,s in [('L',1),('R',-1)]:
        bone('UpperArm.'+side,(s*.34,0,1.34),(s*.60,0,1.135),'Chest')
        bone('Forearm.'+side,(s*.60,0,1.135),(s*.73,-.015,.91),'UpperArm.'+side)
        bone('Hand.'+side,(s*.73,-.015,.91),(s*.77,-.025,.80),'Forearm.'+side)
        bone('Thigh.'+side,(s*.22,0,.68),(s*.24,0,.45),'Hips')
        bone('Shin.'+side,(s*.24,0,.45),(s*.25,0,.23),'Thigh.'+side)
        bone('Foot.'+side,(s*.25,0,.23),(s*.25,-.27,.10),'Shin.'+side)
        for digit,pts in {
            'Thumb':[(.692,-.045,.935),(.641,-.050,.879),(.630,-.055,.818),(.632,-.055,.793)],
            'Index':[(.790,-.014,.869),(.807,-.016,.797),(.785,-.043,.731),(.756,-.071,.727)],
        }.items():
            points=[Vector((s*x,y,z)) for x,y,z in pts];chains[side,digit]=points
            for i in range(3):bone(f'{digit}{i+1}.{side}',points[i],points[i+1],'Hand.'+side if i==0 else f'{digit}{i}.{side}')
    bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False);rig.show_in_front=True
    for b in data.bones:
        if b.name.startswith(('Thumb','Index')):b['fingerCurlRadians']=.82
    rig['rigVersion']='cosmic-reference-review-2';rig['visualApproval']=False
    return rig,chains


def body(rig,chains,m):
    mesh=Mesh()
    parts=[('CosmicBody',mesh,False)]
    mesh.ellipsoid((0,.012,1.055),(.45,.285,.51),m['skin'],n=64,rings=44,power=.86)
    mesh.ellipsoid((0,0,1.49),(.15,.17,.13),m['skin'],n=32,rings=20)
    for side,s in [('L',1),('R',-1)]:
        mesh.ellipsoid((s*.236,0,.515),(.24,.252,.32),m['skin'],n=40,rings=28,power=.58)
        arm=Mesh();parts.append(('CosmicArm'+side,arm,True))
        pts=[(s*(.24+.52*t),-.01*t,1.36-.44*t+.055*math.sin(PI*t)) for t in np.linspace(0,1,20)]
        arm.tube(pts,[float(.16-.050*t) for t in np.linspace(0,1,20)],m['skin'],n=24)
        arm.ellipsoid((s*.34,0,1.34),(.16,.155,.16),m['skin'],n=32,rings=20)
        arm.ellipsoid((s*.765,-.015,.86),(.117,.105,.141),m['skin'],n=32,rings=20)
        for digit in ['Thumb','Index']:
            control=chains[side,digit];pts=[]
            for i in range(3):pts.extend([control[i].lerp(control[i+1],float(t)) for t in np.linspace(0,1,6,endpoint=False)])
            pts.append(control[-1]);r=.063 if digit=='Thumb' else .083
            arm.tube(pts,[r*(1-.22*i/(len(pts)-1)) for i in range(len(pts))],m['skin'],n=16)
            arm.ellipsoid(control[-1],(r*.8,r*.8,r*.8),m['skin'],n=20,rings=14)
    def weights(p,is_arm):
        x,y,z=p;side='L' if x>=0 else 'R';x=abs(x)
        if is_arm:
            hand=1-smooth(.87,1.01,z)
            upper=rig.data.bones['UpperArm.'+side];axis=upper.tail_local-upper.head_local
            along=(p-upper.head_local).dot(axis)/axis.length_squared
            elbow=smooth(.72,1.17,along)
            w={'UpperArm.'+side:1-elbow,'Forearm.'+side:elbow*(1-hand),'Hand.'+side:elbow*hand}
            if z<.91:
                digit='Thumb' if x<.702 else 'Index'
                points=chains[side,digit];nearest=[]
                for i in range(3):
                    a,b=points[i:i+2];t=max(0,min(1,(p-a).dot(b-a)/(b-a).length_squared));nearest.append(((p-a.lerp(b,t)).length,i,t))
                _,i,t=min(nearest);d=1-smooth(.78,.90,z)
                if digit=='Thumb':d=1-smooth(.86,.935,z)
                w={k:v*(1-d) for k,v in w.items()}
                position=i+t
                joint_weights=[max(0,1-abs(position-(j+.5))) for j in range(3)]
                total=sum(joint_weights)
                for j,v in enumerate(joint_weights):w[f'{digit}{j+1}.{side}']=d*v/total
            return dict(sorted(w.items(),key=lambda item:item[1],reverse=True)[:4])
        if z>1.44:return {'Neck':smooth(1.44,1.58,z),'Chest':1-smooth(1.44,1.58,z)}
        if z<.70:
            thigh=1-smooth(.60,.72,z);shin=1-smooth(.37,.51,z)
            return {'Hips':1-thigh,'Thigh.'+side:thigh*(1-shin),'Shin.'+side:thigh*shin}
        upper=smooth(.90,1.27,z);hip=1-smooth(.72,.91,z)
        return {'Hips':hip,'Spine':(1-hip)*(1-upper),'Chest':(1-hip)*upper}
    objects=[]
    for name,part,is_arm in parts:
        obj=part.object(name);bpy.context.view_layer.objects.active=obj;obj.select_set(True)
        rem=obj.modifiers.new('Continuous native surface','REMESH');rem.mode='VOXEL';rem.voxel_size=.019
        bpy.ops.object.modifier_apply(modifier=rem.name)
        mod=obj.modifiers.new('Surface relaxation','SMOOTH');mod.factor=1.1;mod.iterations=6;bpy.ops.object.modifier_apply(modifier=mod.name)
        sub=obj.modifiers.new('Joint resolution','SUBSURF');sub.levels=1;bpy.ops.object.modifier_apply(modifier=sub.name)
        for p in obj.data.polygons:p.use_smooth=True
        bind(obj,rig,lambda p:weights(p,is_arm));projection(obj);obj['armCollisionSurface']=not is_arm
        objects.append(obj)
    feet=Mesh()
    for side,s in [('L',1),('R',-1)]:
        def foot(u,v):
            a=PI*u;t=math.cos(a);z=.17+.164*t
            radius=math.sin(a)**.44
            rx=(.32-.075*t)*radius;ry=(.34-.06*t)*radius
            phi=2*PI*v
            return s*(.275+.05*(1-t)/2)+rx*math.cos(phi),-.095+ry*math.sin(phi)-.08*(1-t)/2,z
        feet.grid(32,64,foot,m['shoe'],{'Foot.'+side:1})
    shoes=feet.object('CosmicOrangeFeet',rig)
    return [*objects,shoes]


def facial(rig,m):
    objects,surface=face(C,rig,m)
    face_obj=objects[0];face_obj.name='CosmicFace'
    jaw=face_obj.data.shape_keys.key_blocks['jawOpen'];base=face_obj.data.shape_keys.key_blocks['Basis']
    for i in range(38*80):
        u=(i//80)/37;a=2*PI*(i%80)/80
        lower=max(0,-math.sin(a))**.40;amount=lower*(1-smooth(.05,.42,u))
        jaw.data[i].co=base.data[i].co+Vector((0,-.012*amount,-.15*amount))
    lip_vertices=sorted({i for poly in face_obj.data.polygons if face_obj.data.materials[poly.material_index]==m['lip'] for i in poly.vertices})
    for j,i in enumerate(lip_vertices):
        a=2*PI*(j//8)/64;amount=max(0,-math.sin(a))**.40
        jaw.data[i].co=base.data[i].co+Vector((0,-.012*amount,-.15*amount))
    lower_vertices=set()
    for poly in face_obj.data.polygons:
        if face_obj.data.materials[poly.material_index]==m['lower']:lower_vertices.update(poly.vertices)
    basis=face_obj.data.shape_keys.key_blocks['Basis']
    for i in lower_vertices:
        p=basis.data[i].co;side='Left' if face_obj.data.attributes['_LID_INDEX'].data[i].value==2 else 'Right';cx=C['eyes'][0]*(1 if side=='Left' else -1)
        cy=surface(cx,C['eyes'][1])-.027;cz=C['hz']+C['eyes'][1]
        rx,ry,rz=[v+.008 for v in C['eyes'][2:]]
        theta=math.acos(max(-1,min(1,(cz-p.z)/rz)))
        phi=math.atan2((p.y-cy)/ry,(p.x-cx)/rx)
        for key in face_obj.data.shape_keys.key_blocks:
            if key.name=='eyeBlink'+side:continue
            if key.name=='eyeWide'+side:angle=.78
            elif key.name=='eyeSquint'+side:angle=1.34
            else:angle=1.10
            t=theta/1.401*angle
            key.data[i].co=(cx+rx*math.sin(t)*math.cos(phi),cy+ry*math.sin(t)*math.sin(phi),cz-rz*math.cos(t))
    # Reference cheek profile is broad at the jaw, indented beside the eyes.
    for key in face_obj.data.shape_keys.key_blocks:
        for i,v in enumerate(key.data):
            original=face_obj.data.vertices[i].co
            if original.y>=0:
                x=original.x/C['head'][0];z=(original.z-C['hz'])/C['head'][2]
                v.co.y=C['head'][1]*max(0,1-abs(x)**(2/C['power'])-abs(z)**(2/C['power']))**(C['power']/2)
            if abs(original.x)>.59:
                local_z=original.z-C['hz']
                v.co.x*=1+.07*math.exp(-((local_z+.43)/.15)**2)-.025*math.exp(-((local_z+.13)/.12)**2)
    for v,k in zip(face_obj.data.vertices,face_obj.data.shape_keys.key_blocks['Basis'].data):v.co=k.co
    projection(face_obj)
    # Keep tongue root fixed under both jaw opening and extension.
    tongue=objects[2];basis=tongue.data.shape_keys.key_blocks['Basis'];jaw=tongue.data.shape_keys.key_blocks['jawOpen']
    for i,p in enumerate(jaw.data):
        u=(i//20)/24;p.co=basis.data[i].co+Vector((0,0,-.10*smooth(0,.6,u)))
    bpy.context.view_layer.objects.active=tongue
    bpy.ops.object.select_all(action='DESELECT');tongue.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.fill_holes(sides=24);bpy.ops.object.mode_set(mode='OBJECT');tongue.select_set(False)
    face_obj['armCollisionSurface']=True
    antenna=Mesh()
    for s in [-1,1]:
        pts=[(s*(.548+.284*t),.02,2.785+.322*t) for t in np.linspace(0,1,18)]
        antenna.tube(pts,[float(.083-.014*math.sin(PI*t)+.035*t*t) for t in np.linspace(0,1,18)],m['green'],n=24)
        antenna.ellipsoid((s*.839,.02,3.132),(.154,.126,.162),m['green'],n=36,rings=24,power=.86)
    objects.append(antenna.object('CosmicGreenAntennae',rig))
    return objects


def reset(rig,objects):
    for b in rig.pose.bones:b.rotation_mode='QUATERNION';b.rotation_quaternion=(1,0,0,0)
    for o in objects:
        if o.type=='MESH' and o.data.shape_keys:
            for k in o.data.shape_keys.key_blocks:k.value=0
    bpy.context.view_layer.update()


def expression(objects,values):
    for o in objects:
        if o.type=='MESH' and o.data.shape_keys:
            for name,value in values.items():
                key=o.data.shape_keys.key_blocks.get(name)
                if key:key.value=value
    bpy.context.view_layer.update()


def swing(rig,name,axis,angle):
    b=rig.pose.bones[name];q=b.bone.matrix_local.to_quaternion();b.rotation_quaternion=q.inverted()@Quaternion(axis,angle)@q
    bpy.context.view_layer.update()


def snapshot(objects):
    result={};dg=bpy.context.evaluated_depsgraph_get()
    for o in objects:
        if o.type!='MESH':continue
        evaluated=o.evaluated_get(dg);mesh=evaluated.to_mesh()
        result[o.name]=np.array([v.co[:] for v in mesh.vertices]);evaluated.to_mesh_clear()
    return result


def validate(rig,objects):
    report={'id':'cosmic','status':'isolated-review-only','installationApproved':False,'bones':len(rig.data.bones),
            'vertices':sum(len(o.data.vertices) for o in objects if o.type=='MESH')}
    errors=[];influences=0;finite=True
    for o in objects:
        if o.type!='MESH':continue
        for v in o.data.vertices:
            errors.append(abs(sum(g.weight for g in v.groups)-1));influences=max(influences,len(v.groups))
        if o.data.shape_keys:
            for k in o.data.shape_keys.key_blocks:finite &= all(all(math.isfinite(c) for c in v.co) for v in k.data)
    report['maxWeightError']=max(errors);report['maxInfluences']=influences;report['finiteMorphCoordinates']=bool(finite)
    reset(rig,objects);base=snapshot(objects)
    swing(rig,'UpperArm.L',(0,1,0),-.65);posed=snapshot(objects)
    body_obj=next(o for o in objects if o.name=='CosmicBody');mask=base[body_obj.name][:,0]<-.50
    report['oppositeArmDrift']=float(np.max(np.linalg.norm(posed['CosmicArmR']-base['CosmicArmR'],axis=1)))
    report['headDrift']=float(np.max(np.linalg.norm(posed['CosmicFace']-base['CosmicFace'],axis=1)))
    lower_mask=(base[body_obj.name][:,2]<.75)&(np.abs(base[body_obj.name][:,0])<.50)
    report['lowerBodyDriftInArmPose']=float(np.max(np.linalg.norm(posed[body_obj.name][lower_mask]-base[body_obj.name][lower_mask],axis=1)))
    reset(rig,objects);swing(rig,'Index2.L',(1,0,0),.65);posed=snapshot(objects)
    report['oppositeHandDrift']=float(np.max(np.linalg.norm(posed['CosmicArmR']-base['CosmicArmR'],axis=1)))
    report['leftDigitMotion']=float(np.max(np.linalg.norm(posed['CosmicArmL']-base['CosmicArmL'],axis=1)))
    reset(rig,objects);expression(objects,{'jawOpen':1,'tongueOut':1,'eyeBlinkLeft':1,'mouthSmileRight':.5})
    posed=snapshot(objects);tongue=next(o for o in objects if o.name=='Tongue')
    report['tongueRootDrift']=float(np.max(np.linalg.norm(posed[tongue.name][:20]-base[tongue.name][:20],axis=1)))
    report['tongueTipTravel']=float(np.max(np.linalg.norm(posed[tongue.name][-20:]-base[tongue.name][-20:],axis=1)))
    report['expressionCombinations']={}
    for name,values in [('jaw-smile',{'jawOpen':1,'mouthSmileLeft':1,'mouthSmileRight':1}),('blink-wide',{'eyeBlinkLeft':1,'eyeWideRight':1}),('pucker-jaw',{'jawOpen':.5,'mouthPucker':1}),('tongue-smile',{'jawOpen':1,'tongueOut':1,'mouthSmileRight':.5})]:
        reset(rig,objects);expression(objects,values);state=snapshot(objects)
        report['expressionCombinations'][name]={'finite':all(bool(np.isfinite(a).all()) for a in state.values())}
    report['limitations']=['Single-view reconstruction; rear and depth inferred.',
        'Reference-derived texture retains photographed lighting; rear uses cleaned repeating skin sample.',
        'Hands use two visible native digit controls; hidden anatomy is not evidenced by this reference.',
        'Arms are separate closed surfaces overlapping the torso at concealed rounded shoulder roots.',
        'Lip texture is softened locally to support opening; expression likeness still needs artist review.',
        'Head edge profile, foot toe divisions and rear texture repetition remain artistic review items.',
        'Numeric checks do not establish final likeness, collision clearance, camera tracking or Orin/ZED performance.']
    assert report['maxWeightError']<1e-5 and finite
    assert report['oppositeArmDrift']<1e-6 and report['headDrift']<1e-6
    assert report['lowerBodyDriftInArmPose']<1e-6
    assert report['oppositeHandDrift']<1e-6 and report['tongueRootDrift']<1e-6
    reset(rig,objects)
    (QA/'cosmic-rig-validation.json').write_text(json.dumps(report,indent=2))
    return report


def studio():
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32
    scene.render.resolution_x=896;scene.render.resolution_y=1152;scene.render.resolution_percentage=75
    scene.world=bpy.data.worlds.new('Cosmic review studio');scene.world.color=(.32,.32,.32)
    scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
    bpy.ops.object.camera_add(location=(0,-8,2.20));camera=bpy.context.object;camera.name='CosmicReviewCamera'
    camera.rotation_euler=(Vector((0,0,1.65))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type='ORTHO';camera.data.ortho_scale=3.85;scene.camera=camera
    for p,power,size in [((-3,-4,6),370,5),((3,-2,3),180,4),((1,3,5),280,3)]:
        bpy.ops.object.light_add(type='AREA',location=p);light=bpy.context.object;light.data.energy=power;light.data.shape='DISK';light.data.size=size
        light.rotation_euler=(Vector((0,0,1.5))-light.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.mesh.primitive_plane_add(size=200);floor=bpy.context.object;floor.name='CosmicReviewFloor';floor.location.z=-.015
    floor.data.materials.append(material('Cosmic review gray','#c4c2c5',.8))
    return camera


def validate_export(path):
    raw=path.read_bytes();length,kind=struct.unpack_from('<II',raw,12)
    assert kind==0x4E4F534A
    gltf=json.loads(raw[20:20+length]);binary_start=20+length+8
    binary=memoryview(raw)[binary_start:]
    types={5120:np.int8,5121:np.uint8,5122:np.int16,5123:np.uint16,5125:np.uint32,5126:np.float32}
    dimensions={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
    def view(index,count,dtype,width,offset=0):
        v=gltf['bufferViews'][index];start=v.get('byteOffset',0)+offset;item=np.dtype(dtype).itemsize
        return np.ndarray((count,width),dtype=dtype,buffer=binary,offset=start,strides=(v.get('byteStride',item*width),item)).copy()
    def accessor(index):
        a=gltf['accessors'][index];dtype=types[a['componentType']];width=dimensions[a['type']]
        result=view(a['bufferView'],a['count'],dtype,width,a.get('byteOffset',0)) if 'bufferView' in a else np.zeros((a['count'],width),dtype=dtype)
        if 'sparse' in a:
            sparse=a['sparse'];indices=sparse['indices'];values=sparse['values']
            rows=view(indices['bufferView'],sparse['count'],types[indices['componentType']],1,indices.get('byteOffset',0)).ravel()
            result[rows]=view(values['bufferView'],sparse['count'],dtype,width,values.get('byteOffset',0))
        return result
    channels=set();max_error=0;primitives=0;morphs=0
    for mesh in gltf['meshes']:
        channels.update(mesh.get('extras',{}).get('targetNames',[]))
        assert all(value==0 for value in mesh.get('weights',[]))
        for primitive in mesh['primitives']:
            primitives+=1
            for idx in primitive['attributes'].values():assert np.isfinite(accessor(idx)).all()
            weights=accessor(primitive['attributes']['WEIGHTS_0']);max_error=max(max_error,float(np.max(abs(weights.sum(1)-1))))
            for target in primitive.get('targets',[]):
                morphs+=1
                for idx in target.values():assert np.isfinite(accessor(idx)).all()
    assert len(gltf['scenes'])==1 and len(gltf['skins'])==1
    assert len(gltf['skins'][0]['joints'])==30 and len(channels)==52 and max_error<1e-5
    assert not any('Floor' in node.get('name','') for node in gltf['nodes'])
    return {'scenes':1,'skins':1,'joints':30,'channels':52,'primitives':primitives,'primitiveMorphTargets':morphs,
            'maxWeightError':max_error,'allCoordinatesFinite':True,'neutralMorphValues':True,'noBackdropGeometry':True}


def main():
    for p in [OUT,BLEND,QA]:p.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
    m=make_materials();rig,chains=skeleton();objects=[rig,*body(rig,chains,m),*facial(rig,m)]
    report=validate(rig,objects)
    for o in objects:o['referenceReview']='cosmic-v2';o['installationApproved']=False
    export(OUT/'cosmic-review.glb',objects,True,morph_normals=True)
    report['exportValidation']=validate_export(OUT/'cosmic-review.glb')
    (QA/'cosmic-rig-validation.json').write_text(json.dumps(report,indent=2))
    reset(rig,objects);camera=studio()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND/'cosmic-review.blend'))
    for case in ['neutral','three-quarter','left-arm','jaw-open','tongue-blink','hand-curl','arms-up']:
        reset(rig,objects)
        camera.location=(1.9,-7.4,2.3) if case=='three-quarter' else (0,-8,2.20)
        camera.rotation_euler=(Vector((0,0,1.65))-camera.location).to_track_quat('-Z','Y').to_euler()
        if case=='left-arm':swing(rig,'UpperArm.L',(0,1,0),-.75)
        if case=='arms-up':
            swing(rig,'UpperArm.L',(0,1,0),-1.65);swing(rig,'UpperArm.R',(0,1,0),1.65)
        if case=='jaw-open':expression(objects,{'jawOpen':1})
        if case=='tongue-blink':expression(objects,{'jawOpen':1,'tongueOut':1,'eyeBlinkLeft':1,'mouthSmileRight':.5})
        if case=='hand-curl':
            for digit in ['Thumb','Index']:
                for i in [1,2,3]:rig.pose.bones[f'{digit}{i}.L'].rotation_quaternion=Quaternion((1,0,0),.60)
        bpy.context.scene.render.filepath=str(QA/f'cosmic-{case}.png');bpy.ops.render.render(write_still=True)
    print('COSMIC REVIEW COMPLETE '+json.dumps(report),flush=True)


if __name__=='__main__':main()
