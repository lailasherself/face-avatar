import test from 'node:test';
import assert from 'node:assert/strict';
import { ArmSignal } from '../arm-signal.js';

test('adaptive filter removes stationary direction jitter without slow step response',()=>{
 const signal=new ArmSignal();let raw=0,filtered=0,lastRaw,lastFiltered;
 for(let i=0;i<150;i++){
  const angle=.04*Math.sin(i*2.4),direction=[Math.cos(angle),Math.sin(angle),0];
  const result=signal.update({L:{upper:direction}},i*1000/30).L.upper;
  assert(Math.abs(Math.hypot(...result)-1)<1e-10);
  if(i>30){raw+=(direction[1]-lastRaw)**2;filtered+=(result[1]-lastFiltered)**2;}
  lastRaw=direction[1];lastFiltered=result[1];
 }
 assert(Math.sqrt(filtered/raw)<.25,'at least 75% less frame-to-frame jitter');
 let result;
 for(let i=150;i<=153;i++)result=signal.update({L:{upper:[0,1,0]}},i*1000/30).L.upper;
 assert(Math.acos(result[1])*180/Math.PI<3,'90-degree change reaches target within 100ms');
});

test('sides are independent, duplicates are ignored and lost tracking resets history',()=>{
 const a=new ArmSignal(),b=new ArmSignal();
 for(let i=0;i<40;i++){
  const R={upper:[-1,.02*Math.sin(i),0]},L={upper:[Math.cos(i),Math.sin(i),0]};
  assert.deepEqual(a.update({L,R},i*33).R,b.update({R},i*33).R);
 }
 assert.deepEqual(a.update({R:{upper:[1,0,0]}},20),{});
 assert.deepEqual(a.update({R:{upper:[0,1,0]}},2000).R.upper,[0,1,0]);
 a.reset();assert.deepEqual(a.update({R:{upper:[-1,0,0]}},2001).R.upper,[-1,0,0]);
 assert.equal(a.update({R:{upper:[NaN,0,1]}},2034).R.upper,null);
 assert.deepEqual(a.update({R:{upper:[1,0,0]}},2067).R.upper,[1,0,0]);
});
