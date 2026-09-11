"""Isolated volumetric Glass study, shaped from the supplied single-view reference.

Run with Blender --background --factory-startup --python this_file.py.
The source image is neither projected nor exported. Review only, not approved.
"""
import json
import math
from pathlib import Path
import struct
import sys

import bpy
import numpy as np
from mathutils import Vector, Quaternion

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_avatar_fleet import Mesh, material, export, CHANNELS
from build_local_characters import face, bind, uv, smooth, pose

QA = ROOT / '.context/qa/reference-characters'
OUT = ROOT / 'assets/reference-characters'
BLENDS = ROOT / 'blender/reference-characters'
C = dict(head=(.93, .66, .80), hz=2.39, power=.85,
         eyes=(.405, -.215, .287, .105, .345), eye='#031110', pupil='#031110',
         sleep=.22, mouth=(.18, -.675, .013), body=.23, leg=.64, arm=.61)


def materials():
    mats = {k: material('Glass ' + k, tint, rough) for k, tint, rough in [
        ('skin', '#035665', .115), ('lip', '#02383c', .13),
        ('eye', '#001411', .07), ('pupil', '#001411', .07),
        ('upper', '#066471', .105), ('lower', '#066471', .105),
        ('limb', '#2498a6', .07), ('cavity', '#010d0e', .5),
        ('tongue', '#207779', .27), ('teeth', '#d9ece0', .21) ]}
    rng = np.random.default_rng(813)
    size = 1024
    tex = np.empty((size, size, 4), dtype=np.float32)
    tex[:] = (.004, .105, .125, 1)
    noise = rng.random((size, size))
    tex[:, :, :3] *= (.82 + noise[:, :, None] * .32)
    flecks = noise > .992
    tex[flecks, :3] = (.025, .48, .61)
    tex[noise > .9992, :3] = (.81, .32, .06)
    im = bpy.data.images.new('Glass embedded turquoise mineral flecks', width=size, height=size)
    im.pixels.foreach_set(tex.ravel()); im.update(); im.pack()
    for name in ['skin', 'upper', 'lower', 'limb']:
        p = mats[name].node_tree.nodes.get('Principled BSDF')
        p.inputs['Transmission Weight'].default_value = .72 if name == 'limb' else .035
        p.inputs['IOR'].default_value = 1.46
        p.inputs['Coat Weight'].default_value = .85
        p.inputs['Coat Roughness'].default_value = .075
        p.inputs['Metallic'].default_value = .24 if name != 'limb' else 0
        if name == 'skin':
            t = mats[name].node_tree.nodes.new('ShaderNodeTexImage'); t.image = im
            mats[name].node_tree.links.new(t.outputs['Color'], p.inputs['Base Color'])
    return mats


def skeleton():
    data = bpy.data.armatures.new('Glass skeleton')
    rig = bpy.data.objects.new('AvatarRig', data); bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig; rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    def bone(name, a, b, parent=None):
        ob = data.edit_bones.new(name); ob.head = a; ob.tail = b
        if parent: ob.parent = data.edit_bones[parent]
        ob.align_roll(Vector((0, -1, 0)))
        return ob
    bone('Root', (0,0,0), (0,0,.15))
    bone('Hips', (0,0,.88), (0,0,1.02), 'Root')
    bone('Spine', (0,0,1.02), (0,0,1.22), 'Hips')
    bone('Chest', (0,0,1.22), (0,0,1.45), 'Spine')
    bone('Neck', (0,0,1.45), (0,0,1.68), 'Chest')
    bone('Head', (0,0,1.68), (0,0,2.82), 'Neck')
    chains = {}
    for side, s in [('L',1), ('R',-1)]:
        bone('UpperArm.'+side, (s*.155,0,1.35), (s*.46,0,1.35), 'Chest')
        bone('Forearm.'+side, (s*.46,0,1.35), (s*.755,0,1.35), 'UpperArm.'+side)
        bone('Hand.'+side, (s*.755,0,1.35), (s*.88,0,1.35), 'Forearm.'+side)
        bone('Thigh.'+side, (s*.17,0,.90), (s*.205,0,.49), 'Hips')
        bone('Shin.'+side, (s*.205,0,.49), (s*.235,0,.16), 'Thigh.'+side)
        bone('Foot.'+side, (s*.235,0,.16), (s*.235,-.19,.085), 'Shin.'+side)
        for digit, offset, length in [('Index',-.063,.145), ('Middle',0,.18), ('Ring',.063,.14)]:
            chains[side,digit] = [Vector((s*(.857+length*t), offset*(1+.65*t),1.35)) for t in [0,.4,.73,1]]
        chains[side,'Thumb'] = [Vector((s*x,y,1.35)) for x,y in [(.78,-.057),(.80,-.11),(.84,-.16),(.88,-.18)]]
        for digit in ['Thumb','Index','Middle','Ring']:
            pts = chains[side,digit]
            for j in range(3):
                finger=bone(f'{digit}{j+1}.{side}', pts[j], pts[j+1], 'Hand.'+side if j==0 else f'{digit}{j}.{side}')
                finger.align_roll(Vector((0,0,s)))
    bpy.ops.object.mode_set(mode='OBJECT'); rig.select_set(False); rig.show_in_front = True
    for b in rig.data.bones:
        if any(b.name.startswith(d) for d in ['Thumb','Index','Middle','Ring']):
            b['fingerCurlRadians'] = .80
    rig['rigVersion'] = 'reference-glass-study-2'; rig['installationApproved'] = False
    return rig, chains


