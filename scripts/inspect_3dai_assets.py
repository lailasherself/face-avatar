"""Inspect downloaded library sources in an isolated background Blender process."""
import hashlib
import json
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.context/qa/3dai'


def inspect(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    objects = []
    bounds = []
    for obj in bpy.context.scene.objects:
        entry = {'name': obj.name, 'type': obj.type}
        if obj.type == 'MESH':
            mesh = obj.data
            mesh.calc_loop_triangles()
            bm = bmesh.new()
            bm.from_mesh(mesh)
            entry.update(vertices=len(mesh.vertices), polygons=len(mesh.polygons),
                         triangles=len(mesh.loop_triangles),
                         boundary_edges=sum(e.is_boundary for e in bm.edges),
                         nonmanifold_edges=sum(not e.is_manifold for e in bm.edges),
                         loose_vertices=sum(not v.link_edges for v in bm.verts),
                         uv_layers=list(mesh.uv_layers.keys()),
                         materials=[m.name if m else None for m in mesh.materials],
                         shape_keys=list(mesh.shape_keys.key_blocks.keys()) if mesh.shape_keys else [],
                         vertex_groups=list(obj.vertex_groups.keys()),
                         armatures=[m.object.name for m in obj.modifiers if m.type == 'ARMATURE' and m.object])
            bm.free()
            bounds.extend(obj.matrix_world @ Vector(c) for c in obj.bound_box)
        if obj.type == 'ARMATURE':
            entry['bones'] = list(obj.data.bones.keys())
        objects.append(entry)
    return {'task_id': path.stem, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'bytes': path.stat().st_size, 'objects': objects,
            'bounds': [[min(p[k] for p in bounds) for k in range(3)],
                       [max(p[k] for p in bounds) for k in range(3)]],
            'images': [{'name': i.name, 'size': list(i.size), 'packed': bool(i.packed_file)}
                       for i in bpy.data.images],
            'actions': list(bpy.data.actions.keys())}


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    reports = []
    for path in sorted((ROOT / 'assets/3dai/originals').glob('*.glb')):
        report = inspect(path)
        reports.append(report)
        print('INSPECT', json.dumps(report), flush=True)
    (OUT / 'source-inspection.json').write_text(json.dumps(reports, indent=2) + '\n')
