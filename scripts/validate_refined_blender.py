"""Read-only validation of the saved FK controls and post-armature corrections."""
import json,sys
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from refine_3dai_rigs import pose
from pose_correctives import evaluated_points

configs=json.loads((ROOT/'scripts/rig_3dai_landmarks.json').read_text())
report=[]
for path in sorted((ROOT/'blender/3dai/refined').glob('*-rigged.blend')):
    name=path.name.removesuffix('-rigged.blend');config=configs.get(name,{})
    bpy.ops.wm.open_mainfile(filepath=str(path))
    rig=bpy.data.objects['AvatarRig'];body=bpy.data.objects[name.title()+'SourceBody']
    copy=body.data.copy();assert not copy.validate(clean_customdata=False),(name,'invalid mesh');bpy.data.meshes.remove(copy)
    hands=[o for o in bpy.context.scene.objects if o.get('assetRole')=='articulated-hand']
    assert len(hands)==2,(name,'missing replacement hands')
    for hand in hands:
        bm=bmesh.new();bm.from_mesh(hand.data)
        assert all(edge.is_manifold for edge in bm.edges),(name,hand.name,'open hand surface')
        remaining=set(bm.verts);todo=[remaining.pop()]
        while todo:
            for edge in todo.pop().link_edges:
                for vertex in edge.verts:
                    if vertex in remaining:remaining.remove(vertex);todo.append(vertex)
        assert not remaining,(name,hand.name,'disconnected fingers');bm.free()
    for side in ['L','R']:
        bone=rig.data.bones['Hand.'+side];origin=bone.head_local;d=(bone.tail_local-origin).normalized()
        length=max(.20,min(.32,bone.length*1.25));group=body.vertex_groups['Hand.'+side].index
        leftovers=[]
        for polygon in body.data.polygons:
            vertices=[body.data.vertices[i] for i in polygon.vertices]
            weight=sum(g.weight for v in vertices for g in v.groups if g.group==group)/len(vertices)
            if weight<.75:continue
            offset=sum((v.co for v in vertices),Vector())/len(vertices)-origin
            along=offset.dot(d);radial=(offset-d*along).length
            if -.2*length+.005<along<length*3 and radial<length*3:leftovers.append(polygon.index)
        assert not leftovers,(name,side,'source-hand fragments remain',len(leftovers))
    modifier=body.modifiers['Post-skin pose corrections'];samples=body['correctiveSamples']
    poses=[]
    for mode in ['Seated','ArmsUp','ArmsForward','HeadLeft','HeadRight']:
        pose(rig,name,config,mode);bpy.context.view_layer.update()
        if mode not in ['Seated']:
            region='Head' if mode.startswith('Head') else 'L'
            assert body.data.shape_keys.key_blocks['corrective'+mode+region].value>.99,(name,mode,'inactive FK driver')
        corrected=evaluated_points(body)
        expected=np.zeros_like(corrected)
        for i,sample in enumerate(samples):
            delta=np.array([v.vector[:] for v in body.data.attributes[f'_PSD_P_{i}'].data])
            expected+=delta*body.data.shape_keys.key_blocks[sample['key']].value
        modifier.show_viewport=False;bpy.context.view_layer.update();plain=evaluated_points(body)
        modifier.show_viewport=True;bpy.context.view_layer.update()
        error=float(np.max(np.linalg.norm(corrected-plain-expected,axis=1)))
        assert np.isfinite(corrected).all() and error<.00001,(name,mode,'post-skin driver mismatch',error)
        poses.append({'pose':mode,'postSkinError':error})
    report.append({'id':name,'validMesh':True,'editablePoseDrivers':True,'poses':poses})
    print('PASS editable Blender rig',name,flush=True)
(ROOT/'.context/qa/refinement/blender-validation.json').write_text(json.dumps({'passed':True,'results':report},indent=2)+'\n')
