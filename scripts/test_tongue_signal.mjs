import test from 'node:test';
import assert from 'node:assert/strict';
import {TongueSignal,faceCropTransform} from '../tongue-signal.js';

test('tongue activation requires sustained model evidence and releases on loss',()=>{
 const signal=new TongueSignal();
 assert.equal(signal.update(.7,1000),0);assert.equal(signal.update(.1,1080),0);
 assert.equal(signal.update(.7,1160),0);assert(signal.update(.7,1240)>.99);
 assert.equal(signal.update(.1,1320),0);
 assert.equal(signal.update(.99,1200),0,'out-of-order cannot re-extend');
 signal.update(.9,1400);signal.update(.9,1480);
 assert(signal.current(1600)>.99);assert.equal(signal.current(1900),0);
 assert.equal(signal.update(.7,2000),0,'ambiguous evidence after loss must re-arm');
 signal.reset();assert.equal(signal.current(2000),0);
});

test('strong tongue evidence activates immediately and a negative sample retracts immediately',()=>{
 const signal=new TongueSignal();assert.equal(signal.update(.85,1000),1);
 assert.equal(signal.update(.1,1033),0);
});

test('crop transform rejects invalid landmarks and aligns the eye line',()=>{
 assert.equal(faceCropTransform([],640,480),null);
 const points=Array.from({length:478},()=>({x:.5,y:.5}));
 points[33]={x:.3,y:.4};points[263]={x:.7,y:.5};points[10]={x:.5,y:.2};points[152]={x:.5,y:.8};
 const [a,b,c,d,e,f]=faceCropTransform(points,640,480);
  const map=p=>[a*p.x*640+c*p.y*480+e,b*p.x*640+d*p.y*480+f];
  assert(Math.abs(map(points[33])[1]-map(points[263])[1])<1e-8);
  const scaled=faceCropTransform(points,1280,960);
  assert(Math.abs(scaled[0]*2-a)<1e-8,'crop is resolution invariant');
  assert(Math.abs(scaled[4]-e)<1e-8);
 points[33].x=NaN;assert.equal(faceCropTransform(points,640,480),null);
});

test('confirmed tongue extends fully, independent of classifier confidence',()=>{
 const signal=new TongueSignal();
 assert.equal(signal.update(.56,1000),0);
 assert.equal(signal.update(.56,1080),1);
 assert.equal(signal.update(.4,1160),1,'hysteresis must not shorten the tongue');
 assert.equal(signal.update(.34,1240),0);
});
