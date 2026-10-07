import test from 'node:test';
import assert from 'node:assert/strict';
import {AirSwipeDetector,openPalm} from '../air-swipe.js';
import {armDirections} from '../body-motion.js';
import {hand,motionFrame,bodyPose} from './motion-fixtures.mjs';

test('coordinate-only MediaPipe output drives arms and retains explicit confidence gates',()=>{
  const frame=bodyPose(['left','right']);
  assert.equal(frame.poseLandmarks[12].visibility,undefined);
  assert.deepEqual(Object.keys(armDirections(frame.poseLandmarks,frame.poseWorldLandmarks)),['L','R']);
  frame.poseLandmarks[14].presence=.2;
  assert.deepEqual(Object.keys(armDirections(frame.poseLandmarks,frame.poseWorldLandmarks)),['R']);
  frame.poseLandmarks[13].x=1.1;
  assert.deepEqual(armDirections(frame.poseLandmarks,frame.poseWorldLandmarks),{});
});

test('inferred 3D motion cannot lift the opposite arm against the observed image',()=>{
  for(const raised of ['right','left']){
    const frame=bodyPose([raised]),idle=raised==='right'?'R':'L';
    const expected=armDirections(frame.poseLandmarks,frame.poseWorldLandmarks)[idle];
    // Reproduce bilateral 3D lift while only one arm actually rises in the image.
    frame.poseWorldLandmarks=bodyPose(['right','left']).poseWorldLandmarks;
    const arms=armDirections(frame.poseLandmarks,frame.poseWorldLandmarks);
    assert.deepEqual(arms[idle],expected);
    assert(arms[idle].lower[1]<-.9);
  }
});

test('hidden arm confidence never suppresses or substitutes the visible arm',()=>{
  for(const hidden of [[11,13,15],[12,14,16]]){
    const frame=bodyPose(['right','left']);
    for(const points of [frame.poseLandmarks,frame.poseWorldLandmarks]){
      for(const p of points){p.visibility=.99;p.presence=.99;}
      for(const i of hidden)points[i].visibility=.71;
    }
    const arms=armDirections(frame.poseLandmarks,frame.poseWorldLandmarks);
    assert.deepEqual(Object.keys(arms),[hidden[0]===11?'L':'R']);
  }
});

test('image-plane directions account for camera aspect and retain depth',()=>{
  const frame=bodyPose();
  frame.poseLandmarks[14]={x:.18,y:.72,z:0};
  frame.poseWorldLandmarks[14].z=.1;
  const a=armDirections(frame.poseLandmarks,frame.poseWorldLandmarks,2).L.upper;
  assert(Math.abs(a[0]/a[1]+2)<1e-8);
  assert(a[2]<0);
  assert.deepEqual(armDirections(frame.poseLandmarks,frame.poseWorldLandmarks,NaN),{});
});