def body(rig, mats):
    verts=[]; edges=[]; radii=[]
    def node(p,r,parent=None):
        idx=len(verts); verts.append(p); radii.append(r)
        if parent is not None: edges.append((parent,idx))
        return idx
    hip=node((0,0,.92),(.22,.155))
    waist=node((0,0,1.08),(.21,.14),hip)
    chest=node((0,0,1.35),(.115,.09),waist)
    neck=node((0,0,1.53),(.068,.065),chest)
    node((0,0,1.69),(.075,.075),neck)
    for s in [-1,1]:
        p=chest
        for x,r in [(.20,.085),(.32,.068),(.46,.056),(.59,.047),(.73,.038),(.80,.042)]:
            p=node((s*x,0,1.35),(r,r),p)
        p=hip
        for x,z,r in [(.17,.83,.071),(.185,.67,.060),(.205,.49,.054),(.22,.30,.046),(.235,.14,.058)]:
            p=node((s*x,0,z),(r,r*.91),p)
    data=bpy.data.meshes.new('Glass branching body cage'); data.from_pydata(verts,edges,[]); data.update()
    ob=bpy.data.objects.new('Glass continuous body',data); bpy.context.collection.objects.link(ob)
    bpy.context.view_layer.objects.active=ob; ob.select_set(True)
    mod=ob.modifiers.new('Continuous shoulder hip junctions','SKIN'); mod.use_smooth_shade=True
    for v,r in zip(data.skin_vertices[0].data,radii): v.radius=r
    data.skin_vertices[0].data[hip].use_root=True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    sub=ob.modifiers.new('Rounded glass support loops','SUBSURF'); sub.levels=3
    bpy.ops.object.modifier_apply(modifier=sub.name); ob.select_set(False)
    bodymat=mats['skin'].copy(); bodymat.name='Glass continuous body color'
    p=bodymat.node_tree.nodes.get('Principled BSDF')
    for link in list(p.inputs['Base Color'].links):bodymat.node_tree.links.remove(link)
    attr=bodymat.node_tree.nodes.new('ShaderNodeVertexColor'); attr.layer_name='GlassColor'
    bodymat.node_tree.links.new(attr.outputs['Color'],p.inputs['Base Color'])
    p.inputs['Transmission Weight'].default_value=.52
    ob.data.materials.append(bodymat)
    colors=ob.data.color_attributes.new(name='GlassColor',type='FLOAT_COLOR',domain='POINT')
    for v,entry in zip(ob.data.vertices,colors.data):
        t=max(1-smooth(.72,1.00,v.co.z),smooth(.35,.67,abs(v.co.x)))
        a=Vector((.002,.044,.051)); b=Vector((.025,.245,.275))
        entry.color=(*a.lerp(b,t),1)
    for poly in ob.data.polygons:
        poly.use_smooth=True
    def weights(p):
        x,y,z=p; side='L' if x>=0 else 'R'; x=abs(x)
        if z>1.45:
            t=smooth(1.46,1.63,z); return {'Neck':1-t,'Head':t}
        if z>1.18 and x>.11:
            a=smooth(.11,.22,x); e=smooth(.38,.53,x); h=smooth(.71,.80,x)
            return {'Chest':1-a, 'UpperArm.'+side:a*(1-e),'Forearm.'+side:a*e*(1-h),'Hand.'+side:a*e*h}
        if z<.92 and x>.09:
            a=1-smooth(.79,.93,z); k=1-smooth(.41,.57,z); f=1-smooth(.12,.22,z)
            return {'Hips':1-a,'Thigh.'+side:a*(1-k),'Shin.'+side:a*k*(1-f),'Foot.'+side:a*k*f}
        t=smooth(.97,1.30,z); return {'Hips':1-t,'Chest':t}
    bind(ob,rig,weights); uv(ob); ob['armCollisionSurface']=True
    bake_body_flecks(ob,bodymat)
    mesh=Mesh()
    for side,s in [('L',1),('R',-1)]:
        mesh.ellipsoid((s*.235,-.065,.108),(.128,.197,.09),mats['limb'],{'Foot.'+side:1},n=40,rings=24,power=.78)
        for offset in [-.058,0,.058]:
            mesh.ellipsoid((s*.235+offset,-.177,.093),(.036,.084,.043),mats['limb'],{'Foot.'+side:1},n=20,rings=12)
    feet=mesh.object('Glass softly webbed feet',rig); uv(feet)
    return [ob,feet]


