import {TongueSignal,faceCropTransform} from './tongue-signal.js';

export class TongueTracker {
  constructor(onError){
    this.signal=new TongueSignal();this.ready=false;this.stopped=false;this.busy=false;
    this.lastSample=-Infinity;this.lastVideoTime=-1;this.lostAt=-Infinity;this.frames=0;this.raw=0;this.latencyMs=0;this.onError=onError;
    this.inferenceMs=0;this.cropAgeMs=0;this.droppedFrames=0;
    try{
      this.worker=new Worker(new URL('./tongue-tracking-worker.js',import.meta.url),{type:'module'});
      this.worker.onmessage=({data})=>{
        if(this.stopped)return;
        if(data.type==='error'){this.fail(new Error(data.message));return;}
        clearTimeout(this.watchdog);
        if(data.type==='ready'){this.ready=true;return;}
        if(data.type!=='result')return;
        this.busy=false;const now=performance.now();
        if(!Number.isFinite(data.time)||data.time<=this.lostAt||data.time>now||now-data.time>300){this.droppedFrames++;return;}
        this.raw=data.score;this.latencyMs=now-data.time;this.frames++;
        this.inferenceMs=data.inferenceMs??0;this.cropAgeMs=data.cropAgeMs??0;
        this.signal.update(data.score,data.time);
      };
      this.worker.onerror=event=>{event.preventDefault();this.fail(new Error(event.message||'Tongue tracker failed'));};
      this.watchdog=setTimeout(()=>this.fail(new Error('Tongue tracker startup timed out')),30000);
      this.worker.postMessage({type:'init'});
    }catch(error){this.fail(error);}
  }
  sampleLatest(video,landmarks,landmarkTime,time,pixelTime=time){
    if(!landmarks){this.sample(video,null,time);return;}
    // Bound crop reuse by the face tracker's acceptance window. In particular,
    // a 100-180ms face result must not force analysis of its older camera frame.
    const age=time-landmarkTime;
    if(!Number.isFinite(age)||age<0||age>180)return;
    if(!Number.isFinite(pixelTime)||pixelTime>time||time-pixelTime>180)return;
    this.sample(video,landmarks,pixelTime,age);
  }
  sample(video,landmarks,time,cropAgeMs=0){
    if(!landmarks){this.lostAt=time;this.signal.reset();return;}
    if(this.stopped||!this.ready||this.busy||time-this.lastSample<33||video.readyState<2||video.currentTime===this.lastVideoTime)return;
    if(!faceCropTransform(landmarks,video.videoWidth,video.videoHeight)){this.lostAt=time;this.signal.reset();return;}
    this.busy=true;this.lastSample=time;this.lastVideoTime=video.currentTime;
    this.watchdog=setTimeout(()=>this.fail(new Error('Tongue tracking frame timed out')),10000);
    createImageBitmap(video).then(frame=>{
      if(this.stopped){frame.close();return;}
      if(time<=this.lostAt||performance.now()-time>180){frame.close();this.busy=false;clearTimeout(this.watchdog);this.droppedFrames++;return;}
      try{this.worker.postMessage({type:'frame',frame,landmarks,time,cropAgeMs},[frame]);}
      catch(error){frame.close();this.fail(error);}
    }).catch(error=>this.fail(error));
  }
  sampleFrame(frame,landmarks,time,videoTime){
    if(!landmarks){frame.close();this.lostAt=time;this.signal.reset();return;}
    if(this.stopped||!this.ready||this.busy||time-this.lastSample<33||performance.now()-time>180||
      (Number.isFinite(videoTime)&&videoTime===this.lastVideoTime)){frame.close();return;}
    if(!faceCropTransform(landmarks,frame.width,frame.height)){frame.close();this.lostAt=time;this.signal.reset();return;}
    this.busy=true;this.lastSample=time;
    if(Number.isFinite(videoTime))this.lastVideoTime=videoTime;
    this.watchdog=setTimeout(()=>this.fail(new Error('Tongue tracking frame timed out')),10000);
    try{this.worker.postMessage({type:'frame',frame,landmarks,time},[frame]);}
    catch(error){frame.close();this.fail(error);}
  }
  value(time){return this.signal.current(time);}
  fail(error){if(this.stopped)return;this.stop();this.onError(error);}
  stop(){this.stopped=true;this.ready=false;this.busy=false;clearTimeout(this.watchdog);this.worker?.terminate();this.signal.reset();}
}
