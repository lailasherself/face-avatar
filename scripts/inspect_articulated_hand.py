import bpy,sys
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(root/'blender/3dai/refined/orbit-rigged.blend'))
rig=bpy.data.objects['AvatarRig'];obj=bpy.data.objects['OrbitArticulatedHandL']
bone=rig.data.bones['Hand.L'];origin=bone.head_local;d=(bone.tail_local-origin).normalized()
n=Vector((0,-1,0));n=(n-d*n.dot(d)).normalized();w=d.cross(n).normalized();length=max(.20,min(.32,bone.length*1.25))
center=origin+d*length*.24
print('CENTER',center,'RAY',obj.ray_cast(center+n, -n),flush=True)
for vertex in sorted(obj.data.vertices,key=lambda v:(v.co-center).length)[:8]:
    print('PALM',vertex.co,[(obj.vertex_groups[g.group].name,g.weight) for g in vertex.groups],flush=True)
print('BOUNDS',[(min((v.co-origin).dot(axis) for v in obj.data.vertices),max((v.co-origin).dot(axis) for v in obj.data.vertices)) for axis in [w,d,n]],flush=True)
bm=__import__('bmesh').new();bm.from_mesh(obj.data)
print('BOUNDARY',sum(e.is_boundary for e in bm.edges),'VOLUME',bm.calc_volume(),flush=True)
