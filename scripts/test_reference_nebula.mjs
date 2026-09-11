import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const bytes=readFileSync(new URL('../assets/reference-characters/nebula-review.glb',import.meta.url));
assert.equal(bytes.readUInt32LE(0),0x46546c67);
assert.equal(bytes.readUInt32LE(4),2);
assert.equal(bytes.readUInt32LE(8),bytes.length);
const jsonLength=bytes.readUInt32LE(12);
const gltf=JSON.parse(bytes.toString('utf8',20,20+jsonLength));
const binary=bytes.subarray(28+jsonLength);

function values(index){
  const accessor=gltf.accessors[index];
  const view=gltf.bufferViews[accessor.bufferView];
  const components={SCALAR:1,VEC2:2,VEC3:3,VEC4:4,MAT4:16}[accessor.type];
  const formats={5121:[1,'readUInt8'],5123:[2,'readUInt16LE'],5125:[4,'readUInt32LE'],5126:[4,'readFloatLE']};
  const [size,read]=formats[accessor.componentType];
  const result=Array(accessor.count*components).fill(0);
  if(view){
    const stride=view.byteStride||size*components;
    const offset=(view.byteOffset||0)+(accessor.byteOffset||0);
    for(let i=0;i<accessor.count;i++)for(let j=0;j<components;j++)result[i*components+j]=binary[read](offset+i*stride+j*size);
  }
  if(accessor.sparse){
    const sparse=accessor.sparse;
    const [indexSize,indexRead]=formats[sparse.indices.componentType];
    const indexOffset=(gltf.bufferViews[sparse.indices.bufferView].byteOffset||0)+(sparse.indices.byteOffset||0);
    const valueOffset=(gltf.bufferViews[sparse.values.bufferView].byteOffset||0)+(sparse.values.byteOffset||0);
    for(let i=0;i<sparse.count;i++){
      const index=binary[indexRead](indexOffset+i*indexSize);
      assert.ok(index<accessor.count,'Sparse index exceeds accessor bounds');
      for(let j=0;j<components;j++)result[index*components+j]=binary[read](valueOffset+(i*components+j)*size);
    }
  }
  return result;
}

test('only the reviewed scene is exported, without the untouched source scene',()=>{
  assert.equal(gltf.scenes.length,1);
  assert.ok(gltf.nodes.some(n=>n.name==='NebulaSourceBody'));
  assert.ok(!gltf.nodes.some(n=>n.name==='Nebula'));
  assert.ok(!gltf.nodes.some(n=>n.camera!==undefined));
  assert.equal(gltf.nodes.find(n=>n.name==='AvatarRig').extras.installationApproved,false);
});

test('body skeleton and three native finger chains survive export',()=>{
  const skin=gltf.skins[0];
  assert.equal(skin.joints.length,36);
  const names=skin.joints.map(i=>gltf.nodes[i].name.replaceAll('.',''));
  for(const side of ['L','R'])for(const digit of ['Thumb','Index','Middle'])for(let i=1;i<=3;i++){
    assert.ok(names.includes(`${digit}${i}${side}`));
    const bone=gltf.nodes[skin.joints[names.indexOf(`${digit}${i}${side}`)]];
    assert.ok(bone.extras.fingerCurlRadians>0&&bone.extras.fingerCurlRadians<.5);
  }
  for(const mesh of gltf.meshes)for(const p of mesh.primitives){
    assert.ok(values(p.attributes.POSITION).every(Number.isFinite));
    const weights=values(p.attributes.WEIGHTS_0);
    for(let i=0;i<weights.length;i+=4)assert.ok(Math.abs(weights.slice(i,i+4).reduce((a,b)=>a+b,0)-1)<1e-5);
  }
});

test('facial channels, neutral values, teeth and embedded textures survive export',()=>{
  const face=gltf.meshes.find(m=>m.name==='NebulaEyesAndMouth');
  assert.equal(face.extras.targetNames.length,52);
  for(const name of ['eyeBlinkLeft','eyeBlinkRight','jawOpen','tongueOut'])assert.ok(face.extras.targetNames.includes(name));
  for(const mesh of gltf.meshes){
    assert.ok((mesh.weights||[]).every(v=>v===0));
    for(const p of mesh.primitives)for(const target of p.targets||[])assert.ok(values(target.POSITION).every(Number.isFinite));
  }
  for(const name of ['UpperTeeth','LowerTeeth'])assert.ok(gltf.nodes.some(n=>n.name===name));
  assert.ok(gltf.images.length>0);
  assert.ok(gltf.images.every(i=>i.bufferView!==undefined&&!i.uri));
});
