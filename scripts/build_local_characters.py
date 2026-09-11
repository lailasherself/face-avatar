"""Build editable, reference-guided review characters entirely in local Blender.

Blender --background --factory-startup --python scripts/build_local_characters.py
Outputs are isolated from the approved/source roster. No remote generation calls.
"""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector, Quaternion

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_avatar_fleet import Mesh, CHANNELS, material, color, export

OUT = ROOT / 'assets/local-characters'
BLENDS = ROOT / 'blender/local-characters'
QA = ROOT / '.context/qa/local-characters'
PI = math.pi
CONFIGS = {
    'cosmic': dict(head=(.70,.43,.61), hz=2.18, power=.70, skin='#4b155f', accent='#86228a',
                   eyes=(.31,.095,.31,.19,.30), eye='#08120b', pupil='#050807',
                   upper='#ff7900', lower='#179700', sleep=1.39, lip='#3a1346',
                   mouth=(.25,-.35,.011), body=.33, leg=.49, arm=.66, shoes='#ff7800'),
    'nebula': dict(head=(.76,.43,.54), hz=2.24, power=.91, skin='#304368', accent='#94546c',
                   eyes=(.39,.025,.215,.105,.125), eye='#ffd0c5', pupil='#133334',
                   sleep=.36, lip='#64425a', mouth=(.13,-.17,.012), body=.24, leg=.70, arm=.85),
    'kudzu': dict(head=(.61,.40,.64), hz=2.22, power=.83, skin='#095e20', accent='#278520',
                  eyes=(.30,.07,.235,.14,.215), eye='#efbe80', pupil='#0b1605',
                  upper='#164b17', lower='#126321', sleep=1.54, lip='#144b1a',
                  mouth=(.35,-.24,.012), body=.23, leg=.70, arm=.84),
    'clay': dict(head=(.98,.38,.49), hz=2.30, power=.95, skin='#943719', accent='#b94c29',
                 eyes=(.40,.025,.155,.09,.095), eye='#090b09', pupil='#060807',
                 sleep=.49, lip='#642211', mouth=(.085,-.17,.012), body=.24, leg=.57, arm=.75),
    'summer': dict(head=(.70,.44,.56), hz=2.15, power=.84, skin='#101329', accent='#252139',
                   eyes=(.37,-.045,.085,.07,.15), eye='#ffb954', pupil='#ffb954',
                   sleep=.32, lip='#101122', mouth=(.15,-.28,.01), body=.32, leg=.45, arm=.61),
    'glass': dict(head=(.79,.50,.70), hz=2.23, power=.90, skin='#053844', accent='#075e6a',
                  eyes=(.36,-.055,.28,.14,.34), eye='#021717', pupil='#010c0c',
                  sleep=.35, lip='#06444e', mouth=(.14,-.42,.012), body=.19, leg=.63, arm=.68),
}


def smooth(a, b, x):
    t = max(0, min(1, (x-a)/(b-a)))
    return t*t*(3-2*t)


def texture(name, c):
    """Original seamless material artwork, not a projection of photographed lighting."""
    size = 1024
    rng = np.random.default_rng(481 + list(CONFIGS).index(name))
    y, x = np.mgrid[0:size, 0:size].astype(np.float32) / size
    field = .5 + .19*np.sin(2*PI*(3*x+2*y)+2*np.sin(2*PI*y))
    field += .14*np.sin(2*PI*(7*y-2*x)) + .07*np.cos(2*PI*(13*x+9*y))
    a, b = np.array(color(c['skin'])[:3]), np.array(color(c['accent'])[:3])
    rgb = a[None,None,:]*(1-field[:,:,None]) + b[None,None,:]*field[:,:,None]
    grain = rng.random((size,size,1))
    rgb *= .78 + grain*.44
    if name == 'clay':
        rgb += (grain>.991)*np.array([.12,.075,.025])
    else:
        stars = (rng.random((size,size)) > (.987 if name=='kudzu' else .997))
        tint = np.array([.45,.85,.035] if name=='kudzu' else [.8,.47,.10])
        rgb[stars] = tint
        if name in ('nebula','glass'):
            rgb[stars] = [.6,.85,.95]
        if name == 'summer':
            for _ in range(28):
                cx,cy=rng.random(2);dx=np.minimum(abs(x-cx),1-abs(x-cx));dy=np.minimum(abs(y-cy),1-abs(y-cy))
                glow=np.exp(-(dx*dx+dy*dy)/rng.uniform(.000025,.00015))
                rgb += glow[:,:,None]*np.array([1.1,.5,.06])
    rgba=np.ones((size,size,4),dtype=np.float32);rgba[:,:,:3]=np.clip(rgb,0,1)
    image=bpy.data.images.new(name+' hand-authored material',width=size,height=size)
    image.pixels.foreach_set(rgba.ravel());image.update()
    image.filepath_raw=str(OUT/'textures'/f'{name}.png');image.file_format='PNG';image.save();image.pack()
    return image


