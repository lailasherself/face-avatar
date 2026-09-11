import test from 'node:test';
import assert from 'node:assert/strict';
import {zedMotion} from '../zed-motion.js';
const point=(x,y,z)=>({position:[x,y,z],image:[.5,.5],confidence:.9});
function packet(){return {version:1,coordinates:'RIGHT_HANDED_Y_UP',reference:'CAMERA',units:'meters',body:{id:1,joints:{
 RIGHT_SHOULDER:point(-.2,0,-2),RIGHT_ELBOW:point(-.4,.3,-2),RIGHT_WRIST:point(-.4,.6,-1.8),
 LEFT_SHOULDER:point(.2,0,-2),LEFT_ELBOW:point(.2,-.3,-2),LEFT_WRIST:point(.2,-.6,-2),
}}};}
test('ZED native depth mirrors one arm independently and keeps camera-facing reach',()=>{
 const {arms,poseLandmarks}=zedMotion(packet());
 assert(arms.L.upper[0]>0&&arms.L.upper[1]>0);assert(arms.L.lower[2]>0);
 assert.deepEqual(arms.R.upper.map(v=>v||0),[0,-1,0]);assert.deepEqual(arms.R.lower.map(v=>v||0),[0,-1,0]);
 assert.equal(arms.L.hand,null);assert.equal(poseLandmarks[12].visibility,.9);
});
test('ZED missing/occluded joints never substitute the other side',()=>{
 const p=packet();p.body.joints.RIGHT_WRIST.confidence=.3;
 assert.deepEqual(Object.keys(zedMotion(p).arms),['R']);
 p.body=null;assert.deepEqual(zedMotion(p).arms,{});
 assert(zedMotion(p).poseLandmarks.every(v=>v.visibility===0));
});
test('ZED rejects wrong units/reference and malformed native joints',()=>{
 for(const [key,value] of [['units','millimeters'],['reference','WORLD'],['version',2]])assert.throws(()=>zedMotion({...packet(),[key]:value}));
 for(const value of [NaN,Infinity]){
  const p=packet();p.body.joints.RIGHT_ELBOW.position[0]=value;
  assert.deepEqual(Object.keys(zedMotion(p).arms),['R']);
 }
});
test('ZED palm crop hints preserve camera coordinates and confidence on the mirrored side',()=>{
 const p=packet();p.body.joints.RIGHT_HAND={...point(-.4,.7,-1.7),image:[.8,.2]};
 assert.deepEqual(zedMotion(p).handHints,{L:{x:.8,y:.2,visibility:.9,presence:.9}});
 p.body.joints.RIGHT_HAND.confidence=.3;
 assert.deepEqual(zedMotion(p).handHints,{});
});
