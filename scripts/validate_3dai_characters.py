"""Validate source rigs from actual exported buffers, not declared channel names."""
import hashlib
import json
import math
from pathlib import Path
import sys

from validate_fleet import GLB

ROOT=Path(__file__).resolve().parents[1]


def validate(name,c):
    model=GLB(ROOT/'assets/3dai/rigged'/(name+'.glb')); doc=model.doc
    channels=json.loads((ROOT/'assets/fleet/manifest.json').read_text())['channels']
    assert len(doc['skins'])==1
    joints=doc['skins'][0]['joints']
    expected=18+max(0,len(c.get('tail',[]))-1)
    assert len(joints)==expected, (name,len(joints),expected)
    assert {'Seated','Standing','T-Pose'}=={a['name'] for a in doc['animations']}
    joint_names={doc['nodes'][j]['name']:i for i,j in enumerate(joints)}
    influenced=dict.fromkeys(joint_names,0)
    counts=dict.fromkeys(channels,0)
    vertices=0
    for mesh in doc['meshes']:
        names=mesh.get('extras',{}).get('targetNames',[])
        assert all(w==0 for w in mesh.get('weights',[])), (name,'non-neutral default')
        for primitive in mesh['primitives']:
            attrs=primitive['attributes']; positions=model.accessor(attrs['POSITION'])
            weights=model.accessor(attrs['WEIGHTS_0']); indices=model.accessor(attrs['JOINTS_0'])
            vertices+=len(positions)
            assert all(math.isfinite(v) for p in positions for v in p)
            assert all(min(w)>=0 and abs(sum(w)-1)<1e-5 for w in weights)
            assert all(0<=j<len(joints) for row in indices for j in row)
            for row,values in zip(indices,weights):
                for j,w in zip(row,values):
                    if w>.01: influenced[doc['nodes'][joints[j]]['name']]+=1
            deltas={n:model.accessor(t['POSITION']) for n,t in zip(names,primitive.get('targets',[]))}
            for n,values in deltas.items():
                assert all(math.isfinite(v) for d in values for v in d)
                for p,d in zip(positions,values):
                    if max(abs(v) for v in d)<1e-6: continue
                    counts[n]+=1
                    assert p[1]>c['faceFloor']-.01, (name,n,'facial delta affects body',p)
                    if not c.get('cyclops'):
                        if n=='eyeBlinkLeft': assert p[0]>-.04, (name,n,p)
                        if n=='eyeBlinkRight': assert p[0]<.04, (name,n,p)
            if 'jawOpen' in deltas and 'mouthClose' in deltas:
                assert all(max(abs(a+b) for a,b in zip(o,cl))<1e-5 for o,cl in zip(deltas['jawOpen'],deltas['mouthClose']))
            if c.get('cyclops'):
                for kind in ['Blink','Squint','Wide','LookUp','LookDown','LookIn','LookOut']:
                    if 'eye'+kind+'Left' in deltas:
                        assert deltas['eye'+kind+'Left']==deltas['eye'+kind+'Right'], (name,'cyclops aliases diverge',kind)
    assert all(counts.values()), (name,'empty facial channels',counts)
    assert all(influenced[n]>0 for n in influenced if n!='Root'), (name,'unused deform bone',influenced)
    lids=[n for n in doc['nodes'] if 'eyelidSurfaces' in n.get('extras',{})]
    assert len(lids)==1 and len(lids[0]['extras']['eyelidSurfaces'])==len(c['eyes'])
    for primitive in doc['meshes'][lids[0]['mesh']]['primitives']:
        assert '_LID_INDEX' in primitive['attributes']
    assert all('uri' not in i for i in doc['images'])
    return {'character':name,'passed':True,'bones':len(joints),'facialChannels':len(counts),'exportedVertices':vertices,
            'changedVerticesByChannel':counts,'influencedVerticesByBone':influenced,'cyclops':c.get('cyclops',False)}


def main():
    configs=json.loads((ROOT/'scripts/rig_3dai_landmarks.json').read_text())
    names=sys.argv[1:] or list(configs)
    results=[validate(name,configs[name]) for name in names]
    originals=json.loads((ROOT/'.context/qa/3dai/source-inspection.json').read_text())
    for original in originals:
        path=ROOT/'assets/3dai/originals'/(original['task_id']+'.glb')
        assert hashlib.sha256(path.read_bytes()).hexdigest()==original['sha256'], 'Original changed: '+str(path)
    report={'passed':True,'originalsPreserved':len(originals),'characters':results}
    (ROOT/'.context/qa/3dai/characters-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    for r in results: print('PASS',r['character'],r['bones'],'bones,',r['facialChannels'],'deforming facial channels,',r['exportedVertices'],'vertices')
    print('PASS all',len(originals),'original source hashes unchanged')


if __name__=='__main__': main()
