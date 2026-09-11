"""Validate the actual exported buffers, including skin weights and facial deltas."""
import json
import math
from pathlib import Path
import struct

ROOT=Path(__file__).resolve().parents[1]
SIZE={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
FORMATS={5120:'b',5121:'B',5122:'h',5123:'H',5125:'I',5126:'f'}

class GLB:
    def __init__(self,path):
        raw=path.read_bytes()
        magic,version,length=struct.unpack_from('<III',raw)
        assert magic==0x46546C67 and version==2 and length==len(raw)
        n=struct.unpack_from('<I',raw,12)[0]
        self.doc=json.loads(raw[20:20+n])
        self.binary=raw[28+n:]

    def accessor(self,index):
        a=self.doc['accessors'][index]
        fmt='<'+FORMATS[a['componentType']]*SIZE[a['type']]
        size=struct.calcsize(fmt)
        result=[(0,)*SIZE[a['type']] for _ in range(a['count'])]
        if 'bufferView' in a:
            view=self.doc['bufferViews'][a['bufferView']]
            stride=view.get('byteStride',size)
            start=view.get('byteOffset',0)+a.get('byteOffset',0)
            result=[struct.unpack_from(fmt,self.binary,start+i*stride) for i in range(a['count'])]
        if 'sparse' in a:
            sparse=a['sparse'];idx=sparse['indices'];val=sparse['values']
            idx_fmt='<'+FORMATS[idx['componentType']];idx_size=struct.calcsize(idx_fmt)
            idx_start=self.doc['bufferViews'][idx['bufferView']].get('byteOffset',0)+idx.get('byteOffset',0)
            val_start=self.doc['bufferViews'][val['bufferView']].get('byteOffset',0)+val.get('byteOffset',0)
            for i in range(sparse['count']):
                index=struct.unpack_from(idx_fmt,self.binary,idx_start+i*idx_size)[0]
                result[index]=struct.unpack_from(fmt,self.binary,val_start+i*size)
        return result

def main():
    manifest=json.loads((ROOT/'assets/fleet/manifest.json').read_text())
    channels=manifest['channels'];assert len(channels)==len(set(channels))==52
    report=[]
    for c in manifest['characters']:
        glb=GLB(ROOT/c['url']);d=glb.doc
        assert len(d['skins'])==1
        joints=d['skins'][0]['joints'];assert len(joints)==c['bones']==28
        assert {'Seated','Standing','T-Pose'}=={a['name'] for a in d['animations']}
        names={d['nodes'][i]['name'] for i in joints}
        assert {'Head','Hips','Root','Hand.L','Thigh.L','Finger1.L'}<=names
        lid_nodes=[n for n in d['nodes'] if 'eyelidSurfaces' in n.get('extras',{})]
        assert len(lid_nodes)==1, 'Missing eyelid projection metadata'
        lid_node=lid_nodes[0];surfaces=lid_node['extras']['eyelidSurfaces']
        assert len(surfaces) in (1,2)
        for surface in surfaces:
            assert len(surface['center'])==len(surface['radii'])==3
            assert all(math.isfinite(v) for v in surface['center'])
            assert all(math.isfinite(v) and v>0 for v in surface['radii'])
        tagged=set()
        for prim in d['meshes'][lid_node['mesh']]['primitives']:
            attrs=prim['attributes'];assert '_LID_INDEX' in attrs
            tags=glb.accessor(attrs['_LID_INDEX'])
            assert len(tags)==len(glb.accessor(attrs['POSITION']))
            assert all(v==int(v) and 0<=v<=len(surfaces) for (v,) in tags)
            tagged.update(int(v) for (v,) in tags if v)
        assert tagged==set(range(1,len(surfaces)+1)), 'Missing tagged eyelid vertices'
        changed={name:0 for name in channels};vertices=0
        for mesh in d['meshes']:
            targets=mesh.get('extras',{}).get('targetNames',[])
            if targets:
                assert targets==channels
                assert all(w==0 for w in mesh['weights']), 'Export must start neutral'
            for prim in mesh['primitives']:
                attrs=prim['attributes'];positions=glb.accessor(attrs['POSITION'])
                vertices+=len(positions)
                assert all(math.isfinite(x) for p in positions for x in p)
                weights=glb.accessor(attrs['WEIGHTS_0']);indices=glb.accessor(attrs['JOINTS_0'])
                assert len(weights)==len(positions)
                assert all(abs(sum(w)-1)<1e-5 and min(w)>=0 for w in weights)
                assert all(0<=i<len(joints) for js in indices for i in js)
                for name,morph in zip(targets,prim.get('targets',[])):
                    deltas=glb.accessor(morph['POSITION'])
                    assert len(deltas)==len(positions)
                    assert all(math.isfinite(v) for p in deltas for v in p)
                    changed[name]+=sum(any(abs(v)>1e-6 for v in p) for p in deltas)
        assert all(changed.values()),f'{c["id"]}: empty facial target'
        assert (ROOT/'blender/fleet'/f'{c["id"]}.blend').exists()
        report.append(dict(character=c['id'],bones=len(joints),facialTargets=len(changed),exportedVertices=vertices,bytes=(ROOT/c['url']).stat().st_size))
    car=GLB(ROOT/manifest['vehicle'])
    assert not car.doc.get('skins') and not car.doc.get('animations')
    assert any(n.get('name')=='SeatAnchor' for n in car.doc['nodes'])
    print(json.dumps({'passed':True,'characters':report,'sharedVehicle':True},indent=2))

if __name__=='__main__':main()
