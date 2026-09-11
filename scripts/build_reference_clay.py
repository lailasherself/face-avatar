"""Isolated volumetric Clay review build; never edits the installation roster.

Run with Blender --background --factory-startup --python this_file.py.
The image supplies surface color only; all rendered parts are shaped meshes.
"""
import json
import math
import struct
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector, Quaternion

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_avatar_fleet import Mesh, material, export
from build_local_characters import face, smooth

QA = ROOT / '.context/qa/reference-characters'
OUT = ROOT / 'assets/reference-characters'
BLENDS = ROOT / 'blender/reference-characters'
REF = ROOT / '.context/attachments/c0oVR0/lailasherself_cosmic_alien_creature_made_of_iron-red_Georgia__306e0169-04a3-45f6-90e1-ace12a5212de_2.png'
PI = math.pi


def texture():
    original = bpy.data.images.load(str(REF), check_existing=True)
    w, h = original.size
    raw = np.array(original.pixels[:], dtype=np.float32).reshape(h, w, 4)
    # A clean interior patch retains the real fine mineral grain. Mirrored tiles
    # avoid seams and never include the reference's eyes, silhouette or backdrop.
    patch = raw[h-347:h-260, 355:535].copy()
    patch = np.concatenate([patch, patch[:, ::-1]], axis=1)
    patch = np.concatenate([patch, patch[::-1]], axis=0)
    tile = np.tile(patch, (8, 4, 1))[:1024, :1024].copy()
    tile[:, :, :3] *= np.array([.94, .47, .26])
    grain=np.random.default_rng(309).random((1024,1024))
    flecks=grain>.976
    tile[flecks,:3]=np.minimum(1,tile[flecks,:3]*1.5+np.array([.20,.15,.08]))
    img = bpy.data.images.new('Clay mineral surface from reference', width=1024, height=1024)
    img.pixels.foreach_set(tile.ravel()); img.update(); img.pack()
    img.filepath_raw = str(OUT / 'clay-surface.png'); img.file_format = 'PNG'; img.save()
    m = material('Clay iron red mineral surface', '#a64020', .63)
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Coat Weight'].default_value = .025
    tex = m.node_tree.nodes.new('ShaderNodeTexImage'); tex.image = img
    m.node_tree.links.new(tex.outputs['Color'], p.inputs['Base Color'])
    noise = m.node_tree.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 175
    bump = m.node_tree.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .18
    bump.inputs['Distance'].default_value = .009
    m.node_tree.links.new(noise.outputs['Fac'], bump.inputs['Height'])
    m.node_tree.links.new(bump.outputs['Normal'], p.inputs['Normal'])
    return m


def planar_uv(obj):
    layer = obj.data.uv_layers.active or obj.data.uv_layers.new(name='ClaySurface')
    for poly in obj.data.polygons:
        axis=max(range(3),key=lambda i:abs(poly.normal[i]))
        for index in poly.loop_indices:
            p=obj.data.vertices[obj.data.loops[index].vertex_index].co
            a,b=((p.y,p.z) if axis==0 else (p.x,p.z) if axis==1 else (p.x,p.y))
            layer.data[index].uv=(a*.62,b*.62)


