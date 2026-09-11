"""Validate dental skinning/morphs and preservation of the pre-teeth facial meshes."""
import json
import math
from pathlib import Path
from validate_fleet import GLB

ROOT=Path(__file__).resolve().parents[1]


def validate(name):
    model=GLB(ROOT/'assets/3dai/rigged'/(name+'.glb')); doc=model.doc
    nodes=[n for n in doc['nodes'] if n.get('extras',{}).get('dentalRigVersion')]
    assert {n['extras']['assetRole'] for n in nodes}=={'upper-teeth','lower-teeth'}
    assert len(nodes)==2
    for node in nodes:
        mesh=doc['meshes'][node['mesh']]
        names=mesh.get('extras',{}).get('targetNames',[])
        joints=doc['skins'][node['skin']]['joints']
        for primitive in mesh['primitives']:
            attrs=primitive['attributes']
            positions=model.accessor(attrs['POSITION'])
            assert len(positions)>100
            for indices,weights in zip(model.accessor(attrs['JOINTS_0']),model.accessor(attrs['WEIGHTS_0'])):
                assert abs(sum(weights)-1)<1e-6
                assert all(doc['nodes'][joints[j]]['name']=='Head' for j,w in zip(indices,weights) if w>0)
            deltas={n:model.accessor(t['POSITION']) for n,t in zip(names,primitive.get('targets',[]))}
            if node['extras']['assetRole']=='upper-teeth':
                assert not deltas, 'Upper teeth must stay fixed to the skull'
            else:
                assert set(deltas)=={'jawOpen','mouthClose','jawLeft','jawRight','jawForward'}
                assert all(any(abs(v)>1e-5 for row in rows for v in row) for rows in deltas.values())
                assert all(abs(a+b)<1e-6 for o,c in zip(deltas['jawOpen'],deltas['mouthClose']) for a,b in zip(o,c))
                opened=[tuple(a+b for a,b in zip(p,d)) for p,d in zip(positions,deltas['jawOpen'])]
                for i in range(0,len(positions)-1,17):
                    j=(i+79)%len(positions)
                    assert abs(math.dist(positions[i],positions[j])-math.dist(opened[i],opened[j]))<1e-6, 'Teeth stretch under jaw rotation'
            material=doc['materials'][primitive['material']]['pbrMetallicRoughness']
            assert min(material['baseColorFactor'][:3])>.5

    # This pass must not change source skin, eyelids, existing facial targets or poses.
    before=GLB(ROOT/'.context/before-teeth'/(name+'.glb'))
    by_name={n['name']:n for n in doc['nodes'] if 'mesh' in n}
    for old_node in before.doc['nodes']:
        if 'mesh' not in old_node:continue
        old=before.doc['meshes'][old_node['mesh']]
        new=doc['meshes'][by_name[old_node['name']]['mesh']]
        assert old.get('extras',{}).get('targetNames')==new.get('extras',{}).get('targetNames')
        assert len(old['primitives'])==len(new['primitives'])
        for a,b in zip(old['primitives'],new['primitives']):
            for attribute in ['POSITION','NORMAL','TEXCOORD_0','WEIGHTS_0','_LID_INDEX']:
                if attribute in a['attributes']:
                    assert before.accessor(a['attributes'][attribute])==model.accessor(b['attributes'][attribute]), (name,attribute,'changed')
            for at,bt in zip(a.get('targets',[]),b.get('targets',[])):
                assert before.accessor(at['POSITION'])==model.accessor(bt['POSITION']), (name,'existing facial delta changed')
    assert {a['name'] for a in before.doc['animations']}=={a['name'] for a in doc['animations']}
    return {'character':name,'passed':True,'teethPerJaw':nodes[0]['extras']['toothCount'],
            'originalFaceBuffersUnchanged':True,'headSkinning':True,'rigidLowerJaw':True}


if __name__=='__main__':
    names=[c['id'] for c in json.loads((ROOT/'assets/3dai/manifest.json').read_text())['characters']]
    results=[validate(name) for name in names]
    (ROOT/'.context/qa/teeth/validation.json').write_text(json.dumps(results,indent=2)+'\n')
    for result in results:print('PASS',result['character'],'dental rig and original face buffers preserved')
