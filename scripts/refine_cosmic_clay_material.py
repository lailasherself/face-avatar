"""Material-only Cosmic revision, executed through the live Blender MCP."""
import bpy
import hashlib
import json
import shutil
import numpy as np
from pathlib import Path
import complete_cosmic_likeness as cosmic

ROOT=Path(__file__).resolve().parents[1]
QA=ROOT/'.context/qa/cosmic-material-review'


def geometry_signature():
    digest=hashlib.sha256()
    def floats(collection,attribute,size):
        values=np.empty(len(collection)*size,dtype=np.float32);collection.foreach_get(attribute,values);digest.update(values.tobytes())
    for o in sorted(bpy.context.scene.objects,key=lambda o:o.name):
        if o.type=='MESH':
            digest.update(o.name.encode());floats(o.data.vertices,'co',3)
            digest.update(json.dumps([list(p.vertices) for p in o.data.polygons]).encode())
            digest.update(json.dumps([[(o.vertex_groups[g.group].name,g.weight) for g in v.groups] for v in o.data.vertices]).encode())
            for uv in o.data.uv_layers:floats(uv.data,'uv',2)
            if o.data.shape_keys:
                for key in o.data.shape_keys.key_blocks:digest.update(key.name.encode());floats(key.data,'co',3)
        elif o.type=='ARMATURE':
            digest.update(json.dumps([(b.name,list(b.head_local),list(b.tail_local),[list(row) for row in b.matrix_local]) for b in o.data.bones]).encode())
    return digest.hexdigest()


def checkpoint():
    assert bpy.context.scene.name=='Cosmic - Reference Contour Character'
    QA.mkdir(parents=True,exist_ok=True)
    snapshot=QA/'before-material-review.blend'
    if not snapshot.exists():
        bpy.ops.wm.save_as_mainfile(filepath=str(snapshot),copy=True)
        shutil.copy2(cosmic.GLB,QA/'before-material-review.glb')
        for name in ['final-neutral.png','final-tongue-blink.png','runtime-neutral.png']:
            source=cosmic.QA/name
            if source.exists():shutil.copy2(source,QA/('before-'+name))
        (QA/'geometry-before.txt').write_text(geometry_signature())


def materials():
    cosmic.reset();s=bpy.context.scene;objects=[cosmic.obj(n) for n in ['Cosmic Head','Cosmic Body']]
    source=objects[0].data.materials[0];clay=source.copy();clay.name='Cosmic Galaxy Clay - Runtime PBR'
    n=clay.node_tree.nodes;l=clay.node_tree.links;p=n['Principled BSDF']
    p.inputs['Roughness'].default_value=.88;p.inputs['Specular IOR Level'].default_value=.14;p.inputs['Metallic'].default_value=0;p.inputs['Coat Weight'].default_value=0
    for link in list(p.inputs['Normal'].links):l.remove(link)
    coordinates=n.new('ShaderNodeTexCoord');previous=None
    for scale,strength,distance in [(42,.38,.012),(135,.30,.0035)]:
        noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=scale;noise.inputs['Detail'].default_value=2.5;noise.inputs['Roughness'].default_value=.7;l.new(coordinates.outputs['Object'],noise.inputs['Vector'])
        bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=strength;bump.inputs['Distance'].default_value=distance;l.new(noise.outputs['Fac'],bump.inputs['Height'])
        if previous:l.new(previous,bump.inputs['Normal'])
        previous=bump.outputs['Normal']
    l.new(previous,p.inputs['Normal'])
    for o in objects:o.data.materials[0]=clay
    procedural=clay.copy();procedural.name='Cosmic Clay Surface - Editable Grain';procedural.use_fake_user=True
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    atlas=bpy.data.images.new('Cosmic clay tangent normal',width=1024,height=1024);atlas.colorspace_settings.name='Non-Color'
    target=n.new('ShaderNodeTexImage');target.image=atlas;n.active=target;samples=s.cycles.samples;s.cycles.samples=8
    bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT',use_clear=False,margin=8)
    atlas.filepath_raw=str(cosmic.GLB.parent/'cosmic-clay-normal.png');atlas.file_format='PNG';atlas.save();atlas.pack();s.cycles.samples=samples
    for link in list(p.inputs['Normal'].links):l.remove(link)
    normal=n.new('ShaderNodeNormalMap');l.new(target.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs['Normal'],p.inputs['Normal'])
    for name in ['Orange','Green']:
        exterior=cosmic.material(name).node_tree.nodes['Principled BSDF'];exterior.inputs['Roughness'].default_value=.81;exterior.inputs['Specular IOR Level'].default_value=.16;exterior.inputs['Coat Weight'].default_value=0
    eye=cosmic.material('Eye').node_tree.nodes['Principled BSDF'];eye.inputs['Base Color'].default_value=(.0005,.0015,.0007,1);eye.inputs['Roughness'].default_value=.028;eye.inputs['Specular IOR Level'].default_value=.5;eye.inputs['IOR'].default_value=1.5;eye.inputs['Metallic'].default_value=0;eye.inputs['Coat Weight'].default_value=1;eye.inputs['Coat Roughness'].default_value=.035
    clay['revision']='Matte clay grain with unchanged purple/star pigment; black eyes retain a separate polished glass-like finish.'
    s['materialRevision']='cosmic-clay-surface-glossy-eyes-1'
    before=(QA/'geometry-before.txt').read_text();after=geometry_signature();assert before==after,'Material revision changed geometry, UVs, weights or morphs'
    report={'geometry_unchanged':True,'geometry_sha256':after,'body_roughness':.88,'body_specular':.14,'eye_roughness':.028,'eye_coat':1,'normal_atlas':atlas.filepath_raw,'color_texture_changed':False,'visual_approval':'pending'}
    (QA/'material-validation.json').write_text(json.dumps(report,indent=2));print(report)
