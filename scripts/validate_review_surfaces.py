"""Validate staged cleanup without accepting unrelated geometry or face changes."""
import argparse
import json
from pathlib import Path
from validate_fleet import GLB

ROOT=Path(__file__).resolve().parents[1]


def validate(name,stage):
    old=GLB(ROOT/'.context/before-review-surfaces'/f'{name}.glb')
    new=GLB(ROOT/'assets/3dai'/stage/f'{name}.glb')
    before={m['name']:m for m in old.doc['meshes']};after={m['name']:m for m in new.doc['meshes']}
    assert before.keys()==after.keys(),(name,'meshes')
    rebound=stage=='clothing-cleanup';changes=set()
    for key,mesh in after.items():
        previous=before[key];names=mesh.get('extras',{}).get('targetNames',[])
        assert names==previous.get('extras',{}).get('targetNames',[]),(name,key,'channels')
        assert len(mesh['primitives'])==len(previous['primitives'])
        source='correctiveSeated' in names
        for a,b in zip(previous['primitives'],mesh['primitives']):
            assert a['attributes'].keys()==b['attributes'].keys(),(name,key,'attributes')
            for attribute,accessor in b['attributes'].items():
                permitted=source and rebound and (attribute.startswith('_PSD_') or attribute in ('JOINTS_0','WEIGHTS_0'))
                equal=new.accessor(accessor)==old.accessor(a['attributes'][attribute])
                if not permitted:assert equal,(name,key,attribute)
                elif not equal:changes.add(attribute)
            assert new.accessor(b['indices'])==old.accessor(a['indices']),(name,key,'topology')
            for channel,x,y in zip(names,a.get('targets',[]),b.get('targets',[])):
                for attribute,accessor in y.items():
                    equal=new.accessor(accessor)==old.accessor(x[attribute])
                    permitted=source and (channel.startswith(('mouth','jaw')) or (rebound and channel.startswith('corrective')))
                    if not permitted:assert equal,(name,key,channel,attribute)
                    elif not equal:changes.add(channel)
            if source:
                for row in new.accessor(b['attributes']['WEIGHTS_0']):
                    assert abs(sum(row)-1)<1e-5 and all(0<=v<=1 for v in row),(name,'invalid weights')
                if rebound:
                    def weights(glb,mesh,primitive):
                        index=glb.doc['meshes'].index(mesh)
                        node=next(n for n in glb.doc['nodes'] if n.get('mesh')==index)
                        joints=[glb.doc['nodes'][i]['name'] for i in glb.doc['skins'][node['skin']]['joints']]
                        return [{joints[i]:v for i,v in zip(indices,values) if v>0} for indices,values in zip(
                            glb.accessor(primitive['attributes']['JOINTS_0']),glb.accessor(primitive['attributes']['WEIGHTS_0']))]
                    for x,y in zip(weights(old,previous,a),weights(new,mesh,b)):
                        for bone in x.keys()|y.keys():
                            if not bone.startswith(('UpperArm','Forearm')):assert abs(x.get(bone,0)-y.get(bone,0))<1e-6,(name,'unrelated bone weight',bone)
    assert any(n.get('extras',{}).get('mouthRefinementVersion')==3 for n in new.doc['nodes'])
    assert len(new.doc['skins'])==len(old.doc['skins'])
    for a,b in zip(old.doc['skins'],new.doc['skins']):
        assert [old.doc['nodes'][i]['name'] for i in a['joints']]==[new.doc['nodes'][i]['name'] for i in b['joints']]
        assert old.accessor(a['inverseBindMatrices'])==new.accessor(b['inverseBindMatrices']),(name,'bind matrices')
    assert {a['name'] for a in old.doc['animations']}=={a['name'] for a in new.doc['animations']},(name,'clips')
    print('PASS exact base/topology/eyes/tongue/teeth/fingers preservation',name,stage,flush=True)
    return {'id':name,'stage':stage,'changes':sorted(changes),'originalGeometryAndUnrelatedMorphsPreserved':True}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['mouth-cleanup','clothing-cleanup'],required=True)
    parser.add_argument('ids',nargs='*');args=parser.parse_args()
    ids=args.ids or [c['id'] for c in json.loads((ROOT/'assets/3dai/manifest.json').read_text())['characters']]
    report=[validate(name,args.stage) for name in ids]
    (ROOT/'.context/qa'/f'{args.stage}-preservation.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