def materials(name,c):
    m={k:material(name+' '+k,v,.36) for k,v in {
        'skin':c['skin'],'lip':c['lip'],'eye':c['eye'],'pupil':c['pupil'],
        'upper':c.get('upper',c['skin']),'lower':c.get('lower',c['skin']),
        'cavity':'#170913','tongue':'#cb647d','teeth':'#fff0d7',
        'leaf':'#154c18','vein':'#326b26','green':'#249515',
        'shoe':c.get('shoes',c['skin']),
    }.items()}
    image=texture(name,c)
    for key in ['skin']+([] if c.get('upper') else ['upper','lower'])+([] if c.get('shoes') else ['shoe']):
        mat=m[key];nodes=mat.node_tree.nodes;p=nodes.get('Principled BSDF')
        tex=nodes.new('ShaderNodeTexImage');tex.image=image
        mat.node_tree.links.new(tex.outputs['Color'],p.inputs['Base Color'])
        if name in ('cosmic','kudzu','summer','nebula','glass'):
            mat.node_tree.links.new(tex.outputs['Color'],p.inputs['Emission Color'])
            p.inputs['Emission Strength'].default_value=.10 if name!='summer' else .32
        p.inputs['Roughness'].default_value=.62 if name in ('clay','nebula','kudzu') else .47
        p.inputs['Coat Weight'].default_value=.05
        if name=='glass':
            p.inputs['Roughness'].default_value=.10;p.inputs['Metallic'].default_value=.38
            p.inputs['Transmission Weight'].default_value=.28;p.inputs['Coat Weight'].default_value=.7
    for key in ['eye','pupil']:
        m[key].node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.17
    return m


def uv(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.015)
    bpy.ops.object.mode_set(mode='OBJECT');obj.select_set(False)


def skeleton(c):
    data=bpy.data.armatures.new('Local character skeleton');rig=bpy.data.objects.new('AvatarRig',data)
    bpy.context.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    def bone(name,head,tail,parent=None,normal=None):
        b=data.edit_bones.new(name);b.head=head;b.tail=tail
        if parent:b.parent=data.edit_bones[parent]
        if normal:b.align_roll(Vector(normal))
    hip=c['leg']+.20;shoulder=1.55;span=c['body']*.92;length=c['arm'];wrist=span+length
    bone('Root',(0,0,0),(0,0,.2));bone('Hips',(0,0,hip),(0,0,hip+.12),'Root')
    bone('Spine',(0,0,hip+.12),(0,0,1.37),'Hips');bone('Chest',(0,0,1.37),(0,0,1.65),'Spine')
    bone('Neck',(0,0,1.65),(0,0,c['hz']-.23),'Chest');bone('Head',(0,0,c['hz']-.23),(0,0,c['hz']+.4),'Neck')
    chains={}
    for side,s in [('L',1),('R',-1)]:
        bone('UpperArm.'+side,(s*span,0,shoulder),(s*(span+length*.51),0,shoulder),'Chest')
        bone('Forearm.'+side,(s*(span+length*.51),0,shoulder),(s*wrist,0,shoulder),'UpperArm.'+side)
        bone('Hand.'+side,(s*wrist,0,shoulder),(s*(wrist+.15),0,shoulder),'Forearm.'+side)
        bone('Thigh.'+side,(s*c['body']*.55,0,hip),(s*c['body']*.62,0,hip*.51),'Hips')
        bone('Shin.'+side,(s*c['body']*.62,0,hip*.51),(s*c['body']*.68,0,.17),'Thigh.'+side)
        bone('Foot.'+side,(s*c['body']*.68,0,.17),(s*c['body']*.68,-.22,.12),'Shin.'+side)
        for digit,j in [('Index',-1),('Middle',0),('Ring',1)]:
            points=[Vector((s*(wrist+.13+t*.16),j*.059*(1+.16*t),shoulder)) for t in [0,.42,.76,1]]
            chains[side,digit]=points
        chains[side,'Thumb']=[Vector((s*(wrist+x),y,shoulder)) for x,y in [(.025,-.05),(.065,-.105),(.12,-.135),(.16,-.15)]]
        for digit in ['Index','Middle','Ring','Thumb']:
            points=chains[side,digit]
            for i in range(3):bone(f'{digit}{i+1}.{side}',points[i],points[i+1], 'Hand.'+side if i==0 else f'{digit}{i}.{side}',(0,-1,0))
    bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False);rig.show_in_front=True
    rig['rigVersion']='local-reference-review-1';rig['visualApproval']=False
    return rig,chains


