import test from 'node:test';
import assert from 'node:assert/strict';
import {AirSwipeTracker} from '../air-swipe.js';

test('a previous native visitor cannot trigger fingers or swipes but releases the capture slot',()=>{
 const Original=globalThis.Worker;let worker,updates=0,motion=0,swipes=0;
 globalThis.Worker=class{constructor(){worker=this;}postMessage(){}terminate(){}};
 const tracker=new AirSwipeTracker(()=>swipes++,()=>{},()=>motion++,{nativeBody:true,acceptResult:r=>r.personId===2});
 try{
  worker.onmessage({data:{type:'ready'}});tracker.busy=true;
  tracker.detector.update=()=>{updates++;return 1;};
  worker.onmessage({data:{type:'result',time:performance.now(),result:{personId:1}}});
  assert.equal(tracker.busy,false);assert.equal(updates+motion+swipes,0);
  worker.onmessage({data:{type:'result',time:performance.now(),result:{personId:2}}});
  assert.equal(updates,1);assert.equal(motion,1);assert.equal(swipes,1);
 }finally{tracker.stop();globalThis.Worker=Original;}
});
