"""Check exported skinning, real facial deltas, blink isolation and source integrity."""
import hashlib
import json
import math
from pathlib import Path
from validate_fleet import GLB

ROOT=Path(__file__).resolve().parents[1]


def main():
    channels=json.loads((ROOT/'assets/fleet/manifest.json').read_text())['channels']
    model=GLB(ROOT/'assets/3dai/rigged/coral.glb')
    doc=model.doc
    assert len(doc['skins'])==1
    joints=doc['skins'][0]['joints']
    assert len(joints)==18
    assert {'Seated','Standing','T-Pose'}=={a['name'] for a in doc['animations']}
    counts=dict.fromkeys(channels,0)
    vertices=0
    for mesh in doc['meshes']:
        names=mesh.get('extras',{}).get('targetNames',[])
        assert all(w==0 for w in mesh.get('weights',[]))
        for primitive in mesh['primitives']:
            attrs=primitive['attributes']
            positions=model.accessor(attrs['POSITION'])
            weights=model.accessor(attrs['WEIGHTS_0'])
            indices=model.accessor(attrs['JOINTS_0'])
            vertices+=len(positions)
            assert all(math.isfinite(c) for p in positions for c in p)
            assert all(min(w)>=0 and abs(sum(w)-1)<1e-5 for w in weights)
            assert all(0<=j<len(joints) for row in indices for j in row)
            deltas={name:model.accessor(target['POSITION']) for name,target in zip(names,primitive.get('targets',[]))}
            for name,values in deltas.items():
                assert all(math.isfinite(c) for p in values for c in p)
                for p,d in zip(positions,values):
                    if max(abs(c) for c in d)<1e-6:continue
                    counts[name]+=1
                    assert p[1]>1.4, (name,'facial target affects body',p)
                    if name=='eyeBlinkLeft':assert p[0]>0
                    if name=='eyeBlinkRight':assert p[0]<0
            if 'jawOpen' in deltas and 'mouthClose' in deltas:
                assert all(max(abs(a+b) for a,b in zip(open_delta,close_delta))<1e-5
                           for open_delta,close_delta in zip(deltas['jawOpen'],deltas['mouthClose']))
    assert all(counts.values()), counts
    lids=[n for n in doc['nodes'] if 'eyelidSurfaces' in n.get('extras',{})]
    assert len(lids)==1 and len(lids[0]['extras']['eyelidSurfaces'])==2
    for primitive in doc['meshes'][lids[0]['mesh']]['primitives']:
        assert '_LID_INDEX' in primitive['attributes']
    car=GLB(ROOT/'assets/3dai/rigged/silver-vehicle.glb')
    assert not car.doc.get('skins')
    assert any(n.get('name')=='SeatAnchor' for n in car.doc['nodes'])
    for asset in [doc,car.doc]:
        assert all('uri' not in i for i in asset['images']), 'Textures must be embedded for offline use'
    originals=json.loads((ROOT/'.context/qa/3dai/source-inspection.json').read_text())
    for original in originals:
        path=ROOT/'assets/3dai/originals'/(original['task_id']+'.glb')
        assert hashlib.sha256(path.read_bytes()).hexdigest()==original['sha256']
    result={'passed':True,'bones':len(joints),'facialChannels':len(counts),
            'exportedVertices':vertices,'changedVerticesByChannel':counts,
            'independentBlinks':True,'mouthCloseCancelsJaw':True,
            'embeddedTextures':True,'originalsPreserved':len(originals)}
    print(json.dumps(result,indent=2))
    (ROOT/'.context/qa/3dai/rig-validation.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