def skeleton():
    data = bpy.data.armatures.new('Clay independent body rig')
    rig = bpy.data.objects.new('AvatarRig', data); bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig; rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    def bone(name, a, b, parent=None):
        ob = data.edit_bones.new(name); ob.head = a; ob.tail = b
        if parent: ob.parent = data.edit_bones[parent]
    bone('Root', (0, 0, 0), (0, 0, .2))
    bone('Hips', (0, 0, .52), (0, 0, .8), 'Root')
    bone('Spine', (0, 0, .8), (0, 0, 1.35), 'Hips')
    bone('Chest', (0, 0, 1.35), (0, 0, 1.82), 'Spine')
    bone('Neck', (0, 0, 1.82), (0, 0, 2.1), 'Chest')
    bone('Head', (0, 0, 2.1), (0, 0, 2.95), 'Neck')
    for side, s in [('L', 1), ('R', -1)]:
        bone('UpperArm.'+side, (s*.10, 0, 1.84), (s*.31, -.005, 1.22), 'Chest')
        bone('Forearm.'+side, (s*.31, -.005, 1.22), (s*.405, -.025, .83), 'UpperArm.'+side)
        bone('Hand.'+side, (s*.405, -.025, .83), (s*.402, -.033, .665), 'Forearm.'+side)
        bone('Thigh.'+side, (s*.16, 0, .56), (s*.19, 0, .33), 'Hips')
        bone('Shin.'+side, (s*.19, 0, .33), (s*.205, -.025, .12), 'Thigh.'+side)
        bone('Foot.'+side, (s*.205, -.025, .12), (s*.205, -.18, .075), 'Shin.'+side)
    bpy.ops.object.mode_set(mode='OBJECT'); rig.select_set(False)
    rig.show_in_front = True
    rig['rigVersion'] = 'reference-clay-review-1'
    rig['installationApproved'] = False
    rig['referenceAnatomy'] = 'Continuous flippers: no separated digits visible in supplied reference'
    return rig


def profile(values, t):
    for i in range(len(values)-1):
        if t <= values[i+1][0]:
            a, b = values[i], values[i+1]
            p = values[max(0, i-1)]; q = values[min(len(values)-1, i+2)]
            f = (t-a[0])/(b[0]-a[0])
            m0 = (b[1]-p[1])/(b[0]-p[0])*(b[0]-a[0])
            m1 = (q[1]-a[1])/(q[0]-a[0])*(b[0]-a[0])
            return max(.001, (2*f**3-3*f*f+1)*a[1]+(f**3-2*f*f+f)*m0+(-2*f**3+3*f*f)*b[1]+(f**3-f*f)*m1)
    return values[-1][1]


def body(rig, skin):
    mesh = Mesh()
    torso = [(0,.12),(.012,.21),(.07,.29),(.20,.34),(.40,.30),(.60,.22),(.78,.14),(.9,.092),(1,.11)]
    def weight(p):
        z = p[2]
        if z < 1.20:
            t = smooth(.68,1.13,z); return {'Hips':1-t,'Spine':t}
        if z < 1.76:
            t = smooth(1.20,1.60,z); return {'Spine':1-t,'Chest':t}
        t = smooth(1.76,2.06,z); return {'Chest':1-t,'Neck':t}
    def surface(u,v):
        r = profile(torso,u); a = v*2*PI
        return r*math.cos(a), .77*r*math.sin(a)+.018, .47+1.70*u
    mesh.grid(90,80,surface,skin,weight)
    torso_obj = mesh.object('Clay tapered torso and neck',rig)
    torso_obj['armCollisionSurface'] = True
    objects = [torso_obj]
    for side,s in [('L',1),('R',-1)]:
        limb = Mesh()
        arm = [(0,.023),(.10,.033),(.32,.046),(.54,.062),(.73,.086),(.86,.10),(.94,.085),(.985,.042),(1,.002)]
        def arm_weight(p):
            z=p[2]; elbow=1-smooth(1.13,1.32,z); hand=1-smooth(.78,.91,z)
            return {'UpperArm.'+side:1-elbow,'Forearm.'+side:elbow*(1-hand),'Hand.'+side:elbow*hand}
        def arm_surface(u,v):
            a=2*PI*v; r=profile(arm,u)
            x=.10+.31*math.sin(u*PI*.48)
            return s*(x+r*math.cos(a)), -.008-.035*u+r*.82*math.sin(a), 1.88-1.245*u
        limb.grid(76,48,arm_surface,skin,arm_weight)
        objects.append(limb.object('Clay continuous flipper '+side,rig))
        foot = Mesh()
        boot=[(0,.16),(.04,.195),(.14,.195),(.40,.145),(.7,.082),(.88,.07),(1,.06)]
        def leg_weight(p):
            z=p[2]; ankle=1-smooth(.12,.24,z); knee=1-smooth(.29,.41,z)
            return {'Thigh.'+side:1-knee,'Shin.'+side:knee*(1-ankle),'Foot.'+side:knee*ankle}
        def foot_surface(u,v):
            a=v*2*PI; r=profile(boot,u)
            return s*(.215-.045*u)+r*math.cos(a), -.07*(1-u)+r*.84*math.sin(a), .015+.65*u
        foot.grid(48,56,foot_surface,skin,leg_weight)
        objects.append(foot.object('Clay flared leg '+side,rig))
    for ob in objects: planar_uv(ob)
    return objects


