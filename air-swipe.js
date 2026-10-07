import {raisedPalmBodySide,visible} from './body-motion.js';
import {trackedFingerCurls} from './finger-motion.js';
const distance=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y);
const HOLD_MS=400,TRACKING_GRACE_MS=240,SWIPE_WINDOW_MS=850;

export function openPalm(landmarks){
  if(landmarks?.length!==21||landmarks.some(p=>!Number.isFinite(p.x)||!Number.isFinite(p.y)))return null;
  const wrist=landmarks[0];
  let extended=0;
  for(const base of [5,9,13,17]){
    const a=landmarks[base],b=landmarks[base+1],tip=landmarks[base+3];
    const dot=(a.x-b.x)*(tip.x-b.x)+(a.y-b.y)*(tip.y-b.y);
    if(distance(tip,wrist)>distance(b,wrist)*1.18&&dot<-.5*distance(a,b)*distance(tip,b))extended++;
  }
  if(extended<3||distance(landmarks[5],landmarks[17])<.0001)return null;
  const palm=[0,5,9,13,17].map(i=>landmarks[i]);
  // Mirror camera coordinates into the visitor's left/right view of the display.
  return {x:1-palm.reduce((sum,p)=>sum+p.x,0)/5,y:palm.reduce((sum,p)=>sum+p.y,0)/5};
}

export class AirSwipeDetector {
  constructor(){this.reset();}
  reset(){
    this.history=[];this.lastTime=-Infinity;this.cooldownUntil=0;
    this.latched=false;this.absentSince=null;this.still=null;this.identity=null;
    this.armedUntil=0;this.progress=0;this.state='idle';this.previousSeen=-Infinity;
    this.reason='waiting';
    this.missingSince=null;
  }
  update(result,time){
    if(!Number.isFinite(time)||time<=this.lastTime)return 0;
    this.lastTime=time;
    // Count eligible gestures, not every detected hand. A resting second hand
    // must not cancel the visitor's deliberately raised palm.
    const observations=(result?.landmarks||[]).map(hand=>({side:raisedPalmBodySide(hand,result.poseLandmarks),point:openPalm(hand)}));
    const candidates=observations.filter(c=>c.side&&c.point);
    const selected=candidates.length===1?candidates[0]:null,point=selected?.point;
    const person=String(result?.personId??'body');
    const activeSide=this.identity?.split(':').at(-1);
    const pose=result?.poseLandmarks,shoulder=pose?.[activeSide==='L'?12:11],wrist=pose?.[activeSide==='L'?16:15];
    const personChanged=this.identity&&this.identity!==person+':'+activeSide;
    const cancelled=personChanged||candidates.length>1||observations.some(o=>o.side===activeSide&&!o.point)||
      (activeSide&&visible(shoulder)&&visible(wrist)&&wrist.y>=shoulder.y+.04);
    this.reason=selected?'eligible':candidates.length>1?'multiple-raised-palms':'no-raised-palm';
    if(!point){
      this.absentSince??=time;
      if(time-this.absentSince>=220)this.latched=false;
      // Brief missing detections pause the hold and preserve an armed gesture.
      // Explicit release and identity changes still cancel immediately.
      if(!cancelled&&this.identity&&time-this.previousSeen<=TRACKING_GRACE_MS&&
         (!this.armedUntil||time<=this.armedUntil)){
        this.missingSince??=this.previousSeen;
        this.reason='tracking-gap';return 0;
      }
      this.history=[];this.still=null;this.identity=null;
      this.missingSince=null;
      this.armedUntil=0;this.progress=0;this.state='idle';
      return 0;
    }
    this.absentSince=null;
    const identity=person+':'+selected.side;
    if(time-this.previousSeen>TRACKING_GRACE_MS||(this.identity&&this.identity!==identity)){
      this.history=[];this.still=null;this.armedUntil=0;
    }else if(this.missingSince!==null&&this.still&&!this.armedUntil){
      this.still.time+=time-this.missingSince;
    }
    this.missingSince=null;
    this.previousSeen=time;
    this.identity=identity;
    if(this.latched){
      this.state='cooldown';this.progress=0;return 0;
    }
    if(time<this.cooldownUntil){this.history=[];this.state='cooldown';return 0;}
    if(!this.armedUntil){
      if(!this.still||distance(point,this.still)>.06)this.still={...point,time};
      this.progress=Math.min(1,(time-this.still.time)/HOLD_MS);this.state='holding';
      if(this.progress<1)return 0;
      this.armedUntil=time+2000;this.history=[];
    }
    if(time>this.armedUntil){
      this.armedUntil=0;this.latched=true;this.progress=0;this.state='idle';return 0;
    }
    this.state='armed';this.progress=1;
    const previous=this.history.at(-1);
    // A reacquired hand can travel farther between samples; reject teleports.
    if(previous&&distance(point,previous)>Math.min(.36,Math.max(.22,.06+(time-previous.time)*.002))){
      this.history=[];this.still=null;this.armedUntil=0;this.progress=0;this.state='idle';return 0;
    }
    this.history.push({...point,time});
    this.history=this.history.filter(p=>time-p.time<=SWIPE_WINDOW_MS);
    if(this.history.length<3)return 0;
    const start=this.history[0],dx=point.x-start.x,dy=point.y-start.y;
    const elapsed=time-start.time;
    const travel=this.history.slice(1).reduce((sum,p,i)=>sum+Math.abs(p.x-this.history[i].x),0);
    const ys=this.history.map(p=>p.y);
    if(elapsed<120||Math.abs(dx)<.18||Math.abs(dx)<Math.abs(dy)*2||
       Math.max(...ys)-Math.min(...ys)>.14||Math.abs(dx)<travel*.8)return 0;
    this.history=[];this.latched=true;this.still={...point,time};this.cooldownUntil=time+1000;
    this.armedUntil=0;this.progress=0;this.state='cooldown';
    return dx<0?1:-1;
  }
}

