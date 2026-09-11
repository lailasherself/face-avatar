import test from 'node:test';
import assert from 'node:assert/strict';
import {TongueTracker} from '../tongue-tracking.js';

const landmarks=()=>{
 const points=Array.from({length:478},()=>({x:.5,y:.5}));
 points[33]={x:.3,y:.4};points[263]={x:.7,y:.4};
 points[10]={x:.5,y:.2};points[152]={x:.5,y:.8};return points;
};
function setup(t){
 let worker,closed=0,now=1000;
 t.mock.method(performance,'now',()=>now);
 const originalWorker=globalThis.Worker,originalBitmap=globalThis.createImageBitmap;
 globalThis.Worker=class{constructor(){worker=this;this.messages=[];}postMessage(m){this.messages.push(m);}terminate(){}};
 globalThis.createImageBitmap=async()=>({close(){closed++;}});
 const tracker=new TongueTracker(error=>{throw error;});
 worker.onmessage({data:{type:'ready'}});
 t.after(()=>{tracker.stop();globalThis.Worker=originalWorker;globalThis.createImageBitmap=originalBitmap;});
 return {tracker,worker,video:{readyState:2,currentTime:1,videoWidth:640,videoHeight:480},
  setTime:value=>now=value,closed:()=>closed};
}

test('slow face landmarks locate a fresh tongue frame without inheriting face latency',async t=>{
 const {tracker,worker,video}=setup(t);
 tracker.sampleLatest(video,landmarks(),860,1000);await Promise.resolve();
 const message=worker.messages.at(-1);
 assert.equal(message.type,'frame');assert.equal(message.time,1000);
 assert.equal(message.cropAgeMs,140,'crop age is recorded separately from pixel age');
 video.currentTime=2;tracker.sampleLatest(video,landmarks(),860,1000);
 assert.equal(worker.messages.length,2,'no queued inference while busy');
 worker.onmessage({data:{type:'result',time:1000,score:.9,inferenceMs:12,cropAgeMs:140}});
 assert.equal(tracker.value(1000),1);assert.equal(tracker.inferenceMs,12);
 assert.equal(tracker.latencyMs,0);assert.equal(tracker.cropAgeMs,140);
});

test('expired and future crops never schedule fresh-image inference',async t=>{
 const {tracker,worker,video}=setup(t);
 for(const time of [819,1001,NaN])tracker.sampleLatest(video,landmarks(),time,1000);
 await Promise.resolve();assert.equal(worker.messages.length,1);
});

test('face loss cancels a pending bitmap and cannot revive the tongue',async t=>{
 const {tracker,worker,video,setTime,closed}=setup(t);
 tracker.sampleLatest(video,landmarks(),990,1000);
 setTime(1010);tracker.sampleLatest(video,null,1010,1010);
 await Promise.resolve();assert.equal(closed(),1);assert.equal(tracker.busy,false);
 assert.equal(worker.messages.length,1);
 worker.onmessage({data:{type:'result',time:1000,score:.99}});
 assert.equal(tracker.value(1010),0);
});

test('slow bitmap creation is discarded and the next camera frame can proceed',async t=>{
 const {tracker,worker,video,setTime,closed}=setup(t);
 tracker.sampleLatest(video,landmarks(),990,1000);setTime(1200);
 await Promise.resolve();assert.equal(closed(),1);assert.equal(tracker.busy,false);
 assert.equal(tracker.droppedFrames,1);assert.equal(worker.messages.length,1);
 video.currentTime=2;tracker.sampleLatest(video,landmarks(),1190,1200);
 await Promise.resolve();assert.equal(worker.messages.at(-1).time,1200);
});