def facial(rig, skin):
    c = dict(head=(1.14,.44,.58),hz=2.62,power=.92,mouth=(.087,-.225,.009),
             eyes=(.468,.026,.165,.087,.10),sleep=.27,skin='#a64020',eye='#040504',pupil='#040504')
    black=material('Clay black glass eyes','#030403',.14)
    black.node_tree.nodes.get('Principled BSDF').inputs['Coat Weight'].default_value=.5
    black.node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value=.25
    mats=dict(skin=skin,lip=skin,upper=skin,lower=skin,eye=black,pupil=black,
              cavity=material('Clay mouth interior','#1c0804',.9),
              tongue=material('Clay tongue','#9a3729',.58),teeth=material('Clay teeth','#e6c699',.4))
    objects,_ = face(c,rig,mats)
    head,teeth,tongue=objects
    head.name='Clay sculpted head and eyelids'
    basis=head.data.shape_keys.key_blocks[0]
    for channel,sign in [('jawOpen',1),('mouthClose',-1)]:
        key=head.data.shape_keys.key_blocks[channel]
        for i,(v,b) in enumerate(zip(key.data,basis.data)):
            v.co=b.co
            if i>=6120 or 3040<=i<4800:continue
            x,y,z=b.co
            transition=.002+.04*smooth(.078,.18,abs(x))+.05*smooth(-.40,-.20,y)
            lower=1-smooth(2.395-transition,2.395+transition,z)
            influence=math.exp(-((x/.25)**4+((z-2.395)/.25)**2))
            if 4800<=i<6120:influence=1
            v.co.z-=sign*.14*lower*influence
            v.co.y-=sign*.010*lower*influence
    for key in [teeth.data.shape_keys.key_blocks['jawOpen']]:
        for v,b in zip(key.data,teeth.data.shape_keys.key_blocks[0].data):v.co=b.co+(v.co-b.co)*.7
    def sculpt(p,index):
        p=p.copy();x,y,z=p;localz=z-c['hz']
        if index<3040:
            socket=sum(math.exp(-((((x-s*.468)/.185)**2+((localz-.026)/.137)**2)*1.5)**2) for s in [-1,1])
            p.y+=.035*socket
        if 5600<=index<6120:
            ring=(index-5600)//8;angle=2*PI*ring/64
            center=Vector((.087*math.cos(angle),-.44*max(0,1-abs(.087*math.cos(angle)/1.14)**(2/.92)-abs((-.225+.009*math.sin(angle))/.58)**(2/.92))**(.92/2)-.007,2.62-.225+.009*math.sin(angle)))
            p=center+(p-center)*.28
        if index>=6120:
            cx=.468 if x>0 else -.468
            q=(localz-.026)/.10
            p.x=cx+(x-cx)*(1-.22*max(0,min(1,q)))
            p.z=2.646+(p.z-2.646)*(.72 if q<0 else 1.23)
            p.y+=.065
        if index<6120:
            w=math.exp(-((x/.14)**6+((localz+.225)/.052)**4))
            p.z+=.01*(1-2*min(1,abs(x)/.087)**2)*w
        return p
    original_basis=[v.co.copy() for v in head.data.shape_keys.key_blocks[0].data]
    for key in head.data.shape_keys.key_blocks:
        for i,v in enumerate(key.data):
            v.co=(sculpt(original_basis[i],i)+v.co-original_basis[i] if 5600<=i<6120 else sculpt(v.co,i))
    # An asymmetric face placement matches the supplied slight turn. The closed
    # back is retained, and the same smooth warp is applied to every morph.
    for ob in objects:
        for key in ob.data.shape_keys.key_blocks:
            for vert in key.data:
                x,y,z=vert.co; localz=z-c['hz']
                warp=.145*max(0,1-(x/1.14)**2)*max(0,1-(localz/.58)**2)
                vert.co.x+=warp
        for vert,basis in zip(ob.data.vertices,ob.data.shape_keys.key_blocks[0].data): vert.co=basis.co
        planar_uv(ob)
    # The reusable oral helper moves the root with jawOpen. Anchor it explicitly
    # so only the exposed tongue bends, including combined jaw/tongue poses.
    basis=tongue.data.shape_keys.key_blocks['Basis']
    jaw=tongue.data.shape_keys.key_blocks['jawOpen']
    ys=[v.co.y for v in basis.data]; back=max(ys); front=min(ys)
    for v,b in zip(jaw.data,basis.data):
        v.co=b.co; v.co.z-=.10*smooth(back,front,b.co.y)
    head['armCollisionSurface']=True
    # Warping changes lid centers; preserve the runtime's glTF coordinate order.
    for item in head['eyelidSurfaces']:
        x,z,ny=item['center']; item['center']=[x+.145*(1-(x/1.14)**2)*(1-((z-2.62)/.58)**2),z,ny-.065]
    head['eyelidRuntimeReviewRequired']='Sculpted asymmetric lids require ellipsoid correction review before installation'
    return objects


