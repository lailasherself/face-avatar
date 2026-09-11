"""Continue the approved Clay head in live Blender MCP, stage by stage.

Never invokes the rejected generic character/face builders or changes the roster.
The source PNG guides contours; mineral color is a bakeable 3D material.
"""
import bpy
import bmesh
import math
import json
import sys
from pathlib import Path
from mathutils import Vector, Quaternion

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / '.context/qa/clay-complete'
BLEND = ROOT / 'blender/likeness-trials/clay-body-rig.blend'
GLB = ROOT / 'assets/likeness-trials/clay-body-rig.glb'
DZ = 2.896
PROMPT = 'okay go ahead and get going to do all of that and dont get back to me until its done'
ARM = {'R': [(-.095,-.015,2.105),(-.337,-.055,1.43),(-.421,-.070,.96),(-.400,-.074,.735)],
       'L': [(.145,.010,2.02),(.377,-.015,1.39),(.478,-.040,.97),(.450,-.055,.755)]}


def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)))
    return t*t*(3-2*t)


def profile(points,x):
    for i,(a,b) in enumerate(zip(points,points[1:])):
        if x<=b[0]:
            p=points[max(0,i-1)];q=points[min(len(points)-1,i+2)]
            t=max(0,(x-a[0])/(b[0]-a[0]))
            m=(b[1]-p[1])/(b[0]-p[0])*(b[0]-a[0])
            n=(q[1]-a[1])/(q[0]-a[0])*(b[0]-a[0])
            return (2*t**3-3*t*t+1)*a[1]+(t**3-2*t*t+t)*m+(-2*t**3+3*t*t)*b[1]+(t**3-t*t)*n
    return points[-1][1]


def obj(name):
    return bpy.context.scene.objects[name]


def mesh(name,verts,faces,mat):
    data=bpy.data.meshes.new(name)
    data.from_pydata(verts,[],faces);data.update()
    bm=bmesh.new();bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(data);bm.free()
    o=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat)
    for p in data.polygons:p.use_smooth=True
    return o


def closed_rings(name,rings,mat):
    n=len(rings[0]);verts=[tuple(p) for ring in rings for p in ring];faces=[]
    for i in range(len(rings)-1):
        for j in range(n):faces.append((i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j))
    for row,reverse in ((0,True),(len(rings)-1,False)):
        center=sum((Vector(p) for p in rings[row]),Vector())/n
        c=len(verts);verts.append(tuple(center))
        for j in range(n):
            f=(row*n+j,row*n+(j+1)%n,c)
            faces.append(tuple(reversed(f)) if reverse else f)
    return mesh(name,verts,faces,mat)


def prepare():
    QA.mkdir(parents=True,exist_ok=True);GLB.parent.mkdir(parents=True,exist_ok=True)
    s=bpy.context.scene
    assert not any(o.type=='ARMATURE' for o in s.objects),'Start from the approved unrigged file'
    s.name='Clay - Approved Head Body Continuation'
    for o in list(s.objects):
        if o.type=='MESH':
            for v in o.data.vertices:v.co.z+=DZ
            if 'Traced Head' in o.name:o.name='Clay Skin'
            elif 'Left Eye' in o.name:o.name='Clay Eye R'
            elif 'Right Eye' in o.name:o.name='Clay Eye L'
            else:o.name='Clay Mouth Study'
        elif o.type=='EMPTY':o.location.z+=DZ
    s['status']='Approved head continued into isolated body/rig, not installation approved.'
    s['source_reference']='c0oVR0 Clay iron-red Georgia PNG, one view; unseen anatomy inferred.'
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    print('Original approved head file preserved; new body/rig file started.')


def body():
    h=obj('Clay Skin');skin=h.data.materials[0]
    bm=bmesh.new();bm.from_mesh(h.data)
    # Join the neck to an actual head boundary, not an intersecting neck tube.
    zcut=2.315
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,plane_co=(0,0,zcut),plane_no=(0,0,1),clear_inner=True)
    rim=[v for v in bm.verts if abs(v.co.z-zcut)<1e-5 and any(e.is_boundary for e in v.link_edges)]
    assert len(rim)>12
    center=sum((v.co for v in rim),Vector())/len(rim)
    rim.sort(key=lambda v:math.atan2((v.co.y-center.y)/.12,(v.co.x-center.x)/.16))
    angles=[math.atan2((v.co.y-center.y)/.12,(v.co.x-center.x)/.16) for v in rim]
    previous=rim
    widths=[(.532,.15),(.56,.265),(.66,.337),(.83,.367),(1.04,.364),(1.30,.313),(1.59,.239),(1.85,.166),(2.03,.122),(2.19,.108),(2.26,.119),(2.315,.16)]
    for row in range(1,83):
        z=zcut-(zcut-.535)*row/82
        radius=max(.01,profile(widths,z));blend=smooth(2.20,zcut,z)
        current=[]
        for j,a in enumerate(angles):
            p=Vector((.025+radius*math.cos(a),.015+radius*.77*math.sin(a),z))
            at_cut=Vector((.025+.16*math.cos(a),.015+.16*.77*math.sin(a),zcut))
            delta=rim[j].co-at_cut
            p.x+=delta.x*blend;p.y+=delta.y*blend
            current.append(bm.verts.new(p))
        for j in range(len(rim)):
            k=(j+1)%len(rim);bm.faces.new((previous[j],previous[k],current[k],current[j]))
        previous=current
    c=bm.verts.new((.025,.015,.529))
    for j in range(len(previous)):bm.faces.new((previous[j],previous[(j+1)%len(previous)],c))
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(h.data);bm.free();h.data.update()
    for p in h.data.polygons:p.use_smooth=True
    h['armCollisionSurface']=True
    for side,points in ARM.items():
        ztop=points[0][2];zbottom=points[-1][2]
        radii=[(0,.022),(.07,.027),(.23,.041),(.44,.052),(.63,.066),(.79,.092),(.88,.106),(.95,.083),(.995,.027),(1,.006)]
        rings=[]
        for i in range(81):
            t=i/80;z=ztop+(zbottom-ztop)*t
            xp=profile(sorted((p[2],p[0]) for p in points),z)
            yp=profile(sorted((p[2],p[1]) for p in points),z)
            r=profile(radii,t)
            rings.append([(xp+r*math.cos(j*math.tau/48),yp+r*.78*math.sin(j*math.tau/48),z) for j in range(48)])
        arm=closed_rings('Clay Flipper '+side,rings,skin)
        arm['anatomy']='Continuous flipper, independently articulated elbow and wrist; no separated reference digits.'
        rings=[]
        sign=1 if side=='L' else -1
        for i in range(45):
            z=.018+.57*i/44
            r=profile([(.018,.215),(.04,.236),(.085,.236),(.20,.186),(.36,.13),(.49,.116),(.588,.116)],z)
            x=sign*(.265-.055*i/44)+.01
            y=-.065*(1-i/44)
            rings.append([(x+r*math.cos(j*math.tau/56),y+r*.79*math.sin(j*math.tau/56),z) for j in range(56)])
        closed_rings('Clay Leg '+side,rings,skin)
    print('Connected head/neck/torso, two reference-shaped flippers, and two flared feet built.')


