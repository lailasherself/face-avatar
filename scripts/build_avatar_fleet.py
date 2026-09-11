"""Build the reference-inspired fleet with Blender 5.x, without third-party addons.

Run: Blender --background --factory-startup --python scripts/build_avatar_fleet.py
All geometry, weights, facial targets, and materials remain editable in the .blend files.
"""

import argparse
import json
import math
from pathlib import Path
import random
import sys

import bpy
from mathutils import Vector, Quaternion

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets' / 'fleet'
SOURCE = ROOT / 'blender' / 'fleet'
OUT.mkdir(parents=True, exist_ok=True)
SOURCE.mkdir(parents=True, exist_ok=True)
PI = math.pi

CHANNELS = '''eyeBlinkLeft eyeBlinkRight eyeSquintLeft eyeSquintRight eyeWideLeft eyeWideRight
eyeLookUpLeft eyeLookUpRight eyeLookDownLeft eyeLookDownRight eyeLookInLeft eyeLookInRight
eyeLookOutLeft eyeLookOutRight jawOpen jawForward jawLeft jawRight mouthClose mouthFunnel
mouthPucker mouthLeft mouthRight mouthSmileLeft mouthSmileRight mouthFrownLeft mouthFrownRight
mouthStretchLeft mouthStretchRight mouthRollLower mouthRollUpper mouthShrugLower mouthShrugUpper
mouthPressLeft mouthPressRight mouthLowerDownLeft mouthLowerDownRight mouthUpperUpLeft mouthUpperUpRight
mouthDimpleLeft mouthDimpleRight browDownLeft browDownRight browInnerUp browOuterUpLeft browOuterUpRight
cheekPuff cheekSquintLeft cheekSquintRight noseSneerLeft noseSneerRight tongueOut'''.split()

CHARACTERS = [
    dict(id='orbit', name='Orbit', skin='#aa72dc', lip='#514068', eye='#ffa914', pupil='#121912', outfit='#c080b4', pants='#aa72dc', shoes='#aa72dc', head=(.70,.48,.62), style='antenna', sleepy=.98, reference='Jy8yzW'),
    dict(id='pearl', name='Pearl', skin='#e5bacf', lip='#d97757', eye='#173bb5', pupil='#a6ce29', outfit='#e5bacf', pants='#e5bacf', shoes='#e5bacf', head=(.46,.39,.70), style='pearl', cyclops=True, reference='kMxwme'),
    dict(id='juno', name='Juno', skin='#ea78b3', lip='#cc5595', eye='#ffe32a', pupil='#0d1511', outfit='#ea78b3', pants='#fa790c', shoes='#fa790c', head=(.69,.43,.57), style='jester', cyclops=True, sleepy=1.02, reference='bjWgsy'),
    dict(id='fuzz', name='Fuzz', skin='#bba1db', lip='#a482bd', eye='#f0e9bf', pupil='#254832', outfit='#bba1db', pants='#bba1db', shoes='#ffc527', head=(.58,.39,.50), style='fuzz', reference='UnGowG'),
    dict(id='clementine', name='Clementine', skin='#f57622', lip='#d84414', eye='#e9edc5', pupil='#286528', outfit='#ed552c', pants='#9684b4', shoes='#295d3a', head=(.70,.45,.61), style='jacket', sleepy=1.04, reference='zF0uXa'),
    dict(id='coral', name='Coral', skin='#ac5c7b', lip='#d36776', eye='#ffe1a0', pupil='#153c56', outfit='#ac5c7b', pants='#565b71', shoes='#925575', head=(.55,.42,.65), style='coral', reference='nkmqsW'),
    dict(id='sprout', name='Sprout', skin='#77538c', lip='#56376d', eye='#27e368', pupil='#07190f', outfit='#f28a15', pants='#24885b', shoes='#77538c', head=(.70,.43,.59), style='beanie', reference='8KA2yn'),
    dict(id='atl', name='ATL', skin='#88b86a', lip='#55784c', eye='#111c3a', pupil='#090f22', outfit='#f3f0d5', pants='#f3f0d5', shoes='#4e7851', head=(.59,.41,.68), style='baseball', reference='ppDO39'),
]

def clamp(v, lo=0., hi=1.):
    return min(hi, max(lo, v))

def color(hexcode):
    vals = [int(hexcode[i:i+2],16)/255 for i in (1,3,5)]
    return tuple(v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in vals) + (1,)

def material(name, tint, rough=.35, metal=0.):
    m = bpy.data.materials.new(name)
    m.diffuse_color = color(tint)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = color(tint)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    p.inputs['Coat Weight'].default_value = .25 if metal == 0 else .4
    return m