def reset(rig, objects):
    for b in rig.pose.bones: b.rotation_mode='QUATERNION'; b.rotation_quaternion=(1,0,0,0)
    for ob in objects:
        if ob.type=='MESH' and ob.data.shape_keys:
            for key in ob.data.shape_keys.key_blocks: key.value=0
    bpy.context.view_layer.update()


def rotate(rig,name,axis,angle):
    b=rig.pose.bones[name]; q=b.bone.matrix_local.to_quaternion()
    b.rotation_quaternion=q.inverted()@Quaternion(axis,angle)@q


def expression(objects, values):
    for ob in objects:
        if ob.type=='MESH' and ob.data.shape_keys:
            for key in ob.data.shape_keys.key_blocks:
                key.value=values.get(key.name,0)
    bpy.context.view_layer.update()


def positions(obj):
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return np.array([tuple(v.co) for v in evaluated.data.vertices])


def validate(rig,objects):
    reset(rig,objects)
    meshes=[o for o in objects if o.type=='MESH']
    totals=[sum(g.weight for g in v.groups) for o in meshes for v in o.data.vertices]
    report=dict(status='review-only',installationApproved=False,bones=len(rig.data.bones),
                vertices=sum(len(o.data.vertices) for o in meshes),weightMaxError=max(abs(t-1) for t in totals),
                finiteWeights=bool(np.isfinite(totals).all()),reference=str(REF.relative_to(ROOT)))
    baseline={o.name:positions(o) for o in meshes}
    rotate(rig,'UpperArm.L',(0,1,0),-1.0); bpy.context.view_layer.update()
    report['oneSidedArm']={o.name:float(np.max(np.linalg.norm(positions(o)-baseline[o.name],axis=1))) for o in meshes}
    reset(rig,objects)
    tongue=next(o for o in meshes if o.name=='Tongue')
    tb=positions(tongue); roots=np.where(tb[:,1]>tb[:,1].max()-.0001)[0]
    checks={}
    for name,values in {'jaw':{'jawOpen':1},'blink':{'eyeBlinkLeft':1,'eyeBlinkRight':1},
                        'smile':{'jawOpen':.5,'mouthSmileLeft':1,'mouthSmileRight':1},
                        'pucker':{'mouthPucker':1,'mouthFunnel':.5},
                        'tongue-blink':{'tongueOut':1,'jawOpen':.7,'eyeBlinkLeft':1}}.items():
        expression(objects,values)
        checks[name]={'finiteGeometry':all(bool(np.isfinite(positions(o)).all()) for o in meshes),
                      'tongueRootDrift':float(np.max(np.linalg.norm(positions(tongue)[roots]-tb[roots],axis=1)))}
    report['facialCombinations']=checks
    report['independentJoints']={}
    for bone,obj_name in [('Forearm.L','Clay continuous flipper L'),('Hand.L','Clay continuous flipper L'),('Thigh.L','Clay flared leg L'),('Shin.L','Clay flared leg L'),('Foot.L','Clay flared leg L')]:
        reset(rig,objects);rotate(rig,bone,(1,0,0),.5);bpy.context.view_layer.update()
        target=next(o for o in meshes if o.name==obj_name)
        other=next(o for o in meshes if o.name==obj_name[:-1]+'R')
        report['independentJoints'][bone]={'drivenMaxDisplacement':float(np.max(np.linalg.norm(positions(target)-baseline[target.name],axis=1))),
                                        'oppositeMaxDisplacement':float(np.max(np.linalg.norm(positions(other)-baseline[other.name],axis=1)))}
    report['knownLimitations']=['Single front reference cannot determine hidden anatomy exactly.',
       'Continuous flippers preserve reference anatomy; no separate fingers are invented.',
       'Review sculpt needs artistic approval; facial extremes and shoulder joins need visual assessment.',
       'Fine reference-derived color is embedded; procedural bump is Blender-only.',
       'Lids are intentionally asymmetric and the runtime ellipsoid correction needs separate visual review.',
       'No browser, physical tracking or Orin performance approval in this build.']
    reset(rig,objects)
    (QA/'clay-rig-validation.json').write_text(json.dumps(report,indent=2))
    print('CLAY_VALIDATION',json.dumps(report),flush=True)


