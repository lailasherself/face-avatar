import test from 'node:test';
import assert from 'node:assert/strict';
import {handCrops,restoreHands} from '../hand-crops.js';
import {AirSwipeTracker} from '../air-swipe.js';

const point=(x,y)=>({x,y,z:0,visibility:1,presence:1});
const body=()=>{
  const poseLandmarks=Array.from({length:33},()=>({...point(0,0),visibility:0}));
  for(const [i,x,y] of [[11,.35,.3],[12,.65,.3],[13,.25,.5],[14,.75,.5],[15,.2,.7],[16,.8,.7]])poseLandmarks[i]=point(x,y);
  return {poseLandmarks};
};
test('wrist crops retain square pixels, stable side slots and frame bounds in both orientations',()=>{
  for(const [w,h] of [[960,540],[540,960]]){
    const b=body(),crops=handCrops(b,w,h);assert.equal(crops.length,2);
    assert.deepEqual(crops.map(c=>[c.side,c.tile]),[['L',0],['R',1]]);
    for(const c of crops){assert(c.x>=0&&c.y>=0&&c.x+c.size<=w&&c.y+c.size<=h);assert(c.size>=80);}
    b.poseLandmarks[16].visibility=0;
    assert.deepEqual(handCrops(b,w,h).map(c=>c.tile),[1]);
    b.poseLandmarks[15].x=NaN;assert.deepEqual(handCrops(b,w,h),[]);
  }
});
test('crop coordinates return to camera coordinates without swapping sides or distorting depth',()=>{
  const crops=handCrops(body(),960,540);
  const landmarks=crops.map(c=>Array.from({length:21},()=>({x:(c.tile+(c.wrist.x*960-c.x)/c.size)/2,y:(c.wrist.y*540-c.y)/c.size,z:.1})));
  const world=landmarks.map((p,i)=>({fixture:i}));
  const result=restoreHands({landmarks,worldLandmarks:world,handedness:[['right'],['left']]},crops);
  assert.equal(result.landmarks.length,2);
  for(let i=0;i<2;i++){
    assert(Math.abs(result.landmarks[i][0].x-crops[i].wrist.x)<1e-8);
    assert(Math.abs(result.landmarks[i][0].y-crops[i].wrist.y)<1e-8);
    assert(Math.abs(result.landmarks[i][0].z-.2*crops[i].size/960)<1e-8);
    assert.equal(result.worldLandmarks[i],world[i]);
  }
});
test('a hand spanning the tile boundary or duplicated in overlapping crops is rejected',()=>{
  const crops=handCrops(body(),960,540),points=Array.from({length:21},()=>({x:.25,y:.5,z:0}));
  points[9].x=.6;
  assert.equal(restoreHands({landmarks:[points]},crops).landmarks.length,0);
  const c={...crops[0],wrist:point(.5,.5),x:380,y:170,size:200};
  const copies=[0,1].map(tile=>Array.from({length:21},()=>({x:(tile+.5)/2,y:.5,z:0})));
  assert.equal(restoreHands({landmarks:copies},[{...c,tile:0},{...c,side:'R',tile:1}]).landmarks.length,1);
});
test('hand diagnostics separate missing detections, missing wrist matches and late inference',()=>{
  const Original=globalThis.Worker;let worker;
  globalThis.Worker=class{constructor(){worker=this;}postMessage(){}terminate(){}};
  const t=new AirSwipeTracker(()=>{},()=>{});
  try{
    worker.onmessage({data:{type:'ready'}});
    const send=(result,time=performance.now())=>worker.onmessage({data:{type:'result',time,result}});
    send({landmarks:[],handDiagnostics:{mode:'wrist-crops',wristHints:2,detected:0}});
    assert.equal(t.handDiagnostics.status,'not-detected');
    send({landmarks:[Array.from({length:21},()=>point(.5,.5))],poseLandmarks:[]});
    assert.equal(t.handDiagnostics.status,'wrist-unmatched');
    send({landmarks:[]},performance.now()-500);
    assert.equal(t.handDiagnostics.status,'late');assert.equal(t.handDiagnostics.lateFrames,1);
    assert.equal(t.handDiagnostics.missedFrames,1);assert.equal(t.handDiagnostics.unmatchedFrames,1);
  }finally{t.stop();globalThis.Worker=Original;}
});

