"""Locate visible topology with the largest pose strain."""
import sys
from pathlib import Path
import bpy
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from refine_3dai_rigs import pose
import json

name=sys.argv[sys.argv.index('--')+1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'.context/before-refinement'/f'{name}-rigged.blend'))
rig=bpy.data.objects['AvatarRig'];body=bpy.data.objects[name.title()+'SourceBody']
rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
pose(rig,name,json.loads((ROOT/'scripts/rig_3dai_landmarks.json').read_text()).get(name,{}),'ArmsUp')
rest=np.array([v.co[:] for v in body.data.vertices])
evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
moved=np.array([v.co[:] for v in mesh.vertices]);evaluated.to_mesh_clear()
edges=np.array([e.vertices[:] for e in body.data.edges])
ratios=np.linalg.norm(moved[edges[:,0]]-moved[edges[:,1]],axis=1)/np.maximum(.006,np.linalg.norm(rest[edges[:,0]]-rest[edges[:,1]],axis=1))
for index in np.argsort(ratios)[-12:]:
    a,b=edges[index]
    print('EDGE',ratios[index],rest[a],rest[b],flush=True)
    for i in [a,b]:print([(body.vertex_groups[g.group].name,round(g.weight,3)) for g in body.data.vertices[i].groups],flush=True)
