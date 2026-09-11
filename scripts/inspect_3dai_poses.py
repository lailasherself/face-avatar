"""Measure posed edge strain and dump suspect weights for visual rig review."""
import json
from pathlib import Path
import sys

import bpy
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_3dai_characters import Character


def inspect(name,c):
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/3dai'/(name+'-rigged.blend')))
    rig=bpy.data.objects['AvatarRig']; body=bpy.data.objects[name.title()+'SourceBody']
    rig.animation_data.action=None
    for track in rig.animation_data.nla_tracks: track.mute=True
    for obj in [body,bpy.data.objects[name.title()+'EyesAndMouth']]:
        for key in obj.data.shape_keys.key_blocks: key.value=0
    character=Character.__new__(Character); character.name=name; character.c=c; character.rig=rig
    positions=np.array([v.co[:] for v in body.data.vertices]); edges=np.array([e.vertices[:] for e in body.data.edges])
    lengths=np.linalg.norm(positions[edges[:,0]]-positions[edges[:,1]],axis=1)
    report={}
    for pose in ['Seated','Standing','T-Pose']:
        character.pose(pose)
        evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get()); mesh=evaluated.to_mesh()
        posed=np.array([v.co[:] for v in mesh.vertices])
        after=np.linalg.norm(posed[edges[:,0]]-posed[edges[:,1]],axis=1)
        ratios=after/np.maximum(.006,lengths)
        suspect=np.argsort(ratios)[-8:][::-1]
        report[pose]={'maxStretch':float(ratios.max()),'edgesOverFour':int((ratios>4).sum()),
                      'worst':[{'stretch':float(ratios[i]),'vertices':[{'index':int(j),'co':positions[j].tolist(),
                                'weights':{body.vertex_groups[g.group].name:round(g.weight,3) for g in body.data.vertices[j].groups}} for j in edges[i]]} for i in suspect]}
        evaluated.to_mesh_clear()
    (ROOT/'.context/qa/3dai'/(name+'-pose-strain.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(name,json.dumps({p:{k:v for k,v in r.items() if k!='worst'} for p,r in report.items()}),flush=True)


if __name__=='__main__':
    configs=json.loads((ROOT/'scripts/rig_3dai_landmarks.json').read_text())
    names=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else list(configs)
    for name in names: inspect(name,configs[name])
