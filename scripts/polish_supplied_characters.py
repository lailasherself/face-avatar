"""Material and junction refinement of the supplied-image rigs, via live Blender MCP.

Stages are explicit. Preserve the rig, native digits and every facial target.
Never invoke geometry() twice on the same source.
"""
import json
import math
import shutil
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
import complete_supplied_characters as rig
from complete_clay_likeness import plain_material, smooth

ROOT = Path(__file__).resolve().parents[1]


def qa():
    p = ROOT / '.context/qa' / (rig.prefix().lower() + '-surface-refinement')
    p.mkdir(parents=True, exist_ok=True)
    return p


def preserve():
    target = qa() / 'before'
    target.mkdir(exist_ok=True)
    name = rig.prefix().lower()
    paths = [ROOT / 'blender/likeness-trials' / (name + '-image-rig.blend')]
    paths += list((ROOT / 'assets/likeness-trials').glob(name + '-image-*'))
    for p in paths:
        if p.is_file() and not (target / p.name).exists():
            shutil.copy2(p, target / p.name)
    for name in ['geometry-validation.json', 'runtime-validation.json', 'final-neutral.png']:
        source = rig.qa() / name
        if source.exists() and not (target / name).exists():
            shutil.copy2(source, target / name)
    rig.reset()
    print('Preserved previous source, exports, textures and checks:', target)


class Surface:
    def __init__(self, label, color, roughness):
        self.mat = plain_material(rig.prefix() + ' Refined ' + label, color, roughness)
        self.nodes = self.mat.node_tree.nodes
        self.links = self.mat.node_tree.links
        self.p = self.nodes['Principled BSDF']
        self.coord = self.node('ShaderNodeTexCoord').outputs['Object']
        self.p.inputs['Specular IOR Level'].default_value = .32

    def node(self, kind):
        return self.nodes.new(kind)

    def wire(self, value, socket):
        if isinstance(value, bpy.types.NodeSocket):
            self.links.new(value, socket)
        else:
            socket.default_value = value

    def math(self, op, a, b=0):
        n = self.node('ShaderNodeMath'); n.operation = op
        self.wire(a, n.inputs[0]); self.wire(b, n.inputs[1])
        return n.outputs[0]

    def noise(self, scale, detail=3, vector=None):
        n = self.node('ShaderNodeTexNoise')
        n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = detail
        n.inputs['Roughness'].default_value = .7
        self.wire(self.coord if vector is None else vector, n.inputs['Vector'])
        return n.outputs['Fac']

    def mix(self, value, a, b):
        n = self.node('ShaderNodeMixRGB')
        self.wire(value, n.inputs[0]); self.wire(a, n.inputs[1]); self.wire(b, n.inputs[2])
        return n.outputs[0]

    def ramp(self, value, stops):
        n = self.node('ShaderNodeValToRGB'); r = n.color_ramp
        for i, (position, color) in enumerate(stops):
            e = r.elements[i] if i < 2 else r.elements.new(position)
            e.position = position; e.color = (*color, 1) if len(color) == 3 else color
        r.interpolation = 'EASE'; self.wire(value, n.inputs[0])
        return n.outputs['Color']

    def bump(self, value, distance, strength=.3):
        n = self.node('ShaderNodeBump')
        n.inputs['Distance'].default_value = distance
        n.inputs['Strength'].default_value = strength
        self.wire(value, n.inputs['Height'])
        if self.p.inputs['Normal'].is_linked:
            self.wire(self.p.inputs['Normal'].links[0].from_socket, n.inputs['Normal'])
        self.wire(n.outputs['Normal'], self.p.inputs['Normal'])

    def attribute(self, name):
        n = self.node('ShaderNodeAttribute'); n.attribute_name = name
        return n.outputs['Fac']

    def folds(self, flow, frequency, distance, warp=2.6):
        phase = self.math('ADD', self.math('MULTIPLY', flow, frequency), self.math('MULTIPLY', self.noise(9, 2), warp))
        ridge = self.math('POWER', self.math('ABSOLUTE', self.math('SINE', phase)), 5)
        self.bump(ridge, distance, .34)
        return ridge


def restore_originals():
    for o in rig.meshes():
        for i, m in enumerate(list(o.data.materials)):
            name = m.name.split(' - Baked PBR')[0]
            assert name in bpy.data.materials, name
            o.data.materials[i] = bpy.data.materials[name]