class Mesh:
    def __init__(self):
        self.v, self.f, self.mi, self.weights, self.tags = [], [], [], [], []
        self.mats = []

    def vertex(self, p, weight=None, tag=None):
        self.v.append(tuple(p))
        self.weights.append(weight or {'Head':1.})
        self.tags.append(tag)
        return len(self.v)-1

    def face(self, verts, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        self.f.append(verts)
        self.mi.append(self.mats.index(mat))

    def grid(self, nu, nv, fn, mat, weight=None, tag=None, wrap=True):
        start = len(self.v)
        for i in range(nu):
            for j in range(nv):
                u, v = i/(nu-1), j/(nv if wrap else nv-1)
                p = fn(u,v)
                self.vertex(p, weight(p) if callable(weight) else weight,
                            tag(u,v,p) if callable(tag) else tag)
        for i in range(nu-1):
            for j in range(nv if wrap else nv-1):
                k = (j+1)%nv
                self.face((start+i*nv+j,start+i*nv+k,start+(i+1)*nv+k,start+(i+1)*nv+j),mat)

    def ellipsoid(self, center, scale, mat, weight=None, tag=None, n=24, rings=14, power=1.):
        def sp(v):
            return math.copysign(abs(v)**power,v)
        def fn(u,v):
            a,b = PI*u,2*PI*v
            return (center[0]+scale[0]*sp(math.sin(a)*math.cos(b)),
                    center[1]+scale[1]*sp(math.sin(a)*math.sin(b)),
                    center[2]+scale[2]*sp(math.cos(a)))
        self.grid(rings,n,fn,mat,weight,tag)

    def tube(self, points, radii, mat, weight=None, n=10, tag=None):
        pts = [Vector(p) for p in points]
        start = len(self.v)
        for i,p in enumerate(pts):
            tangent = (pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)]).normalized()
            axis = tangent.cross(Vector((0,1,0)))
            if axis.length < .01:
                axis = tangent.cross(Vector((1,0,0)))
            axis.normalize()
            other = tangent.cross(axis).normalized()
            for j in range(n):
                q = p+radii[i]*(axis*math.cos(2*PI*j/n)+other*math.sin(2*PI*j/n))
                self.vertex(q,weight(q) if callable(weight) else weight,tag)
        for i in range(len(pts)-1):
            for j in range(n):
                self.face((start+i*n+j,start+i*n+(j+1)%n,start+(i+1)*n+(j+1)%n,start+(i+1)*n+j),mat)
        self.face(tuple(start+j for j in reversed(range(n))),mat)
        self.face(tuple(start+(len(pts)-1)*n+j for j in range(n)),mat)

    def object(self,name,rig=None):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(self.v,[],self.f)
        mesh.update()
        obj = bpy.data.objects.new(name,mesh)
        bpy.context.collection.objects.link(obj)
        for mat in self.mats:
            mesh.materials.append(mat)
        for poly,idx in zip(mesh.polygons,self.mi):
            poly.material_index=idx
            poly.use_smooth=True
        # Recalculate normals for all procedural surfaces, including cavity interiors.
        bpy.context.view_layer.objects.active=obj
        obj.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        obj.select_set(False)
        if rig:
            groups={b.name:obj.vertex_groups.new(name=b.name) for b in rig.data.bones}
            for i,weights in enumerate(self.weights):
                total=sum(weights.values())
                for bone,w in weights.items():
                    if w>0:
                        groups[bone].add([i],w/total,'REPLACE')
            mod=obj.modifiers.new('Body deformation','ARMATURE')
            mod.object=rig
            obj.parent=rig
        return obj

def armature():
    data=bpy.data.armatures.new('Fleet skeleton')
    rig=bpy.data.objects.new('AvatarRig',data)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active=rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    def bone(name,head,tail,parent=None):
        b=data.edit_bones.new(name)
        b.head,b.tail=head,tail
        if parent:
            b.parent=data.edit_bones[parent]
    bone('Root',(0,0,0),(0,0,.3))
    bone('Hips',(0,0,1.02),(0,0,1.25),'Root')
    bone('Spine',(0,0,1.25),(0,0,1.53),'Hips')
    bone('Chest',(0,0,1.53),(0,0,1.80),'Spine')
    bone('Neck',(0,0,1.80),(0,0,2.04),'Chest')
    bone('Head',(0,0,2.04),(0,0,2.65),'Neck')
    for side,s in [('L',1),('R',-1)]:
        bone('UpperArm.'+side,(s*.32,0,1.72),(s*.68,0,1.72),'Chest')
        bone('Forearm.'+side,(s*.68,0,1.72),(s*1.02,0,1.72),'UpperArm.'+side)
        bone('Hand.'+side,(s*1.02,0,1.72),(s*1.17,0,1.72),'Forearm.'+side)
        for j in range(4):
            y=(j-1.5)*.068
            tip=1.36 if j in (1,2) else 1.29
            bone(f'Finger{j+1}.{side}',(s*1.15,y,1.72),(s*tip,y,1.72),'Hand.'+side)
        bone('Thigh.'+side,(s*.19,0,1.06),(s*.22,0,.59),'Hips')
        bone('Shin.'+side,(s*.22,0,.59),(s*.22,0,.17),'Thigh.'+side)
        bone('Foot.'+side,(s*.22,0,.17),(s*.22,-.26,.10),'Shin.'+side)
        bone('Toe.'+side,(s*.22,-.26,.1),(s*.22,-.39,.08),'Foot.'+side)
    bpy.ops.object.mode_set(mode='OBJECT')
    rig.select_set(False)
    rig.show_in_front=True
    rig['seatAnchor']=[0,0,.82]
    rig['rigVersion']='fleet-1'
    return rig