def bind(obj,rig,weights):
    groups={b.name:obj.vertex_groups.new(name=b.name) for b in rig.data.bones}
    for vertex in obj.data.vertices:
        values={k:v for k,v in weights(vertex.co).items() if v>1e-7};total=sum(values.values())
        assert total>0
        for key,value in values.items():groups[key].add([vertex.index],value/total,'REPLACE')
    modifier=obj.modifiers.new('Local body skin','ARMATURE');modifier.object=rig;obj.parent=rig


def body(c,rig,m):
    verts=[];edges=[];radii=[]
    def node(p,r,parent=None):
        index=len(verts);verts.append(p);radii.append(r)
        if parent is not None:edges.append((parent,index))
        return index
    hip=c['leg']+.20;span=c['body']*.92;length=c['arm']
    root=node((0,0,hip),(c['body']*.80,c['body']*.68))
    waist=node((0,0,(hip+1.55)/2),(c['body']*.86,c['body']*.61),root)
    chest=node((0,0,1.55),(c['body']*.79,c['body']*.58),waist)
    neck=node((0,0,1.79),(.09,.095),chest)
    node((0,0,c['hz']-.22),(.085,.09),neck)
    for s in [-1,1]:
        p=chest
        for t in [.12,.3,.52,.72,.91,1.04]:
            p=node((s*(span+length*t),0,1.55),(.11-.05*t,.11-.05*t),p)
        p=root
        for t in [.18,.48,.75,1]:
            p=node((s*c['body']*(.5+.18*t),0,hip*(1-t)+.15*t),
                   (c['body']*(.40+.02*t),c['body']*(.43+.01*t)),p)
    data=bpy.data.meshes.new('Body branch cage');data.from_pydata(verts,edges,[]);data.update()
    obj=bpy.data.objects.new('Body',data);bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    skin=obj.modifiers.new('Connected shoulder and hip topology','SKIN');skin.use_smooth_shade=True
    for v,r in zip(data.skin_vertices[0].data,radii):v.radius=r
    data.skin_vertices[0].data[root].use_root=True
    bpy.ops.object.modifier_apply(modifier=skin.name)
    sub=obj.modifiers.new('Joint support loops','SUBSURF');sub.levels=2
    bpy.ops.object.modifier_apply(modifier=sub.name)
    obj.data.materials.append(m['skin'])
    for poly in obj.data.polygons:poly.use_smooth=True
    def weights(p):
        x,y,z=p;side='L' if x>=0 else 'R';x=abs(x)
        if z>1.72:
            t=smooth(1.70,c['hz']-.30,z);return {'Chest':1-t,'Neck':t}
        if z>1.28 and x>span*.65:
            shoulder=smooth(span*.62,span+.08,x);elbow=smooth(span+length*.40,span+length*.62,x)
            hand=smooth(span+length*.94,span+length*1.06,x)
            return {'Chest':1-shoulder,'UpperArm.'+side:shoulder*(1-elbow),
                    'Forearm.'+side:shoulder*elbow*(1-hand),'Hand.'+side:shoulder*elbow*hand}
        if z<hip-.09:
            lower=1-smooth(hip*.42,hip*.62,z);pelvis=smooth(hip-.22,hip-.05,z)
            return {'Hips':pelvis,'Thigh.'+side:(1-pelvis)*(1-lower),'Shin.'+side:(1-pelvis)*lower}
        upper=smooth(hip+.08,1.49,z);return {'Hips':1-upper,'Chest':upper}
    bind(obj,rig,weights);uv(obj)
    details=Mesh()
    for side,s in [('L',1),('R',-1)]:
        details.ellipsoid((s*c['body']*.68,-.06,.13),(c['body']*.64,.22,.13),m['shoe'],{'Foot.'+side:1},n=24,rings=14,power=.65)
    feet=details.object('Feet',rig);uv(feet)
    return obj,feet,weights