test('capture preserves source detail and releases stale bitmaps without scheduling inference',async()=>{
  const Original=globalThis.Worker,bitmap=globalThis.createImageBitmap;let worker,options,closed=0;
  globalThis.Worker=class{constructor(){worker=this;this.frames=[];}postMessage(data){if(data.type==='frame')this.frames.push(data);}terminate(){}};
  globalThis.createImageBitmap=async(video,resize)=>{options=resize;return {close(){closed++;}};};
  const t=new AirSwipeTracker(()=>{},()=>{},()=>{},{nativeBody:true});
  try{
    worker.onmessage({data:{type:'ready'}});
    const video={readyState:2,currentTime:1,videoWidth:1920,videoHeight:1080};
    t.sample(video,performance.now()-500,body());await Promise.resolve();
    assert.deepEqual(options,{resizeWidth:960,resizeHeight:540});
    assert.equal(closed,1);assert.equal(worker.frames.length,0);assert.equal(t.busy,false);
    assert.equal(t.handDiagnostics.status,'late-capture');
    video.currentTime=2;video.videoWidth=640;video.videoHeight=480;
    t.sample(video,performance.now(),body());await Promise.resolve();
    assert.deepEqual(options,{resizeWidth:640,resizeHeight:480});
    assert.equal(worker.frames.length,1);assert.equal(worker.frames[0].body.poseLandmarks.length,33);
  }finally{t.stop();globalThis.Worker=Original;globalThis.createImageBitmap=bitmap;}
});
test('fingertips extrapolated just past the crop edge keep the hand; a real tile crossing does not',()=>{
  const crops=handCrops(body(),960,540);
  const inside=Array.from({length:21},()=>({x:.25,y:.5,z:0}));
  inside[12].y=1.05;inside[8].x=-.03;
  assert.equal(restoreHands({landmarks:[inside]},crops).landmarks.length,1);
  const crossing=Array.from({length:21},()=>({x:.25,y:.5,z:0}));
  crossing[12].x=.56;
  assert.equal(restoreHands({landmarks:[crossing]},crops).landmarks.length,0);
});
test('a close seated visitor with the elbow out of frame still gets a crop that contains the fingertips',()=>{
  // Shoulders span 41% of a 960x540 frame; wrist at (.80,.64), knuckles ~.06 above it, elbow below the frame.
  const b={poseLandmarks:Array.from({length:33},()=>({...point(0,0),visibility:0}))};
  for(const [i,x,y] of [[11,.55,.85],[12,.14,.82],[15,.80,.64],[17,.83,.49],[19,.74,.47],[21,.70,.56]])b.poseLandmarks[i]=point(x,y);
  const [crop]=handCrops(b,960,540);
  assert.equal(crop.side,'R');
  // Fingertips sit roughly 2.2x the wrist-to-knuckle distance beyond the wrist.
  const tip={x:(.80+(.74-.80)*2.2)*960,y:(.64+(.47-.64)*2.2)*540};
  assert(tip.y>=crop.y&&tip.y<=crop.y+crop.size,`fingertip y ${tip.y} outside crop ${crop.y}..${crop.y+crop.size}`);
  assert(tip.x>=crop.x&&tip.x<=crop.x+crop.size);
  // Without knuckles the old wrist-centred crop misses the same fingertips.
  for(const i of [17,19,21])b.poseLandmarks[i].visibility=0;
  const [legacy]=handCrops(b,960,540);
  assert(tip.y<legacy.y,'regression fixture no longer reproduces the spill');
});
