"""Continuous reference-fitted bodies and native-digit skinning for live Blender builds."""
import bpy
import math
import numpy as np
from mathutils import Vector
from complete_cosmic_likeness import tube,ellipsoid
from complete_clay_likeness import closed_rings,profile,smooth


def body(prefix,material,torso,arms,legs,digits,voxel=.010):
    def named(n):return prefix+' '+n
    rings=[]
    for i in range(70):
        z=torso[0][0]+(torso[-1][0]-torso[0][0])*i/69
        x=profile([(p[0],p[1]) for p in torso],z);rx=profile([(p[0],p[2]) for p in torso],z);ry=profile([(p[0],p[3]) for p in torso],z)
        rings.append([(x+rx*math.cos(j*math.tau/64),ry*math.sin(j*math.tau/64),z) for j in range(64)])
    parts=[closed_rings(named('Torso'),rings,material)]
    for side,(path,radii) in arms.items():
        root=Vector(path[0]);root.x=torso[-1][1]
        parts.append(tube(named('Arm '+side),[root,*path],[radii[0],*radii],material,rings=70,sides=32))
        parts.append(ellipsoid(named('Palm '+side),path[-1],(radii[-1]*1.2,radii[-1],radii[-1]*1.35),material,nr=20,nc=32))
        for digit,points in digits[side].items():parts.append(tube(named(digit+' '+side),points,[radii[-1]*.64,radii[-1]*.59,radii[-1]*.51,.014],material,rings=32,sides=24))
        stations=legs[side];rings=[]
        for i in range(54):
            z=stations[0][0]+(stations[-1][0]-stations[0][0])*i/53
            x=profile([(p[0],p[1]) for p in stations],z);rx=profile([(p[0],p[2]) for p in stations],z);ry=profile([(p[0],p[3]) for p in stations],z)
            rings.append([(x+rx*math.cos(j*math.tau/48),-.025+ry*math.sin(j*math.tau/48),z) for j in range(48)])
        parts.append(closed_rings(named('Leg '+side),rings,material))
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();o=bpy.context.object;o.name=named('Body')
    mod=o.modifiers.new('Continuous shoulder wrist hip skin','REMESH');mod.mode='VOXEL';mod.voxel_size=voxel;mod.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=mod.name)
    mod=o.modifiers.new('Soft junctions','SMOOTH');mod.factor=1;mod.iterations=5;bpy.ops.object.modifier_apply(modifier=mod.name)
    o['armCollisionSurface']=True
    return o