export class AirSwipeTracker {
  constructor(onSwipe,onError,onMotion=()=>{},options={}){
    this.nativeBody=!!options.nativeBody;
    this.acceptResult=options.acceptResult||(()=>true);
    this.detector=new AirSwipeDetector();this.onSwipe=onSwipe;this.onError=onError;
    this.onMotion=onMotion;this.lastResultTime=0;this.lastPoseTime=-Infinity;
    this.lastAcceptedTime=-Infinity;this.latencyMs=0;this.droppedFrames=0;
    this.ready=false;this.stopped=false;this.busy=false;this.frames=0;this.poseFrames=0;
    this.lastFrame=-Infinity;this.lastVideoTime=-1;
    this.handDiagnostics={status:'starting',lateFrames:0,lateCaptureFrames:0,missedFrames:0,unmatchedFrames:0,identityDrops:0};
    try{
      this.worker=new Worker(new URL(this.nativeBody?'./finger-tracking-worker.js':'./hand-tracking-worker.js',import.meta.url));
      this.worker.onmessage=({data})=>{
        if(this.stopped)return;
        if(data.type==='ready'){clearTimeout(this.watchdog);this.ready=true;this.handDiagnostics.status='waiting';return;}
        if(data.type==='error'){this.fail(new Error(data.message));return;}
        if(data.type!=='result'&&data.type!=='pose')return;
        const now=performance.now();
        if(data.type==='pose'){
          if(data.complete){clearTimeout(this.watchdog);this.busy=false;}
          if(Number.isFinite(data.time)&&data.time>this.lastPoseTime&&data.time<=now&&now-data.time<=250){
            this.lastPoseTime=data.time;this.latencyMs=now-data.time;
            this.poseFrames++;
            this.onMotion(data.result,this.detector,data.time);
          }
          return;
        }
        if(!data.independentHands){clearTimeout(this.watchdog);this.busy=false;}
        if(!this.acceptResult(data.result)){this.handDiagnostics.identityDrops++;return;}
        this.frames++;
        const age=now-data.time;
        Object.assign(this.handDiagnostics,data.result.handDiagnostics,{ageMs:age});
        if(!Number.isFinite(data.time)||data.time<=this.lastAcceptedTime||data.time>now||now-data.time>250){
          this.handDiagnostics.status=age>250?'late':'out-of-order';
          if(age>250)this.handDiagnostics.lateFrames++;
          this.droppedFrames++;return;
        }
        const detected=data.result.landmarks?.length||0,matched=Object.keys(trackedFingerCurls(data.result)).length;
        const d=this.handDiagnostics;
        d.matched=matched;
        d.status=matched?'tracking':d.mode==='no-body'?'no-body':detected?'wrist-unmatched':
          d.detected>0?'crop-rejected':d.wristHints===0?'no-wrist':'not-detected';
        if(!detected)d.missedFrames++;
        if(detected&&!matched)d.unmatchedFrames++;
        this.lastAcceptedTime=data.time;this.lastResultTime=data.time;
        const direction=this.detector.update(data.result,data.time);
        this.onMotion(data.result,this.detector,data.time);
        if(direction)this.onSwipe(direction);
      };
      this.worker.onerror=event=>{event.preventDefault();this.fail(new Error(event.message||'Hand tracking worker failed'));};
      this.watchdog=setTimeout(()=>this.fail(new Error('Hand tracking startup timed out')),30000);
      this.worker.postMessage({type:'init'});
    }catch(error){this.fail(error);}
  }
  sample(video,time,body){
    if(this.stopped||!this.ready||this.busy||video.readyState<2||time-this.lastFrame<33||video.currentTime===this.lastVideoTime)return;
    this.busy=true;this.lastFrame=time;this.lastVideoTime=video.currentTime;
    // A single transferable frame in flight bounds memory and CPU use on mini PCs.
    this.watchdog=setTimeout(()=>this.fail(new Error('Hand tracking frame timed out')),10000);
    const width=Math.min(960,video.videoWidth);
    createImageBitmap(video,{resizeWidth:width,resizeHeight:Math.round(width*video.videoHeight/video.videoWidth)}).then(frame=>{
      if(this.stopped){frame.close();return;}
      if(performance.now()-time>250){
        frame.close();this.busy=false;clearTimeout(this.watchdog);this.droppedFrames++;
        this.handDiagnostics.status='late-capture';this.handDiagnostics.lateCaptureFrames++;return;
      }
      try{this.worker.postMessage({type:'frame',frame,time,body:this.nativeBody?body:undefined},[frame]);}
      catch(error){frame.close();this.fail(error);}
    }).catch(error=>this.fail(error));
  }
  fail(error){if(this.stopped)return;this.stop();this.onError(error);}
  stop(){
    this.stopped=true;this.ready=false;this.busy=false;
    this.handDiagnostics.status='stopped';
    clearTimeout(this.watchdog);this.worker?.terminate();this.detector.reset();
  }
}