def bake_body_flecks(ob,mat):
    """Rasterize rest-position colors into UV space for a portable GLB material."""
    size=1024; rng=np.random.default_rng(572)
    rgba=np.zeros((size,size,4),dtype=np.float32); rgba[:]=(.004,.075,.09,1)
    noise=rng.random((size,size)); ob.data.calc_loop_triangles()
    uvdata=ob.data.uv_layers.active.data
    for tri in ob.data.loop_triangles:
        uvp=np.array([uvdata[i].uv[:] for i in tri.loops])*size
        lo=np.maximum(np.floor(uvp.min(axis=0)).astype(int),0)
        hi=np.minimum(np.ceil(uvp.max(axis=0)).astype(int),size-1)
        if np.any(hi<lo):continue
        yy,xx=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
        a,b,c=uvp; den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-9:continue
        wa=((b[1]-c[1])*(xx+.5-c[0])+(c[0]-b[0])*(yy+.5-c[1]))/den
        wb=((c[1]-a[1])*(xx+.5-c[0])+(a[0]-c[0])*(yy+.5-c[1]))/den
        wc=1-wa-wb; mask=(wa>=-.025)&(wb>=-.025)&(wc>=-.025)
        coords=np.array([ob.data.vertices[i].co[:] for i in tri.vertices])
        pos=wa[:,:,None]*coords[0]+wb[:,:,None]*coords[1]+wc[:,:,None]*coords[2]
        def easing(a,b,x):
            t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
        t=np.maximum(1-easing(.72,1.,pos[:,:,2]),easing(.35,.67,np.abs(pos[:,:,0])))
        rgb=np.array([.003,.050,.065])*(1-t[:,:,None])+np.array([.013,.18,.215])*t[:,:,None]
        flakes=noise[lo[1]:hi[1]+1,lo[0]:hi[0]+1]>.985
        rgb+=flakes[:,:,None]*(1-t[:,:,None])*.75*np.array([.13,.68,.82])
        patch=rgba[lo[1]:hi[1]+1,lo[0]:hi[0]+1,:3];patch[mask]=rgb[mask]
    im=bpy.data.images.new('Glass embedded torso mineral field',width=size,height=size)
    im.pixels.foreach_set(rgba.ravel());im.update();im.pack()
    p=mat.node_tree.nodes.get('Principled BSDF')
    for link in list(p.inputs['Base Color'].links):mat.node_tree.links.remove(link)
    tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=im
    mat.node_tree.links.new(tex.outputs['Color'],p.inputs['Base Color'])
    # The image already includes the rest-position color transition.
    ob.data.color_attributes.remove(ob.data.color_attributes['GlassColor'])