def hands(c,rig,chains,m):
    objects=[]
    for side,s in [('L',1),('R',-1)]:
        mesh=Mesh();origin=rig.data.bones['Hand.'+side].head_local
        mesh.ellipsoid(origin+Vector((s*.09,0,0)),(.14,.095,.055),m['skin'],{'Hand.'+side:1},n=24,rings=14)
        for digit in ['Thumb','Index','Middle','Ring']:
            points=chains[side,digit];radius=.034 if digit=='Thumb' else .029
            pts=[points[0].lerp(points[-1],i/16) for i in range(17)]
            axis=points[-1]-points[0]
            def weight(p):
                t=(Vector(p)-points[0]).dot(axis)/axis.length_squared
                active=smooth(-.15,.12,t);one=1-smooth(.33,.53,t);three=smooth(.68,.86,t)
                return {'Hand.'+side:1-active,f'{digit}1.{side}':active*one,
                        f'{digit}2.{side}':active*(1-one-three),f'{digit}3.{side}':active*three}
            mesh.tube(pts,[radius*(1-.32*i/16) if i<16 else .005 for i in range(17)],m['skin'],weight,n=12)
        obj=mesh.object('ArticulatedHand'+side,rig);uv(obj);objects.append(obj)
    return objects


def face(c,rig,m):
    mesh=Mesh();hw,hd,hh=c['head'];hz=c['hz'];power=c['power'];mw,mz,mh=c['mouth']
    def signed(x):return math.copysign(abs(x)**power,x)
    def surface(x,z):return -hd*max(0,1-abs(x/hw)**(2/power)-abs(z/hh)**(2/power))**(power/2)
    def front(u,v):
        a=v*2*PI;x=(1-u)*mw*math.cos(a)+u*hw*signed(math.cos(a))
        z=(1-u)*(mz+mh*math.sin(a))+u*hh*signed(math.sin(a))
        return x,surface(x,z),z
    mesh.grid(38,80,front,m['skin'],tag='skin')
    mesh.grid(22,80,lambda u,v:(hw*math.cos(u*PI/2)*signed(math.cos(v*2*PI)),
                              hd*math.sin(u*PI/2),hh*math.cos(u*PI/2)*signed(math.sin(v*2*PI))),m['skin'],tag='back')
    def cavity(u,v):
        a=v*2*PI;x=mw*math.cos(a)*(1-.22*u);z=mz+mh*math.sin(a)*(1+u)
        return x,surface(mw*math.cos(a),mz+mh*math.sin(a))+.25*u,z
    mesh.grid(8,64,cavity,m['cavity'],tag='cavity')
    mesh.ellipsoid((0,surface(0,mz)+.24,mz),(mw*.85,.035,.16),m['cavity'],tag='cavity',n=24,rings=12)
    lip=[]
    for i in range(65):
        a=2*PI*i/64;x=mw*math.cos(a);z=mz+mh*math.sin(a);lip.append((x,surface(x,z)-.007,z))
    mesh.tube(lip,[.014]*65,m['lip'],n=8,tag='lip')
    eye_specs=[]
    ex,ez,rx,ry,rz=c['eyes']
    for s in [-1,1]:
        cx=s*ex;cy=surface(cx,ez)-.027;side='Left' if s>0 else 'Right'
        center=(cx,cy,ez);radii=(rx,ry,rz);eye_specs.append((center,radii))
        tag={'part':'eye','side':side,'center':center,'radii':radii}
        mesh.ellipsoid(center,radii,m['eye'],tag=tag,n=40,rings=24)
        def pupil(u,v):
            a=v*2*PI;t=.001+u*(.22 if c['eye']!=c['pupil'] else .16)
            x=math.sin(t)*math.cos(a);z=math.sin(t)*math.sin(a)
            return cx+rx*x,cy-(ry+.003)*math.sqrt(max(0,1-x*x-z*z)),ez+rz*z
        mesh.grid(8,32,pupil,m['pupil'],tag={**tag,'part':'pupil'})
        for upper in [True,False]:
            angle=c['sleep'] if upper else (1.40 if c.get('upper') else .42)
            def lid(u,v):
                theta=.001+u*angle;phi=2*PI*v
                return cx+(rx+.008)*math.sin(theta)*math.cos(phi),cy+(ry+.008)*math.sin(theta)*math.sin(phi),ez+(1 if upper else -1)*(rz+.008)*math.cos(theta)
            mesh.grid(13,40,lid,m['upper' if upper else 'lower'],tag=lambda u,v,p:{**tag,'part':'lid','u':u,'v':v,'upper':upper,'angle':angle})
    local=list(mesh.v);mesh.v=[(x,y,z+hz) for x,y,z in local]
    obj=mesh.object('Face',rig);uv(obj);obj.shape_key_add(name='Basis')
    mouth_y=surface(0,mz)
    def delta(p,tag,name):
        x,y,z=p;d=Vector((0,0,0))
        if isinstance(tag,dict):
            if not name.endswith(tag['side']):return d
            cx,cy,cz=tag['center'];rx,ry,rz=tag['radii']
            if tag['part']=='lid':
                angle=tag['angle']
                if name.startswith('eyeBlink'):angle=PI/2+.012
                elif name.startswith('eyeWide'):angle=max(.15,angle-.48)
                elif name.startswith('eyeSquint'):angle=min(1.56,angle+.21)
                else:return d
                t=.001+tag['u']*angle;a=2*PI*tag['v'];sign=1 if tag['upper'] else -1
                return Vector((cx+(rx+.008)*math.sin(t)*math.cos(a),cy+(ry+.008)*math.sin(t)*math.sin(a),cz+sign*(rz+.008)*math.cos(t)))-Vector(p)
            if tag['part']=='pupil' and name.startswith('eyeLook'):
                v=Vector(((x-cx)/rx,(y-cy)/ry,(z-cz)/rz))
                if 'Up' in name:q=Quaternion((1,0,0),-.28)
                elif 'Down' in name:q=Quaternion((1,0,0),.28)
                else:q=Quaternion((0,0,1),(.28 if 'Out' in name else -.28)*(1 if tag['side']=='Left' else -1))
                dv=q@v-v;return Vector((dv.x*rx,dv.y*ry,dv.z*rz))
            return d
        if tag=='back':return d
        front=smooth(.02,.20,-y);mouth=math.exp(-((x/(mw+.14))**4+((z-mz)/.17)**2))*front
        if tag in ('lip','cavity'):mouth=1
        lower=1-smooth(mz-.025,mz+.025,z);corner=min(1,abs(x)/mw)
        side=smooth(-.07,.07,x) if name.endswith('Left') else 1-smooth(-.07,.07,x) if name.endswith('Right') else 1
        if name=='jawOpen':d.z=-.20*lower*mouth;d.y=-.024*lower*mouth
        elif name=='mouthClose':d.z=.17*lower*mouth
        elif name in ('jawLeft','jawRight','mouthLeft','mouthRight'):d.x=(1 if 'Left' in name else -1)*.045*mouth*lower
        elif name=='jawForward':d.y=-.05*mouth*lower
        elif name=='mouthFunnel':d.x=-x*.16*mouth;d.y=-.05*mouth;d.z=(z-mz)*.5*mouth
        elif name=='mouthPucker':d.x=-x*.26*mouth;d.y=-.07*mouth
        elif name.startswith('mouthSmile'):d.z=.065*corner**1.8*side*mouth;d.x=math.copysign(.025,x)*corner*side*mouth
        elif name.startswith('mouthFrown'):d.z=-.045*corner*side*mouth
        elif name.startswith('mouthStretch'):d.x=math.copysign(.04,x)*corner*side*mouth
        elif name.startswith('mouthDimple'):d.y=.025*side*mouth*corner
        elif name.startswith('mouthPress'):d.z=-(z-mz)*.40*side*mouth
        elif name in ('mouthRollLower','mouthRollUpper'):d.y=.025*mouth*(lower if name.endswith('Lower') else 1-lower)
        elif name in ('mouthShrugLower','mouthShrugUpper'):d.z=.035*mouth*(lower if name.endswith('Lower') else 1-lower)
        elif name.startswith('mouthLowerDown'):d.z=-.065*mouth*lower*side
        elif name.startswith('mouthUpperUp'):d.z=.05*mouth*(1-lower)*side
        elif name.startswith('brow'):
            w=math.exp(-((abs(x)-ex)/.22)**2-((z-ez-c['eyes'][4]*.9)/.16)**2)*front
            d.z=w*(.045 if 'Up' in name else -.035)*side
        elif name=='cheekPuff':d.y=-.045*mouth*(1-corner*.4)
        elif name.startswith('cheekSquint'):d.z=.025*mouth*side
        elif name.startswith('noseSneer'):d.z=.025*mouth*side
        return d
    for channel in CHANNELS:
        if channel=='tongueOut':continue
        key=obj.shape_key_add(name=channel)
        for i,(p,tag) in enumerate(zip(local,mesh.tags)):key.data[i].co=Vector(mesh.v[i])+delta(p,tag,channel)
    lid=obj.data.attributes.new(name='_LID_INDEX',type='FLOAT',domain='POINT')
    lid.data.foreach_set('value',[1 if isinstance(t,dict) and t['part']=='lid' and t['side']=='Right' else 2 if isinstance(t,dict) and t['part']=='lid' else 0 for t in mesh.tags])
    obj['eyelidSurfaces']=[dict(center=[p[0],p[2]+hz,-p[1]],radii=[r[0]+.009,r[2]+.009,r[1]+.009]) for p,r in eye_specs]
    obj['assetRole']='local-face';obj['visualApproval']=False
    oral=Mesh()
    for upper in [True,False]:
        for j in range(6):
            x=(j-2.5)*mw*.25
            oral.ellipsoid((x,mouth_y+.066,mz+hz+(.006 if upper else -.026)),(mw*.117,.025,.025),m['teeth'],tag='upper' if upper else 'lower',n=10,rings=8)
    teeth=oral.object('Teeth',rig);teeth.shape_key_add(name='Basis');jaw=teeth.shape_key_add(name='jawOpen')
    for i,tag in enumerate(oral.tags):
        if tag=='lower':jaw.data[i].co.z-=.20;jaw.data[i].co.y-=.024
    tongue=Mesh();start=mouth_y+.21
    # The root stays inside the mouth; the rest curves past the lower lip.
    def tongue_surface(u,v):
        a=v*2*PI;width=mw*.70*math.sin(PI*(.12+.86*u))
        return width*math.cos(a),start-.19*u,mz+hz-.012+.016*math.sin(a)
    tongue.grid(25,20,tongue_surface,m['tongue'],tag=lambda u,v,p:u)
    to=tongue.object('Tongue',rig);to.shape_key_add(name='Basis');key=to.shape_key_add(name='tongueOut')
    for i,u in enumerate(tongue.tags):
        t=smooth(0,1,u);key.data[i].co.y-=.72*t;key.data[i].co.z+=.015*t-.25*max(0,(t-.50)/.50)**2
    jaw=to.shape_key_add(name='jawOpen')
    for v in jaw.data:v.co.z-=.10
    to['tongueRig']='Root-anchored, extensible, downward-curved tip';to['tongueRigVersion']=6
    return [obj,teeth,to],surface