def rig(prefix,torso,arms,legs,digits,hip,knee,ankle,neck,head,split_z,arm_x,iterations=750):
    s=bpy.context.scene;body=s.objects[prefix+' Body'];data=bpy.data.armatures.new(prefix+' Skeleton');rig=bpy.data.objects.new(prefix+' AvatarRig',data);s.collection.objects.link(rig)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
    def bone(n,a,b,parent=None):
        e=data.edit_bones.new(n);e.head=a;e.tail=b
        if parent:e.parent=data.edit_bones[parent]
        return e
    chest=min(p[0][0][2] for p in arms.values());cx=torso[-1][1]
    bone('Root',(0,0,0),(0,0,.1));bone('Hips',(cx,0,hip),(cx,0,hip+.15),'Root');bone('Spine',(cx,0,hip+.15),(cx,0,chest-.12),'Hips');bone('Chest',(cx,0,chest-.12),(cx,0,chest),'Spine');bone('Neck',(cx,0,chest),(cx,0,neck),'Chest');bone('Head',(cx,0,neck),(cx,0,head),'Neck')
    for side,(p,radii) in arms.items():
        bone('UpperArm.'+side,p[0],p[1],'Chest');bone('Forearm.'+side,p[1],p[2],'UpperArm.'+side);bone('Hand.'+side,p[2],p[3],'Forearm.'+side)
        x=legs[side][-2][1];bone('Thigh.'+side,(x,0,hip),(x,-.015,knee),'Hips');bone('Shin.'+side,(x,-.015,knee),(x,-.02,ankle),'Thigh.'+side);bone('Foot.'+side,(x,-.02,ankle),(x,-.17,.045),'Shin.'+side)
        for digit,points in digits[side].items():
            for i in range(3):e=bone(f'{digit}{i+1}.{side}',points[i],points[i+1],f'{digit}{i}.{side}' if i else 'Hand.'+side);e.align_roll(Vector((0,-1,0)))
    bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True;rig['installationApproved']=False;rig['rigVersion']=prefix.lower()+'-reference-contour-1'
    for side in arms:
        data.bones['UpperArm.'+side]['armCollisionRestContact']=True
        for digit in digits[side]:
            for i,a in enumerate([.45,.55,.40]):data.bones[f'{digit}{i+1}.{side}']['fingerCurlRadians']=a
    adj=[[] for v in body.data.vertices]
    for e in body.data.edges:a,b=e.vertices;adj[a].append(b);adj[b].append(a)
    remaining={v.index for v in body.data.vertices if v.co.z<split_z};regions={}
    while remaining:
        todo=[remaining.pop()];component=list(todo)
        while todo:
            for j in adj[todo.pop()]:
                if j in remaining:remaining.remove(j);todo.append(j);component.append(j)
        mx=sum(body.data.vertices[i].co.x for i in component)/len(component)
        for i in component:regions[i]=1 if abs(mx-cx)>arm_x else 0
    def closest(p,path):
        result=(1e9,0)
        for i,(a,b) in enumerate(zip(path,path[1:])):
            a,b=Vector(a),Vector(b);d=b-a;t=max(0,min(1,(p-a).dot(d)/d.length_squared));distance=(p-a-d*t).length
            if distance<result[0]:result=(distance,i+t)
        return result
    groups={b.name:body.vertex_groups.new(name=b.name) for b in data.bones}
    for v in body.data.vertices:
        x,y,z=v.co;side='L' if x>cx else 'R';t=smooth(hip+.08,chest-.08,z);n=smooth(chest+.06,neck,z);w={'Hips':(1-t)*(1-n),'Chest':t*(1-n),'Neck':n}
        leg=1-smooth(hip-.14,hip+.09,z)
        if leg:
            k=1-smooth(knee-.13,knee+.13,z);f=1-smooth(ankle-.03,ankle+.10,z);lw={'Thigh.'+side:1-k,'Shin.'+side:k*(1-f),'Foot.'+side:k*f};w={n:a*(1-leg) for n,a in w.items()};w.update({n:a*leg for n,a in lw.items()})
        p,radii=arms[side];arm=regions[v.index] if v.index in regions else smooth(abs(p[0][0]-cx)*.45,abs(p[0][0]-cx)+radii[0]*.35,abs(x-cx))
        if arm:
            e=1-smooth(p[1][2]-.15,p[1][2]+.15,z);hand=1-smooth(p[2][2]-.065,p[2][2]+.065,z);aw={'UpperArm.'+side:1-e,'Forearm.'+side:e*(1-hand),'Hand.'+side:e*hand}
            if z<p[2][2]+.07:
                dist,u,digit=min((*closest(v.co,path),digit) for digit,path in digits[side].items());factor=smooth(.12,.94,u)*(1-smooth(p[2][2]-.055,p[2][2]+.07,z));q=max(0,min(2,u-.5));i=min(1,int(q));f=q-i;aw={n:a*(1-factor) for n,a in aw.items()};aw[f'{digit}{i+1}.{side}']=(1-f)*factor;aw[f'{digit}{i+2}.{side}']=f*factor
            w={n:a*(1-arm) for n,a in w.items()};w.update({n:a*arm for n,a in aw.items()})
        for n,a in w.items():
            if a>1e-8:groups[n].add([v.index],a,'REPLACE')
    count=len(body.data.vertices);gs=list(body.vertex_groups);w=np.zeros((count,len(gs)))
    for v in body.data.vertices:
        for g in v.groups:w[v.index,g.group]=g.weight
    edges=np.array([e.vertices[:] for e in body.data.edges]);a=np.r_[edges[:,0],edges[:,1]];b=np.r_[edges[:,1],edges[:,0]];degree=np.maximum(np.bincount(a,minlength=count),1)
    mask=np.array([smooth(.025,.12,abs(v.co.x-cx))*smooth(split_z-.14,split_z+.02,v.co.z)*(1-smooth(neck-.02,neck+.10,v.co.z)) for v in body.data.vertices])*.7
    for _ in range(iterations):
        mean=np.stack([np.bincount(a,weights=w[b,i],minlength=count)/degree for i in range(len(gs))],axis=1);w+=(mean-w)*mask[:,None]
    for g in gs:g.remove(list(range(count)))
    for v,row in zip(body.data.vertices,w):
        weights={gs[i].name:float(a) for i,a in enumerate(row) if a>1e-8};side='L' if v.co.x>cx else 'R'
        if any(weights.get(n+'.'+side,0)>1e-8 for n in ['UpperArm','Forearm','Hand']):
            trunk=sum(weights.pop(n,0) for n in ['Hips','Spine','Chest','Neck','Head'])
            if trunk:weights['Chest']=trunk
        if any(weights.get(f'{d}{i}.{side}',0)>1e-8 for d in digits[side] for i in [1,2,3]):weights['Forearm.'+side]=weights.get('Forearm.'+side,0)+weights.pop('UpperArm.'+side,0)
        pairs=sorted(weights.items(),key=lambda p:-p[1])[:4];total=sum(a for _,a in pairs)
        for n,a in pairs:groups[n].add([v.index],a/total,'REPLACE')
    for o in s.objects:
        if o.type!='MESH':continue
        if o!=body:o.vertex_groups.new(name='Head').add(list(range(len(o.data.vertices))),1,'REPLACE')
        o.parent=rig;m=o.modifiers.new('Reference skin deformation','ARMATURE');m.object=rig
    return rig
