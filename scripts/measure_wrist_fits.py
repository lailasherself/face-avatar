import bpy,sys,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from rebind_upper_body import rebind_upper_body
from refine_3dai_rigs import refit_sprout_arms
configs=json.loads((ROOT/'scripts/rig_3dai_landmarks.json').read_text())
for name in [*configs,'coral']:
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'.context/before-refinement'/(name+'-rigged.blend')))
    rig=bpy.data.objects['AvatarRig'];body=bpy.data.objects[name.title()+'SourceBody'];config=configs.get(name,{})
    if name=='sprout':config=refit_sprout_arms(rig,config)
    rebind_upper_body(body,rig,config)
    for side in ['L','R']:
        bone=rig.data.bones['Hand.'+side];origin=bone.head_local;d=(bone.tail_local-origin).normalized()
        length=max(.2,min(.32,bone.length*1.25));groups={body.vertex_groups[n+'.'+side].index for n in ['UpperArm','Forearm','Hand']}
        points=[]
        for edge in body.data.edges:
            a,b=[body.data.vertices[i] for i in edge.vertices]
            wa=sum(g.weight for g in a.groups if g.group in groups);wb=sum(g.weight for g in b.groups if g.group in groups)
            if (wa+wb)/2<.55:continue
            da=(a.co-origin).dot(d)+length*.2;db=(b.co-origin).dot(d)+length*.2
            if da*db>=0:continue
            p=a.co.lerp(b.co,da/(da-db))
            if (p-origin).length<length*3:points.append(p)
        if points:
            center=sum(points,Vector())/len(points);delta=center-origin;delta-=d*delta.dot(d)
            print('WRIST_FIT',name,side,'offset',list(delta),'center',list(origin+delta),'points',len(points),flush=True)
