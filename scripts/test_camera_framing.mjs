import test from 'node:test';
import assert from 'node:assert/strict';
import {cameraConstraints,armFraming} from '../camera-framing.js';
const pose=()=>Array.from({length:33},()=>({x:.5,y:.5,z:0,visibility:1,presence:1}));
test('camera requests a native mode without browser cropping where supported',()=>{
  const constraints=cameraConstraints({resizeMode:true});
  assert.deepEqual(constraints.video.resizeMode,{exact:'none'});
  assert.deepEqual(constraints.video.width,{ideal:1280});
  assert.deepEqual(constraints.video.height,{ideal:720});
  assert.equal(constraints.audio,false);
  assert.equal(cameraConstraints().video.resizeMode,undefined);
});
test('framing distinguishes a near edge from an unseen or off-frame arm independently',()=>{
  const p=pose();assert.deepEqual(armFraming(p,100,110),{left:'in-frame',right:'in-frame'});
  p[15].x=.03;assert.deepEqual(armFraming(p,100,110),{left:'near-edge',right:'in-frame'});
  p[15].x=-.1;assert.equal(armFraming(p,100,110).left,'outside-frame');
  p[15].visibility=.1;assert.equal(armFraming(p,100,110).left,'not-tracked');
  assert.deepEqual(armFraming(p,100,501),{left:'not-tracked',right:'not-tracked'});
  assert.equal(armFraming(p,200,100).right,'not-tracked');
});
test('framing confidence follows the active body source rather than accepting weak webcam poses',()=>{
  const p=pose();p[15].visibility=.7;
  assert.equal(armFraming(p,100,110).left,'not-tracked');
  assert.equal(armFraming(p,100,110,.6).left,'in-frame');
});
