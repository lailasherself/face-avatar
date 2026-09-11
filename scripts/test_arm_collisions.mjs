import test from 'node:test';
import assert from 'node:assert/strict';
import {registerHooks} from 'node:module';
registerHooks({resolve(specifier,context,next){return specifier==='three'?{url:new URL('../vendor/three/three.module.js',import.meta.url).href,shortCircuit:true}:next(specifier,context);}});
const THREE=await import('../vendor/three/three.module.js');
const {ArmCollisions}=await import('../arm-collisions.js');
const {ArmRetargeter}=await import('../arm-retarget.js');
const {default:RAPIER}=await import('../vendor/rapier/rapier.mjs');

test('explicit collision surfaces work without legacy corrective shapes',()=>{
 const root=new THREE.Group(),owner=new THREE.Group();root.add(owner);
 owner.userData.armCollisionSurface=true;
 const head=Object.assign(new THREE.Bone(),{name:'Head'});root.add(head);
 const geometry=new THREE.BoxGeometry(.8,.9,.6),count=geometry.attributes.position.count;
 geometry.setAttribute('skinIndex',new THREE.Uint16BufferAttribute(new Uint16Array(count*4),4));
 const weights=new Float32Array(count*4);for(let i=0;i<count;i++)weights[i*4]=1;
 geometry.setAttribute('skinWeight',new THREE.Float32BufferAttribute(weights,4));
 const mesh=new THREE.SkinnedMesh(geometry,new THREE.MeshBasicMaterial());owner.add(mesh);
 mesh.bind(new THREE.Skeleton([head]));root.updateMatrixWorld(true);
 const guard=new ArmCollisions(root,{});
 try{assert.equal(guard.colliders.length,1);assert(guard.contact(new THREE.Vector3(1,0,0),new THREE.Vector3(0,0,0),.05));}
 finally{guard.dispose();geometry.dispose();mesh.material.dispose();}
 owner.userData.armCollisionSurface=false;
 const excluded=new ArmCollisions(root,{});
 try{assert.equal(excluded.colliders.length,0);}finally{excluded.dispose();}
});

test('capsule contacts prevent an arm passing through a convex body without stretching',()=>{
 const root=new THREE.Group(),guard=new ArmCollisions(root,{});
 guard.colliders.push({anchor:root,collider:guard.world.createCollider(RAPIER.ColliderDesc.ball(.5))});
 try{
  const start=new THREE.Vector3(1,0,0),direction=new THREE.Vector3(-1,0,0);
  assert(guard.contact(start,new THREE.Vector3(0,0,0),.08));
  const safe=guard.avoid(start,direction,1,.08,0,1);
  assert(Math.abs(safe.length()-1)<1e-9);
  assert.equal(guard.contact(start,start.clone().add(safe),.08),null);
  const clear=new THREE.Vector3(0,1,0);
  assert(guard.avoid(start,clear,1,.08,0,1).distanceTo(clear)<1e-8);
 }finally{guard.dispose();}
});

test('collision release eases prior deflection without filtering unconstrained motion',()=>{
 const root=new THREE.Group(),guard=new ArmCollisions(root,{});
 const start=new THREE.Vector3(),previous=new THREE.Vector3(1,0,0),desired=new THREE.Vector3(0,1,0);
 guard.responseAlpha=.25;
 try{
  const direct=guard.avoid(start,desired,1,.05,0,1,null,Math.PI,previous,false);
  assert(direct.distanceTo(desired)<1e-9,'Never-constrained motion must remain direct');
  const released=guard.avoid(start,desired,1,.05,0,1,null,Math.PI,previous,true);
  assert(Math.abs(previous.angleTo(released)-Math.PI/8)<1e-8,'Release must interpolate the feasible output');
  assert(Math.abs(released.length()-1)<1e-9);
  assert(previous.distanceTo(new THREE.Vector3(1,0,0))<1e-9,'History must not be mutated');
 }finally{guard.dispose();}
});

