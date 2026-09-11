"""Install editable pose drivers after GLB export, without changing runtime assets."""
import json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from refine_3dai_rigs import pose
from pose_correctives import install_drivers
configs=json.loads((ROOT/'scripts/rig_3dai_landmarks.json').read_text())
for path in sorted((ROOT/'blender/3dai/refined').glob('*-rigged.blend')):
    name=path.name.removesuffix('-rigged.blend');c=configs.get(name,{})
    bpy.ops.wm.open_mainfile(filepath=str(path));bpy.context.preferences.filepaths.save_version=0
    rig=bpy.data.objects['AvatarRig'];body=bpy.data.objects[name.title()+'SourceBody']
    samples=[dict(s) for s in body['correctiveSamples']]
    if body.data.shape_keys.animation_data:body.data.shape_keys.animation_data_clear()
    if rig.animation_data:
        for driver in list(rig.animation_data.drivers):rig.driver_remove(driver.data_path,driver.array_index)
    install_drivers(body,rig,samples,lambda mode:pose(rig,name,c,mode))
    pose(rig,name,c,'ArmsUp');bpy.context.view_layer.update()
    assert body.data.shape_keys.key_blocks['correctiveArmsUpL'].value>.99,(name,'driver did not follow arm')
    pose(rig,name,c,'Seated');bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(path));print('DRIVERS',name,flush=True)