def skeleton():
    data=bpy.data.armatures.new('Clay Body Skeleton');rig=bpy.data.objects.new('AvatarRig',data)
    bpy.context.scene.collection.objects.link(rig)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.object.mode_set(mode='EDIT')
    def bone(name,a,b,parent=None):
        e=data.edit_bones.new(name);e.head=a;e.tail=b
        if parent:e.parent=data.edit_bones[parent]
    bone('Root',(0,0,0),(0,0,.2))
    bone('Hips',(.025,.015,.55),(.025,.015,.83),'Root')
    bone('Spine',(.025,.015,.83),(.025,.015,1.43),'Hips')
    bone('Chest',(.025,.015,1.43),(.025,.015,2.03),'Spine')
    bone('Neck',(.025,.015,2.03),(.015,-.01,2.34),'Chest')
    bone('Head',(.015,-.01,2.34),(.015,-.01,3.30),'Neck')
    for side,p in ARM.items():
        bone('UpperArm.'+side,p[0],p[1],'Chest');bone('Forearm.'+side,p[1],p[2],'UpperArm.'+side);bone('Hand.'+side,p[2],p[3],'Forearm.'+side)
        sign=1 if side=='L' else -1
        bone('Thigh.'+side,(sign*.21+.01,0,.58),(sign*.24+.01,-.025,.33),'Hips')
        bone('Shin.'+side,(sign*.24+.01,-.025,.33),(sign*.26+.01,-.06,.13),'Thigh.'+side)
        bone('Foot.'+side,(sign*.26+.01,-.06,.13),(sign*.26+.01,-.20,.06),'Shin.'+side)
    bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
    rig.show_in_front=True;rig['rigVersion']='clay-approved-likeness-1';rig['installationApproved']=False
    rig['referenceAnatomy']='Flippers: independent upper arm, forearm and wrist; no invented human fingers.'
    for side in ARM:data.bones['UpperArm.'+side]['armCollisionRestContact']=True
    for o in bpy.context.scene.objects:
        if o.type!='MESH':continue
        groups={b.name:o.vertex_groups.new(name=b.name) for b in data.bones}
        for v in o.data.vertices:
            z=v.co.z
            if o.name.startswith('Clay Flipper'):
                side=o.name[-1];p=ARM[side]
                elbow=1-smooth(p[1][2]-.13,p[1][2]+.13,z)
                hand=1-smooth(p[2][2]-.075,p[2][2]+.075,z)
                w={'UpperArm.'+side:1-elbow,'Forearm.'+side:elbow*(1-hand),'Hand.'+side:elbow*hand}
            elif o.name.startswith('Clay Leg'):
                side=o.name[-1];knee=1-smooth(.25,.41,z);foot=1-smooth(.09,.22,z)
                w={'Thigh.'+side:1-knee,'Shin.'+side:knee*(1-foot),'Foot.'+side:knee*foot}
            elif o.name=='Clay Skin':
                if z<1.35:t=smooth(.65,1.15,z);w={'Hips':1-t,'Spine':t}
                elif z<1.97:t=smooth(1.35,1.83,z);w={'Spine':1-t,'Chest':t}
                elif z<2.22:t=smooth(1.97,2.17,z);w={'Chest':1-t,'Neck':t}
                else:t=smooth(2.22,2.46,z);w={'Neck':1-t,'Head':t}
            else:w={'Head':1}
            for n,value in w.items():
                if value>0:groups[n].add([v.index],value,'REPLACE')
        mod=o.modifiers.new('Body deformation','ARMATURE');mod.object=rig
        o.parent=rig
    print('18-bone body rig bound with explicitly isolated left/right arm weights.')


def mineral_material():
    h=obj('Clay Skin');m=h.data.materials[0];m.name='Clay Iron Red Mineral'
    n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF')
    p.inputs['Roughness'].default_value=.64;p.inputs['Specular IOR Level'].default_value=.27
    tex=n.new('ShaderNodeTexCoord')
    noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=42;noise.inputs['Detail'].default_value=3
    l.new(tex.outputs['Object'],noise.inputs['Vector'])
    ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.18;ramp.color_ramp.elements[0].color=(.13,.016,.005,1)
    ramp.color_ramp.elements[1].position=.8;ramp.color_ramp.elements[1].color=(.38,.065,.023,1)
    l.new(noise.outputs['Fac'],ramp.inputs[0])
    grain=n.new('ShaderNodeTexVoronoi');grain.distance='EUCLIDEAN';grain.inputs['Scale'].default_value=330
    l.new(tex.outputs['Object'],grain.inputs['Vector'])
    speck=n.new('ShaderNodeValToRGB');speck.color_ramp.elements[0].position=.14;speck.color_ramp.elements[0].color=(.88,.55,.27,1)
    speck.color_ramp.elements[1].position=.26;speck.color_ramp.elements[1].color=(0,0,0,1)
    l.new(grain.outputs['Distance'],speck.inputs[0])
    mix=n.new('ShaderNodeMixRGB');mix.blend_type='ADD';mix.inputs[0].default_value=.42
    l.new(ramp.outputs[0],mix.inputs[1]);l.new(speck.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],p.inputs['Base Color'])
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.20;bump.inputs['Distance'].default_value=.002
    l.new(grain.outputs['Distance'],bump.inputs['Height']);l.new(bump.outputs[0],p.inputs['Normal'])
    m['source']='Procedural mineral material matched to reference colors, no projected source face/background.'
    print('3D iron-red grain, fine gold mineral flecks and micro-normal material created.')


def reset():
    for o in bpy.context.scene.objects:
        if o.type=='ARMATURE':
            for b in o.pose.bones:b.rotation_mode='QUATERNION';b.rotation_quaternion=(1,0,0,0)
        if o.type=='MESH' and o.data.shape_keys:
            for k in o.data.shape_keys.key_blocks:k.value=0
    bpy.context.view_layer.update()


def rotate(name,axis,angle):
    b=obj('AvatarRig').pose.bones[name];b.rotation_mode='QUATERNION'
    q=b.bone.matrix_local.to_quaternion();b.rotation_quaternion=q.inverted()@Quaternion(axis,angle)@q


def expression(values):
    for o in bpy.context.scene.objects:
        if o.type=='MESH' and o.data.shape_keys:
            for k in o.data.shape_keys.key_blocks:k.value=values.get(k.name,0)
    bpy.context.view_layer.update()


def view(full=True,angle=False):
    s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=32
    s.render.resolution_x=1100;s.render.resolution_y=1400;s.render.resolution_percentage=100
    camera=s.camera;camera.location=(4,-8,3.2) if angle else (0,-8,1.80)
    target=Vector((0,0,1.8));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=4.2
    for o in s.objects:
        if o.type=='LIGHT':
            if 'Key' in o.name:o.location=(-3,-4,6)
            elif 'Fill' in o.name:o.location=(3,-3,3)
            else:o.location=(1,3,5)
            o.rotation_euler=(Vector((0,0,2))-o.location).to_track_quat('-Z','Y').to_euler()
        if o.type in {'ARMATURE','CAMERA','LIGHT'}:o.hide_set(True)
    for a in bpy.context.screen.areas:
        if a.type=='VIEW_3D':
            sp=a.spaces.active;sp.overlay.show_overlays=True;sp.overlay.show_cursor=False
            sp.region_3d.view_location=(-1.5,0,1.8);sp.region_3d.view_distance=5.8
            sp.region_3d.view_rotation=Quaternion((1,0,0),math.pi/2)
    bpy.context.view_layer.update()


def render(name):
    bpy.context.scene.render.filepath=str(QA/(name+'.png'));bpy.ops.render.render(write_still=True)


def save():
    reset();bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))