def refine_mouth(facial,mats):
    ob,teeth,tongue=facial; basis=ob.data.shape_keys.key_blocks['Basis']; jaw=ob.data.shape_keys.key_blocks['jawOpen']
    mouthz=C['hz']+C['mouth'][1]
    # The generic oral backwall was taller than this chin. Its silhouette became
    # visible through the glass forehead when the mouth admitted light.
    backwall_start=38*80+22*80+8*64
    for block in ob.data.shape_keys.key_blocks:
        for i in range(backwall_start,backwall_start+24*12):
            block.data[i].co.z=mouthz+(block.data[i].co.z-mouthz)*.25
    for block in tongue.data.shape_keys.key_blocks:
        for v in block.data:v.co.y+=.23;v.co.z+=.035
    for i,v in enumerate(tongue.data.vertices):v.co=tongue.data.shape_keys.key_blocks['Basis'].data[i].co
    moving={mats[k] for k in ['skin','lip','cavity']}
    ids={i for p in ob.data.polygons if ob.data.materials[p.material_index] in moving for i in p.vertices}
    def offset(p):
        x,y,z=p
        lower=1-smooth(mouthz-.015,mouthz+.015,z)
        horizontal=1-smooth(.19,.55,abs(x))
        upperfade=1-smooth(mouthz+.035,mouthz+.23,z)
        depth=1-smooth(.05,.48,y)
        w=horizontal*upperfade*depth
        return Vector((0,-.005*lower*w,-.115*lower*w))
    for i in ids:
        p=basis.data[i].co; jaw.data[i].co=p+offset(p)
    lip_ids=sorted({i for p in ob.data.polygons if ob.data.materials[p.material_index]==mats['lip'] for i in p.vertices})
    # Move each complete lip cross-section together so opening cannot inflate it.
    for start in range(0,len(lip_ids),8):
        ring=lip_ids[start:start+8]; center=sum((basis.data[i].co for i in ring),Vector())/len(ring)
        d=offset(center)
        for i in ring:jaw.data[i].co=basis.data[i].co+d
    for obj,amount in [(teeth,.115),(tongue,.0575)]:
        base=obj.data.shape_keys.key_blocks['Basis']; key=obj.data.shape_keys.key_blocks['jawOpen']
        for i,v in enumerate(base.data):
            d=key.data[i].co-v.co
            key.data[i].co=v.co+d*(amount/(.20 if obj==teeth else .10))


def hands(rig, chains, mats):
    result=[]
    for side,s in [('L',1),('R',-1)]:
        mesh=Mesh()
        mesh.ellipsoid((s*.834,0,1.35),(.099,.098,.041),mats['limb'],{'Hand.'+side:1},n=32,rings=18)
        for digit in ['Thumb','Index','Middle','Ring']:
            pts=chains[side,digit]; axis=pts[-1]-pts[0]
            def w(p):
                t=(Vector(p)-pts[0]).dot(axis)/axis.length_squared
                root=smooth(-.15,.15,t); a=1-smooth(.29,.50,t); c=smooth(.66,.85,t)
                return {'Hand.'+side:1-root,f'{digit}1.{side}':root*a,f'{digit}2.{side}':root*(1-a-c),f'{digit}3.{side}':root*c}
            samples=[pts[0].lerp(pts[-1],i/20) for i in range(21)]
            mesh.tube(samples,[.032+.009*math.sin(math.pi*i/20)-.009*(i/20) for i in range(21)],mats['limb'],w,n=16)
            mesh.ellipsoid(pts[-1],(.034,.036,.028),mats['limb'],{f'{digit}3.{side}':1},n=20,rings=12)
        ob=mesh.object('Glass articulated hand '+side,rig); uv(ob); result.append(ob)
    return result


def eye_rims(rig,mats,surface):
    mesh=Mesh()
    ex,ez,rx,ry,rz=C['eyes']
    for s in [-1,1]:
        cx=s*ex; cy=surface(cx,ez)-.027
        points=[]
        for i in range(97):
            a=2*math.pi*i/96
            x=cx+(rx+.015)*math.cos(a); z=ez+(rz+.014)*math.sin(a)
            points.append((x,cy-.023+.85*(surface(x,z)-surface(cx,ez)), C['hz']+z))
        mesh.tube(points,[.014]*97,mats['upper'],n=12)
    ob=mesh.object('Glass raised oval eye rims',rig); uv(ob)
    return ob