def body_mesh(c,rig,m):
    mesh=Mesh()
    style=c['style']
    def torso_weight(p):
        z=p[2]
        if z<1.25:
            t=clamp((z-1.1)/.2)
            return {'Hips':1-t,'Spine':t}
        t=clamp((z-1.4)/.2)
        return {'Spine':1-t,'Chest':t}
    mesh.ellipsoid((0,0,1.40),(.34,.23,.43),m['outfit'],torso_weight,n=32,rings=22)
    mesh.ellipsoid((0,0,1.09),(.29,.22,.20),m['pants'],{'Hips':1},n=24)
    mesh.ellipsoid((0,0,1.91),(.15,.15,.20),m['skin'],{'Neck':1},n=20)
    for side,s in [('L',1),('R',-1)]:
        def arm_weight(p):
            x=abs(p[0]);t=clamp((x-.58)/.2)
            if x>.96:
                h=clamp((x-.97)/.09)
                return {'Forearm.'+side:1-h,'Hand.'+side:h}
            return {'UpperArm.'+side:1-t,'Forearm.'+side:t}
        ar=[.15,.15,.14,.125,.115,.10,.092,.085]
        points=[(s*(.28+i*.11),0,1.72) for i in range(8)]
        mesh.tube(points,ar,m['outfit'],arm_weight,n=16)
        hand=m['green'] if style=='jacket' else m['skin']
        if style=='jester':hand=m['pants']
        mesh.ellipsoid((s*1.115,0,1.72),(.14,.12,.072),hand,{'Hand.'+side:1},n=16,rings=10)
        for j in range(4):
            y=(j-1.5)*.068
            length=.23 if j in (1,2) else .16
            pts=[(s*(1.13+t*length),y*(1+.25*t),1.72-.02*math.sin(t*PI)) for t in [0,.25,.5,.75,1]]
            mesh.tube(pts,[.039,.04,.037,.029,.006],hand,{f'Finger{j+1}.{side}':1},n=8)
        def leg_weight(p):
            t=clamp((.69-p[2])/.20)
            return {'Thigh.'+side:1-t,'Shin.'+side:t}
        points=[(s*(.19+.03*i/9),0,1.1-i*.10) for i in range(10)]
        radii=[.145,.155,.148,.132,.118,.112,.107,.101,.097,.095]
        mesh.tube(points,radii,m['pants'],leg_weight,n=16)
        shoe=m['shoes']
        mesh.ellipsoid((s*.22,-.115,.135),(.15,.28,.125),shoe,{'Foot.'+side:1},n=24)
        if style in ['fuzz','jacket','baseball']:
            mesh.ellipsoid((s*.22,-.12,.056),(.155,.282,.052),m['sole'],{'Foot.'+side:1},n=24)
            for j in range(4):
                y=-.05-j*.045
                mesh.tube([(s*.22-.07,y,.236),(s*.22,y-.01,.25),(s*.22+.07,y,.236)], [.009]*3,m['sole'],{'Foot.'+side:1},n=6)
        else:
            for j in range(3):
                mesh.ellipsoid((s*.22+(j-1)*.085,-.32,.11),(.052,.10,.064),shoe,{'Toe.'+side:1},n=12,rings=8)
        if style in ['fuzz','pearl','antenna']:
            # Subtle raised rings retain the toy-like ribbed limbs from the references.
            for j in range(13):
                x=.38+j*.045
                r=.138-(x-.38)*.08
                mesh.tube([(s*x,r*math.cos(k*2*PI/20),1.72+r*math.sin(k*2*PI/20)) for k in range(21)], [.006]*21,m['skin'],arm_weight,n=5)
    if style=='jacket':
        mesh.ellipsoid((0,-.223,1.43),(.155,.026,.31),m['yellow'],torso_weight,n=20)
        for s in (-1,1):
            mesh.tube([(s*.13,-.21,1.77),(s*.10,-.253,1.57),(s*.16,-.225,1.14)],[.045,.037,.035],m['outfit'],torso_weight,n=10)
    if style in ['baseball','jester']:
        mesh.tube([(-.27,-.15,1.14),(0,-.235,1.12),(.27,-.15,1.14)],[.035]*3,m['navy'] if style=='baseball' else m['pants'],{'Hips':1},n=10)
        mesh.ellipsoid((0,-.258,1.14),(.047,.015,.044),m['yellow'],{'Hips':1},n=12,rings=8)
    if style=='baseball':
        for s in (-1,1):
            mesh.tube([(s*.025,-.215,1.18),(s*.025,-.246,1.48),(s*.025,-.17,1.74)],[.013]*3,m['red'],torso_weight,n=6)
    if style in ['pearl','fuzz']:
        mesh.tube([(0,.14,1.08),(0,.30,.87),(0,.36,.54),(0,.27,.42)],[.08,.075,.063,.02],m['skin'],{'Hips':1},n=14)
    return mesh.object('Body',rig)