function hold(d,x=.3,time=0){
  for(let i=0;i<=9;i++)assert.equal(d.update(motionFrame({x}),time+i*80),0);
  return time+800;
}
function sweep(d,{start=.3,dx=.32,dy=0,time=800,step=80,closed=false}={}){
  return Array.from({length:5},(_,i)=>d.update(motionFrame({x:start+dx*i/4,y:.3+dy*i/4,closed}),time+i*step));
}
test('a lowered second hand does not prevent a deliberate raised-palm swipe',()=>{
  const d=new AirSwipeDetector();
  const frame=x=>{
    const f=motionFrame({x});f.poseLandmarks[16]={x,y:.4,z:0};f.poseLandmarks[15]={x:.8,y:.85,z:0};
    f.landmarks.push(hand(.8,.75));return f;
  };
  for(let time=0;time<=720;time+=80)d.update(frame(.3),time);
  assert.equal(d.state,'armed');
  const events=Array.from({length:5},(_,i)=>d.update(frame(.3+i*.08),800+i*80));
  assert.deepEqual(events.filter(Boolean),[1]);
});
test('a confidently detected small open palm remains eligible at full-body distance',()=>{
  const small=hand().map(p=>({...p,x:.3+(p.x-.3)*.15,y:.3+(p.y-.3)*.15}));
  assert(openPalm(small),'small palm was discarded after successful hand detection');
});
test('body-wrist identity survives handedness-label flips and reordered resting hands',()=>{
  const d=new AirSwipeDetector();
  for(let time=0;time<=800;time+=80){
    const frame=motionFrame();frame.landmarks.push(hand(.8,.75));
    frame.poseLandmarks[15]={x:.8,y:.85,z:0};
    frame.handedness=[[{categoryName:time%160?'Right':'Left'}],[{categoryName:'Left'}]];
    if(time%160){frame.landmarks.reverse();frame.handedness.reverse();}
    d.update(frame,time);
  }
  assert.equal(d.state,'armed');
});
test('open-palm detection rejects fists and malformed points',()=>{
  assert(openPalm(hand()));assert.equal(openPalm(hand(.3,.3,true)),null);
  assert.equal(openPalm([]),null);const invalid=hand();invalid[0].x=NaN;
  assert.equal(openPalm(invalid),null);
});
test('normal swipes and raised-arm movement never switch without the hold',()=>{
  assert(sweep(new AirSwipeDetector()).every(v=>v===0));
  assert(sweep(new AirSwipeDetector(),{dx:0,dy:-.25}).every(v=>v===0));
});
test('steady raised palm arms; mirrored swipe switches exactly once',()=>{
  for(const [x,dx,wanted] of [[.3,.32,1],[.7,-.32,-1]]){
    const d=new AirSwipeDetector();hold(d,x);assert.equal(d.state,'armed');
    assert.deepEqual(sweep(d,{start:x,dx}),[0,0,0,wanted,0]);
  }
});
test('stationary noise, short, slow, diagonal and closed-palm motion do not swap',()=>{
  for(const options of [{dx:.04},{dx:.15},{step:400},{dy:.3},{dx:0,dy:.3},{closed:true}]){
    const d=new AirSwipeDetector();hold(d);
    assert(sweep(d,options).every(v=>v===0),JSON.stringify(options));
  }
});
test('two raised palms, hands below shoulders and unmatched hands cannot arm',()=>{
  for(const options of [{both:true},{y:.65},{noPose:true},{unmatched:true}]){
    const d=new AirSwipeDetector();
    for(let time=0;time<1200;time+=80)d.update(motionFrame(options),time);
    assert.notEqual(d.state,'armed');
  }
});
test('lowering hand cancels readiness; reacquiring requires a new hold',()=>{
  const d=new AirSwipeDetector();hold(d);
  d.update(motionFrame({closed:true}),800);assert.equal(d.state,'idle');
  assert(sweep(d,{time:880}).every(v=>v===0));
});
test('recoil and continued hold cannot cause repeated swaps; release rearms',()=>{
  const d=new AirSwipeDetector();hold(d);sweep(d);
  assert(sweep(d,{start:.62,dx:-.32,time:1200}).every(v=>v===0));
  for(let time=1600;time<4000;time+=80)assert.equal(d.update(motionFrame(),time),0);
  assert.notEqual(d.state,'armed');
  d.update({landmarks:[]},4000);d.update({landmarks:[]},4300);
  hold(d,.3,4400);assert.equal(sweep(d,{time:5200}).filter(Boolean).length,1);
});
test('readiness expires and tracking gaps or identity changes cancel it',()=>{
  const expired=new AirSwipeDetector();hold(expired);
  for(let time=800;time<3000;time+=80)expired.update(motionFrame(),time);
  assert.notEqual(expired.state,'armed');
  for(const gap of [true,false]){
    const d=new AirSwipeDetector();hold(d);
    const frame=motionFrame(gap?{}:{wrist:15});
    d.update(frame,gap?1100:800);assert.notEqual(d.state,'armed');
  }
});
test('reset and out-of-order timestamps cannot trigger a stale swipe',()=>{
  const d=new AirSwipeDetector();hold(d);d.reset();
  assert(sweep(d).every(v=>v===0));assert.equal(d.update(motionFrame({x:.9}),700),0);
});
test('a deliberate hold arms in 400ms and tolerates small hand tremor',()=>{
  const d=new AirSwipeDetector();
  for(let time=0;time<=400;time+=80)d.update(motionFrame({x:time%160?.35:.3}),time);
  assert.equal(d.state,'armed');
});
test('one missed hand or body detection preserves a swipe in either direction',()=>{
  for(const missing of [{landmarks:[]},motionFrame({noPose:true})])for(const [start,dx,wanted] of [[.3,.32,1],[.7,-.32,-1]]){
    const d=new AirSwipeDetector();hold(d,start);
    const events=[];
    for(let i=0;i<5;i++)events.push(d.update(i===1?missing:motionFrame({x:start+dx*i/4}),800+i*80));
    assert.deepEqual(events.filter(Boolean),[wanted]);
  }
});
test('missing detections do not count toward completing the hold',()=>{
  const d=new AirSwipeDetector();
  for(const time of [0,80,160])d.update(motionFrame(),time);
  d.update({landmarks:[]},240);
  for(const time of [320,400,480])d.update(motionFrame(),time);
  assert.equal(d.state,'holding');
  d.update(motionFrame(),560);assert.equal(d.state,'armed');
});
test('reacquisition permits real travel during a short gap but rejects a teleport',()=>{
  for(const [end,wanted] of [[.6,1],[.9,0]]){
    const d=new AirSwipeDetector();hold(d);
    d.update(motionFrame(),800);d.update({landmarks:[]},880);
    assert.equal(d.update(motionFrame({x:end}),960),wanted);
  }
});
test('long tracking loss, another person, two palms and deliberate lowering cancel readiness',()=>{
  for(const frame of [{landmarks:[]},motionFrame({both:true}),motionFrame({y:.65}),{...motionFrame(),personId:42}]){
    const d=new AirSwipeDetector();hold(d);
    d.update(frame,800);d.update(frame,1040);
    assert.notEqual(d.state,'armed');
  }
});
test('an empty frame cannot preserve readiness after its deadline',()=>{
  const d=new AirSwipeDetector();hold(d);
  for(let time=800;time<=2320;time+=80)d.update(motionFrame(),time);
  d.update({landmarks:[]},2480);assert.notEqual(d.state,'armed');
});
test('a shorter or gently angled deliberate swipe works without allowing a short flick',()=>{
  for(const [dx,dy,wanted] of [[.19,0,1],[.24,.11,1],[.12,0,0]]){
    const d=new AirSwipeDetector();hold(d);
    assert.equal(sweep(d,{dx,dy}).filter(Boolean).length,wanted);
  }
});
test('arm directions mirror both sides, keep upper/lower independent, and reject occlusion',()=>{
  const frame=bodyPose(['right']);
  const arms=armDirections(frame.poseLandmarks,frame.poseWorldLandmarks);
  assert(arms.L.lower[1]>.9);assert(arms.R.lower[1]<-.9);
  assert(arms.L.upper[0]>.9);
  frame.poseLandmarks[14].visibility=.1;
  assert.equal(armDirections(frame.poseLandmarks,frame.poseWorldLandmarks).L,undefined);
  frame.poseWorldLandmarks[13].z=NaN;
  assert.deepEqual(armDirections(frame.poseLandmarks,frame.poseWorldLandmarks),{});
});