def studio():
    scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=40
    scene.cycles.use_denoising=True
    scene.render.resolution_x=760; scene.render.resolution_y=1040; scene.render.resolution_percentage=100
    scene.world=bpy.data.worlds.new('Glass mint studio'); scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.23,.38,.29,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
    scene.view_settings.view_transform='AgX'
    bpy.ops.object.camera_add(location=(.60,-7,2.65)); camera=bpy.context.object
    camera.rotation_euler=(Vector((0,0,1.61))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type='ORTHO'; camera.data.ortho_scale=3.75; scene.camera=camera
    for loc,energy,size,scale,tint in [((-3,-4,5),650,3,.45,(1,.78,.55)),((3,-4,5),900,2,.32,(.76,1,1)),((1,3,4),1100,3,1,(.55,1,.88))]:
        bpy.ops.object.light_add(type='AREA',location=loc); lamp=bpy.context.object
        lamp.data.energy=energy; lamp.data.shape='RECTANGLE'; lamp.data.size=size; lamp.data.size_y=size*scale; lamp.data.color=tint
        lamp.rotation_euler=(Vector((0,0,1.6))-lamp.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.005)); floor=bpy.context.object
    floor.name='Review floor excluded from export'; floor.data.materials.append(material('Mint review floor','#a8d99a',.8))


def reset(rig,objects):
    pose(rig,'T-Pose')
    for ob in objects:
        if ob.type=='MESH' and ob.data.shape_keys:
            for key in ob.data.shape_keys.key_blocks: key.value=0
    bpy.context.view_layer.update()


def standing(rig):
    pose(rig,'Standing')
    for side,s in [('L',1),('R',-1)]:
        b=rig.pose.bones['Hand.'+side]
        b.rotation_quaternion=Quaternion((0,1,0),s*1.25)
    bpy.context.view_layer.update()


def evaluated(ob):
    deps=bpy.context.evaluated_depsgraph_get(); ev=ob.evaluated_get(deps); mesh=ev.to_mesh()
    result=np.array([tuple(v.co) for v in mesh.vertices]); ev.to_mesh_clear(); return result


def validate(rig,objects):
    reset(rig,objects); meshes=[o for o in objects if o.type=='MESH']
    err=max(abs(sum(g.weight for g in v.groups)-1) for o in meshes for v in o.data.vertices)
    assert err<1e-5
    baseline={o.name:evaluated(o) for o in meshes}
    def swing(name,a):
        b=rig.pose.bones[name]; q=b.bone.matrix_local.to_quaternion()
        b.rotation_quaternion=q.inverted()@Quaternion((0,1,0),a)@q
        bpy.context.view_layer.update()
    swing('UpperArm.L',.8)
    opposite=max(float(np.max(np.abs(evaluated(o)-baseline[o.name]))) for o in meshes if o.name in ['Glass articulated hand R','Face'])
    moved=float(np.max(np.abs(evaluated(bpy.data.objects['Glass articulated hand L'])-baseline['Glass articulated hand L'])))
    assert opposite<1e-6 and moved>.1
    reset(rig,objects)
    left=bpy.data.objects['Glass articulated hand L']; group=left.vertex_groups['Index3.L'].index
    indices=[v.index for v in left.data.vertices if any(g.group==group and g.weight>.99 for g in v.groups)]
    for j in range(1,4): rig.pose.bones[f'Middle{j}.L'].rotation_mode='XYZ'; rig.pose.bones[f'Middle{j}.L'].rotation_euler.x=.7
    bpy.context.view_layer.update()
    finger_drift=float(np.max(np.abs(evaluated(left)[indices]-baseline[left.name][indices])))
    assert finger_drift<1e-6
    middle=left.vertex_groups['Middle3.L'].index
    tips=[v.index for v in left.data.vertices if any(g.group==middle and g.weight>.99 for g in v.groups)]
    curl_depth=float(np.max(np.abs(evaluated(left)[tips,2]-baseline[left.name][tips,2])))
    assert curl_depth>.025, 'Finger must bend out of the open-palm plane'
    reset(rig,objects)
    tongue=bpy.data.objects['Tongue']; key=tongue.data.shape_keys.key_blocks['tongueOut']
    root=max((key.data[i].co-tongue.data.vertices[i].co).length for i in range(20))
    assert root<1e-7
    combinations=[]; mouth_checks=[]
    faceob=bpy.data.objects['Face']; faceob.data.calc_loop_triangles()
    triangles=np.array([tri.vertices[:] for tri in faceob.data.loop_triangles if faceob.data.materials[tri.material_index].name=='Glass skin'])
    base=evaluated(faceob); a=base[triangles]
    normals=np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0]); areas=np.linalg.norm(normals,axis=1)
    valid=areas>1e-9
    for names in [('jawOpen',),('eyeBlinkLeft','eyeBlinkRight','jawOpen'),('mouthSmileLeft','mouthSmileRight','jawOpen'),('jawOpen','tongueOut'),('mouthPucker','mouthFunnel','eyeBlinkLeft')]:
        reset(rig,objects)
        for o in meshes:
            if o.data.shape_keys:
                for name in names:
                    if name in o.data.shape_keys.key_blocks:o.data.shape_keys.key_blocks[name].value=1
        bpy.context.view_layer.update()
        assert all(np.isfinite(evaluated(o)).all() for o in meshes)
        current=evaluated(faceob)[triangles]
        n=np.cross(current[:,1]-current[:,0],current[:,2]-current[:,0])
        inverted=int(np.sum(np.einsum('ij,ij->i',n,normals)[valid]<0))
        mouth_checks.append(dict(channels=list(names),skinTriangleInversions=inverted))
        combinations.append(list(names))
    reset(rig,objects)
    return dict(status='review-only',installationApproved=False,bones=len(rig.data.bones),vertices=sum(len(o.data.vertices) for o in meshes),
                maxWeightError=err,oppositeArmAndHeadDrift=opposite,activeArmMovement=moved,independentFingerTipDrift=finger_drift,fingerCurlDepth=curl_depth,tongueRootDrift=root,
                finiteExpressionCombinations=combinations,mouthTopologyChecks=mouth_checks,limitations=['Single-view hand-built likeness; unseen sides inferred','No physical camera/ZED validation','Extreme self-collision and facial topology approval remain open'])