def face_mesh(c,rig,m):
    mesh=Mesh()
    hw,hd,hh=c['head']
    hz=2.40
    mz=-.31
    mw=.29 if not c.get('cyclops') else .31
    mh=.035
    power=.73 if c['style'] in ['beanie','jester','antenna'] else 1.
    def surface(x,z):
        rr=(abs(x/hw)**(2/power)+abs(z/hh)**(2/power))
        return -hd*max(0.,1-rr)**(power/2)
    def face_grid(u,v):
        a=v*2*PI
        x=(1-u)*mw*math.cos(a)+u*hw*math.copysign(abs(math.cos(a))**power,math.cos(a))
        z=(1-u)*(mz+mh*math.sin(a))+u*hh*math.copysign(abs(math.sin(a))**power,math.sin(a))
        return (x,surface(x,z),z)
    mesh.grid(28,64,face_grid,m['skin'],tag='skin')
    def back(u,v):
        a=2*PI*v;t=u*PI/2
        return (hw*math.cos(t)*math.copysign(abs(math.cos(a))**power,math.cos(a)),hd*math.sin(t),hh*math.cos(t)*math.copysign(abs(math.sin(a))**power,math.sin(a)))
    mesh.grid(16,64,back,m['skin'],tag='back')
    # A real opening with an inset oral cavity. No skin polygon spans the lips.
    def cavity(u,v):
        a=v*2*PI;x=mw*math.cos(a)*(1-.25*u);z=mz+mh*math.sin(a)*(1+u)
        return (x,surface(mw*math.cos(a),mz+mh*math.sin(a))+.26*u,z)
    mesh.grid(5,64,cavity,m['cavity'],tag='cavity')
    mesh.ellipsoid((0,-.12,mz),(.26,.045,.21),m['cavity'],tag='cavity',n=24)
    lip_points=[]
    for i in range(65):
        a=2*PI*i/64;x=mw*math.cos(a);z=mz+mh*math.sin(a)
        lip_points.append((x,surface(x,z)-.018,z))
    mesh.tube(lip_points,[.038 if c['style']!='pearl' else .065]*65,m['lip'],n=8,tag='lip')
    mouth_y=surface(0,mz)
    mesh.ellipsoid((0,mouth_y+.14,mz-.026),(.20,.065,.026),m['tongue'],tag='tongue',n=20,rings=8)
    for j in range(6):
        mesh.ellipsoid(((j-2.5)*.06,mouth_y+.075,mz+.009),(.033,.025,.040),m['teeth'],tag='teeth',n=8,rings=6)
    # Eyes and their enclosing spherical eyelids use geometric morph targets.
    eyes=[(0.,.21,.31)] if c.get('cyclops') else [(-hw*.44,.16,.245),(hw*.44,.16,.245)]
    if c['style']=='pearl':eyes=[(0.,.26,.235)]
    for ex,ez,radius in eyes:
        ey=surface(ex,ez)-.025
        er=(radius,.155,radius*.93)
        center=(ex,ey,ez)
        side='Left' if ex>=0 else 'Right'
        eye_tag={'part':'eye','side':side,'center':center}
        mesh.ellipsoid(center,er,m['eye'],tag=eye_tag,n=32,rings=18)
        def pupil(u,v):
            a=2*PI*v;t=.001+u*.48
            px=math.sin(t)*math.cos(a)*(.53 if c['style']=='jester' else 1)
            pz=math.sin(t)*math.sin(a)*(1.4 if c['style']=='jester' else 1)
            return (ex+er[0]*px,ey-(er[1]+.002)*math.sqrt(max(.01,1-px*px-pz*pz)),ez+er[2]*pz)
        pupil_tag={**eye_tag,'part':'pupil','radius':er}
        mesh.grid(8,24,pupil,m['pupil'],tag=pupil_tag)
        mesh.ellipsoid((ex-radius*.12,ey-er[1]*.975-.003,ez+radius*.16),(radius*.085,.002,radius*.095),m['glint'],tag=pupil_tag,n=12,rings=8)
        for upper in [True,False]:
            angle=c.get('sleepy',.65) if upper else .58
            def lid(u,v):
                theta=.001+u*angle;phi=2*PI*v
                return (ex+(er[0]+.008)*math.sin(theta)*math.cos(phi),
                        ey+(er[1]+.008)*math.sin(theta)*math.sin(phi),
                        ez+(1 if upper else -1)*(er[2]+.008)*math.cos(theta))
            def lid_tag(u,v,p):
                return {**eye_tag,'part':'lid','upper':upper,'u':u,'v':v,'angle':angle,'radius':er}
            mesh.grid(9,32,lid,m['skin'],tag=lid_tag)
        # Low, rounded orbital ridge, integrated visually with the eyelid.
        pts=[]
        for j in range(13):
            a=.18*PI+j*.64*PI/12
            x=ex+radius*1.03*math.cos(a);z=ez+radius*1.05*math.sin(a)
            pts.append((x,surface(x,z)-.015,z))
        mesh.tube(pts,[.032]*13,m['skin'],n=8,tag='brow')
    if not c.get('cyclops'):
        mesh.ellipsoid((0,-hd-.018,-.07),(.075,.075,.125 if c['style']=='coral' else .082),m['skin'],tag='nose',n=20,rings=12)

    def delta(p,tag,name):
        x,y,z=p;d=Vector((0,0,0))
        if isinstance(tag,dict):
            side=tag['side']
            match=name.endswith(side) or c.get('cyclops',False)
            if tag['part']=='lid' and match:
                a=tag['angle'];upper=tag['upper']
                if name.startswith('eyeBlink'):a=1.66 if upper else 1.49
                elif name.startswith('eyeSquint'):a=min(1.56,a+.18) if upper else 1.22
                elif name.startswith('eyeWide'):a=.32
                else:return d
                theta=.001+tag['u']*a;phi=2*PI*tag['v'];rx,ry,rz=tag['radius'];cx,cy,cz=tag['center']
                return Vector((cx+(rx+.008)*math.sin(theta)*math.cos(phi),cy+(ry+.008)*math.sin(theta)*math.sin(phi),cz+(1 if upper else -1)*(rz+.008)*math.cos(theta)))-Vector(p)
            if tag['part']=='pupil' and match and name.startswith('eyeLook'):
                cx,cy,cz=tag['center'];rx,ry,rz=tag['radius']
                v=Vector(((x-cx)/rx,(y-cy)/ry,(z-cz)/rz))
                if 'Up' in name:q=Quaternion((1,0,0),-.30)
                elif 'Down' in name:q=Quaternion((1,0,0),.30)
                else:
                    sign=1 if side=='Left' else -1
                    q=Quaternion((0,0,1),(-1 if 'In' in name else 1)*sign*.30)
                dv=q@v-v
                return Vector((dv.x*rx,dv.y*ry,dv.z*rz))
            return d
        if tag=='back':return d
        left=clamp(.5+x/.18);right=1-left
        side=left if name.endswith('Left') else right if name.endswith('Right') else 1.
        mouth=math.exp(-((x/.46)**4+((z-mz)/.26)**2))
        lower=clamp((mz+.025-z)/.08)
        upper=1-lower
        corner=clamp(abs(x)/mw)
        front=clamp((-y-.04)/.24)
        if tag in ['lip','cavity','tongue','teeth']:mouth=1.
        if name=='jawOpen':
            weight=clamp((.06-z)/.39)*front
            if tag=='teeth':weight=0
            d.z-=.26*weight;d.y-=.045*weight
        elif name in ['jawLeft','jawRight','jawForward']:
            w=clamp((.03-z)/.4)*front
            if name=='jawForward':d.y-=.07*w
            else:d.x+=(1 if name=='jawLeft' else -1)*.10*w
        elif name=='mouthClose':d.z+=.23*lower*mouth
        elif name=='mouthFunnel':
            d.x-=x*.28*mouth;d.y-=.075*mouth;d.z+=(z-mz)*1.1*mouth
        elif name=='mouthPucker':
            d.x-=x*.54*mouth;d.y-=.12*mouth;d.z-=(z-mz)*.3*mouth
        elif name in ['mouthLeft','mouthRight']:d.x+=(1 if name=='mouthLeft' else -1)*.10*mouth
        elif name.startswith('mouthSmile'):
            d.x+=math.copysign(.075,x)*side*mouth*corner;d.z+=.115*corner**1.6*side*mouth
        elif name.startswith('mouthFrown'):d.z-=.09*corner*side*mouth
        elif name.startswith('mouthStretch'):d.x+=math.copysign(.10,x)*side*mouth*corner
        elif name.startswith('mouthDimple'):
            d.y+=.055*side*mouth*corner;d.x+=math.copysign(.04,x)*side*mouth
        elif name.startswith('mouthPress'):d.z-=(z-mz)*.8*mouth*side
        elif name=='mouthRollLower':d.y+=.05*lower*mouth;d.z+=.022*lower*mouth
        elif name=='mouthRollUpper':d.y+=.05*upper*mouth;d.z-=.022*upper*mouth
        elif name=='mouthShrugLower':d.z+=.07*lower*mouth;d.y-=.025*lower*mouth
        elif name=='mouthShrugUpper':d.z+=.07*upper*mouth;d.y-=.025*upper*mouth
        elif name.startswith('mouthLowerDown'):d.z-=.12*lower*mouth*side
        elif name.startswith('mouthUpperUp'):d.z+=.10*upper*mouth*side
        elif name.startswith('brow'):
            w=math.exp(-((abs(x)-hw*.38)/.30)**2-((z-.39)/.16)**2)*front
            if name=='browInnerUp':d.z+=.10*w*(1-clamp(abs(x)/hw))
            elif 'OuterUp' in name:d.z+=.12*w*side*clamp(abs(x)/hw)
            else:d.z-=.085*w*side
        elif name=='cheekPuff':
            w=math.exp(-((abs(x)-hw*.62)/.20)**2-((z+.12)/.22)**2)*front
            d.y-=.09*w;d.x+=math.copysign(.035,x)*w
        elif name.startswith('cheekSquint'):
            w=math.exp(-((abs(x)-hw*.45)/.2)**2-((z+.06)/.17)**2)*front*side
            d.z+=.065*w
        elif name.startswith('noseSneer'):
            w=math.exp(-(x/.22)**2-((z+.12)/.17)**2)*front*side
            d.z+=.065*w;d.y-=.035*w
        elif name=='tongueOut' and tag=='tongue':d.y-=.31;d.z-=.025
        return d

    local=list(mesh.v)
    mesh.v=[(x,y,z+hz) for x,y,z in local]
    obj=mesh.object('Face',rig)
    surfaces=[]
    for ex,ez,radius in eyes:
        ey=surface(ex,ez)-.025
        surfaces.append(dict(center=[ex,hz+ez,-ey],radii=[radius+.012,radius*.93+.012,.155+.012]))
    lid_attribute=obj.data.attributes.new(name='_LID_INDEX',type='FLOAT',domain='POINT')
    lid_indices=[]
    for tag in mesh.tags:
        index=0
        if isinstance(tag,dict) and tag['part']=='lid':
            index=next(i+1 for i,(ex,ez,r) in enumerate(eyes) if ex==tag['center'][0])
        lid_indices.append(index)
    lid_attribute.data.foreach_set('value',lid_indices)
    obj['eyelidSurfaces']=surfaces
    obj.shape_key_add(name='Basis',from_mix=False).value=0
    changed={}
    for name in CHANNELS:
        key=obj.shape_key_add(name=name,from_mix=False)
        key.value=0
        count=0
        for i,(p,tag) in enumerate(zip(local,mesh.tags)):
            d=delta(p,tag,name)
            if d.length>1e-6:count+=1
            key.data[i].co=Vector(mesh.v[i])+d
        changed[name]=count
    assert all(changed.values()), f'Empty facial targets: {changed}'
    obj['blendshapeConvention']='ARKit 52; anatomical left is character left'
    return obj, changed

