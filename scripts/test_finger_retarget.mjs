import test from 'node:test';
import assert from 'node:assert/strict';
import {registerHooks} from 'node:module';
registerHooks({resolve(specifier,context,next){return specifier==='three'?{url:new URL('../vendor/three/three.module.js',import.meta.url).href,shortCircuit:true}:next(specifier,context);}});
const THREE=await import('../vendor/three/three.module.js');
const {FingerRetargeter}=await import('../finger-retarget.js');

function fixture(limit){
  const root=new THREE.Group();
  const bone=Object.assign(new THREE.Bone(),{name:'Index1.L'});
  bone.rotation.z=.25;bone.userData.fingerCurlRadians=limit;root.add(bone);
  const tracker=new FingerRetargeter(root),rest=bone.quaternion.clone();
  return {bone,tracker,rest};
}
function settle(tracker,hands){for(let i=0;i<120;i++)tracker.update(hands,1/60);}

test('existing rigs retain the default curl range',()=>{
  const {bone,tracker,rest}=fixture();settle(tracker,{L:{Index:[1,1,1]}});
  assert.ok(Math.abs(rest.angleTo(bone.quaternion)-1.15)<1e-6);
});
test('native anatomy can specify a smaller tested range',()=>{
  const {bone,tracker,rest}=fixture(.38);settle(tracker,{L:{Index:[1,1,1]}});
  assert.ok(Math.abs(rest.angleTo(bone.quaternion)-.38)<1e-6);
  settle(tracker,{});assert.ok(rest.angleTo(bone.quaternion)<1e-6);
});
test('invalid metadata falls back without changing existing behavior',()=>{
  for(const limit of [-1,NaN,Infinity,'0.3',Math.PI+.1]){
    const {bone,tracker,rest}=fixture(limit);settle(tracker,{L:{Index:[1,1,1]}});
    assert.ok(Math.abs(rest.angleTo(bone.quaternion)-1.15)<1e-6);
  }
});
test('right-hand input cannot curl a left-hand joint',()=>{
  const {bone,tracker,rest}=fixture(.38);settle(tracker,{R:{Index:[1,1,1]}});
  assert.ok(rest.angleTo(bone.quaternion)<1e-6);
});
