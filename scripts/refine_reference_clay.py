"""Sequential live-MCP repair of Clay's low mouth and native eyelids."""
import math
import bpy
import numpy as np
from refine_reference_glass import rebuild_front


def mouth():
    config=dict(head=(1.14,.44,.58),hz=2.62,power=.92,mouth=(.087,-.225,.009),eyes=(.468,.026,.165,.087,.10))
    def sculpt(point,index):
        p=point.copy();x,y,z=p;localz=z-2.62
        if index<3040:
            socket=sum(math.exp(-((((x-s*.468)/.185)**2+((localz-.026)/.137)**2)*1.5)**2) for s in [-1,1])
            p.y+=.035*socket
            w=math.exp(-((x/.14)**6+((localz+.225)/.052)**4))
            p.z+=.01*(1-2*min(1,abs(x)/.087)**2)*w
        p.x+=.145*max(0,1-(x/1.14)**2)*max(0,1-(localz/.58)**2)
        return p
    report=rebuild_front('Clay sculpted head and eyelids',config,sculpt,'Clay mouth interior',.095,0)
    head=bpy.context.scene.objects['Clay sculpted head and eyelids']
    keys=head.data.shape_keys.key_blocks
    for key in keys:
        if key.name.startswith('mouth') and key.name!='mouthClose':
            for v,b in zip(key.data,keys['Basis'].data):v.co=b.co+(v.co-b.co)*.25
    from build_reference_clay import planar_uv
    planar_uv(head)
    return report


def check_mouth():
    from build_reference_clay import reset,expression,positions
    rig=bpy.context.scene.objects['AvatarRig'];objects=[o for o in bpy.context.scene.objects if o.parent==rig]+[rig]
    head=bpy.context.scene.objects['Clay sculpted head and eyelids'];reset(rig,objects)
    head.data.calc_loop_triangles()
    tri=np.array([tuple(t.vertices) for t in head.data.loop_triangles if all(i<3040 for i in t.vertices)])
    p=positions(head)[tri];normal=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);valid=np.linalg.norm(normal,axis=1)>1e-9
    report={}
    for names in [('jawOpen',),('mouthSmileLeft','mouthSmileRight','jawOpen'),('mouthPucker','mouthFunnel'),('mouthFrownLeft','mouthFrownRight'),('tongueOut','eyeBlinkLeft','jawOpen')]:
        expression(objects,{n:1 for n in names});p=positions(head)[tri];n=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0])
        report['+'.join(names)]={'triangleReversals':int(np.sum((np.sum(normal*n,axis=1)<0)&valid)),'finite':bool(np.isfinite(p).all())}
    reset(rig,objects)
    return report


def save():
    import json
    from build_reference_clay import ROOT,OUT,BLENDS,reset,validate,validate_export
    rig=bpy.context.scene.objects['AvatarRig'];objects=[o for o in bpy.context.scene.objects if o.parent==rig]+[rig]
    validate(rig,objects)
    report=json.loads((ROOT/'.context/qa/reference-characters/clay-rig-validation.json').read_text())
    report['mouthTopologyChecks']=check_mouth();reset(rig,objects)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.gltf(filepath=str(OUT/'clay-review.glb'),export_format='GLB',use_selection=True,use_active_scene=True,export_animations=False,export_extras=True,export_attributes=True,export_morph=True,export_morph_normal=True)
    validate_export()
    (ROOT/'.context/qa/reference-characters/clay-rig-validation.json').write_text(json.dumps(report,indent=2))
    (ROOT/'.context/qa/reference-characters/clay-face-strain.json').write_text(json.dumps(report['mouthTopologyChecks'],indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(BLENDS/'clay-review.blend'))
    print(report)
