export async function photoConfiguration(){
  const local=['localhost','127.0.0.1'].includes(location.hostname);
  try{
    const response=await fetch(local?'/api/photo-config':'/api/photos?action=config',{cache:'no-store',signal:AbortSignal.timeout(5000)});
    if(!response.ok)return {enabled:false};
    const config=await response.json();
    if(!config.enabled||config.mode!=='cloud')return config;
    const fragment=new URLSearchParams(location.hash.slice(1));
    if(fragment.has('photo-owner')){
      const owner=fragment.get('photo-owner');
      if(/^[\w-]{43}$/.test(owner))localStorage.setItem('alien-photo-owner',owner);
      fragment.delete('photo-owner');history.replaceState(null,'',location.pathname+location.search+(fragment.size?'#'+fragment:''));
    }
    const owner=localStorage.getItem('alien-photo-owner');
    const bytes=crypto.getRandomValues(new Uint8Array(32));
    const instance=btoa(String.fromCharCode(...bytes)).replaceAll('+','-').replaceAll('/','_').replaceAll('=','');
    return {...config,owner,instance,operator:!!owner};
  }catch{return {enabled:false};}
}

export class SpaceshipPhoto {
  constructor(config){
    this.config=config;this.online=false;
    const style=document.createElement('link');style.rel='stylesheet';style.href=new URL('./spaceship-photo.css',import.meta.url).href;document.head.append(style);
    this.element=document.createElement('aside');this.element.id='spaceship-photo';this.element.hidden=true;
    this.element.setAttribute('aria-label','Take your alien photo');
    this.element.innerHTML='<strong>Your alien photo</strong><a target="_blank" rel="noopener" aria-label="Open phone photo controls" hidden><img alt="Scan to take your alien photo"></a><p role="status">Photo station offline</p><small hidden>Same Wi-Fi as this screen</small>';
    document.getElementById('app').append(this.element);
    this.link=this.element.querySelector('a');this.status=this.element.querySelector('p');this.hint=this.element.querySelector('small');
    if(config.network==='public')this.hint.textContent='Take it home on your phone';
    if(config.enabled&&config.phoneURL)void this.makeCode();
    if(config.enabled&&config.mode==='cloud'&&!config.operator)void this.poll();
  }
  async poll(){
    try{
      const response=await fetch(`/api/photos?action=availability&room=${this.config.room}`,{cache:'no-store',signal:AbortSignal.timeout(5000)});
      if(!response.ok)throw new Error('Offline');this.update(await response.json());
    }catch{this.update({online:false});}
    this.timer=setTimeout(()=>this.poll(),3000);
  }
  async makeCode(){
    try{
      const url=new URL(this.config.phoneURL);
      if(!['http:','https:'].includes(url.protocol)||url.username||url.password||['localhost','127.0.0.1','0.0.0.0','[::1]'].includes(url.hostname))return;
      await new Promise((resolve,reject)=>{
        const script=document.createElement('script');script.src=new URL('./vendor/qrcode/qrcode.js',import.meta.url).href;
        script.onload=resolve;script.onerror=reject;document.head.append(script);
      });
      const code=window.qrcode(0,'M');code.addData(url.href);code.make();
      this.link.href=url.href;this.link.querySelector('img').src=code.createDataURL(6,24);this.codeReady=true;this.update(this.lastState||{});
    }catch{this.status.textContent='Photo station unavailable';}
  }
  setView(view){this.element.hidden=view!=='ship';}
  update({online=false,ready=false,busy=false}={}){
    this.lastState={online,ready,busy};
    // The public QR is permanent; camera availability must not hide its entry point.
    this.link.hidden=!this.codeReady||(!online&&this.config.network!=='public');this.hint.hidden=this.link.hidden;
    this.status.textContent=!this.config.enabled||!online?'Photo station offline':!this.config.phoneURL?'Phone connection not configured':this.config.demo?'Scan for a sample photo':busy?'Photo in progress':ready?'Scan. Pose. Save.':'Scan, then face the camera';
  }
}