def accessories(c,rig,m):
    mesh=Mesh();style=c['style'];hw,hd,hh=c['head'];hz=2.4
    random.seed(42)
    if style in ['antenna','jester']:
        for s in [-1,1]:
            for rear in [False,True]:
                y=.18 if rear else -.025
                pts=[]
                for i in range(21):
                    t=i/20
                    pts.append((s*(.39+.63*t),y+.06*t,hz+hh*.79+.59*math.sin(PI*t*.9)))
                radii=[.105-.052*i/20 for i in range(21)]
                mesh.tube(pts,radii,m['skin'],n=14)
                tip=Vector(pts[-1]);tip.z-=.065
                mesh.ellipsoid(tip,(.12,.12,.15),m['orange'] if style=='antenna' else m['navy'],n=20)
                mesh.ellipsoid(pts[-1],(.129,.129,.065),m['skin'] if style=='antenna' else m['orange'],n=20)
                for j in range(1,18):
                    p=Vector(pts[j]);tangent=(Vector(pts[j+1])-Vector(pts[j-1])).normalized()
                    a=tangent.cross(Vector((0,1,0))).normalized();b=tangent.cross(a).normalized();r=radii[j]
                    mesh.tube([p+(r+.001)*(a*math.cos(k*2*PI/12)+b*math.sin(k*2*PI/12)) for k in range(13)],[.006]*13,m['skin'],n=5)
    if style=='coral':
        for j in range(7):
            a=.07*PI+j*.86*PI/6
            start=Vector((hw*.80*math.cos(a),0,hz+hh*.80*math.sin(a)))
            end=Vector((hw*1.28*math.cos(a),0,hz+hh*1.28*math.sin(a)))
            mesh.tube([start,start.lerp(end,.45),end],[.08,.065,.09],m['skin'],n=14)
            mesh.ellipsoid(end,(.10,.09,.10),m['skin'],n=16,rings=10)
        for s in [-1,1]:
            mesh.ellipsoid((s*.55,.01,hz-.08),(.125,.09,.16),m['skin'],n=20)
            mesh.ellipsoid((s*.61,-.068,hz-.07),(.055,.019,.085),m['lip'],n=16)
    if style in ['beanie','jacket','baseball']:
        hat=m['orange'] if style=='beanie' else m['lavender'] if style=='jacket' else m['navy']
        h=.49 if style!='baseball' else .39
        base=hz+hh*.62
        def crown(u,v):
            a=2*PI*v;t=u*PI/2
            return ((hw+.04)*math.cos(t)*math.cos(a),(hd+.05)*math.cos(t)*math.sin(a),base+h*math.sin(t))
        mesh.grid(16,64,crown,hat)
        if style!='baseball':
            mesh.grid(8,64,lambda u,v:((hw+.053+.015*math.sin(PI*u))*math.cos(2*PI*v),(hd+.06+.015*math.sin(PI*u))*math.sin(2*PI*v),base-.055+u*.17),hat)
            for j in range(64):
                a=2*PI*j/64
                pts=[]
                for k in range(16):
                    t=k/15*PI*.48
                    pts.append(((hw+.048)*math.cos(t)*math.cos(a),(hd+.059)*math.cos(t)*math.sin(a),base+h*math.sin(t)))
                mesh.tube(pts,[.008]*16,hat,n=5)
            if style=='jacket':
                mesh.ellipsoid((0,0,base+h+.095),(.115,.11,.12),m['green'],n=20)
        else:
            mesh.ellipsoid((0,-.46,base-.01),(.64,.37,.045),m['red'],n=40,rings=10)
            mesh.ellipsoid((0,0,base+h),(.055,.055,.035),m['red'],n=16,rings=8)
            for s in [-1,1]:
                mesh.tube([(s*.30,-.39,base+.02),(s*.22,-.35,base+.24),(s*.09,-.18,base+.36)],[.008]*3,m['red'],n=6)
            # An editable letter on the cap; the reference's team wordmark is not a texture dependency.
            a=Mesh()
            for pts in [[(-.11,-hd-.055,base+.09),(0,-hd-.075,base+.29),(.11,-hd-.055,base+.09)],[(-.064,-hd-.075,base+.17),(.064,-hd-.075,base+.17)]]:
                mesh.tube(pts,[.019]*len(pts),m['red'],n=8)
    if style=='fuzz':
        # Exportable tapered strands instead of Blender-only particle hair.
        for j in range(210):
            a=random.random()*2*PI;r=random.random()**.5
            p=Vector((.36*r*math.cos(a),.22*r*math.sin(a),hz+hh*.76))
            end=p+Vector((math.cos(a)*(.08+.2*r),math.sin(a)*.10,.40+random.random()*.30))
            mesh.tube([p,p.lerp(end,.40),p.lerp(end,.77),end],[.016,.019,.012,.001],m['fur'],n=5)
        for j in range(90):
            x=random.uniform(-.24,.24);z=random.uniform(1.19,1.76)
            y=-.23*math.sqrt(max(.1,1-(x/.34)**2))
            mesh.tube([(x,y,z),(x*.98,y-.05,z-.05),(x*.9,y-.07,z-.13)],[.02,.015,.001],m['fur'],{'Chest':1} if z>1.5 else {'Spine':1},n=5)
    return mesh.object('Details',rig)

