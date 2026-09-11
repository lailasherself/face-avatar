import test from 'node:test';
import assert from 'node:assert/strict';
import {resolveMouth,oralWeight} from '../mouth-signals.js';
import {readFileSync} from 'node:fs';

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
 assert.equal(oralWeight('mouthUpperUpLeft',.32,'Orbit Oral interior'),.32);
 assert.equal(oralWeight('mouthLowerDownRight',.12,'Coral Oral interior'),.12);
 assert.equal(oralWeight('mouthUpperUpLeft',.32,'Orbit tongue'),0);
 assert.equal(oralWeight('mouthSmileLeft',.8,'Orbit Oral interior'),.8);
});

test('a bilateral smile exposes teeth without requiring a large tracked jaw opening',()=>{
 const smile=resolveMouth({mouthSmileLeft:.8,mouthSmileRight:.8,jawOpen:.04,mouthUpperUpLeft:.25,mouthUpperUpRight:.25});
 assert.equal(smile.jawOpen,.42);
 assert.equal(smile.dentalJawOpen,0);assert.equal(smile.smileBite,1);
 assert(Math.abs(smile.mouthUpperUpLeft-.5135)<1e-10);assert.equal(smile.mouthUpperUpRight,smile.mouthUpperUpLeft);
 assert.equal(smile.mouthSmileLeft,.8);assert.equal(smile.mouthSmileRight,.8);
 const talking=resolveMouth({mouthSmileLeft:1,mouthSmileRight:1,jawOpen:.8});
 assert.equal(talking.jawOpen,.8,'do not limit a genuinely open jaw');
});

test('smile clearance stays neutral for rest, one-sided smirks and deliberate closed lips',()=>{
 for(const extra of [{mouthClose:1},{mouthPressLeft:1},{mouthRollUpper:1},{mouthPucker:1},{mouthFunnel:1}]){
  const v=resolveMouth({mouthSmileLeft:1,mouthSmileRight:1,...extra});
  assert.equal(v.jawOpen-v.mouthClose,0);assert.equal(v.mouthUpperUpLeft,0);
 }
 for(const input of [{},{mouthSmileLeft:.1,mouthSmileRight:.1},{mouthSmileLeft:1}]){
  const v=resolveMouth(input);assert.equal(v.jawOpen,0);assert.equal(v.mouthUpperUpLeft,0);
 }
 const tongue=resolveMouth({mouthSmileLeft:1,mouthSmileRight:1,tongueOut:1});
 assert.equal(tongue.jawOpen,.65);assert.equal(tongue.mouthUpperUpLeft,0);
});

test('smile reveal ramps continuously instead of snapping the jaw open',()=>{
 let previous=0;
 for(let i=0;i<=100;i++){
  const v=resolveMouth({mouthSmileLeft:i/100,mouthSmileRight:i/100});
  assert(v.jawOpen>=previous);assert(v.jawOpen-previous<.010);previous=v.jawOpen;
 }
});

test('measured photo smile retracts both lips with a nearly closed dental bite',()=>{
 const photo=JSON.parse(readFileSync(new URL('./fixtures/smile-photo-scores.json',import.meta.url)));
 const v=resolveMouth({...photo});
 assert(v.smileBite>.99);assert(v.dentalJawOpen<.001);
 assert(v.mouthUpperUpLeft>.9);assert(v.mouthLowerDownLeft>.4);
 assert.equal(oralWeight('jawOpen',v.jawOpen,'Orbit Upper ivory teeth',v),v.dentalJawOpen);
 assert.equal(oralWeight('jawOpen',v.jawOpen,'Orbit skin',v),v.jawOpen);
});

test('talking, tongue extension and deliberate closed lips release smile bite',()=>{
 for(const extra of [{jawOpen:.7},{tongueOut:1},{mouthClose:1},{mouthPucker:1},{mouthPressLeft:1}]){
  const v=resolveMouth({mouthSmileLeft:1,mouthSmileRight:1,...extra});
  assert.equal(v.smileBite,0);
  if(extra.jawOpen)assert.equal(v.dentalJawOpen,.7);
  if(extra.tongueOut)assert.equal(v.dentalJawOpen,.65);
 }
 assert.equal(resolveMouth({mouthSmileLeft:1}).smileBite,0);
 assert.equal(resolveMouth({}).smileBite,0);
});
