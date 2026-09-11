import test from 'node:test';
import assert from 'node:assert/strict';
import {registerHooks} from 'node:module';
registerHooks({resolve(specifier,context,next){
  return specifier==='three'?{url:new URL('../vendor/three/three.module.js',import.meta.url).href,shortCircuit:true}:next(specifier,context);
}});
const THREE=await import('../vendor/three/three.module.js');
const {ArmRetargeter}=await import('../arm-retarget.js');
const {AirSwipeTracker}=await import('../air-swipe.js');

test('upper arm and forearm advance together in world space at every frame rate',()=>{
  for(const fps of [20,30,60]){
    const root=new THREE.Group(),upper=new THREE.Bone(),lower=new THREE.Bone(),hand=new THREE.Bone();
    upper.name='UpperArmL';lower.name='ForearmL';hand.name='HandL';
    root.add(upper);upper.add(lower);lower.add(hand);lower.position.y=.5;hand.position.y=.5;
    root.rotation.z=.35;
    const tracker=new ArmRetargeter(root);
    const arms={L:{upper:[1,0,0],lower:[1,0,0],hand:[1,0,0]}};
    for(let i=0;i<fps/5;i++){
      tracker.update(arms,1/fps);
      const uq=upper.getWorldQuaternion(new THREE.Quaternion()),lq=lower.getWorldQuaternion(new THREE.Quaternion());
      assert(uq.angleTo(lq)<1e-6,'forearm must not accumulate parent smoothing lag');
    }
    const direction=new THREE.Vector3(0,1,0).applyQuaternion(upper.getWorldQuaternion(new THREE.Quaternion()));
    const expected=new THREE.Vector3(1,0,0).applyQuaternion(root.quaternion);
    assert(direction.angleTo(expected)<.005,'settles promptly');
    for(let i=0;i<fps/5;i++)tracker.update({},1/fps);
    assert(upper.quaternion.angleTo(new THREE.Quaternion())<.005,'loss recovers rest pose');
  }
});

test('pose arrives before fingers, stale and reordered frames cannot refresh tracking',()=>{
  const Original=globalThis.Worker;
  let worker;globalThis.Worker=class{constructor(){worker=this;}postMessage(){}terminate(){}};
  const received=[],errors=[];
  const tracker=new AirSwipeTracker(()=>{},error=>errors.push(error),(data,gesture,time)=>received.push({data,time}));
  try{
    const send=(type,time)=>worker.onmessage({data:{type,time,result:{landmarks:[]}}});
    send('ready');const now=performance.now();
    tracker.busy=true;send('pose',now-10);
    assert.equal(received.length,1);assert.equal(tracker.busy,true);
    send('result',now-10);assert.equal(received.length,2);assert.equal(tracker.busy,false);
    assert.equal(tracker.lastResultTime,now-10);
    send('result',now-20);send('result',now-500);send('result',now+10000);
    assert.equal(received.length,2);assert.equal(tracker.droppedFrames,3);
    send('pose',now-11);send('pose',now-600);assert.equal(received.length,2);
    assert.deepEqual(errors,[]);
  }finally{tracker.stop();globalThis.Worker=Original;}
});

test('independent pose completion releases capture but delayed fingers cannot release another pose',()=>{
 const Original=globalThis.Worker;let worker;
 globalThis.Worker=class{constructor(){worker=this;}postMessage(){}terminate(){}};
 const tracker=new AirSwipeTracker(()=>{},()=>{});
 try{
  worker.onmessage({data:{type:'ready'}});const time=performance.now();tracker.busy=true;
  worker.onmessage({data:{type:'pose',time,complete:true,result:{landmarks:[]}}});
  assert.equal(tracker.busy,false);assert.equal(tracker.poseFrames,1);
  tracker.busy=true;
  worker.onmessage({data:{type:'result',time,independentHands:true,result:{landmarks:[]}}});
  assert.equal(tracker.busy,true);
 }finally{tracker.stop();globalThis.Worker=Original;}
});