def pose(rig,mode):
    for b in rig.pose.bones:
        b.rotation_mode='QUATERNION';b.rotation_quaternion=(1,0,0,0);b.location=(0,0,0)
    if mode=='Seated':
        rig.pose.bones['Root'].location.y=-.25
        for s in ['L','R']:
            # World-space swing converted into each bone's rest coordinate system.
            def swing(name,axis,angle):
                b=rig.pose.bones[name];q=b.bone.matrix_local.to_quaternion()
                b.rotation_quaternion=q.inverted()@Quaternion(axis,angle)@q
            swing('Thigh.'+s,(1,0,0),-PI/2)
            swing('Shin.'+s,(1,0,0),PI/2)
            sign=1 if s=='L' else -1
            swing('UpperArm.'+s,(0,1,0),sign*.96)
            swing('Forearm.'+s,(0,0,1),-sign*.62)
    elif mode=='Standing':
        for side,sign in [('L',1),('R',-1)]:
            b=rig.pose.bones['UpperArm.'+side];q=b.bone.matrix_local.to_quaternion()
            b.rotation_quaternion=q.inverted()@Quaternion((0,1,0),sign*1.14)@q
    bpy.context.view_layer.update()

def actions(rig):
    for mode in ['Seated','Standing','T-Pose']:
        rig.animation_data_create();rig.animation_data.action=None
        pose(rig,mode)
        for b in rig.pose.bones:
            for frame in [1,2]:
                b.keyframe_insert('rotation_quaternion',frame=frame,group=b.name)
                b.keyframe_insert('location',frame=frame,group=b.name)
        action=rig.animation_data.action;action.name=mode
        track=rig.animation_data.nla_tracks.new();track.name=mode
        track.strips.new(mode,1,action);track.mute=True
    rig.animation_data.action=None
    pose(rig,'Seated')