def validate_export(path):
    raw=path.read_bytes(); length=struct.unpack_from('<I',raw,12)[0]
    doc=json.loads(raw[20:20+length]); binary=raw[28+length:]
    formats={5121:('B',1),5123:('H',2),5125:('I',4),5126:('f',4)}
    counts={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
    def values(idx):
        a=doc['accessors'][idx]; count=counts[a['type']]; fmt,size=formats[a['componentType']]
        data=np.zeros((a['count'],count))
        if 'bufferView' in a:
            view=doc['bufferViews'][a['bufferView']]; offset=view.get('byteOffset',0)+a.get('byteOffset',0)
            stride=view.get('byteStride',size*count)
            for i in range(a['count']):data[i]=struct.unpack_from('<'+fmt*count,binary,offset+i*stride)
        if 'sparse' in a:
            sparse=a['sparse']; indices=sparse['indices']; vals=sparse['values']
            indexfmt,indexsize=formats[indices['componentType']]
            offset=doc['bufferViews'][indices['bufferView']].get('byteOffset',0)+indices.get('byteOffset',0)
            start=doc['bufferViews'][vals['bufferView']].get('byteOffset',0)+vals.get('byteOffset',0)
            for i in range(sparse['count']):
                index=struct.unpack_from('<'+indexfmt,binary,offset+i*indexsize)[0]
                assert index<a['count']; data[index]=struct.unpack_from('<'+fmt*count,binary,start+i*size*count)
        return data
    assert len(doc['scenes'])==1 and len(doc['skins'][0]['joints'])==42
    assert all('camera' not in node for node in doc['nodes'])
    names=set(); weight_error=0
    for mesh in doc['meshes']:
        names.update(mesh.get('extras',{}).get('targetNames',[]))
        assert not any(mesh.get('weights',[]))
        for prim in mesh['primitives']:
            assert np.isfinite(values(prim['attributes']['POSITION'])).all()
            weight_error=max(weight_error,float(np.max(np.abs(values(prim['attributes']['WEIGHTS_0']).sum(axis=1)-1))))
            for target in prim.get('targets',[]):
                for accessor in target.values():assert np.isfinite(values(accessor)).all()
    assert weight_error<1e-5 and set(CHANNELS)<=names
    assert all('bufferView' in im and 'uri' not in im for im in doc.get('images',[]))
    return dict(singleScene=True,joints=42,facialChannels=len(names),neutralMorphs=True,finiteSparseAndDenseMorphs=True,maxSkinWeightError=weight_error,embeddedTextures=len(doc.get('images',[])))


def main():
    for p in [QA,OUT,BLENDS]:p.mkdir(parents=True,exist_ok=True)
    if '--validate-only' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(BLENDS/'glass-review.blend'))
        rig=bpy.data.objects['AvatarRig']; objects=[rig]+[o for o in bpy.context.scene.objects if o.parent==rig]
        report=validate(rig,objects); report['exportValidation']=validate_export(OUT/'glass-review.glb')
        (QA/'glass-validation.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report),flush=True)
        return
    bpy.ops.wm.read_factory_settings(use_empty=True); bpy.context.preferences.filepaths.save_version=0
    mats=materials(); rig,chains=skeleton(); objects=[rig,*body(rig,mats),*hands(rig,chains,mats)]
    facial,surface=face(C,rig,mats); objects+=facial+[eye_rims(rig,mats,surface)]
    refine_mouth(facial,mats)
    # Conform eye backs and lids to the curved skull instead of floating ovals.
    eye_mats={mats[k] for k in ['eye','pupil','upper','lower']}
    eye_indices={i for poly in facial[0].data.polygons if facial[0].data.materials[poly.material_index] in eye_mats for i in poly.vertices}
    ex,ez,rx,ry,rz=C['eyes']
    for block in facial[0].data.shape_keys.key_blocks:
        for i in eye_indices:
            v=block.data[i]; cx=ex if v.co.x>0 else -ex
            v.co.y+=.85*(surface(v.co.x,v.co.z-C['hz'])-surface(cx,ez))
    # Tuck tooth crowns behind the shallow neutral opening near the rounded chin.
    teeth=facial[1]
    for block in teeth.data.shape_keys.key_blocks:
        for i,v in enumerate(block.data):
            v.co.y+=.15
    for i,v in enumerate(teeth.data.vertices):v.co=teeth.data.shape_keys.key_blocks['Basis'].data[i].co
    # Broaden the upper dome and taper the chin, including all facial deformations.
    for ob in facial[:1]:
        for block in ob.data.shape_keys.key_blocks:
            for v in block.data:v.co.x*=1+.085*(v.co.z-C['hz'])/C['head'][2]
        for i,v in enumerate(ob.data.vertices):v.co=ob.data.shape_keys.key_blocks['Basis'].data[i].co
    report=validate(rig,objects)
    export(OUT/'glass-review.glb',objects,True,morph_normals=True)
    report['exportValidation']=validate_export(OUT/'glass-review.glb')
    studio(); reset(rig,objects); standing(rig)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLENDS/'glass-review.blend'))
    for case in ['neutral','three-quarter','arm-fingers','full-jaw','smile-jaw','tongue-blink']:
        reset(rig,objects);standing(rig)
        camera=bpy.context.scene.camera
        camera.location=(.60,-7,2.65) if case!='three-quarter' else (4,-6,2.65)
        camera.rotation_euler=(Vector((0,0,1.61))-camera.location).to_track_quat('-Z','Y').to_euler()
        if case=='arm-fingers':
            b=rig.pose.bones['UpperArm.L']; b.rotation_quaternion=(1,0,0,0)
            for j in range(1,4):
                b=rig.pose.bones[f'Middle{j}.L'];b.rotation_mode='XYZ';b.rotation_euler.x=.7
        if case in ['tongue-blink','full-jaw','smile-jaw']:
            for o in facial:
                names={'tongue-blink':['jawOpen','tongueOut','eyeBlinkLeft','eyeBlinkRight'],
                       'full-jaw':['jawOpen'],'smile-jaw':['jawOpen','mouthSmileLeft','mouthSmileRight']}[case]
                for name in names:
                    if name in o.data.shape_keys.key_blocks:o.data.shape_keys.key_blocks[name].value=1
        bpy.context.view_layer.update();bpy.context.scene.render.filepath=str(QA/f'glass-{case}.png')
        bpy.ops.render.render(write_still=True)
    (QA/'glass-validation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
