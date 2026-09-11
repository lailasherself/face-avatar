export class FaceTracker {
  constructor(){
    this.busy=false;this.stopped=false;this.initialized=false;this.latest=null;this.lastVideoTime=-1;this.lastCaptureTime=-Infinity;
    this.frames=0;this.latencyMs=0;this.error=null;
    this.discardBefore=-Infinity;
    this.ready=new Promise((resolve,reject)=>{this.resolve=resolve;this.reject=reject;});
    try{
      this.worker=new Worker(new URL('./face-tracking-worker.js',import.meta.url));
      this.worker.onmessage=({data})=>{
        if(this.stopped){data.frame?.close();return;}
        clearTimeout(this.watchdog);
        if(data.type==='ready'){this.initialized=true;this.delegate=data.delegate;this.resolve();return;}
        if(data.type==='error'){this.fail(new Error(data.message));return;}
        if(data.type!=='result')return;
        this.busy=false;this.frames++;this.latencyMs=performance.now()-data.time;
        if(!Number.isFinite(data.time)||data.time<this.discardBefore||this.latencyMs<0||this.latencyMs>180){data.frame?.close();return;}
        this.latest?.frame?.close();this.latest={...data.result,frame:data.frame,captureTime:data.time,videoTime:data.videoTime};
      };
      this.worker.onerror=e=>{e.preventDefault();this.fail(new Error(e.message||'Face worker failed'));};
      this.watchdog=setTimeout(()=>this.fail(new Error('Face tracker startup timed out')),30000);
      this.worker.postMessage({type:'init'});
    }catch(error){this.fail(error);}
  }
  detectForVideo(video,time){
    if(this.error)throw this.error;
    if(this.stopped||!this.initialized)return null;
    if(!this.busy&&video.readyState>=2&&video.currentTime!==this.lastVideoTime&&Number.isFinite(time)&&time>this.lastCaptureTime){
      this.busy=true;this.lastVideoTime=video.currentTime;this.lastCaptureTime=time;
      this.watchdog=setTimeout(()=>this.fail(new Error('Face tracking frame timed out')),10000);
      createImageBitmap(video).then(frame=>{
        if(this.stopped){frame.close();return;}
        try{this.worker.postMessage({type:'frame',frame,time,videoTime:this.lastVideoTime},[frame]);}
        catch(error){frame.close();this.fail(error);}
      }).catch(error=>this.fail(error));
    }
    const result=this.latest;this.latest=null;
    if(result&&performance.now()-result.captureTime>180){result.frame?.close();return null;}
    return result;
  }
  fail(error){this.error=error;this.reject(error);this.close();}
  invalidate(time){this.discardBefore=time;this.latest?.frame?.close();this.latest=null;}
  close(){
    this.stopped=true;clearTimeout(this.watchdog);this.worker?.terminate();
    this.latest?.frame?.close();this.latest=null;
    this.reject(new Error('Face tracking stopped'));
  }
}
