"""Validate articulated joints, corrective data, dental rigs and source integrity."""
import hashlib,json,math
from pathlib import Path
from validate_fleet import GLB

ROOT=Path(__file__).resolve().parents[1]
channels=set(json.loads((ROOT/'assets/fleet/manifest.json').read_text())['channels'])
results=[]
for entry in json.loads((ROOT/'assets/3dai/manifest.json').read_text())['characters']:
    name=entry['id'];model=GLB(ROOT/'assets/3dai/refined'/f'{name}.glb');doc=model.doc
    assert len(doc['skins'])==1
    joints=doc['skins'][0]['joints'];names=[doc['nodes'][j]['name'] for j in joints]
    finger_names={f'{digit}{joint}.{side}' for digit in ['Thumb','Index','Middle','Ring'] for joint in [1,2,3] for side in ['L','R']}
    assert finger_names<=set(names),(name,'missing finger joints')
    expected=50 if name=='pearl' else 45 if name=='fuzz' else 42
    assert len(joints)==expected,(name,len(joints))
    influenced=dict.fromkeys(names,0);active=set();correctives=set();vertices=0
    for mesh in doc['meshes']:
        targets=mesh.get('extras',{}).get('targetNames',[])
        assert all(w==0 for w in mesh.get('weights',[])),(name,'nonzero default morph')
        for primitive in mesh['primitives']:
            attrs=primitive['attributes'];positions=model.accessor(attrs['POSITION']);vertices+=len(positions)
            assert all(math.isfinite(v) for p in positions for v in p)
            if any(target.startswith('corrective') for target in targets):
                first=next(i for i,target in enumerate(targets) if target.startswith('corrective'))
                assert all(target.startswith('corrective') for target in targets[first:]),(name,'noncontiguous pose morphs')
                for i in range(15):
                    values=model.accessor(attrs[f'_PSD_N_{i}'])
                    assert len(values)==len(positions) and all(math.isfinite(v) for p in values for v in p)
            for indices,weights in zip(model.accessor(attrs['JOINTS_0']),model.accessor(attrs['WEIGHTS_0'])):
                assert min(weights)>=0 and abs(sum(weights)-1)<1e-5
                for joint,weight in zip(indices,weights):
                    assert 0<=joint<len(joints)
                    if weight>.01:influenced[names[joint]]+=1
            for target,buffer in zip(targets,primitive.get('targets',[])):
                values=model.accessor(buffer['POSITION'])
                assert all(math.isfinite(v) for p in values for v in p)
                if any(abs(v)>1e-6 for p in values for v in p):active.add(target)
                if target.startswith('corrective'):correctives.add(target)
    assert channels<=active,(name,'empty facial channels',channels-active)
    assert all(influenced[n]>0 for n in finger_names),(name,'unweighted finger')
    assert len(correctives)==15,(name,len(correctives))
    assert len(doc['animations'])==11,(name,'missing pose samples')
    assert len([n for n in doc['nodes'] if n.get('extras',{}).get('dentalRigVersion')])==2
    owners=[n for n in doc['nodes'] if n.get('extras',{}).get('correctiveSamples')]
    assert len(owners)==1 and len(owners[0]['extras']['correctiveSamples'])==15
    assert owners[0]['extras']['correctiveSpace']=='postSkin'
    assert any(n.get('extras',{}).get('eyelidSurfaces') for n in doc['nodes'])
    assert all('uri' not in image for image in doc['images'])
    results.append({'id':name,'bones':len(joints),'fingerBones':24,'correctives':15,'vertices':vertices})
    print('PASS',name,len(joints),'bones, 24 weighted finger joints, 15 correctives, 52 facial channels')
    preserved=ROOT/'.context/before-refinement'/(name+'-rigged.blend')
    assert preserved.read_bytes()==(ROOT/'blender/3dai'/(name+'-rigged.blend')).read_bytes(),(name,'working Blender scene changed')
originals=json.loads((ROOT/'.context/qa/3dai/source-inspection.json').read_text())
for original in originals:
    path=ROOT/'assets/3dai/originals'/(original['task_id']+'.glb')
    assert hashlib.sha256(path.read_bytes()).hexdigest()==original['sha256']
(ROOT/'.context/qa/refinement/validation.json').write_text(json.dumps({'structuralChecksPassed':True,'productionReady':False,'results':results,'originalsPreserved':len(originals)},indent=2)+'\n')
