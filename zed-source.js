import {zedMotion} from './zed-motion.js';

async function serviceError(response,fallback){
  try{return new Error((await response.json()).error||fallback);}
  catch{return new Error(fallback);}
}

export class ZedSource {
  constructor(onMotion,onError){
    this.onMotion=onMotion;this.onError=onError;this.stopped=false;
    this.controller=new AbortController();this.sequence=-1;this.frames=0;this.droppedFrames=0;
    this.capturedAt=-Infinity;this.body=null;this.personId=null;this.session=null;
    this.canvas=document.createElement('canvas');this.canvas.width=960;this.canvas.height=540;
    this.context=this.canvas.getContext('2d');this.stream=this.canvas.captureStream(0);
  }
  async start(){
    try{
      const response=await fetch('/api/zed/start',{method:'POST',headers:{'X-Face-Avatar':'zed'},signal:this.controller.signal});
      if(!response.ok)throw await serviceError(response,'Native ZED service unavailable. Launch with --tracking zed on the Orin.');
      const deadline=performance.now()+60000;
      while(!this.stopped&&this.frames===0){
        await this.read();
        if(performance.now()>deadline)throw new Error('ZED startup timed out. Check the native SDK/camera, then retry.');
        if(!this.frames)await new Promise(resolve=>setTimeout(resolve,50));
      }
      if(this.stopped)throw new Error('ZED capture stopped');
      this.loop();return this.stream;
    }catch(error){this.stop();throw error;}
  }
  async read(){
    const start=performance.now();
    const response=await fetch('/api/zed/frame',{cache:'no-store',signal:AbortSignal.any([this.controller.signal,AbortSignal.timeout(5000)])});
    if(response.status===204)return;
    if(!response.ok)throw await serviceError(response,'ZED capture failed. Check the native installation log.');
    const packet=JSON.parse(response.headers.get('X-Zed-Sample'));
    if(!packet||!Number.isSafeInteger(packet.sequence)||packet.sequence<0||typeof packet.session!=='string'||!Number.isFinite(packet.ageMs)||packet.ageMs<0)throw new Error('Invalid ZED sample');
    if(packet.session===this.session&&packet.sequence<=this.sequence){await response.body?.cancel();return;}
    if(packet.ageMs>250){this.droppedFrames++;await response.body?.cancel();return;}
    const body=zedMotion(packet),blob=await response.blob();
    const frame=await createImageBitmap(blob);
    try{
      if(this.stopped)return;
      // Conservative clock bridge: native sample age plus the entire round trip
      // and decode. Never relabel delayed native frames as newly captured.
      const now=performance.now(),age=packet.ageMs+now-start;
      if(age>250){this.droppedFrames++;return;}
      this.latencyMs=age;this.capturedAt=now-age;
      const changed=this.session!==packet.session||this.personId!==body.personId;
      this.sequence=packet.sequence;this.session=packet.session;this.personId=body.personId;this.body=body;
      if(this.canvas.width!==frame.width||this.canvas.height!==frame.height){this.canvas.width=frame.width;this.canvas.height=frame.height;}
      this.context.drawImage(frame,0,0);this.stream.getVideoTracks()[0].requestFrame();
      this.frames++;this.lastFrameAt=now;this.onMotion(body,this.capturedAt,changed);
    }finally{frame.close();}
  }
  async loop(){
    try{
      while(!this.stopped){
        await this.read();
        if(performance.now()-this.lastFrameAt>5000)throw new Error('ZED frames stopped arriving');
        await new Promise(resolve=>setTimeout(resolve,8));
      }
    }catch(error){if(!this.stopped){this.stop();this.onError(error);}}
  }
  stop(){
    if(this.stopped)return;
    this.stopped=true;this.controller.abort();this.stream.getTracks().forEach(track=>track.stop());
    this.body=null;
    fetch('/api/zed/stop',{method:'POST',headers:{'X-Face-Avatar':'zed'},keepalive:true}).catch(()=>{});
  }
}
