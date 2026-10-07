import {brandAlienPhoto} from './photo-render.js';

export class PhotoBooth {
  constructor({demo=false,state,capture,captureReady=()=>true,onStatus=()=>{},connection=null}){
    this.demo=demo;this.state=state;this.capture=capture;this.captureReady=captureReady;this.onStatus=onStatus;this.connection=connection;this.locked=false;
    this.overlay=document.createElement('div');this.overlay.hidden=true;this.overlay.setAttribute('role','status');
    Object.assign(this.overlay.style,{position:'fixed',inset:'auto 0 8%',zIndex:'40',textAlign:'center',pointerEvents:'none',color:'#fff',fontFamily:'Arial,sans-serif',textShadow:'0 2px 8px #000'});
    this.digit=document.createElement('div');Object.assign(this.digit.style,{fontSize:'96px',fontWeight:'800',lineHeight:'1.1',height:'106px'});
    this.label=document.createElement('div');this.label.style.fontSize='22px';
    this.overlay.append(this.digit,this.label);document.body.append(this.overlay);this.loop();
  }
  async request(action,data,job){
    const cloud=this.connection?.mode==='cloud';
    const endpoint=cloud?`/api/photos?action=${action}&room=${this.connection.room}`:`/api/photo-operator/${action}`;
    const response=await fetch(endpoint,{method:'POST',
      headers:{'X-Face-Avatar':cloud?'photo':'photo-operator',...(cloud?{Authorization:`Bearer ${this.connection.owner}`,'X-Photo-Instance':this.connection.instance}:{ }),...(job?{'X-Photo-Job':job,'Content-Type':'image/jpeg'}:{'Content-Type':'application/json'})},
      body:job?data:JSON.stringify({...data,...(cloud?{instance:this.connection.instance}:{})}),signal:AbortSignal.timeout(job?15000:5000)});
    if(!response.ok)throw new Error(`Photo service: ${response.status}`);return response.json();
  }
  async loop(){
    try{
      const state=this.state(),command=await this.request('heartbeat',{...state,demo:this.demo});
      if(command.demo!==this.demo)throw new Error('Photo test mode does not match the installation');
      this.locked=command.state!=='idle';this.overlay.hidden=command.state!=='countdown';
      this.onStatus({online:true,ready:state.ready,busy:this.locked});
      this.label.textContent='Lower your phone. Look at the camera.';
      this.digit.textContent=String(Math.max(1,Math.ceil(command.remaining||0)));
      if(command.state==='processing'&&this.job!==command.job){this.job=command.job;void this.makePhoto(command.job,state.person,state.character);}
    }catch(error){this.overlay.hidden=true;this.onStatus({online:false});}
    this.timer=setTimeout(()=>this.loop(),this.connection?.mode==='cloud'?500:200);
  }
  async makePhoto(job,person,character){
    try{
      const valid=()=>{const s=this.state();return s.ready&&s.people===1&&s.person===person&&s.character===character;};
      if(!valid())throw new Error('Visitor moved away');
      // Brief inference gaps may pause the shutter, but never permit an old frame.
      const deadline=performance.now()+1000;
      while(!this.captureReady()){
        if(performance.now()>deadline||!valid())throw new Error('Face tracking is unavailable');
        await new Promise(resolve=>setTimeout(resolve,30));
      }
      if(!valid())throw new Error('Visitor moved away');
      const source=this.capture();let frame=source.composite;
      if(this.demo){
        frame=document.createElement('canvas');frame.width=1200;frame.height=796;
        const ctx=frame.getContext('2d');ctx.fillStyle='#071b20';ctx.fillRect(0,0,1200,796);
        ctx.drawImage(source.alien,600,0,600,780);ctx.fillStyle='#d8f660';ctx.font='bold 38px Arial';
        ctx.fillText('SAMPLE',60,360);ctx.font='24px Arial';ctx.fillText('No visitor captured',60,410);
      }
      if(!frame)throw new Error('AR camera frame is unavailable');
      const photo=brandAlienPhoto(frame,source.name);
      const encode=quality=>new Promise((resolve,reject)=>photo.toBlob(b=>b?resolve(b):reject(new Error('Photo encoding failed')),'image/jpeg',quality));
      let image=await encode(.92);
      if(this.connection?.mode==='cloud'){
        for(const quality of [.82,.72,.62,.52]){if(image.size<=700*1024)break;image=await encode(quality);}
        if(image.size>700*1024)throw new Error('Photo is too large. Please try again.');
      }
      if(!valid())throw new Error('Visitor moved away');
      await this.request('complete',image,job);
    }catch(error){await this.request('fail',{job}).catch(()=>{});console.warn('Photo capture:',error.message);}
  }
}