def export(path,objects,animated=False,morph_normals=False):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
        export_animations=animated,export_animation_mode='ACTIONS',export_nla_strips=True,
        export_skins=True,export_morph=True,export_morph_normal=morph_normals,
        export_extras=True,export_attributes=True,export_yup=True,export_cameras=False,export_lights=False)

def car():
    mesh=Mesh()
    chrome=material('Polished silver','#dce7eb',.19,1)
    dark=material('Cockpit charcoal','#19242a',.43)
    red=material('Coral leather','#c95536',.42)
    trim=material('Brushed silver','#a1b7c0',.31,.87)
    lamp=material('Ice running lights','#9ce9ef',.16,.2)
    glass=material('Blue windscreen','#66a7b8',.12,.12)
    p=glass.node_tree.nodes.get('Principled BSDF');p.inputs['Alpha'].default_value=.27
    glass.diffuse_color=(*glass.diffuse_color[:3],.27)
    # Annular hull: the top is an open cockpit, never a solid oval through the driver.
    sections=[(.57,.99,.89),(.67,1.14,.83),(.75,1.25,.60),(.70,1.18,.32),(.53,.92,.23),(.22,.44,.22)]
    def hull(u,v):
        t=u*(len(sections)-1);i=min(len(sections)-2,int(t));f=t-i
        w,l,z=[sections[i][k]*(1-f)+sections[i+1][k]*f for k in range(3)]
        a=2*PI*v
        return (w*math.cos(a),l*math.sin(a)-.14,z)
    mesh.grid(31,96,hull,chrome)
    def inner(u,v):
        a=2*PI*v;w=.57-.08*u;l=.99-.14*u
        return (w*math.cos(a),l*math.sin(a)-.14,.89-.39*u)
    mesh.grid(8,96,inner,dark)
    mesh.ellipsoid((0,-.14,.47),(.50,.85,.09),dark,n=48)
    for z,w,l in [(.82,.675,1.144),(.60,.754,1.254)]:
        mesh.tube([(w*math.cos(i*2*PI/96),l*math.sin(i*2*PI/96)-.14,z) for i in range(97)],[.018]*97,trim,n=8)
    # Low nose deck ahead of the windscreen.
    mesh.ellipsoid((0,-1.01,.73),(.50,.39,.14),chrome,n=40)
    for s in [-1,1]:
        mesh.ellipsoid((s*.31,-1.27,.755),(.16,.027,.042),lamp,n=20,rings=8)
        # Swept tail fins with closed, smoothed thickness.
        outline=[(.38,.62,.83),(.48,.82,1.04),(.58,1.17,1.66),(.62,1.27,1.70),(.68,1.22,.55),(.66,.78,.64)]
        start=len(mesh.v)
        for dx in [-.035,.035]:
            for x,y,z in outline:mesh.vertex((s*(x+dx),y-.14,z),{})
        for i in range(6):mesh.face((start+i,start+(i+1)%6,start+6+(i+1)%6,start+6+i),chrome)
        mesh.face(tuple(start+i for i in reversed(range(6))),chrome)
        mesh.face(tuple(start+6+i for i in range(6)),chrome)
    obj=mesh.object('Silver vehicle')
    bevel=obj.modifiers.new('Soft coachwork edges','BEVEL');bevel.width=.025;bevel.segments=3
    bpy.context.view_layer.objects.active=obj
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    interior=Mesh()
    interior.ellipsoid((0,.12,.65),(.38,.37,.10),red,n=32)
    interior.ellipsoid((0,.39,.94),(.36,.10,.33),red,n=32)
    for x in [-.22,-.11,0,.11,.22]:
        interior.tube([(x,.275,.77),(x,.279,.94),(x,.306,1.12)],[.010]*3,trim,n=6)
    # Windshield is low enough to leave the entire face unobstructed.
    def windshield(u,v):
        a=(v-.5)*PI*.92;w=.53*(1-.30*u)
        return (w*math.sin(a),-.76*math.cos(a)+.23*u,.86+.43*u)
    interior.grid(12,40,windshield,glass,wrap=False)
    for u in [0,1]:
        interior.tube([windshield(u,j/40) for j in range(41)],[.013]*41,trim,n=8)
    for v in [0,1]:
        interior.tube([windshield(j/12,v) for j in range(13)],[.014]*13,trim,n=8)
    # Steering yoke, support, and dashboard.
    interior.ellipsoid((0,-.51,.89),(.40,.12,.085),dark,n=24)
    interior.tube([(0,-.49,.78),(0,-.38,.99)],[.025,.025],trim,n=10)
    interior.tube([(-.20,-.40,1.01),(-.13,-.43,.96),(0,-.44,.96),(.13,-.43,.96),(.20,-.40,1.01)],[.025]*5,dark,n=10)
    detail=interior.object('Cockpit fittings')
    anchor=bpy.data.objects.new('SeatAnchor',None);bpy.context.collection.objects.link(anchor);anchor.location=(0,0,.82)
    obj['assetRole']='shared-vehicle';obj['seatHeight']=.82
    return [obj,detail,anchor]