def validate_export():
    data=(OUT/'clay-review.glb').read_bytes()
    size=struct.unpack_from('<I',data,12)[0]
    doc=json.loads(data[20:20+size]);binary=data[28+size:]
    def values(index):
        a=doc['accessors'][index];n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
        dtype={5121:'u1',5123:'<u2',5125:'<u4',5126:'<f4'}[a['componentType']]
        out=np.zeros((a['count'],n),dtype=dtype)
        if 'bufferView' in a:
            view=doc['bufferViews'][a['bufferView']];offset=view.get('byteOffset',0)+a.get('byteOffset',0)
            stride=view.get('byteStride',np.dtype(dtype).itemsize*n)
            out[:]=np.ndarray(out.shape,dtype=dtype,buffer=binary,offset=offset,strides=(stride,np.dtype(dtype).itemsize))
        if 'sparse' in a:
            s=a['sparse'];indices=s['indices'];v=s['values'];it={5121:'u1',5123:'<u2',5125:'<u4'}[indices['componentType']]
            inds=np.frombuffer(binary,dtype=it,count=s['count'],offset=doc['bufferViews'][indices['bufferView']].get('byteOffset',0)+indices.get('byteOffset',0))
            vals=np.frombuffer(binary,dtype=dtype,count=s['count']*n,offset=doc['bufferViews'][v['bufferView']].get('byteOffset',0)+v.get('byteOffset',0)).reshape(-1,n)
            out[inds]=vals
        return out
    weights=[];finite=True;channels=set()
    for mesh in doc['meshes']:
        assert not any(mesh.get('weights',[])), 'Nonneutral export'
        channels.update(mesh.get('extras',{}).get('targetNames',[]))
        for p in mesh['primitives']:
            finite &= bool(np.isfinite(values(p['attributes']['POSITION'])).all())
            weights.extend(np.abs(values(p['attributes']['WEIGHTS_0']).sum(axis=1)-1).tolist())
            for target in p.get('targets',[]):finite &= bool(np.isfinite(values(target['POSITION'])).all())
    assert finite and max(weights)<1e-5
    assert len(doc['skins'][0]['joints'])==18 and len(channels)==52
    assert all('bufferView' in image and 'uri' not in image for image in doc['images'])
    report={'finiteGeometryAndMorphs':finite,'normalizedSkinMaxError':max(weights),'bones':18,'uniqueFacialChannels':len(channels),
            'embeddedImages':len(doc['images']),'bytes':len(data),'sceneCount':len(doc['scenes']),
            'noCameraOrReferenceBackdrop':not any('camera' in n or 'reference -' in n.get('name','').lower() for n in doc['nodes'])}
    (QA/'clay-glb-validation.json').write_text(json.dumps(report,indent=2))
    print('CLAY_GLB_VALIDATION',json.dumps(report),flush=True)


