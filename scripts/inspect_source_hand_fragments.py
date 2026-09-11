import bpy,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
name=sys.argv[sys.argv.index('--')+1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/3dai/refined'/(name+'-rigged.blend')))
rig=bpy.data.objects['AvatarRig'];body=bpy.data.objects[name.title()+'SourceBody']
for side in ['L','R']:
    bone=rig.data.bones['Hand.'+side];origin=bone.head_local;direction=(bone.tail_local-origin).normalized()
    length=max(.2,min(.32,bone.length*1.25));groups={body.vertex_groups[n+'.'+side].index for n in ['UpperArm','Forearm','Hand']}
    rows=[]
    for face in body.data.polygons:
        center=sum((body.data.vertices[i].co for i in face.vertices),Vector())/len(face.vertices)
        offset=center-origin;along=offset.dot(direction);radial=(offset-direction*along).length
        if along>-.2*length and along<length*3 and radial<length*2:
            weight=sum(sum(g.weight for g in body.data.vertices[i].groups if g.group in groups) for i in face.vertices)/len(face.vertices)
            if weight>.01:rows.append((face.index,tuple(round(c,3) for c in center),round(along/length,3),round(radial/length,3),round(weight,3)))
    print('REMAINING',side,len(rows),rows[::max(1,len(rows)//35)],flush=True)