def details(name,c,rig,m,weights):
    mesh=Mesh();hw,hd,hh=c['head'];hz=c['hz']
    if name=='cosmic':
        for s in [-1,1]:
            points=[(s*(.41+.19*t),.01,hz+.49+.35*t) for t in [0,.25,.5,.75,1]]
            mesh.tube(points,[.075,.065,.075,.11,.12],m['green'],n=20)
            mesh.ellipsoid(points[-1],(.13,.10,.14),m['green'],n=24,rings=16)
    if name=='summer':
        for s in [-1,1]:
            for x,z,dx,dz,r in [(.43,.40,.12,.33,.125),(.61,.16,.25,.16,.105),(.65,-.12,.20,-.01,.085)]:
                points=[(s*(x+dx*t),.04,hz+z+dz*t) for t in [0,.25,.5,.75,1]]
                mesh.tube(points,[r*.8,r*.9,r,r*1.1,r*.7],m['skin'],n=18)
                mesh.ellipsoid(points[-1],(r,r*.85,r),m['skin'],n=20,rings=12)
    if name=='kudzu':
        def leaf(origin,length,width,angle,weight):
            origin=Vector(origin);direction=Vector((math.sin(angle),0,math.cos(angle)));across=Vector((math.cos(angle),0,-math.sin(angle)))
            def shape(u,v):
                t=2*v-1;edge=math.sin(PI*u)**.75*(.84+.16*math.cos(8*PI*u))
                p=origin+direction*(length*u)+across*(width*t*edge)
                p.y-=.028*(1-t*t)*math.sin(PI*u)
                return p
            mesh.grid(17,9,shape,m['leaf'],weight,wrap=False)
            mesh.tube([origin+direction*(length*t)+Vector((0,-.035*math.sin(PI*t)-.005,0)) for t in [i/16 for i in range(17)]],[.009]*17,m['vein'],weight,n=6)
        leaf((0,-.32,hz+.47),.43,.19,0,{'Head':1})
        for s in [-1,1]:leaf((s*.29,-.12,hz+.40),.27,.11,s*.85,{'Head':1})
        for s in [-1,1]:
            pts=[]
            for i in range(48):
                t=i/47;z=.50+t*1.12;x=s*(c['body']*.72+.045*math.sin(5*PI*t));y=-c['body']*.57-.026*math.cos(5*PI*t)
                pts.append((x,y,z))
            mesh.tube(pts,[.017]*48,m['leaf'],weights,n=8)
            for j in range(5):
                p=pts[j*9+4];leaf(p,.13,.055,s*(.6 if j%2 else -.4),weights(Vector(p)))
    if not mesh.v:return []
    obj=mesh.object('ReferenceDetails',rig);uv(obj);return [obj]


