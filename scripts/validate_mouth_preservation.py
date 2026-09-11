"""Only source-body mouth/jaw targets may change during mouth cleanup."""
import json
from pathlib import Path
from validate_fleet import GLB

ROOT=Path(__file__).resolve().parents[1]
report=[]
for entry in json.loads((ROOT/'assets/3dai/manifest.json').read_text())['characters']:
    name=entry['id'];old=GLB(ROOT/'.context/before-mouth-cleanup'/f'{name}.glb');new=GLB(ROOT/entry['url'])
    before={m['name']:m for m in old.doc['meshes']};after={m['name']:m for m in new.doc['meshes']}
    assert before.keys()==after.keys()
    changed=set()
    for key,mesh in after.items():
        previous=before[key];names=mesh.get('extras',{}).get('targetNames',[])
        assert names==previous.get('extras',{}).get('targetNames',[])
        assert len(mesh['primitives'])==len(previous['primitives'])
        source='correctiveSeated' in names
        for a,b in zip(previous['primitives'],mesh['primitives']):
            assert a['attributes'].keys()==b['attributes'].keys()
            for attribute,accessor in b['attributes'].items():assert new.accessor(accessor)==old.accessor(a['attributes'][attribute]),(name,key,attribute)
            assert new.accessor(b['indices'])==old.accessor(a['indices'])
            for channel,x,y in zip(names,a.get('targets',[]),b.get('targets',[])):
                for attribute,accessor in y.items():
                    equal=new.accessor(accessor)==old.accessor(x[attribute])
                    if source and channel.startswith(('mouth','jaw')):
                        if not equal:changed.add(channel)
                    else:assert equal,(name,key,channel,attribute)
    assert any(n.get('extras',{}).get('mouthRefinementVersion')==2 for n in new.doc['nodes'])
    report.append({'id':name,'changedMouthTargets':sorted(changed),'baseSkinEyesFingersTongueAndBodyCorrectivesPreserved':True})
    print('PASS exact unrelated mesh/morph preservation',name,flush=True)
(ROOT/'.context/qa/mouth-combinations/preservation.json').write_text(json.dumps(report,indent=2)+'\n')
