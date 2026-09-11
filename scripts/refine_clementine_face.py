"""Rebuild Clementine's small mouth below the nose on locally refined topology."""
import math
import bpy
import bmesh
from mathutils import Vector
from build_3dai_characters import Character, ROOT
from add_3dai_teeth import add_teeth


def rebuild(config,source):
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/3dai/clementine-prepared.blend'))
    body=bpy.data.objects['ClementineSourceBody']
    bm=bmesh.new();bm.from_mesh(body.data)
    edges=set()
    for face in bm.faces:
        x,y,z=face.calc_center_median()
        if abs(x)<.18 and y<-.25 and 1.90<z<2.08:edges.update(face.edges)
    bmesh.ops.subdivide_edges(bm,edges=list(edges),cuts=5,use_grid_fill=True)
    bm.to_mesh(body.data);bm.free();body.data.update()
    character=Character('clementine',config,source)
    character.create_rig();character.facial_targets();character.actions()
    bm=bmesh.new();bm.from_mesh(body.data)
    eye_edges=set()
    for face in bm.faces:
        x,y,z=face.calc_center_median()
        if y<-.25 and any(((x-ex)/rx)**2+((z-ez)/rz)**2<1.8 for ex,ez,rx,ry,rz in config['eyes']):
            eye_edges.update(face.edges)
    bmesh.ops.subdivide_edges(bm,edges=list(eye_edges),cuts=2,use_grid_fill=True)
    bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3])
    bm.to_mesh(body.data);bm.free();body.data.update()
    scale=max(.40,min(1.3,max(.12,character.mw)/.34))
    add_teeth(character.rig,{'mx':character.mx,'mz':character.mz,'mw':character.mw,'my':character.my,
                           'curve':character.curve,'wave':config.get('mouthWave',0),'rim':character.mouth_rim,'scale':scale,'angle':.4,
                           'sideways':.08*scale,'hinge':[character.mx,character.my+.30*scale,character.mz+.10*scale],
                           'fit':{'span':.62,'recess':.16,'upperZ':.025,'lowerZ':-.06,'upperHeight':.017,'lowerHeight':.017}})
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'assets/3dai/rigged/silver-vehicle.glb'))
    camera=bpy.context.scene.camera;camera.location=(3.8,-7,3.3)
    camera.rotation_euler=(Vector((0,0,1.6))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=4.3
    return character.rig,character.body