test('feasible collision corrections transition the whole chain without stretching',()=>{
 const root=new THREE.Group(),bones=['UpperArmL','ForearmL','HandL'].map(name=>Object.assign(new THREE.Bone(),{name}));
 root.add(bones[0]);bones[0].add(bones[1]);bones[1].add(bones[2]);bones[1].position.y=.5;bones[2].position.y=.5;
 const tracker=new ArmRetargeter(root),guard=new ArmCollisions(root,tracker.chains);
 const before=bones.map(b=>b.getWorldQuaternion(new THREE.Quaternion()));
 guard.previousPose.L=before.map(q=>q.clone());
 guard.avoid=()=>new THREE.Vector3(0,0,1);
 try{
  guard.update(1/60);
  bones.forEach((b,i)=>assert(before[i].angleTo(b.getWorldQuaternion(new THREE.Quaternion()))<=4.5/60+1e-6));
  assert.equal(bones[1].position.length(),.5);assert.equal(bones[2].position.length(),.5);
  assert(guard.corrected.L.some(Boolean));
  // A changed obstacle can invalidate the old pose: do not prefer a smooth but
  // colliding interpolation over the solver's escape pose.
  guard.contact=()=>({distance:-.03});
  guard.update(1/60);
  assert(new THREE.Vector3(0,1,0).applyQuaternion(bones[0].getWorldQuaternion(new THREE.Quaternion())).distanceTo(new THREE.Vector3(0,0,1))<1e-6);
 }finally{guard.dispose();}
});

test('large deliberate tracking changes do not inherit the collision continuity speed limit',()=>{
 const root=new THREE.Group(),bones=['UpperArmL','ForearmL','HandL'].map(name=>Object.assign(new THREE.Bone(),{name}));
 root.add(bones[0]);bones[0].add(bones[1]);bones[1].add(bones[2]);bones[1].position.y=.5;bones[2].position.y=.5;
 const tracker=new ArmRetargeter(root),guard=new ArmCollisions(root,tracker.chains);
 guard.previousPose.L=bones.map(b=>b.getWorldQuaternion(new THREE.Quaternion()));
 guard.previousRequested.L=guard.previousPose.L.map(q=>q.clone());
 bones[0].rotation.x=.35;root.updateMatrixWorld(true);
 guard.avoid=()=>new THREE.Vector3(0,0,1);
 try{
  guard.update(1/60);
  assert(new THREE.Vector3(0,1,0).applyQuaternion(bones[0].getWorldQuaternion(new THREE.Quaternion())).distanceTo(new THREE.Vector3(0,0,1))<1e-6);
 }finally{guard.dispose();}
});

test('elbow and wrist limits survive abrupt targets; missing hand follows the forearm',()=>{
 const root=new THREE.Group(),bones=['UpperArmL','ForearmL','HandL'].map(name=>Object.assign(new THREE.Bone(),{name}));
 root.add(bones[0]);bones[0].add(bones[1]);bones[1].add(bones[2]);bones[1].position.y=.5;bones[2].position.y=.5;
 const tracker=new ArmRetargeter(root),guard=new ArmCollisions(root,tracker.chains);
 try{
  for(let i=0;i<20;i++){
   tracker.update({L:{upper:[1,0,0],lower:[-1,0,0],hand:[0,-1,0]}},1/30);guard.update();
   const axes=bones.map(b=>new THREE.Vector3(0,1,0).applyQuaternion(b.getWorldQuaternion(new THREE.Quaternion())));
   assert(axes[0].angleTo(axes[1])<=145*Math.PI/180+1e-6);
   assert(axes[1].angleTo(axes[2])<=65*Math.PI/180+1e-6);
   assert.equal(bones[1].position.length(),.5);assert.equal(bones[2].position.length(),.5);
  }
  for(let i=0;i<20;i++)tracker.update({L:{upper:[1,0,0],lower:[0,0,1],hand:null}},1/30);
  assert(bones[1].getWorldQuaternion(new THREE.Quaternion()).angleTo(bones[2].getWorldQuaternion(new THREE.Quaternion()))<1e-6);
 }finally{guard.dispose();}
});

test('tracking loss returns to the captured safe neutral without changing live calibration',()=>{
 const root=new THREE.Group(),bones=['UpperArmL','ForearmL','HandL'].map(name=>Object.assign(new THREE.Bone(),{name}));
 root.add(bones[0]);bones[0].add(bones[1]);bones[1].add(bones[2]);bones[1].position.y=.5;bones[2].position.y=.5;
 const tracker=new ArmRetargeter(root),calibration=tracker.chains.L.map(j=>j.rest.clone());
 bones[0].rotation.z=-.2;root.updateMatrixWorld(true);tracker.captureNeutral();
 const neutral=bones.map(b=>b.quaternion.clone());
 for(let i=0;i<60;i++)tracker.update({L:{upper:[1,0,0],lower:[0,0,1]}},1/30);
 for(let i=0;i<60;i++)tracker.update({},1/30);
 bones.forEach((b,i)=>assert(b.quaternion.angleTo(neutral[i])<1e-6));
 tracker.chains.L.forEach((j,i)=>assert(j.rest.angleTo(calibration[i])<1e-6));
});