def finish_body():
    for side,p in ARM.items():
        o=obj('Clay Flipper '+side);zb=p[-1][2];zt=p[0][2]
        for v in o.data.vertices:
            z=v.co.z;t=(zt-z)/(zt-zb)
            cx=profile(sorted((a[2],a[0]) for a in p),z)
            cy=profile(sorted((a[2],a[1]) for a in p),z)
            if z<zb+.12:
                old=profile([(0,.022),(.07,.027),(.23,.041),(.44,.052),(.63,.066),(.79,.092),(.88,.106),(.95,.083),(.995,.027),(1,.006)],t)
                r=max(.001,.106*math.sqrt(max(0,1-((z-zb-.12)/.12)**2)))
                v.co.x=cx+(v.co.x-cx)*r/old;v.co.y=cy+(v.co.y-cy)*r/old
            shift=(.035 if side=='R' else -.04)*(1-t)**5
            v.co.x+=shift
        leg=obj('Clay Leg '+side)
        for v in leg.data.vertices:
            t=smooth(.49,.588,v.co.z);v.co.z+=.09*t
    m=obj('Clay Skin').data.materials[0]
    ramps=[n for n in m.node_tree.nodes if n.type=='VALTORGB']
    ramps[0].color_ramp.elements[0].color=(.085,.007,.0018,1)
    ramps[0].color_ramp.elements[1].color=(.25,.032,.009,1)
    for n in m.node_tree.nodes:
        if n.type=='TEX_NOISE':n.inputs['Scale'].default_value=105
        if n.type=='TEX_VORONOI':n.inputs['Scale'].default_value=155
        if n.type=='MIX_RGB':n.inputs[0].default_value=.80
        if n.type=='BUMP':n.inputs['Strength'].default_value=.12;n.inputs['Distance'].default_value=.001
    print('Rounded flipper tips, tucked shoulder/hip roots, and finer red mineral finish.')


def bind_head(o):
    g=o.vertex_groups.new(name='Head');g.add(list(range(len(o.data.vertices))),1,'REPLACE')
    o.parent=obj('AvatarRig');mod=o.modifiers.new('Body deformation','ARMATURE');mod.object=o.parent


def plain_material(name,color,rough):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough
    return m


def mouth_delta(p,name):
    x,y,z=p;dx=x-.23;zc=2.680
    if y>-.12 or z<2.25 or z>3.05 or abs(dx)>.55:return Vector()
    w=math.exp(-((dx/.32)**4+((z-zc)/.32)**4))*smooth(-.12,-.43,y)
    # Shared deformation field keeps the concentric mouth patch connected.
    lipline=2.690-.022*min(1,(dx/.108)**2)
    lower=1-smooth(lipline-.009,lipline+.009,z)
    upper=1-lower
    side=1 if name.endswith('Left') else -1
    sw=smooth(-.04,.10,dx*side)
    d=Vector()
    if name in ('jawOpen','mouthClose'):
        sign=1 if name=='jawOpen' else -1
        d.z=sign*w*(-.18*lower+.022*upper)
        d.y=sign*w*(-.012*lower)
    elif name in ('jawLeft','jawRight','mouthLeft','mouthRight'):
        d.x=(.043 if name.endswith('Left') else -.043)*w*(lower if name.startswith('jaw') else 1)
    elif name=='jawForward':d.y=-.028*w*lower
    elif name.startswith(('mouthSmile','mouthFrown','mouthStretch','mouthDimple')):
        corner=math.exp(-((dx-side*.12)/.16)**2)*w*sw
        if name.startswith('mouthSmile'):d.z=.042*corner;d.x=side*.019*corner
        if name.startswith('mouthFrown'):d.z=-.030*corner
        if name.startswith('mouthStretch'):d.x=side*.045*corner
        if name.startswith('mouthDimple'):d.y=.012*corner
    elif name in ('mouthFunnel','mouthPucker'):
        d.x=-dx*.22*w;d.y=-.05*w
        if name=='mouthFunnel':d.z=(z-zc)*.30*w
    elif name.startswith('mouthLowerDown'):d.z=-.035*lower*w*sw
    elif name.startswith('mouthUpperUp'):d.z=.024*upper*w*sw
    elif name.startswith('mouthPress'):d.z=-(z-zc)*.2*w*sw
    elif name.startswith(('mouthRoll','mouthShrug')):
        part=upper if name.endswith('Upper') else lower
        if name.startswith('mouthRoll'):d.y=.013*w*part
        else:d.z=(.012 if name.endswith('Lower') else -.012)*w*part
    return d


EYES={'Left':(.718,2.961,.174,.135),'Right':(-.340,2.964,.205,.135)}


def eye_delta(p,name,eye_mesh=False):
    x,y,z=p;out=Vector()
    if y>-.2:return out
    for side,(cx,cz,rx,rz) in EYES.items():
        if not name.endswith(side) and name!='browInnerUp':continue
        dx=x-cx;dz=z-cz
        w=(1-smooth(1.0,1.7,max(abs(dx)/rx,abs(dz)/rz))) if not eye_mesh else 1
        if w<=0:continue
        if name in ('eyeBlink'+side,'eyeSquint'+side):
            amount=.997 if name.startswith('eyeBlink') else .38
            line=2.936+.009*(dx/rx)**2
            out.z=-(z-line)*amount*w
            if eye_mesh:out.y=.025*(amount/.997)*w
        elif name=='eyeWide'+side:out.z=dz*.20*w
        elif name.startswith('eyeLook') and eye_mesh:
            if 'Up' in name:out.z=.009*w
            elif 'Down' in name:out.z=-.009*w
            else:out.x=(.010 if ('Out' in name)==(side=='Left') else -.010)*w
        elif name.startswith('brow'):
            brow=math.exp(-((dx/(rx*1.6))**4+((dz-.19)/.16)**4))
            out.z+=(-.027 if 'Down' in name else .038)*brow
        elif name.startswith('cheekSquint'):out.z=.024*w*max(0,-dz/rz)
    return out