def pose(rig,mode):
    for b in rig.pose.bones:b.rotation_mode='QUATERNION';b.rotation_quaternion=(1,0,0,0);b.location=(0,0,0)
    def swing(name,axis,a):
        b=rig.pose.bones[name];q=b.bone.matrix_local.to_quaternion();b.rotation_quaternion=q.inverted()@Quaternion(axis,a)@q
    if mode!='T-Pose':
        for side,s in [('L',1),('R',-1)]:
            angle={'Standing':1.24,'Seated':1.0,'ArmsUp':-1.05,'ArmsForward':.12,'ArmsOut':0}.get(mode,1.24)
            swing('UpperArm.'+side,(0,1,0),s*angle)
            if mode=='ArmsForward':swing('UpperArm.'+side,(0,0,1),-s*1.1)
            if mode=='Seated':swing('Thigh.'+side,(1,0,0),-1.5);swing('Shin.'+side,(1,0,0),1.5)
        if mode=='HeadLeft':swing('Head',(0,0,1),.5)
    bpy.context.view_layer.update()


def actions(rig):
    for mode in ['Standing','Seated','T-Pose','ArmsUp','ArmsOut','ArmsForward','HeadLeft']:
        rig.animation_data_create();rig.animation_data.action=None;pose(rig,mode)
        for b in rig.pose.bones:
            for frame in [1,2]:b.keyframe_insert('rotation_quaternion',frame=frame,group=b.name)
        action=rig.animation_data.action;action.name=mode
        track=rig.animation_data.nla_tracks.new();track.name=mode;track.strips.new(mode,1,action);track.mute=True
    rig.animation_data.action=None;pose(rig,'T-Pose')


