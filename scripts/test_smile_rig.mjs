import test from 'node:test';
import assert from 'node:assert/strict';
import {registerHooks} from 'node:module';
registerHooks({resolve(specifier,context,next){return specifier==='three'?{url:new URL('../vendor/three/three.module.js',import.meta.url).href,shortCircuit:true}:next(specifier,context);}});
const THREE=await import('../vendor/three/three.module.js');
const {attachSmileBite}=await import('../smile-rig.js');

function fixture(skinned=false){
  const root=new THREE.Group(),bone=new THREE.Bone();root.add(bone);
  const rows=['Upper','Lower'].map((row,index)=>{
    const geometry=new THREE.BoxGeometry(.4,.1,.1);geometry.translate(0,index?-.13:.13,0);
    const material=new THREE.MeshBasicMaterial();material.name=row+' dental enamel';
    const mesh=skinned?new THREE.SkinnedMesh(geometry,material):new THREE.Mesh(geometry,material);
    mesh.name=row+' Teeth';root.add(mesh);
    geometry.morphTargetsRelative=true;
    geometry.morphAttributes.position=[new THREE.Float32BufferAttribute(new Float32Array(geometry.attributes.position.count*3),3)];
    mesh.updateMorphTargets();mesh.morphTargetDictionary={jawOpen:0};
    if(skinned){
      const count=geometry.attributes.position.count,weights=new Float32Array(count*4);
      for(let i=0;i<count;i++)weights[i*4]=1;
      geometry.setAttribute('skinIndex',new THREE.Uint16BufferAttribute(new Uint16Array(count*4),4));
      geometry.setAttribute('skinWeight',new THREE.Float32BufferAttribute(weights,4));
      mesh.bind(new THREE.Skeleton([bone]));
    }
    return mesh;
  });
  return {root,rows,bone};
}

function points(mesh){
  mesh.skeleton?.update();const v=new THREE.Vector3(),result=[];
  for(let i=0;i<mesh.geometry.attributes.position.count;i++)result.push(mesh.getVertexPosition(i,v).clone().applyMatrix4(mesh.matrixWorld));
  return result;
}

for(const skinned of [false,true])test(`smile bite preserves neutral data and closes rows (${skinned?'skinned':'static'})`,()=>{
  const {root,rows,bone}=fixture(skinned);
  const basis=rows.map(m=>[...m.geometry.attributes.position.array]);
  attachSmileBite(root);attachSmileBite(root);
  for(const [i,mesh] of rows.entries()){
    assert.deepEqual([...mesh.geometry.attributes.position.array],basis[i]);
    assert.deepEqual(mesh.morphTargetDictionary,{jawOpen:0,smileBite:1});
    assert.equal(mesh.geometry.morphAttributes.position.length,2);
    assert.equal(mesh.morphTargetInfluences[1],0);
    mesh.morphTargetInfluences[1]=1;
  }
  const a=new THREE.Box3().setFromPoints(points(rows[0])),b=new THREE.Box3().setFromPoints(points(rows[1]));
  assert(Math.abs(a.min.y-b.max.y-.0025)<1e-6);
  if(skinned){
    const before=rows.map(points),rotation=new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,0,1),.5);
    bone.quaternion.copy(rotation);root.updateMatrixWorld(true);
    rows.forEach((mesh,i)=>points(mesh).forEach((p,j)=>assert(p.distanceTo(before[i][j].applyQuaternion(rotation))<1e-6)));
  }
});

test('a missing dental row is left alone',()=>{
  const {root,rows}=fixture();root.remove(rows[1]);attachSmileBite(root);
  assert.equal(rows[0].morphTargetDictionary.smileBite,undefined);
});

test('gums follow their dental row without changing the bite fit',()=>{
  const {root,rows}=fixture();
  const gum=new THREE.Mesh(new THREE.BoxGeometry(2,2,2),new THREE.MeshBasicMaterial());
  gum.name='Upper Gums';gum.material.name='Upper gingiva';root.add(gum);
  attachSmileBite(root);
  const dental=rows[0].geometry.morphAttributes.position[rows[0].morphTargetDictionary.smileBite];
  const gingiva=gum.geometry.morphAttributes.position[gum.morphTargetDictionary.smileBite];
  assert(Math.abs((gingiva.getY(0)-gum.geometry.attributes.position.getY(0))-dental.getY(0))<1e-6);
});

test('gums without crowns do not produce invalid morphs',()=>{
  const {root,rows}=fixture();
  for(const mesh of rows){mesh.name=mesh.material.name=mesh.name.replace('Teeth','Gums');}
  attachSmileBite(root);
  for(const mesh of rows)assert.equal(mesh.morphTargetDictionary.smileBite,undefined);
});
