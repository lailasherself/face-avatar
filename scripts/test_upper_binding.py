import json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from refine_3dai_rigs import pose,strain
from rebind_upper_body import rebind_upper_body
name=sys.argv[sys.argv.index('--')+1]
c=json.loads((ROOT/'scripts/rig_3dai_landmarks.json').read_text()).get(name,{})
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'.context/before-refinement'/f'{name}-rigged.blend'))
rig=bpy.data.objects['AvatarRig'];body=bpy.data.objects[name.title()+'SourceBody']
rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
rebind_upper_body(body,rig,c)
for mode in ['Seated','Standing','T-Pose','ArmsUp','ArmsForward','HeadLeft']:
    pose(rig,name,c,mode);print('BINDING',mode,json.dumps(strain(body)),flush=True)
pose(rig,name,c,'ArmsUp')
scene=bpy.context.scene;scene.cycles.samples=12;scene.render.resolution_x=800;scene.render.resolution_y=800
scene.render.filepath=str(ROOT/'.context/qa/refinement'/f'{name}-binding-overhead.png');bpy.ops.render.render(write_still=True)