def studio():
    scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=32
    scene.render.resolution_x=800; scene.render.resolution_y=1000; scene.render.resolution_percentage=100
    scene.world=bpy.data.worlds.new('Clay review world'); scene.world.color=(.26,.26,.26)
    scene.view_settings.view_transform='AgX'
    bpy.ops.object.camera_add(location=(0,-7,2.25)); cam=bpy.context.object
    cam.data.type='ORTHO';cam.data.ortho_scale=3.65;scene.camera=cam
    cam.rotation_euler=(Vector((0,0,1.61))-cam.location).to_track_quat('-Z','Y').to_euler()
    for p,energy,size in [((-3,-4,6),500,4),((3,-2,4),270,3),((1,3,4),400,3)]:
        bpy.ops.object.light_add(type='AREA',location=p); ob=bpy.context.object
        ob.data.energy=energy;ob.data.shape='DISK';ob.data.size=size
        ob.rotation_euler=(Vector((0,0,1.6))-ob.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.mesh.primitive_plane_add(size=200);floor=bpy.context.object
    floor.name='Review stage - excluded from GLB';floor.location.z=.002
    floor.data.materials.append(material('Review neutral gray','#b6bab9',.85))
    return cam


def main():
    for folder in [QA,OUT,BLENDS]: folder.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version=0
    skin=texture();rig=skeleton();objects=[rig,*body(rig,skin),*facial(rig,skin)]
    validate(rig,objects)
    export(OUT/'clay-review.glb',objects,True,morph_normals=True)
    validate_export()
    reset(rig,objects);cam=studio()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLENDS/'clay-review.blend'))
    for case in ['neutral','three-quarter','profile','left-arm','tongue-blink','smile']:
        reset(rig,objects)
        cam.location=(0,-7,2.25)
        if case=='three-quarter':cam.location=(4,-6,2.4)
        if case=='profile':cam.location=(7,-.8,2.3)
        cam.rotation_euler=(Vector((0,0,1.61))-cam.location).to_track_quat('-Z','Y').to_euler()
        if case=='left-arm':rotate(rig,'UpperArm.L',(0,1,0),-1.0)
        if case=='tongue-blink':expression(objects,{'jawOpen':.7,'tongueOut':1,'eyeBlinkLeft':1})
        if case=='smile':expression(objects,{'jawOpen':.4,'mouthSmileLeft':1,'mouthSmileRight':1})
        bpy.context.view_layer.update();bpy.context.scene.render.filepath=str(QA/f'clay-{case}.png')
        bpy.ops.render.render(write_still=True)
    reset(rig,objects)


if __name__=='__main__': main()
