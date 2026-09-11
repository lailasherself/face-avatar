"""Fit a continuous four-influence torso/arm field to the reviewed skeleton."""
import numpy as np


def smooth(a,b,x):
    t=np.clip((x-a)/max(1e-6,b-a),0,1)
    return t*t*(3-2*t)


def rebind_upper_body(body,rig,config):
    groups=list(body.vertex_groups);lookup={g.name:g.index for g in groups}
    points=np.array([v.co[:] for v in body.data.vertices]);old=np.zeros((len(points),len(groups)))
    for v in body.data.vertices:
        for g in v.groups:old[v.index,g.group]=g.weight
    locked_head=old[:,lookup['Head']]>.999
    edges=np.array([e.vertices[:] for e in body.data.edges]);a,b=edges.T
    strength=1/np.maximum(.006,np.linalg.norm(points[a]-points[b],axis=1))
    degree=np.zeros(len(points));np.add.at(degree,a,strength);np.add.at(degree,b,strength)
    arms=np.stack([sum(old[:,lookup[n+'.'+side]] for n in ['UpperArm','Forearm','Hand']) for side in ['L','R']],axis=1)
    for _ in range(90):
        neighbors=np.zeros_like(arms)
        np.add.at(neighbors,a,arms[b]*strength[:,None]);np.add.at(neighbors,b,arms[a]*strength[:,None])
        arms=.5*arms+.5*neighbors/np.maximum(1,degree[:,None])
        arms[locked_head]=0
    arms=smooth(.03,.92,arms)
    arms/=np.maximum(1,arms.sum(axis=1,keepdims=True))
    weights=np.zeros_like(old)
    hips=rig.data.bones['Hips'].head_local.z
    chest=rig.data.bones['Chest'].head_local.z
    floor=config.get('headPinFloor',config.get('faceFloor',1.62))
    knots=[hips,(hips+chest)/2,chest,min(floor-.04,rig.data.bones['Neck'].head_local.z),floor+.055]
    knots=np.maximum.accumulate(knots)
    torso=1-arms.sum(axis=1)
    z=points[:,2]
    for i,name in enumerate(['Hips','Spine','Chest','Neck','Head']):
        lower=smooth(knots[i-1],knots[i],z) if i else np.ones(len(z))
        upper=1-smooth(knots[i],knots[i+1],z) if i<4 else np.ones(len(z))
        weights[:,lookup[name]]=torso*lower*upper
    for j,side in enumerate(['L','R']):
        bones=[rig.data.bones[n+'.'+side] for n in ['UpperArm','Forearm','Hand']]
        lengths=np.array([b.length for b in bones]);start=0.;distances=[];parameters=[]
        for bone,length in zip(bones,lengths):
            origin=np.array(bone.head_local);direction=np.array(bone.tail_local)-origin
            t=np.clip((points-origin)@direction/(direction@direction),0,1)
            distances.append(np.linalg.norm(points-origin-t[:,None]*direction,axis=1))
            parameters.append(start+t*length);start+=length
        closest=np.argmin(distances,axis=0)
        t=np.take_along_axis(np.array(parameters),closest[None,:],axis=0)[0]
        elbow=smooth(lengths[0]-.12,lengths[0]+.12,t)
        wrist=smooth(lengths[:2].sum()-.11,lengths[:2].sum()+.025,t)
        for name,value in [('UpperArm',1-elbow),('Forearm',elbow-wrist),('Hand',wrist)]:
            weights[:,lookup[name+'.'+side]]=arms[:,j]*np.maximum(value,0)
    blend=np.maximum(smooth(hips+.05,hips+.23,z),smooth(.25,.75,arms.sum(axis=1)))
    # Leave legs/tails and their existing seated binding unchanged.
    weights=old*(1-blend[:,None])+weights*blend[:,None]
    weights[locked_head]=old[locked_head]
    for vertex in body.data.vertices:
        row=weights[vertex.index];keep=np.argsort(row)[-4:];total=row[keep].sum()
        if total<1e-10:continue
        for index in [g.group for g in vertex.groups]:body.vertex_groups[index].remove([vertex.index])
        for i in keep:
            if row[i]>1e-8:groups[i].add([vertex.index],float(row[i]/total),'REPLACE')