def assign(o, surface, index=0):
    o.data.materials[index] = surface.mat


def geometry():
    rig.reset(); s = bpy.context.scene
    assert not s.get('surfaceJunctionRefined'), 'Junction refinement already applied'
    body = rig.obj('Body'); points = np.array([v.co[:] for v in body.data.vertices])
    before = points.copy(); edges = np.array([e.vertices[:] for e in body.data.edges])
    a = np.r_[edges[:, 0], edges[:, 1]]; b = np.r_[edges[:, 1], edges[:, 0]]
    degree = np.maximum(np.bincount(a, minlength=len(points)), 1)
    # Concentrate rounding on torso/hip seams; protect foot tips and outer hands.
    mask = []
    orbit = rig.prefix() == 'Orbit'
    for x, y, z in points:
        if orbit:
            amount = (1 - smooth(.80, 1.05, z)) * (1 - smooth(.53, .67, abs(x))) * smooth(.17,.29,z)
        else:
            amount = (1 - smooth(.45, .62, z)) * (1 - smooth(.23, .31, abs(x)))
        mask.append(amount * .48)
    mask = np.array(mask)[:, None]
    for _ in range(180 if orbit else 120):
        mean = np.stack([np.bincount(a, weights=points[b, i], minlength=len(points)) / degree for i in range(3)], axis=1)
        points += (mean - points) * mask
    if orbit:
        for p in points:
            x,y,z=p
            front=1-smooth(-.25,-.08,y)
            abdomen=(1-smooth(.45,.60,abs(x-.025)))*smooth(.48,.70,z)*(1-smooth(1.10,1.35,z))
            p[1]-=.045*front*abdomen
            p[2]-=.045*front*math.exp(-((x-.025)/.29)**2)*smooth(.46,.59,z)*(1-smooth(.68,.86,z))
    for v, p in zip(body.data.vertices, points):
        v.co = p
    body.data.update()
    # Bury the exposed neck-cap edge behind the throat rather than presenting a disk.
    neck = rig.obj('Neck Bridge')
    for v in neck.data.vertices:
        v.co.y += .032 if orbit else .055
    neck.data.update()
    if orbit:
        head=rig.obj('Head');patch=head['patches']['mouth'];start,n=patch['start'],patch['size']
        for key in head.data.shape_keys.key_blocks:
            for i in range(start,len(key.data)):
                t=rig.LEVELS[(i-start)//n]
                key.data[i].co.y-=.008*math.sin(t*math.pi/1.4)
        head.data.update()
    s['surfaceJunctionRefined'] = True
    (qa() / 'junction-changes.json').write_text(json.dumps({'vertices': len(points), 'maxDisplacement': float(np.max(np.linalg.norm(points-before, axis=1))), 'unchangedArmatureAndWeights': True}, indent=2))
    print('Rounded lower-body seams without replacing topology, weights or morphs')


def orbit_materials():
    restore_originals()
    face = Surface('Pebbled lavender skin', (.32, .16, .44), .53)
    color = face.ramp(face.noise(6, 3), [(.18, (.31,.155,.425)), (.82, (.35,.18,.46))])
    face.wire(color, face.p.inputs['Base Color'])
    pebble = face.node('ShaderNodeTexVoronoi'); pebble.feature = 'SMOOTH_F1'
    pebble.inputs['Scale'].default_value = 110; pebble.inputs['Smoothness'].default_value = .28
    face.wire(face.coord, pebble.inputs['Vector'])
    face.bump(pebble.outputs['Distance'], .010, .48)
    face.bump(face.noise(430, 2), .0012, .18)
    face.p.inputs['Coat Weight'].default_value = .10
    face.p.inputs['Coat Roughness'].default_value = .32
    assign(rig.obj('Head'), face); assign(rig.obj('Neck Bridge'), face)
    for o in rig.meshes():
        if 'Collar' in o.name: assign(o, face)

    body = Surface('Irregular folded lavender skin', (.32,.16,.44), .53)
    tint = body.mix(body.attribute('belly_mask'), (.32,.16,.44,1), (.53,.19,.24,1))
    body.wire(body.mix(body.math('MULTIPLY', body.noise(5), .10), tint, (.44,.24,.44,1)), body.p.inputs['Base Color'])
    stretch = body.node('ShaderNodeVectorMath'); stretch.operation='MULTIPLY'
    body.wire(body.coord,stretch.inputs[0]);stretch.inputs[1].default_value=(9,9,70)
    creases=body.noise(1,2,stretch.outputs[0])
    sep=body.node('ShaderNodeSeparateXYZ');body.wire(body.coord,sep.inputs[0])
    mask=body.ramp(sep.outputs['Z'],[(.22,(0,0,0)),(.45,(1,1,1))])
    body.bump(body.math('MULTIPLY',creases,mask), .026, .48)
    body.bump(body.noise(240, 2), .0015, .2)
    body.p.inputs['Coat Weight'].default_value = .12
    body.p.inputs['Coat Roughness'].default_value = .3
    assign(rig.obj('Body'), body)
    for o in rig.meshes():
        if 'Antenna' not in o.name: continue
        stem = Surface(o.name + ' folds', (.34,.17,.46), .48)
        stem.folds(stem.attribute('sculpt_flow'), 152, .004, 6)
        stem.bump(stem.noise(290, 2), .0013, .16)
        assign(o, stem)

    lips = Surface('Blue charcoal lip skin', (.027,.055,.070), .4)
    lips.bump(lips.noise(200), .0014, .25)
    assign(rig.obj('Head'), lips, 1)
    for o in rig.meshes():
        if 'Orange tip' in o.name:
            bulb = Surface(o.name + ' amber glaze', (.95,.185,.002), .25)
            bulb.bump(bulb.noise(85,2), .0018, .16)
            bulb.p.inputs['Coat Weight'].default_value = .7
            bulb.p.inputs['Coat Roughness'].default_value = .12
            assign(o, bulb)
    oral_materials()
    bpy.context.scene['surfaceRevision'] = 'reference-material-refinement-2'


def coral_materials():
    restore_originals()
    skin = Surface('Burgundy wax skin', (.27,.07,.12), .42)
    separate = skin.node('ShaderNodeSeparateXYZ'); skin.wire(skin.coord, separate.inputs[0])
    height = skin.math('MULTIPLY', skin.math('SUBTRACT', separate.outputs['Z'], 1.03), .9)
    colors = skin.ramp(height, [(0, (.13,.065,.11)), (.58, (.31,.075,.11)), (1, (.34,.065,.095))])
    skin.wire(skin.mix(skin.math('MULTIPLY', skin.noise(7, 2), .13), colors, (.43,.18,.22,1)), skin.p.inputs['Base Color'])
    stretch=skin.node('ShaderNodeVectorMath');stretch.operation='MULTIPLY'
    skin.wire(skin.coord,stretch.inputs[0]);stretch.inputs[1].default_value=(11,11,105)
    skin.bump(skin.noise(1,2,stretch.outputs[0]), .0055, .28)
    skin.bump(skin.noise(310,2), .00065, .18)
    height=0
    x=skin.math('ADD',separate.outputs['X'],.056)
    for j in range(5):
        line=skin.math('ADD',2.005+j*.063,skin.math('MULTIPLY',skin.math('POWER',x,2),-.19))
        line=skin.math('ADD',line,skin.math('MULTIPLY',skin.math('SINE',skin.math('ADD',skin.math('MULTIPLY',x,14),j)),.005))
        d=skin.math('DIVIDE',skin.math('SUBTRACT',separate.outputs['Z'],line),.007+j*.0006)
        groove=skin.math('EXPONENT',skin.math('MULTIPLY',skin.math('MULTIPLY',d,d),-1))
        height=skin.math('SUBTRACT',height,groove)
    front=skin.ramp(separate.outputs['Y'],[(0,(1,1,1)),(.1,(0,0,0))])
    sides=skin.ramp(skin.math('ABSOLUTE',x),[(.40,(1,1,1)),(.60,(0,0,0))])
    skin.bump(skin.math('MULTIPLY',height,skin.math('MULTIPLY',front,sides)), .003, .28)
    skin.p.inputs['Coat Weight'].default_value = .20
    skin.p.inputs['Coat Roughness'].default_value = .24
    assign(rig.obj('Head'), skin)
    for side in ['L','R']: assign(rig.obj('Eyelids '+side), skin)

    body = Surface('Deep plum body wax', (.052,.029,.058), .43)
    sep = body.node('ShaderNodeSeparateXYZ'); body.wire(body.coord,sep.inputs[0])
    stretch=body.node('ShaderNodeVectorMath');stretch.operation='MULTIPLY'
    body.wire(body.coord,stretch.inputs[0]);stretch.inputs[1].default_value=(12,12,105)
    body.bump(body.noise(1,2,stretch.outputs[0]), .0027, .22)
    body.bump(body.noise(290,2), .0005, .15)
    body.p.inputs['Coat Weight'].default_value = .18
    assign(rig.obj('Body'), body); assign(rig.obj('Body'), skin, 1)
    assign(rig.obj('Neck Bridge'), body)

    lips = Surface('Soft red lip transition', (.43,.045,.060), .34)
    # An attribute follows the lip rings through animation, avoiding a painted-on outline.
    head = rig.obj('Head'); patch = head['patches']['mouth']; start, n = patch['start'], patch['size']
    attr = head.data.attributes.get('lip_color') or head.data.attributes.new('lip_color','FLOAT','POINT')
    for i in range(len(head.data.vertices)):
        t = ((i-start)//n+1)/16 if i >= start else 0
        attr.data[i].value = smooth(.16,.61,t)
    lips.wire(lips.mix(lips.attribute('lip_color'), (.19,.073,.12,1), (.47,.04,.053,1)), lips.p.inputs['Base Color'])
    lips.bump(lips.noise(320,2), .00055, .15)
    lips.p.inputs['Coat Weight'].default_value = .28
    lips.p.inputs['Coat Roughness'].default_value = .22
    assign(head,lips,1)
    for side in ['L','R']:
        eye = Surface('Warm ivory eye '+side, (.80,.56,.265), .25)
        eye.bump(eye.noise(180,2), .0007, .14)
        eye.p.inputs['Coat Weight'].default_value=.55
        eye.p.inputs['Coat Roughness'].default_value=.10
        assign(rig.obj('Eye '+side),eye)
    oral_materials()
    bpy.context.scene['surfaceRevision'] = 'reference-material-refinement-2'


def coral_face():
    assert rig.prefix()=='Coral'
    head=rig.obj('Head');keys=head.data.shape_keys.key_blocks
    assert not head.get('restingLipRefined'), 'Resting lip refinement already applied'
    patch=head['patches']['mouth'];start,n=patch['start'],patch['size']
    for key in keys:
        factor=0 if key.name=='jawOpen' else 2 if key.name=='mouthClose' else 1
        for i in range(start,len(key.data)):
            row,j=divmod(i-start,n);t=(row+1)/16
            key.data[i].co.z-=factor*.010*math.sin(j*math.tau/n)*t**3
    head['restingLipRefined']=True;head.data.update()


def oral_materials():
    for row in ['Upper','Lower']:
        teeth = Surface(row+' ivory teeth', (.72,.61,.43), .29)
        assign(rig.obj(row+' Teeth'),teeth)
    tongue = Surface('Moist tongue', (.43,.065,.105), .36)
    tongue.bump(tongue.noise(310,2), .0006, .12)
    tongue.p.inputs['Coat Weight'].default_value = .18
    assign(rig.obj('Long Tongue'),tongue)


def render(label='material-study'):
    s=bpy.context.scene; s.render.filepath=str(qa()/(label+'.png'))
    bpy.ops.render.render(write_still=True)


def validate():
    import reference_rig_checks
    report=reference_rig_checks.validate(rig.prefix(),rig.obj('AvatarRig').name,qa(),rig.obj('Head')['patches']['mouth']['start'],rig.reset,rig.rotate,rig.expression)
    print('PASS',rig.prefix(),'mouth, weights, isolated limbs and tongue root')
    return report


def audit_preserved_controls():
    current={o.name:o for o in rig.meshes()};current[rig.obj('AvatarRig').name]=rig.obj('AvatarRig')
    path=qa()/'before'/(rig.prefix().lower()+'-image-rig.blend')
    names=tuple(current)
    with bpy.data.libraries.load(str(path),link=False) as (source,target):
        assert set(names)<=set(source.objects)
        target.objects=list(names)
    old=dict(zip(names,target.objects));weight_error=0;bone_error=0
    try:
        for name,o in current.items():
            before=old[name]
            if o.type=='ARMATURE':
                assert list(o.data.bones.keys())==list(before.data.bones.keys())
                for b in o.data.bones:
                    bone_error=max(bone_error,max(abs(a-c) for row1,row2 in zip(b.matrix_local,before.data.bones[b.name].matrix_local) for a,c in zip(row1,row2)))
                continue
            assert len(o.data.vertices)==len(before.data.vertices)
            assert [tuple(p.vertices) for p in o.data.polygons]==[tuple(p.vertices) for p in before.data.polygons]
            assert list(o.vertex_groups.keys())==list(before.vertex_groups.keys())
            for v,b in zip(o.data.vertices,before.data.vertices):
                a={g.group:g.weight for g in v.groups};c={g.group:g.weight for g in b.groups}
                assert a.keys()==c.keys()
                weight_error=max(weight_error,max((abs(a[i]-c[i]) for i in a),default=0))
            if o.data.shape_keys:
                assert list(o.data.shape_keys.key_blocks.keys())==list(before.data.shape_keys.key_blocks.keys())
            if 'Long Tongue' in name:
                for key in o.data.shape_keys.key_blocks:
                    assert all((v.co-b.co).length<1e-7 for v,b in zip(key.data,before.data.shape_keys.key_blocks[key.name].data))
        assert weight_error==0 and bone_error==0
        report={'boneRestChange':bone_error,'skinWeightChange':weight_error,'topologyPreserved':True,'facialChannelSetsPreserved':True,'tongueTargetsPreserved':True}
        (qa()/'preserved-controls.json').write_text(json.dumps(report,indent=2));print(report)
        return report
    finally:
        for o in old.values():bpy.data.objects.remove(o,do_unlink=True)


def bake():
    rig.reset(); s=bpy.context.scene; objects=rig.meshes()
    materials={m.name:m for o in objects for m in o.data.materials}
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects: o.hide_set(False);o.select_set(True);o.active_shape_key_index=0
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(78),island_margin=.012)
    bpy.ops.object.mode_set(mode='OBJECT')
    nodes={}; s.cycles.samples=8
    for name,m in materials.items():
        m.use_fake_user=True; node=m.node_tree.nodes.new('ShaderNodeTexImage')
        m.node_tree.nodes.active=node;nodes[name]=node
    images={}
    for label,size,kind in [('basecolor',2048,'DIFFUSE'),('normal',2048,'NORMAL')]:
        atlas=bpy.data.images.new(rig.prefix()+' refined '+label,width=size,height=size)
        if kind=='NORMAL': atlas.colorspace_settings.name='Non-Color'
        for node in nodes.values(): node.image=atlas
        if kind=='NORMAL': bpy.ops.object.bake(type=kind,use_clear=False,margin=8,normal_space='TANGENT')
        else: bpy.ops.object.bake(type=kind,pass_filter={'COLOR'},use_clear=False,margin=8)
        atlas.filepath_raw=str(qa()/(rig.prefix().lower()+'-image-'+label+'.png'));atlas.file_format='PNG';atlas.save();atlas.pack();images[label]=atlas
    replacements={}
    for name,original in materials.items():
        old=original.node_tree.nodes['Principled BSDF']
        m=plain_material(name+' - Baked PBR',(.5,.5,.5),old.inputs['Roughness'].default_value)
        n=m.node_tree.nodes;l=m.node_tree.links;p=n['Principled BSDF']
        for label in ['Metallic','Specular IOR Level','Coat Weight','Coat Roughness','IOR','Transmission Weight']:
            p.inputs[label].default_value=old.inputs[label].default_value
        color=n.new('ShaderNodeTexImage');color.image=images['basecolor'];l.new(color.outputs['Color'],p.inputs['Base Color'])
        tex=n.new('ShaderNodeTexImage');tex.image=images['normal'];normal=n.new('ShaderNodeNormalMap')
        l.new(tex.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs['Normal'],p.inputs['Normal'])
        replacements[name]=m
    for o in objects:
        for i,m in enumerate(list(o.data.materials)): o.data.materials[i]=replacements[m.name]
    s['editableProceduralMaterials']=list(materials);s.cycles.samples=32
    bpy.ops.wm.save_as_mainfile(filepath=str(qa()/(rig.prefix().lower()+'-refinement.blend')))
    print('Baked improved surfaces on repacked UVs; production exports not yet replaced')


def promote():
    name=rig.prefix().lower()
    assert bpy.context.scene.get('surfaceRevision')=='reference-material-refinement-2'
    for label in ['basecolor','normal']:
        shutil.copy2(qa()/(name+'-image-'+label+'.png'),ROOT/'assets/likeness-trials'/(name+'-image-'+label+'.png'))
    rig.export_runtime()
    print('Promoted refined',name,'with existing body and facial controls')
