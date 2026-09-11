"""Read-only Blender diagnostics for staged mesh validity and body weights."""
import bpy
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
names=sys.argv[sys.argv.index('--')+1:]
for name in names:
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/3dai/refined'/(name+'-rigged.blend')))
    body=bpy.data.objects[name.title()+'SourceBody']
    mesh=body.data.copy()
    print('VALIDATE_MESH',name,flush=True)
    changed=mesh.validate(verbose=True,clean_customdata=False)
    print('VALIDATE_RESULT',name,changed,'vertices',len(body.data.vertices),len(mesh.vertices),
          'faces',len(body.data.polygons),len(mesh.polygons),flush=True)
    bpy.data.meshes.remove(mesh)
