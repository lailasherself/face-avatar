import test from 'node:test';
import assert from 'node:assert/strict';
import {FaceTracker} from '../face-tracking.js';

test('face worker waits for initialization, bounds captures, and transfers frame ownership',async()=>{
 const Original=globalThis.Worker,bitmap=globalThis.createImageBitmap;let worker,closed=0;
 globalThis.Worker=class{constructor(){worker=this;this.messages=[];}postMessage(m){this.messages.push(m);}terminate(){}};
 globalThis.createImageBitmap=async()=>({close(){closed++;}});
 const tracker=new FaceTracker(),video={readyState:2,currentTime:0};
 try{
  assert.equal(tracker.detectForVideo(video,performance.now()),null);assert.equal(worker.messages.length,1);
  worker.onmessage({data:{type:'ready',delegate:'CPU'}});await tracker.ready;
  const time=performance.now();tracker.detectForVideo(video,time);await Promise.resolve();
  assert.equal(worker.messages.length,2);video.currentTime=1;tracker.detectForVideo(video,time+1);
  assert.equal(worker.messages.length,2,'one frame in flight');
  const frame={close(){closed++;}};
  worker.onmessage({data:{type:'result',time,result:{faceLandmarks:[]},frame}});
  const result=tracker.detectForVideo(video,performance.now());await Promise.resolve();
  assert.equal(result.frame,frame);assert.equal(result.captureTime,time);assert.equal(closed,0);
  result.frame.close();assert.equal(closed,1);
  worker.onmessage({data:{type:'result',time:performance.now()-500,result:{},frame:{close(){closed++;}}}});
  assert.equal(closed,2,'stale frames are closed instead of displayed');
  assert.equal(tracker.detectForVideo(video,performance.now()),null);
 }finally{tracker.close();globalThis.Worker=Original;globalThis.createImageBitmap=bitmap;}
});

test('closing a starting face worker rejects startup and releases late frames',async()=>{
 const Original=globalThis.Worker;let worker,closed=0;
 globalThis.Worker=class{constructor(){worker=this;}postMessage(){}terminate(){}};
 const tracker=new FaceTracker();const ready=assert.rejects(tracker.ready,/stopped/);
 try{tracker.close();await ready;worker.onmessage({data:{type:'result',frame:{close(){closed++;}}}});assert.equal(closed,1);}
 finally{globalThis.Worker=Original;}
});

test('native duplicate timestamps cannot reach MediaPipe and visitor changes discard old faces',async()=>{
 const Original=globalThis.Worker,bitmap=globalThis.createImageBitmap;let worker,closed=0;
 globalThis.Worker=class{constructor(){worker=this;this.messages=[];}postMessage(m){this.messages.push(m);}terminate(){}};
 globalThis.createImageBitmap=async()=>({close(){closed++;}});
 const tracker=new FaceTracker(),video={readyState:2,currentTime:0};
 try{
  worker.onmessage({data:{type:'ready'}});await tracker.ready;
  const time=performance.now();tracker.detectForVideo(video,time);await Promise.resolve();
  worker.onmessage({data:{type:'result',time,result:{},frame:{close(){closed++;}}}});
  tracker.invalidate(time+1);assert.equal(closed,1);
  video.currentTime=1;tracker.detectForVideo(video,time);await Promise.resolve();
  assert.equal(worker.messages.length,2,'a new canvas frame with the same native timestamp is skipped');
  worker.onmessage({data:{type:'result',time,result:{},frame:{close(){closed++;}}}});
  assert.equal(closed,2);assert.equal(tracker.latest,null);
 }finally{tracker.close();globalThis.Worker=Original;globalThis.createImageBitmap=bitmap;}
});
