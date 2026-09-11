import test from 'node:test';
import assert from 'node:assert/strict';
import {fingerCurls,trackedFingerCurls} from '../finger-motion.js';
import {fingerHand as hand} from './finger-fixtures.mjs';
test('an open palm does not curl spread fingers',()=>{
  const curls=fingerCurls(hand());
  for(const digit of ['Index','Middle','Ring'])assert.ok(curls[digit].every(v=>v<1e-6));
});
test('pointing keeps the index extended while other fingers close',()=>{
  const curls=fingerCurls(hand({Middle:[1.2,1.5,1.2],Ring:[1.2,1.5,1.2],Pinky:[1.2,1.5,1.2]}));
  assert.ok(curls.Index.every(v=>v<1e-6));
  assert.ok(curls.Middle.every(v=>v>.99));assert.ok(curls.Ring.every(v=>v>.99));
});
test('joints bend independently and remain bounded',()=>{
  const curls=fingerCurls(hand({Index:[0,.75,0]}));
  assert.ok(curls.Index[0]<1e-6);assert.ok(Math.abs(curls.Index[1]-.5)<1e-6);assert.ok(curls.Index[2]<1e-6);
  assert.ok(Object.values(curls).flat().every(v=>v>=0&&v<=1));
});
test('invalid and degenerate landmarks are rejected',()=>{
  assert.equal(fingerCurls([]),null);
  assert.equal(fingerCurls(Array(21).fill(null)),null);
  assert.equal(fingerCurls(Array(21).fill({x:0,y:0,z:0})),null);
  const points=hand();points[8].z=NaN;assert.equal(fingerCurls(points),null);
});
test('both hands use pose wrists, independent of handedness labels',()=>{
  const pose=Array.from({length:33},()=>({x:.5,y:.5,z:0}));pose[16].x=.2;pose[15].x=.8;
  const left=hand().map(p=>({...p,x:p.x+.2,y:p.y+.5}));
  const right=hand({Index:[1.2,1.5,1.2]}).map(p=>({...p,x:p.x+.8,y:p.y+.5}));
  const result=trackedFingerCurls({poseLandmarks:pose,landmarks:[right,left],worldLandmarks:[hand({Index:[1.2,1.5,1.2]}),hand()]});
  assert.ok(result.L.Index[0]<1e-6);assert.ok(result.R.Index[0]>.99);
  assert.deepEqual(trackedFingerCurls({landmarks:[left]}),{});
  assert.deepEqual(trackedFingerCurls({poseLandmarks:pose,landmarks:[hand()]}),{});
  pose[16].visibility=.2;
  assert.deepEqual(trackedFingerCurls({poseLandmarks:pose,landmarks:[left]}),{});
});
