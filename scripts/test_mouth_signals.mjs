import test from 'node:test';
import assert from 'node:assert/strict';
import {resolveMouth,oralWeight} from '../mouth-signals.js';

test('opposing mouth directions cancel and opening expressions share a budget',()=>{
 const v=resolveMouth({jawOpen:.8,jawLeft:.7,jawRight:.5,mouthLeft:1,mouthRight:1,mouthFunnel:.8,mouthPucker:.9,
  mouthLowerDownLeft:1,mouthLowerDownRight:1,mouthUpperUpLeft:1,mouthSmileLeft:1,mouthStretchLeft:1});
 assert(Math.abs(v.jawLeft-.2)<1e-10);assert.equal(v.jawRight,0);assert.equal(v.mouthLeft,0);
 assert(v.mouthFunnel+v.mouthPucker<=.800001);
 assert(v.mouthSmileLeft+v.mouthStretchLeft<=1);
 assert(v.mouthLowerDownLeft<.15);assert(v.mouthUpperUpLeft<=.35);
});

test('tongue clears closing lips and does not inherit lip distortion',()=>{
 const v=resolveMouth({tongueOut:.5,jawOpen:.3,mouthClose:1,mouthPucker:1,mouthRollLower:1,mouthPressLeft:1});
 assert(v.jawOpen-v.mouthClose>=.65);assert.equal(v.mouthPucker,0);assert.equal(v.mouthRollLower,0);assert.equal(v.mouthPressLeft,0);
 assert.equal(oralWeight('mouthFunnel',1,'Juno oral interior'),0);
 assert.equal(oralWeight('mouthSmileLeft',1,'Juno tongue'),0);
 assert.equal(oralWeight('tongueOut',1,'Juno tongue'),1);
 assert.equal(oralWeight('jawOpen',.4,'Juno oral interior'),.4);
 assert.equal(oralWeight('mouthFunnel',.5,'skin'),.5);
});
