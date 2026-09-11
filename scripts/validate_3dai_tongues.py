"""Check tongue extension and exact preservation of all unrelated GLB mesh data."""
import json
from pathlib import Path
from validate_fleet import GLB

ROOT=Path(__file__).resolve().parents[1]
results=[]
for entry in json.loads((ROOT/'assets/3dai/manifest.json').read_text())['characters']:
    name=entry['id'];old=GLB(ROOT/'.context/before-tongue'/f'{name}.glb');new=GLB(ROOT/entry['url'])
    old_meshes={m['name']:m for m in old.doc['meshes']};new_meshes={m['name']:m for m in new.doc['meshes']}
    assert old_meshes.keys()==new_meshes.keys(),(name,'mesh set changed')
    changed=0
    for key,mesh in new_meshes.items():
        previous=old_meshes[key];targets=mesh.get('extras',{}).get('targetNames',[])
        assert targets==previous.get('extras',{}).get('targetNames',[])
        assert len(mesh['primitives'])==len(previous['primitives'])
        for before,after in zip(previous['primitives'],mesh['primitives']):
            assert before['attributes'].keys()==after['attributes'].keys()
            for attribute,accessor in after['attributes'].items():
                assert new.accessor(accessor)==old.accessor(before['attributes'][attribute]),(name,key,attribute)
            assert new.accessor(after['indices'])==old.accessor(before['indices'])
            material=new.doc['materials'][after['material']]['name']
            for channel,a,b in zip(targets,before.get('targets',[]),after.get('targets',[])):
                for attribute,accessor in b.items():
                    values=new.accessor(accessor);original=old.accessor(a[attribute])
                    if channel=='tongueOut' and 'tongue' in material.lower():
                        if attribute=='POSITION':
                            assert values!=original
                            assert any(sum(v*v for v in p)<1e-12 for p in values),'root must stay anchored'
                            assert max(p[2] for p in values)>.4,'long tip must extend forward'
                            assert min(p[1] for p in values)<-.15,'long tip must curve downward'
                            changed+=1
                    else:assert values==original,(name,key,material,channel,attribute)
    assert changed==1,(name,'one tongue primitive expected',changed)
    assert any(n.get('extras',{}).get('tongueRigVersion')==5 for n in new.doc['nodes'])
    results.append({'name':name,'tonguePrimitives':changed,'unrelatedMeshDataPreserved':True})
    print('PASS tongue root/extension and exact unrelated mesh preservation',name,flush=True)
(ROOT/'.context/qa/tongue/preservation-test.json').write_text(json.dumps(results,indent=2)+'\n')