def studio():
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24
    scene.render.resolution_x=720;scene.render.resolution_y=840;scene.render.resolution_percentage=100
    scene.world=bpy.data.worlds.new('ReviewWorld');scene.world.color=(.25,.25,.25);scene.view_settings.view_transform='AgX'
    bpy.ops.object.camera_add(location=(.65,-7,3.05));camera=bpy.context.object;camera.name='ReviewCamera'
    camera.rotation_euler=(Vector((0,0,1.6))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type='ORTHO';camera.data.ortho_scale=3.7;scene.camera=camera
    for p,power,size in [((-3,-4,6),650,4),((3,-2,3),420,3),((1,3,5),850,3)]:
        bpy.ops.object.light_add(type='AREA',location=p);light=bpy.context.object;light.data.energy=power;light.data.shape='DISK';light.data.size=size
        light.rotation_euler=(Vector((0,0,1.5))-light.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.mesh.primitive_plane_add(size=200);floor=bpy.context.object;floor.name='ReviewFloor';floor.location.z=-.015
    floor.data.materials.append(material('Review neutral','#c5cecc',.8))


def build(name,render=True):
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
    c=CONFIGS[name];m=materials(name,c);rig,chains=skeleton(c)
    skin,feet,weights=body(c,rig,m);objects=[rig,skin,feet,*hands(c,rig,chains,m)]
    facial,_=face(c,rig,m);objects+=facial+details(name,c,rig,m,weights)
    # Collision hull discovery is explicit for new geometry; no fake corrective target.
    skin['armCollisionSurface']=True;facial[0]['armCollisionSurface']=True
    actions(rig)
    for obj in objects:
        if obj.type=='MESH':obj['localBuild']='reference-review-1'
        if obj.type=='MESH' and obj.data.shape_keys:
            for key in obj.data.shape_keys.key_blocks:key.value=0
    export(OUT/f'{name}.glb',objects,True,morph_normals=True)
    for obj in objects:
        if obj.type=='MESH' and obj.data.shape_keys:
            for key in obj.data.shape_keys.key_blocks:key.value=0
    studio();pose(rig,'Standing')
    refs=json.loads((ROOT/'.context/replacement-roster-2026-09-10.json').read_text())
    ref=next(c['reference'] for c in refs['characters'] if c['id']==name)
    image=bpy.data.images.load(str(ROOT/ref));image.pack()
    empty=bpy.data.objects.new('Original reference - not exported',None);bpy.context.collection.objects.link(empty)
    empty.empty_display_type='IMAGE';empty.data=image;empty.empty_display_size=3.3;empty.location=(3,1,1.65);empty.rotation_euler=(PI/2,0,0);empty.hide_render=True
    bpy.ops.wm.save_as_mainfile(filepath=str(BLENDS/f'{name}.blend'))
    report={'id':name,'status':'review-only','vertices':sum(len(o.data.vertices) for o in objects if o.type=='MESH'),
            'bones':len(rig.data.bones),'reference':ref,'glb':str((OUT/f'{name}.glb').relative_to(ROOT)),'visualApproval':False}
    (QA/f'{name}-build.json').write_text(json.dumps(report,indent=2))
    if render:
        bpy.context.scene.render.filepath=str(OUT/'thumbnails'/f'{name}.png');bpy.ops.render.render(write_still=True)
    print('LOCAL CHARACTER BUILT',json.dumps(report),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ids',default=','.join(CONFIGS));parser.add_argument('--no-render',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    for folder in [OUT,OUT/'textures',OUT/'thumbnails',BLENDS,QA]:folder.mkdir(parents=True,exist_ok=True)
    for name in args.ids.split(','):build(name,not args.no_render)
    original=json.loads((ROOT/'assets/3dai/manifest.json').read_text())
    roster=json.loads((ROOT/'.context/replacement-roster-2026-09-10.json').read_text())
    chars=[]
    for entry in roster['characters']:
        if entry['action']=='retain':chars.append(next(c for c in original['characters'] if c['id']==entry['id']))
        else:chars.append(dict(id=entry['id'],name=entry['name'],url=f"assets/local-characters/{entry['id']}.glb",thumbnail=f"assets/local-characters/thumbnails/{entry['id']}.png",status='review-only'))
    if all((ROOT/c['url']).exists() for c in chars):
        (OUT/'manifest.json').write_text(json.dumps({'version':1,'status':'local Blender review roster; not production-approved','vehicle':None,'characters':chars},indent=2))


if __name__=='__main__':main()