def facial():
    sys.path.insert(0,str(ROOT/'scripts'))
    from build_avatar_fleet import CHANNELS
    h=obj('Clay Skin')
    assert h.data.shape_keys is None,'Facial stage already exists'
    basis=h.shape_key_add(name='Basis')
    for name in CHANNELS:
        if name=='tongueOut':continue
        key=h.shape_key_add(name=name)
        for v,b in zip(key.data,basis.data):
            v.co=b.co+mouth_delta(b.co,name)+eye_delta(b.co,name)
            if name=='cheekPuff' and b.co.y<-.25 and 2.65<b.co.z<3.05:
                v.co.y-=.027*math.exp(-((b.co.z-2.83)/.15)**4)
            if name.startswith('noseSneer'):
                side=1 if name.endswith('Left') else -1
                v.co.z+=.017*math.exp(-(((b.co.x-.23-side*.1)/.16)**4+((b.co.z-2.80)/.13)**4))*smooth(-.15,-.45,b.co.y)
    for side,label in [('L','Left'),('R','Right')]:
        eye=obj('Clay Eye '+side);basis=eye.shape_key_add(name='Basis')
        for name in CHANNELS:
            if not name.startswith('eye') or not name.endswith(label):continue
            key=eye.shape_key_add(name=name)
            for v,b in zip(key.data,basis.data):v.co=b.co+eye_delta(b.co,name,True)
        eye['blinkMethod']='Matched aperture/eye morphs; no intersecting separate spherical eyelid overlay.'
    old=obj('Clay Mouth Study');bpy.data.objects.remove(old,do_unlink=True)
    bm=bmesh.new();bm.from_mesh(h.data)
    rim=[v.co.copy() for v in bm.verts if any(e.is_boundary for e in v.link_edges) and .10<v.co.x<.36 and 2.63<v.co.z<2.76]
    bm.free();assert len(rim)==36,len(rim)
    cx=sum(v.x for v in rim)/len(rim);cz=sum(v.z for v in rim)/len(rim)
    rim.sort(key=lambda p:math.atan2((p.z-cz)*8,p.x-cx))
    interior=plain_material('Clay oral interior',(.015,.0015,.001),.94)
    rings=[]
    for i in range(13):
        t=i/12
        rings.append([(p.x+(p.x-cx)*t*.3,p.y+.004+t*.19,p.z+(p.z-cz)*t*3-t*.045) for p in rim])
    cavity=closed_rings('Clay Oral Cavity',rings,interior)
    # Remove the front cap; the back remains closed and stationary under lip motion.
    bm=bmesh.new();bm.from_mesh(cavity.data)
    front=[f for f in bm.faces if any(v.index==13*len(rim) for v in f.verts)]
    bmesh.ops.delete(bm,geom=front,context='FACES');bm.to_mesh(cavity.data);bm.free()
    bind_head(cavity);base=cavity.shape_key_add(name='Basis')
    for name in CHANNELS:
        if not name.startswith(('mouth','jaw')):continue
        key=cavity.shape_key_add(name=name)
        for i,(v,b) in enumerate(zip(key.data,base.data)):
            t=min(1,i//len(rim)/12)
            v.co=b.co+mouth_delta(b.co,name)*(1-smooth(.1,.8,t))
    toothmat=plain_material('Clay teeth enamel',(.73,.60,.40),.32)
    for row,zcenter in [('Upper',2.743),('Lower',2.644)]:
        vs=[];fs=[]
        for i in range(6):
            center=Vector((.23+(i-2.5)*.026,-.491+abs(i-2.5)*.003,zcenter))
            start=len(vs);n=12;nr=9
            for r in range(nr):
                theta=math.pi*(.025+.95*r/(nr-1))
                for j in range(n):
                    phi=j*math.tau/n
                    vs.append(tuple(center+Vector((.014*math.sin(theta)*math.cos(phi),.018*math.sin(theta)*math.sin(phi),.027*math.cos(theta)))))
            for r in range(nr-1):
                for j in range(n):fs.append((start+r*n+j,start+r*n+(j+1)%n,start+(r+1)*n+(j+1)%n,start+(r+1)*n+j))
            fs.append(tuple(start+j for j in reversed(range(n))))
            fs.append(tuple(start+(nr-1)*n+j for j in range(n)))
        teeth=mesh('Clay '+row+' Teeth',vs,fs,toothmat);bind_head(teeth)
        base=teeth.shape_key_add(name='Basis')
        for name in ('jawOpen','mouthClose'):
            key=teeth.shape_key_add(name=name);sign=1 if name=='jawOpen' else -1
            for v,b in zip(key.data,base.data):v.co=b.co+Vector((0,0,sign*(-.023 if row=='Upper' else -.130)))
    tongue_mat=plain_material('Clay tongue',(.38,.052,.035),.44)
    rings=[];nr=41;nc=20
    for i in range(nr):
        t=i/(nr-1);r=.058*math.sqrt(max(.015,1-t**8))
        rings.append([(.23+r*math.cos(j*math.tau/nc),-.365-.105*t,2.624+.013*math.sin(j*math.tau/nc)*math.sqrt(max(.02,1-t**8))) for j in range(nc)])
    tongue=closed_rings('Clay Long Tongue',rings,tongue_mat);bind_head(tongue)
    base=tongue.shape_key_add(name='Basis')
    for name in ('tongueOut','jawOpen','mouthClose'):
        key=tongue.shape_key_add(name=name)
        for i,(v,b) in enumerate(zip(key.data,base.data)):
            t=(i//nc)/(nr-1) if i<nr*nc else (0 if i==nr*nc else 1)
            v.co=b.co
            if name=='tongueOut':v.co.y-=.78*t;v.co.z-=.115*t*t
            else:v.co.z-=(-1 if name=='mouthClose' else 1)*.095*smooth(0,.38,t)
    tongue['tongueRootAnchored']=True;tongue['extendedLength']=.885
    h['faceRig']='Independent geometric blinks and 51 expression channels; oral tongueOut is separate.'
    print('Facial morphs, matched blinking apertures, closed oral cavity, 12 teeth and anchored long tongue built.')


def refine_blinks_tongue():
    import numpy as np
    h=obj('Clay Skin');base=h.data.shape_keys.key_blocks['Basis']
    points=[v.co.copy() for v in base.data]
    neighbors=[{} for _ in points]
    for e in h.data.edges:
        a,b=e.vertices;w=1/max(.001,(points[a]-points[b]).length)
        neighbors[a][b]=w;neighbors[b][a]=w
    bm=bmesh.new();bm.from_mesh(h.data);bm.verts.ensure_lookup_table()
    boundaries=[v.index for v in bm.verts if any(e.is_boundary for e in v.link_edges)];bm.free()
    for side,cx in [('Left',.705),('Right',-.351)]:
        boundary={i for i in boundaries if abs(points[i].x-cx)<.25 and points[i].z>2.82}
        active={i for i,p in enumerate(points) if p.y<-.25 and ((p.x-cx)/.35)**2+((p.z-2.965)/.25)**2<1}
        free=sorted(active-boundary);index={v:i for i,v in enumerate(free)}
        fixed={}
        for i in boundary:
            p=points[i];line=2.936+.009*((p.x-cx)/.18)**2
            fixed[i]=Vector((0,-.55-p.y,(line-p.z)*.997))
        # Dirichlet interpolation pins the outer face and closes only the real rim.
        a=np.zeros((len(free),len(free)));b=np.zeros((len(free),3))
        for vertex,row in index.items():
            a[row,row]=sum(neighbors[vertex].values())
            for other,w in neighbors[vertex].items():
                if other in index:a[row,index[other]]-=w
                elif other in fixed:b[row]+=w*np.array(fixed[other])
        solution=np.linalg.solve(a,b)
        for prefix,scale in [('eyeBlink',1),('eyeSquint',.30)]:
            key=h.data.shape_keys.key_blocks[prefix+side]
            for v,p in zip(key.data,points):v.co=p
            for i,d in fixed.items():key.data[i].co=points[i]+d*scale
            for i,row in index.items():key.data[i].co=points[i]+Vector(solution[row])*scale
        eye=obj('Clay Eye '+('L' if side=='Left' else 'R'))
        for prefix,scale in [('eyeBlink',1),('eyeSquint',.30)]:
            key=eye.data.shape_keys.key_blocks[prefix+side]
            for v,p in zip(key.data,eye.data.shape_keys.key_blocks['Basis'].data):
                line=2.936+.009*((p.co.x-cx)/.18)**2
                v.co=p.co+Vector((0,.085*scale,(line-p.co.z)*.997*scale))
        print(side+' eyelid: '+str(len(boundary))+' pinned rim vertices, '+str(len(free))+' smoothly interpolated neighbors')
    tongue=obj('Clay Long Tongue');base=tongue.data.shape_keys.key_blocks['Basis'];key=tongue.data.shape_keys.key_blocks['tongueOut']
    for i,(v,p) in enumerate(zip(key.data,base.data)):
        t=(i//20)/40 if i<820 else (0 if i==820 else 1)
        v.co=p.co+Vector((0,-.78*t,-.38*t*t))
    cavity=obj('Clay Oral Cavity');p=cavity.data.materials[0].node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(.001,.0002,.0001,1);p.inputs['Specular IOR Level'].default_value=0
    reset()


def refine_mouth():
    for o in [obj('Clay Skin'),obj('Clay Oral Cavity')]:
        keys=o.data.shape_keys.key_blocks;base=keys['Basis']
        for key in keys:
            if not key.name.startswith(('mouth','jaw')):continue
            for i,(v,b) in enumerate(zip(key.data,base.data)):
                weight=1 if o.name=='Clay Skin' else 1-smooth(.1,.8,min(1,i//36/12))
                v.co=b.co+mouth_delta(b.co,key.name)*weight
    reset()


def solve_mouth_patch():
    import numpy as np
    h=obj('Clay Skin');keys=h.data.shape_keys.key_blocks;base=keys['Basis']
    points=[v.co.copy() for v in base.data]
    bm=bmesh.new();bm.from_mesh(h.data);bm.verts.ensure_lookup_table()
    boundary={v.index for v in bm.verts if any(e.is_boundary for e in v.link_edges) and .10<v.co.x<.36 and 2.63<v.co.z<2.76}
    rim_neighbors={i:[e.other_vert(bm.verts[i]).index for e in bm.verts[i].link_edges if e.is_boundary] for i in boundary}
    bm.free()
    first=min(boundary,key=lambda i:points[i].x);following=max(rim_neighbors[first],key=lambda i:points[i].z)
    ordered=[first,following]
    while len(ordered)<len(boundary):ordered.append(next(i for i in rim_neighbors[ordered[-1]] if i!=ordered[-2]))
    right=max(range(len(ordered)),key=lambda i:points[ordered[i]].x)
    jaw={}
    for arc,sign in [(ordered[:right+1],1),(ordered[right:]+ordered[:1],-1)]:
        distances=[0]
        for a,b in zip(arc,arc[1:]):distances.append(distances[-1]+(points[a]-points[b]).length)
        for i,distance in zip(arc,distances):
            t=distance/distances[-1]
            x=.23+(-1 if sign==1 else 1)*.135*math.cos(math.pi*t)
            z=2.605+sign*.115*math.sin(math.pi*t)
            p=points[i];jaw[i]=Vector((x-p.x,-.010,z-p.z))
    neighbors=[{} for _ in points]
    for e in h.data.edges:
        a,b=e.vertices;w=1/max(.001,(points[a]-points[b]).length);neighbors[a][b]=w;neighbors[b][a]=w
    active={i for i,p in enumerate(points) if p.y<-.22 and p.z<2.91 and ((p.x-.23)/.50)**2+((p.z-2.61)/.40)**2<1}
    free=sorted(active-boundary);index={v:i for i,v in enumerate(free)}
    names=[k.name for k in keys if k.name.startswith(('mouth','jaw'))]
    fixed={name:{i:(jaw[i] if name=='jawOpen' else -jaw[i] if name=='mouthClose' else mouth_delta(points[i],name)) for i in boundary} for name in names}
    a=np.zeros((len(free),len(free)));b=np.zeros((len(free),len(names)*3))
    for vertex,row in index.items():
        a[row,row]=sum(neighbors[vertex].values())
        for other,w in neighbors[vertex].items():
            if other in index:a[row,index[other]]-=w
            elif other in boundary:
                for j,name in enumerate(names):b[row,j*3:j*3+3]+=w*np.array(fixed[name][other])
    solution=np.linalg.solve(a,b)
    for j,name in enumerate(names):
        key=keys[name]
        for v,p in zip(key.data,points):v.co=p
        for i,delta in fixed[name].items():key.data[i].co=points[i]+delta
        for i,row in index.items():key.data[i].co=points[i]+Vector(solution[row,j*3:j*3+3])
    cavity=obj('Clay Oral Cavity');cb=cavity.data.shape_keys.key_blocks['Basis']
    mapping=[min(boundary,key=lambda i:(Vector((points[i].x,points[i].z))-Vector((cb.data[j].co.x,cb.data[j].co.z))).length) for j in range(36)]
    for name in names:
        key=cavity.data.shape_keys.key_blocks[name]
        for i,(v,p) in enumerate(zip(key.data,cb.data)):
            t=min(1,i//36/12);delta=fixed[name][mapping[i%36]]
            v.co=p.co+delta*(1-smooth(.1,.8,t))
    reset();print('Mouth rebuilt as bounded harmonic patch around 36 traced lip vertices; '+str(len(free))+' interior points.')


def retopologize_mouth():
    reset();h=obj('Clay Skin');old=h.data
    oldkeys={k.name:[v.co.copy() for v in k.data] for k in old.shape_keys.key_blocks}
    points=oldkeys['Basis'];weights=[{h.vertex_groups[g.group].name:g.weight for g in v.groups} for v in old.vertices]
    keep=[]
    for p in old.polygons:
        near=any(points[i].y<-.2 and ((points[i].x-.23)/.32)**2+((points[i].z-2.68)/.19)**2<1 for i in p.vertices)
        if not near:keep.append(tuple(p.vertices))
    used=sorted({i for f in keep for i in f});mapping={v:i for i,v in enumerate(used)}
    verts=[points[i].copy() for i in used];faces=[tuple(mapping[i] for i in f) for f in keep]
    edges={}
    for f in faces:
        for a,b in zip(f,f[1:]+f[:1]):
            pair=tuple(sorted((a,b)));edges[pair]=edges.get(pair,0)+1
    original_edges={}
    for p in old.polygons:
        f=list(p.vertices)
        for a,b in zip(f,f[1:]+f[:1]):
            e=tuple(sorted((a,b)));original_edges[e]=original_edges.get(e,0)+1
    boundary_edges=[e for e,n in edges.items() if n==1 and original_edges.get(tuple(sorted(used[i] for i in e)),0)>1]
    neighbors={}
    for a,b in boundary_edges:neighbors.setdefault(a,[]).append(b);neighbors.setdefault(b,[]).append(a)
    assert all(len(v)==2 for v in neighbors.values()),'Patch boundary is not one closed loop'
    first=min(neighbors,key=lambda i:verts[i].x);ordered=[first,neighbors[first][0]]
    while len(ordered)<len(neighbors):ordered.append(next(i for i in neighbors[ordered[-1]] if i!=ordered[-2]))
    area=sum(verts[a].x*verts[b].z-verts[b].x*verts[a].z for a,b in zip(ordered,ordered[1:]+ordered[:1]))
    if area<0:ordered.reverse()
    n=len(ordered);outer=[verts[i].copy() for i in ordered]
    phis=[math.atan2((p.z-2.68)/.19,(p.x-.23)/.32)%math.tau for p in outer]
    # Preserve the neutral downturned contour; use convex support loops outside it.
    upper=[(-1,2.668),(-.70,2.686),(-.30,2.701),(0,2.702),(.35,2.699),(.70,2.688),(1,2.668)]
    lower=[(-1,2.668),(-.70,2.675),(-.30,2.676),(0,2.678),(.35,2.676),(.70,2.674),(1,2.668)]
    inner=[];delta={name:[] for name in oldkeys if name.startswith(('mouth','jaw'))}
    for phi in phis:
        q=math.cos(phi);x=.23+.108*q;z=profile(upper if math.sin(phi)>=0 else lower,q)
        y=-.540+.12*(x-.23)
        p=Vector((x,y,z));inner.append(p)
        for name in delta:
            target=Vector((.23+.135*math.cos(phi),y-.006,2.605+.115*math.sin(phi)))
            d=target-p if name=='jawOpen' else p-target if name=='mouthClose' else mouth_delta(p,name)
            delta[name].append(d)
    patch=[];previous=ordered
    levels=[.08,.18,.30,.43,.56,.68,.78,.86,.92,.96,.985,1.0]
    for t in levels:
        ring=[]
        for j,(a,b) in enumerate(zip(outer,inner)):
            p=a.lerp(b,t)
            # Preserve face depth across the patch, with a small rolled inner edge.
            p.y-=.035*math.sin(math.pi*t)
            ring.append(len(verts));patch.append((len(verts),j,t));verts.append(p)
        for j in range(n):faces.append((previous[j],previous[(j+1)%n],ring[(j+1)%n],ring[j]))
        previous=ring
    data=bpy.data.meshes.new('Clay continuous animation mouth topology');data.from_pydata(verts,[],faces);data.update()
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    data.materials.append(old.materials[0]);h.data=data
    for p in data.polygons:p.use_smooth=True
    h.vertex_groups.clear();groups={b.name:h.vertex_groups.new(name=b.name) for b in obj('AvatarRig').data.bones}
    for new,original in enumerate(used):
        for name,w in weights[original].items():groups[name].add([new],w,'REPLACE')
    groups['Head'].add(list(range(len(used),len(verts))),1,'REPLACE')
    for name,coordinates in oldkeys.items():
        key=h.shape_key_add(name=name)
        for new,original in enumerate(used):key.data[new].co=points[original] if name in delta else coordinates[original]
        for index,j,t in patch:
            if name in delta:d=delta[name][j]*t
            elif name=='Basis':d=Vector()
            else:d=(coordinates[used[ordered[j]]]-points[used[ordered[j]]])*(1-t)
            key.data[index].co=verts[index]+d
    h['mouthPatchStart']=len(used);h['mouthPatchRingSize']=n;h['mouthPatchRings']=len(levels)
    h['mouthTopology']='12 connected quad rings with fixed outer boundary and bounded oval jaw-open target.'
    oldc=obj('Clay Oral Cavity');mat=oldc.data.materials[0];bpy.data.objects.remove(oldc,do_unlink=True)
    rings=[]
    for row in range(13):
        t=row/12;rings.append([(p.x+(p.x-.23)*t*.25,p.y+.002+.22*t,p.z+(p.z-2.68)*t*3-.055*t) for p in inner])
    cavity=closed_rings('Clay Oral Cavity',rings,mat)
    bm=bmesh.new();bm.from_mesh(cavity.data)
    front=[f for f in bm.faces if any(v.index==13*n for v in f.verts)]
    bmesh.ops.delete(bm,geom=front,context='FACES_ONLY');bm.to_mesh(cavity.data);bm.free();bind_head(cavity)
    basis=cavity.shape_key_add(name='Basis')
    for name in delta:
        key=cavity.shape_key_add(name=name)
        for i,(v,p) in enumerate(zip(key.data,basis.data)):
            t=min(1,i//n/12);v.co=p.co+delta[name][i%n]*(1-smooth(.1,.8,t))
    reset();print({'mouth_ring_vertices':n,'mouth_quads':n*len(levels),'head_vertices':len(data.vertices)})


def conform_mouth_depth():
    namespace={'__name__':'clay_reference_math'}
    exec(compile((ROOT/'.context/clay-head-trial.py').read_text(),'clay-head-trial.py','exec'),namespace)
    namespace['outline']=namespace['smooth_loop'](namespace['OUTLINE'],6)
    depth=namespace['surface_depth'];h=obj('Clay Skin');start=h['mouthPatchStart'];n=h['mouthPatchRingSize']
    levels=[.08,.18,.30,.43,.56,.68,.78,.86,.92,.96,.985,1.0]
    keys=h.data.shape_keys.key_blocks
    for key in keys:
        for i in range(start,len(key.data)):
            p=key.data[i].co;t=levels[(i-start)//n]
            p.y=depth((p.x*250+440,1134-p.z*250))+.008*t**8
    for v,b in zip(h.data.vertices,keys['Basis'].data):v.co=b.co
    cavity=obj('Clay Oral Cavity');ck=cavity.data.shape_keys.key_blocks
    for key in ck:
        for i in range(13*n):
            t=(i//n)/12;j=i%n
            rim=keys[key.name if key.name in keys else 'Basis'].data[start+11*n+j].co
            neutral=keys['Basis'].data[start+11*n+j].co
            offset=rim.y-neutral.y
            key.data[i].co.y=neutral.y+.002+.22*t+offset*(1-smooth(.1,.8,t))
    reset();print('Mouth patch depth conformed to the approved head dome.')


def stabilize_mouth_topology():
    from mathutils.geometry import delaunay_2d_cdt
    reset();h=obj('Clay Skin');old=h.data;start=h['mouthPatchStart']
    oldkeys={k.name:[v.co.copy() for v in k.data] for k in old.shape_keys.key_blocks}
    verts=oldkeys['Basis'][:start];faces=[tuple(p.vertices) for p in old.polygons if max(p.vertices)<start]
    weights=[{h.vertex_groups[g.group].name:g.weight for g in v.groups} for v in old.vertices[:start]]
    counts={}
    for f in faces:
        for a,b in zip(f,f[1:]+f[:1]):e=tuple(sorted((a,b)));counts[e]=counts.get(e,0)+1
    full_counts={}
    for poly in old.polygons:
        f=list(poly.vertices)
        for a,b in zip(f,f[1:]+f[:1]):e=tuple(sorted((a,b)));full_counts[e]=full_counts.get(e,0)+1
    edge_ids=[e for e,n in counts.items() if n==1 and full_counts.get(e)==2]
    neighbors={}
    for a,b in edge_ids:neighbors.setdefault(a,[]).append(b);neighbors.setdefault(b,[]).append(a)
    assert all(len(n)==2 for n in neighbors.values())
    first=min(neighbors);ordered=[first,neighbors[first][0]]
    while len(ordered)<len(neighbors):ordered.append(next(i for i in neighbors[ordered[-1]] if i!=ordered[-2]))
    outer=[Vector((verts[i].x,verts[i].z)) for i in ordered]
    n=120;circle=[Vector((.23+.27*math.cos(j*math.tau/n),2.68+.14*math.sin(j*math.tau/n))) for j in range(n)]
    coords=outer+circle;no=len(outer)
    constraints=[(i,(i+1)%no) for i in range(no)]+[(no+j,no+(j+1)%n) for j in range(n)]
    dv,de,df,ov,oe,of=delaunay_2d_cdt(coords,constraints,[],0,1e-7)
    def inside(p,loop):
        odd=False
        for a,b in zip(loop,loop[1:]+loop[:1]):
            if (a.y>p.y)!=(b.y>p.y) and p.x<(b.x-a.x)*(p.y-a.y)/(b.y-a.y)+a.x:odd=not odd
        return odd
    source={'__name__':'clay_reference_math'};exec(compile((ROOT/'.context/clay-head-trial.py').read_text(),'clay-head-trial.py','exec'),source)
    source['outline']=source['smooth_loop'](source['OUTLINE'],6)
    def point(p):return Vector((p.x,source['surface_depth']((p.x*250+440,1134-p.y*250)),p.y))
    remap={};input_map={}
    for i,originals in enumerate(ov):
        original=originals[0]
        if original<no:remap[i]=ordered[original]
        else:remap[i]=len(verts);verts.append(point(dv[i]))
        for original in originals:input_map[original]=remap[i]
    for f in df:
        p=sum((dv[i] for i in f),Vector((0,0)))/len(f)
        if inside(p,outer) and not inside(p,circle):faces.append(tuple(remap[i] for i in f))
    previous=[input_map[no+j] for j in range(n)]
    upper=[(-1,2.668),(-.70,2.686),(-.30,2.701),(0,2.702),(.35,2.699),(.70,2.688),(1,2.668)]
    lower=[(-1,2.668),(-.70,2.675),(-.30,2.676),(0,2.678),(.35,2.676),(.70,2.674),(1,2.668)]
    mouth_names=[name for name in oldkeys if name.startswith(('mouth','jaw'))]
    inner=[];delta={name:[] for name in mouth_names}
    for j in range(n):
        phi=j*math.tau/n;q=math.cos(phi)
        p=point(Vector((.23+.108*q,profile(upper if math.sin(phi)>=0 else lower,q))));inner.append(p)
        target=point(Vector((.23+.135*q,2.65+.075*math.sin(phi))))
        for name in mouth_names:delta[name].append(target-p if name=='jawOpen' else p-target if name=='mouthClose' else mouth_delta(p,name)*.70)
    patch=[];ring_start=len(verts);levels=[.07,.15,.25,.36,.48,.60,.71,.81,.89,.94,.975,1.0]
    for t in levels:
        current=[]
        for j in range(n):
            a=point(circle[j]);p=a.lerp(inner[j],t);p=point(Vector((p.x,p.z)))
            current.append(len(verts));patch.append((len(verts),j,t));verts.append(p)
        for j in range(n):faces.append((previous[j],previous[(j+1)%n],current[(j+1)%n],current[j]))
        previous=current
    data=bpy.data.meshes.new('Clay production mouth loops');data.from_pydata(verts,[],faces);data.update()
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    data.materials.append(old.materials[0]);h.data=data
    for p in data.polygons:p.use_smooth=True
    h.vertex_groups.clear();groups={b.name:h.vertex_groups.new(name=b.name) for b in obj('AvatarRig').data.bones}
    for i,w in enumerate(weights):
        for name,value in w.items():groups[name].add([i],value,'REPLACE')
    groups['Head'].add(list(range(start,len(verts))),1,'REPLACE')
    for name,oldco in oldkeys.items():
        key=h.shape_key_add(name=name)
        for i in range(start):key.data[i].co=oldkeys['Basis'][i] if name in mouth_names else oldco[i]
        for index,j,t in patch:
            p=verts[index].copy()
            if name in delta:
                p+=delta[name][j]*t;p.y=point(Vector((p.x,p.z))).y
            key.data[index].co=p
    h['mouthPatchStart']=ring_start;h['mouthPatchRingSize']=n;h['mouthPatchRings']=12
    cavity=obj('Clay Oral Cavity');mat=cavity.data.materials[0];bpy.data.objects.remove(cavity,do_unlink=True)
    rings=[[(p.x,p.y+.003+.23*t,p.z-.04*t+(p.z-2.68)*t*3) for p in inner] for t in [i/12 for i in range(13)]]
    cavity=closed_rings('Clay Oral Cavity',rings,mat)
    bm=bmesh.new();bm.from_mesh(cavity.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if any(v.index==13*n for v in f.verts)],context='FACES_ONLY');bm.to_mesh(cavity.data);bm.free();bind_head(cavity)
    base=cavity.shape_key_add(name='Basis')
    for name in mouth_names:
        key=cavity.shape_key_add(name=name)
        for i,(v,p) in enumerate(zip(key.data,base.data)):
            t=min(1,i//n/12);v.co=p.co+delta[name][i%n]*(1-smooth(.1,.8,t))
    for row,travel in [('Upper',-.023),('Lower',-.08)]:
        teeth=obj('Clay '+row+' Teeth');base=teeth.data.shape_keys.key_blocks['Basis']
        for name,sign in [('jawOpen',1),('mouthClose',-1)]:
            for v,b in zip(teeth.data.shape_keys.key_blocks[name].data,base.data):v.co=b.co+Vector((0,0,travel*sign))
    reset();print('Uniform 120-column mouth patch replaces folded nonuniform contour interpolation.')


def finalize_mouth_contour():
    reset();h=obj('Clay Skin');keys=h.data.shape_keys.key_blocks;start=h['mouthPatchStart'];n=h['mouthPatchRingSize']
    source={'__name__':'clay_reference_math'};exec(compile((ROOT/'.context/clay-head-trial.py').read_text(),'clay-head-trial.py','exec'),source)
    source['outline']=source['smooth_loop'](source['OUTLINE'],6)
    def point(x,z):return Vector((x,source['surface_depth']((x*250+440,1134-z*250)),z))
    levels=[.07,.15,.25,.36,.48,.60,.71,.81,.89,.94,.975,1.0]
    delta={k.name:[] for k in keys if k.name.startswith(('mouth','jaw'))};inner=[]
    for j in range(n):
        phi=j*math.tau/n;q=math.cos(phi);s=math.sin(phi)
        p=point(.23+.108*q,2.668+.020*(1-q*q)+(.014 if s>=0 else .010)*s);inner.append(p)
        target=point(.23+.135*q,2.65+.075*s)
        for name in delta:delta[name].append(target-p if name=='jawOpen' else p-target if name=='mouthClose' else mouth_delta(p,name)*.70)
    for row,t in enumerate(levels):
        for j,p in enumerate(inner):
            phi=j*math.tau/n;a=point(.23+.27*math.cos(phi),2.68+.14*math.sin(phi));neutral=a.lerp(p,t)
            for key in keys:
                v=neutral+delta[key.name][j]*t if key.name in delta else neutral
                key.data[start+row*n+j].co=point(v.x,v.z)
    for v,b in zip(h.data.vertices,keys['Basis'].data):v.co=b.co
    cavity=obj('Clay Oral Cavity');ck=cavity.data.shape_keys.key_blocks
    for row in range(13):
        t=row/12
        for j,p in enumerate(inner):
            neutral=Vector((p.x,p.y+.003+.23*t,p.z-.04*t+(p.z-2.68)*t*3))
            for key in ck:
                key.data[row*n+j].co=neutral+(delta[key.name][j]*(1-smooth(.1,.8,t)) if key.name in delta else Vector())
    for v,b in zip(cavity.data.vertices,ck['Basis'].data):v.co=b.co
    print('Neutral frown contour regularized at both corners without changing its overall width/height.')


def fit_oral_clearance():
    tongue=obj('Clay Long Tongue');keys=tongue.data.shape_keys.key_blocks
    for i,v in enumerate(keys['Basis'].data):
        t=(i//20)/40 if i<820 else (0 if i==820 else 1)
        v.co.y=-.30-.05*t
        for name in ('tongueOut','jawOpen','mouthClose'):
            p=v.co.copy()
            if name=='tongueOut':p.y-=.88*t;p.z+=.13*math.sin(math.pi*t)-.38*t*t
            else:p.z-=(-1 if name=='mouthClose' else 1)*.040*smooth(0,.38,t)
            keys[name].data[i].co=p
    for v,b in zip(tongue.data.vertices,keys['Basis'].data):v.co=b.co
    for row,travel in [('Upper',-.023),('Lower',-.060)]:
        teeth=obj('Clay '+row+' Teeth');base=teeth.data.shape_keys.key_blocks['Basis']
        if not teeth.get('dentalRecessFitted'):
            for v in base.data:v.co.y+=.075
        for name,sign in [('jawOpen',1),('mouthClose',-1)]:
            for v,b in zip(teeth.data.shape_keys.key_blocks[name].data,base.data):v.co=b.co+Vector((0,0,travel*sign))
        for v,b in zip(teeth.data.vertices,base.data):v.co=b.co
        teeth['dentalRecessFitted']=True
    reset()


def bake_material():
    reset();s=bpy.context.scene;s.cycles.samples=8
    skin=obj('Clay Skin').data.materials[0];skin.use_fake_user=True
    objects=[o for o in s.objects if o.type=='MESH' and skin in list(o.data.materials)]
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.012)
    bpy.ops.object.mode_set(mode='OBJECT')
    atlas=bpy.data.images.new('Clay mineral base color 2048',width=2048,height=2048)
    node=skin.node_tree.nodes.new('ShaderNodeTexImage');node.image=atlas;skin.node_tree.nodes.active=node
    s.render.bake.use_clear=False
    bpy.ops.object.bake(type='DIFFUSE',pass_filter={'COLOR'},use_clear=False,margin=8)
    atlas.filepath_raw=str(GLB.parent/'clay-mineral-basecolor.png');atlas.file_format='PNG';atlas.save();atlas.pack()
    normal=bpy.data.images.new('Clay mineral normal 1024',width=1024,height=1024)
    normal.colorspace_settings.name='Non-Color';node.image=normal
    bpy.ops.object.bake(type='NORMAL',use_clear=False,margin=8,normal_space='TANGENT')
    normal.filepath_raw=str(GLB.parent/'clay-mineral-normal.png');normal.file_format='PNG';normal.save();normal.pack()
    baked=plain_material('Clay Mineral - Runtime PBR',(.25,.032,.009),.64)
    n=baked.node_tree.nodes;l=baked.node_tree.links;p=n.get('Principled BSDF');p.inputs['Specular IOR Level'].default_value=.27
    color=n.new('ShaderNodeTexImage');color.image=atlas;l.new(color.outputs['Color'],p.inputs['Base Color'])
    tex=n.new('ShaderNodeTexImage');tex.image=normal;nm=n.new('ShaderNodeNormalMap');l.new(tex.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs['Normal'],p.inputs['Normal'])
    baked['bakedFrom']='Editable Clay Iron Red Mineral procedural material retained in this .blend.'
    for o in objects:o.data.materials[0]=baked
    s.cycles.samples=32
    print('Baked shared base-color and tangent-normal atlases for the runtime; procedural source retained.')


def export_runtime():
    reset();rig=obj('AvatarRig');rig.hide_set(False)
    bpy.ops.object.select_all(action='DESELECT')
    for o in bpy.context.scene.objects:
        if o.type in {'MESH','ARMATURE'}:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.gltf(filepath=str(GLB),export_format='GLB',use_selection=True,
        export_animations=False,export_skins=True,export_morph=True,export_morph_normal=True,
        export_extras=True,export_yup=True,export_cameras=False,export_lights=False)
    rig.hide_set(True);save();print('Isolated textured GLB exported: '+str(GLB))


def clean_oral_cap():
    o=obj('Clay Oral Cavity');bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.delete(bm,geom=[e for e in bm.edges if e.is_wire],context='EDGES')
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
    bm.to_mesh(o.data);bm.free()


def validate_geometry():
    import numpy as np
    reset();h=obj('Clay Skin');h.data.calc_loop_triangles();keys=h.data.shape_keys.key_blocks
    base=np.array([v.co[:] for v in keys['Basis'].data]);tri=np.array([t.vertices[:] for t in h.data.loop_triangles])
    mouth_tri=tri[np.any(tri>=h['mouthPatchStart'],axis=1)]
    def area(points):
        t=points[mouth_tri][:,:,[0,2]];a=t[:,1]-t[:,0];b=t[:,2]-t[:,0];return a[:,0]*b[:,1]-a[:,1]*b[:,0]
    original=area(base)
    poses=[{}, {'jawOpen':1},{'jawOpen':1,'mouthClose':1}, {'mouthSmileLeft':1,'mouthSmileRight':1},
        {'jawOpen':.8,'mouthSmileLeft':.7,'mouthSmileRight':.7}, {'mouthFrownLeft':1,'mouthFrownRight':1},
        {'jawOpen':.6,'mouthFunnel':.5,'mouthPucker':.3}, {'jawOpen':.8,'tongueOut':1},
        {'jawOpen':1,'mouthStretchLeft':.7,'mouthStretchRight':.7}, {'jawOpen':.4,'jawLeft':1},
        {'jawOpen':.4,'jawRight':1},{'mouthPressLeft':1,'mouthPressRight':1}]
    report={'status':'isolated rig, not physical ZED validation','mouth':[],'meshes':[],'arm_poses':[]}
    for values in poses:
        p=base.copy()
        for name,value in values.items():
            if name in keys:p+=(np.array([v.co[:] for v in keys[name].data])-base)*value
        flipped=int(np.sum(area(p)*original < -1e-12))
        report['mouth'].append({'values':values,'flipped_triangles':flipped})
    for o in bpy.context.scene.objects:
        if o.type!='MESH':continue
        bm=bmesh.new();bm.from_mesh(o.data)
        groups=[sum(g.weight for g in v.groups) for v in o.data.vertices]
        report['meshes'].append({'name':o.name,'vertices':len(bm.verts),'zero_area_faces':sum(f.calc_area()<1e-12 for f in bm.faces),
            'nonmanifold_nonboundary_edges':sum(not e.is_manifold and not e.is_boundary for e in bm.edges),
            'weight_error':max(abs(w-1) for w in groups)})
        bm.free()
    dg=bpy.context.evaluated_depsgraph_get()
    def evaluated(o):
        mesh=o.evaluated_get(dg).to_mesh();p=np.array([v.co[:] for v in mesh.vertices]);o.evaluated_get(dg).to_mesh_clear();return p
    rest={o.name:evaluated(o) for o in [obj('Clay Flipper L'),obj('Clay Flipper R'),h]}
    for side,shoulder,elbow,wrist in [('L',-.8,-.7,.4),('L',-1.6,-1.5,.7),('R',.8,-.7,.4),('R',1.6,-1.5,.7)]:
        reset();rotate('UpperArm.'+side,(0,1,0),shoulder);rotate('Forearm.'+side,(1,0,0),elbow);rotate('Hand.'+side,(1,0,0),wrist);bpy.context.view_layer.update()
        o=obj('Clay Flipper '+side);p=evaluated(o);q=rest[o.name];edges=np.array([e.vertices[:] for e in o.data.edges])
        before=np.linalg.norm(q[edges[:,0]]-q[edges[:,1]],axis=1);after=np.linalg.norm(p[edges[:,0]]-p[edges[:,1]],axis=1)
        ratio=after[before>1e-5]/before[before>1e-5]
        opposite=obj('Clay Flipper '+('R' if side=='L' else 'L'))
        report['arm_poses'].append({'side':side,'shoulder':shoulder,'elbow':elbow,'wrist':wrist,
            'opposite_arm_drift':float(np.max(np.linalg.norm(evaluated(opposite)-rest[opposite.name],axis=1))),
            'head_torso_drift':float(np.max(np.linalg.norm(evaluated(h)-rest[h.name],axis=1))),
            'edge_stretch_p99':float(np.quantile(ratio,.99)),'edge_stretch_max':float(np.max(ratio))})
    reset();tongue=obj('Clay Long Tongue');tb=tongue.data.shape_keys.key_blocks['Basis']
    report['tongue_root_drift']=max((tongue.data.shape_keys.key_blocks[name].data[i].co-tb.data[i].co).length for name in ['tongueOut','jawOpen','mouthClose'] for i in range(20))
    report['bones']=len(obj('AvatarRig').data.bones)
    (QA/'geometry-validation.json').write_text(json.dumps(report,indent=2))
    assert all(p['flipped_triangles']==0 for p in report['mouth'])
    assert all(p['zero_area_faces']==0 and p['nonmanifold_nonboundary_edges']==0 and p['weight_error']<1e-6 for p in report['meshes'])
    assert all(p['opposite_arm_drift']<1e-6 and p['head_torso_drift']<1e-6 and p['edge_stretch_p99']<1.35 and p['edge_stretch_max']<1.6 for p in report['arm_poses'])
    assert report['tongue_root_drift']<1e-6 and report['bones']==18
    print(json.dumps(report))
    return report