test('arm roll remains continuous across the rest-axis antipode',()=>{
 const root=new THREE.Group(),bones=['UpperArmL','ForearmL','HandL'].map(name=>Object.assign(new THREE.Bone(),{name}));
 root.add(bones[0]);bones[0].add(bones[1]);bones[1].add(bones[2]);bones[1].position.y=.5;bones[2].position.y=.5;
 const tracker=new ArmRetargeter(root);let previous;
 for(let i=0;i<240;i++){
  const t=-.12+i*.001,d=[Math.sin(t),-Math.cos(t),.002*Math.sin(i)];
  tracker.update({L:{upper:d,lower:d,hand:d}},1/60);
  const q=bones[0].getWorldQuaternion(new THREE.Quaternion());
  if(i>60)assert(q.angleTo(previous)<5*Math.PI/180,'roll must not flip at the antipode');
  previous=q;
 }
});

test('external collision rotations do not feed back into tracking smoothing',()=>{
 const make=()=>{
  const root=new THREE.Group(),a=Object.assign(new THREE.Bone(),{name:'UpperArmL'}),b=Object.assign(new THREE.Bone(),{name:'ForearmL'}),c=Object.assign(new THREE.Bone(),{name:'HandL'});
  root.add(a);a.add(b);b.add(c);b.position.y=.5;c.position.y=.5;
  return {a,tracker:new ArmRetargeter(root)};
 };
 const a=make(),b=make(),sample={L:{upper:[1,0,0],lower:[0,1,0]}};
 for(let i=0;i<30;i++){
  a.tracker.update(sample,1/60);b.tracker.update(sample,1/60);
  assert(a.a.quaternion.angleTo(b.a.quaternion)<1e-6);
  a.a.rotation.set(1,1,1);a.a.updateWorldMatrix(false,true);
 }
});

test('a held direction does not keep recentering idle-arm twist',()=>{
 const root=new THREE.Group(),bones=['UpperArmL','ForearmL','HandL'].map(name=>Object.assign(new THREE.Bone(),{name}));
 root.add(bones[0]);bones[0].add(bones[1]);bones[1].add(bones[2]);bones[1].position.y=.5;bones[2].position.y=.5;
 const tracker=new ArmRetargeter(root);
 for(const d of [[1,0,0],[0,0,1],[0,-1,0],[1,0,0]])tracker.update({L:{upper:d,lower:d,hand:d}},1/60);
 const solved=tracker.chains.L.map(j=>j.solved.clone());
 for(let i=0;i<60;i++)tracker.update({L:{upper:[1,0,0],lower:[1,0,0],hand:[1,0,0]}},1/60);
 tracker.chains.L.forEach((j,i)=>assert(j.solved.angleTo(solved[i])<1e-6));
});

test('authored rest contact is opt-in and does not bypass collision solving on a moving arm',()=>{
 const root=new THREE.Group(),bones=['UpperArmL','ForearmL','HandL'].map(name=>Object.assign(new THREE.Bone(),{name}));
 root.rotation.set(.1,.3,-.2);
 root.add(bones[0]);bones[0].add(bones[1]);bones[1].add(bones[2]);bones[1].position.y=.5;bones[2].position.y=.5;
 const tracker=new ArmRetargeter(root);tracker.captureNeutral();
 const guard=new ArmCollisions(root,tracker.chains),avoid=guard.avoid.bind(guard);let calls=0;
 guard.avoid=(...args)=>{calls++;return avoid(...args);};
 try{
  tracker.update({},1/60);guard.update();assert.equal(calls,3,'Legacy rigs must keep solving at rest');
  calls=0;bones[0].userData.armCollisionRestContact=true;
  guard.previous.L=[new THREE.Vector3(1,0,0)];guard.corrected.L=[true];tracker.update({},1/60);guard.update();
  assert.equal(calls,0,'Opted-in neutral contact should not invent arm motion');assert.equal(guard.previous.L,undefined);assert.equal(guard.corrected.L,undefined);
  tracker.update({L:{upper:[1,0,0],lower:[1,0,0]}},1/60);guard.update();
  assert.equal(calls,3,'An opted-in moving arm must still run collision avoidance');
 }finally{guard.dispose();}
});
