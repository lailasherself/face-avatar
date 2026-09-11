"""Mesh and deformation checks for isolated, live-Blender reference builds."""
import bpy
import bmesh
import json
import numpy as np


def validate(prefix,rig_name,qa,mouth_start,reset,rotate,expression):
    reset();head=bpy.context.scene.objects[prefix+' Head'];body=bpy.context.scene.objects[prefix+' Body'];rig=bpy.context.scene.objects[rig_name]
    head.data.calc_loop_triangles();keys=head.data.shape_keys.key_blocks;base=np.array([v.co[:] for v in keys['Basis'].data]);tri=np.array([t.vertices[:] for t in head.data.loop_triangles]);tri=tri[np.any(tri>=mouth_start,axis=1)]
    def area(p):
        t=p[tri][:,:,[0,2]];a=t[:,1]-t[:,0];b=t[:,2]-t[:,0];return a[:,0]*b[:,1]-a[:,1]*b[:,0]
    original=area(base);report={'status':'Isolated review asset, not physical ZED/Orin validation','mouth':[],'meshes':[],'arms':[],'fingers':[]}
    report['head_morph_max_delta']={k.name:float(np.max(np.linalg.norm(np.array([v.co[:] for v in k.data])-base,axis=1))) for k in keys if k.name!='Basis'}
    report['jaw_outside_mouth_drift']=float(np.max(np.linalg.norm(np.array([v.co[:] for v in keys['jawOpen'].data])[:mouth_start]-base[:mouth_start],axis=1)))
    poses=[{}, {'jawOpen':1},{'jawOpen':1,'mouthClose':1},{'mouthSmileLeft':1,'mouthSmileRight':1},{'jawOpen':.8,'mouthSmileLeft':.7,'mouthSmileRight':.7},{'mouthFrownLeft':1,'mouthFrownRight':1},{'jawOpen':.6,'mouthFunnel':.5,'mouthPucker':.3},{'jawOpen':.8,'tongueOut':1},{'jawOpen':1,'mouthStretchLeft':.7,'mouthStretchRight':.7},{'jawOpen':.4,'jawLeft':1},{'jawOpen':.4,'jawRight':1},{'mouthPressLeft':1,'mouthPressRight':1}]
    for values in poses:
        p=base.copy()
        for name,value in values.items():
            if name in keys:p+=(np.array([v.co[:] for v in keys[name].data])-base)*value
        report['mouth'].append({'values':values,'flipped_triangles':int(np.sum(area(p)*original < -1e-12))})
    for o in bpy.context.scene.objects:
        if o.type!='MESH':continue
        bm=bmesh.new();bm.from_mesh(o.data);weights=[sum(g.weight for g in v.groups) for v in o.data.vertices]
        report['meshes'].append({'name':o.name,'vertices':len(bm.verts),'zero_area_faces':sum(f.calc_area()<1e-12 for f in bm.faces),'nonmanifold_nonboundary_edges':sum(not e.is_manifold and not e.is_boundary for e in bm.edges),'weight_error':max(abs(w-1) for w in weights),'max_influences':max(len(v.groups) for v in o.data.vertices)});bm.free()
    dg=bpy.context.evaluated_depsgraph_get()
    def evaluated(o):
        ev=o.evaluated_get(dg);m=ev.to_mesh();p=np.array([v.co[:] for v in m.vertices]);ev.to_mesh_clear();return p
    rest=evaluated(body);headrest=evaluated(head);edges=np.array([e.vertices[:] for e in body.data.edges]);before=np.linalg.norm(rest[edges[:,0]]-rest[edges[:,1]],axis=1)
    for side,shoulder,elbow in [('L',-.8,-.7),('L',-1.6,-1.5),('R',.8,-.7),('R',1.6,-1.5)]:
        reset();rotate('UpperArm.'+side,(0,1,0),shoulder);rotate('Forearm.'+side,(1,0,0),elbow);rotate('Hand.'+side,(1,0,0),.4)
        p=evaluated(body);after=np.linalg.norm(p[edges[:,0]]-p[edges[:,1]],axis=1);ratio=after[before>1e-5]/before[before>1e-5];opposite=rest[:,0]<-.1 if side=='L' else rest[:,0]>.1
        report['arms'].append({'side':side,'shoulder':shoulder,'elbow':elbow,'opposite_drift':float(np.max(np.linalg.norm(p[opposite]-rest[opposite],axis=1))),'head_drift':float(np.max(np.linalg.norm(evaluated(head)-headrest,axis=1))),'edge_stretch_max':float(np.max(ratio)),'edge_stretch_p99':float(np.quantile(ratio,.99))})
    for side in ['L','R']:
        for digit in [d for d in ['Thumb','Index','Middle','Ring'] if f'{d}1.{side}' in rig.data.bones]:
            reset()
            for i in range(3):rotate(f'{digit}{i+1}.{side}',(1,0,0),rig.data.bones[f'{digit}{i+1}.{side}']['fingerCurlRadians'])
            p=evaluated(body);opposite=rest[:,0]<-.1 if side=='L' else rest[:,0]>.1
            report['fingers'].append({'side':side,'digit':digit,'maximum_motion':float(np.max(np.linalg.norm(p-rest,axis=1))),'opposite_drift':float(np.max(np.linalg.norm(p[opposite]-rest[opposite],axis=1)))})
    reset();tongue=bpy.context.scene.objects[prefix+' Long Tongue'];tb=tongue.data.shape_keys.key_blocks['Basis'];report['tongue_root_drift']=max((tongue.data.shape_keys.key_blocks[name].data[i].co-tb.data[i].co).length for name in ['tongueOut','jawOpen','mouthClose'] for i in range(24));report['bones']=len(rig.data.bones)
    (qa/'geometry-validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
    assert all(p['flipped_triangles']==0 for p in report['mouth'])
    assert all(np.isfinite(x) and x<.4 for x in report['head_morph_max_delta'].values())
    assert report['jaw_outside_mouth_drift']<1e-6
    assert all(p['zero_area_faces']==0 and p['nonmanifold_nonboundary_edges']==0 and p['weight_error']<1e-6 and p['max_influences']<=4 for p in report['meshes'])
    assert all(p['opposite_drift']<1e-6 and p['head_drift']<1e-6 and p['edge_stretch_p99']<1.35 and p['edge_stretch_max']<1.8 for p in report['arms'])
    assert all(p['opposite_drift']<1e-6 and p['maximum_motion']>.015 for p in report['fingers'])
    assert report['tongue_root_drift']<1e-6 and report['bones']==18+3*len(report['fingers'])
    return report