def stage():
    scene=bpy.context.scene
    scene.render.engine='CYCLES';scene.cycles.samples=24
    scene.render.resolution_x=1100;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
    if not scene.world:
        scene.world=bpy.data.worlds.new('Studio world')
    scene.world.color=(.20,.20,.20)
    scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.32,.38,.43,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.45
    floor_mat=material('Studio white','#e5eceb',.75)
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,.04))
    floor=bpy.context.object;floor.name='Studio floor';floor.data.materials.append(floor_mat)
    for name,loc,power,size in [('Key',(-3,-4,6),700,4),('Fill',(4,-1,4),550,3),('Rim',(1,4,5),900,3)]:
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
        obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=loc
        obj.rotation_euler=(Vector((0,0,1.4))-obj.location).to_track_quat('-Z','Y').to_euler()
    data=bpy.data.cameras.new('Preview camera');camera=bpy.data.objects.new('Preview camera',data)
    scene.collection.objects.link(camera);scene.camera=camera
    camera.location=(3.8,-7,3.3);camera.rotation_euler=(Vector((0,0,1.6))-camera.location).to_track_quat('-Z','Y').to_euler()
    data.type='ORTHO';data.ortho_scale=4.1
    scene.view_settings.view_transform='AgX'
    for area in bpy.context.screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective='CAMERA'
    return camera

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version=0

def build_character(c,render=True):
    reset()
    m={k:material(k,c[k],.29 if k in ['skin','lip'] else .4) for k in ['skin','lip','eye','pupil','outfit','pants','shoes']}
    for k,tint in dict(cavity='#230f26',tongue='#de7490',teeth='#fff0d8',glint='#ffffff',sole='#f0eddc',green='#4bb16e',yellow='#ffe259',navy='#12223b',red='#d62056',orange='#ff8917',lavender='#b4a0bf',fur='#b8a2e5').items():
        m[k]=material(k,tint,.48 if k in ['fur','lavender'] else .30)
    for k in ['eye','pupil','glint']:m[k].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.18
    rig=armature();body=body_mesh(c,rig,m);face,changed=face_mesh(c,rig,m);detail=accessories(c,rig,m)
    rig['characterId']=c['id'];rig['cyclops']=c.get('cyclops',False)
    actions(rig)
    export(OUT/(c['id']+'.glb'),[rig,body,face,detail],True)
    vehicle=car();camera=stage()
    rig.animation_data.action=None
    for track in rig.animation_data.nla_tracks:track.mute=True
    bpy.context.scene.frame_set(1)
    pose(rig,'Seated')
    for key in face.data.shape_keys.key_blocks:key.value=0
    bpy.context.scene['README']='Editable reference-inspired prototype. Face: 52 ARKit shape keys. AvatarRig: Seated / Standing / T-Pose actions. Shared car exports separately.'
    bpy.ops.object.select_all(action='DESELECT');face.select_set(True);bpy.context.view_layer.objects.active=face
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/(c['id']+'.blend')))
    if render:
        bpy.context.scene.render.filepath=str(OUT/(c['id']+'.png'));bpy.ops.render.render(write_still=True)
    return {**c,'url':f'assets/fleet/{c["id"]}.glb','thumbnail':f'assets/fleet/{c["id"]}.png','vertices':len(body.data.vertices)+len(face.data.vertices)+len(detail.data.vertices),'bones':len(rig.data.bones),'morphVertices':changed}

def main():
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    parser=argparse.ArgumentParser();parser.add_argument('--only');parser.add_argument('--no-render',action='store_true')
    opts=parser.parse_args(args)
    selected=[c for c in CHARACTERS if not opts.only or c['id']==opts.only]
    manifest=[]
    for c in selected:
        print('BUILDING',c['id'],flush=True)
        manifest.append(build_character(c,not opts.no_render))
    if not opts.only:
        reset();objects=car();export(OUT/'silver-vehicle.glb',objects);stage()
        bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/'silver-vehicle.blend'))
        (OUT/'manifest.json').write_text(json.dumps({'version':1,'vehicle':'assets/fleet/silver-vehicle.glb','channels':CHANNELS,'characters':manifest},indent=2)+'\n')
    print('FLEET BUILD COMPLETE',flush=True)

if __name__=='__main__':main()
