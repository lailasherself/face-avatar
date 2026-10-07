function cameraToken(){
  const bytes=crypto.getRandomValues(new Uint8Array(32));
  return btoa(String.fromCharCode(...bytes)).replaceAll('+','-').replaceAll('/','_').replaceAll('=','');
}

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
      const search=new URLSearchParams(location.search);search.set('station',config.room);
      fragment.delete('photo-owner');history.replaceState(null,'',location.pathname+'?'+search+(fragment.size?'#'+fragment:''));
    }
    const fixed=new URLSearchParams(location.search).get('station')===config.room;
    if(config.testStations&&!fixed){
      // A tab keeps its QR across reloads; other testers get unrelated cameras.
      let owner=sessionStorage.getItem('alien-photo-test-owner');
      if(!/^[\w-]{43}$/.test(owner||'')){owner=cameraToken();sessionStorage.setItem('alien-photo-test-owner',owner);}
      const response=await fetch('/api/photos?action=provision',{method:'POST',headers:{'X-Face-Avatar':'photo',Authorization:`Bearer ${owner}`},signal:AbortSignal.timeout(10000)});
      if(!response.ok)throw new Error('Photo station unavailable');
      const station=await response.json();
      return {...config,...station,owner,instance:cameraToken(),operator:true};
    }
    const owner=localStorage.getItem('alien-photo-owner');
    return {...config,owner,instance:cameraToken(),operator:!!owner};
  }catch{return {enabled:false};}
}

export class SpaceshipPhoto {
  constructor(config){
    this.config=config;this.online=false;
    const style=document.createElement('link');style.rel='stylesheet';style.href=new URL('./spaceship-photo.css',import.meta.url).href;document.head.append(style);
    this.element=document.createElement('aside');this.element.id='spaceship-photo';this.element.hidden=true;
    this.element.setAttribute('aria-label','Take your alien photo');
    this.element.innerHTML='<a target="_blank" rel="noopener" aria-label="Scan QR code or open phone photo controls" hidden><img alt=""></a><p role="status">Photo station offline</p>';
    document.getElementById('app').append(this.element);
    this.link=this.element.querySelector('a');this.status=this.element.querySelector('p');
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
    // Camera availability must not hide the public QR's entry point.
    this.link.hidden=!this.codeReady||(!online&&this.config.network!=='public');
    this.status.textContent=!this.config.enabled||!online?'Photo station offline':!this.config.phoneURL?'Phone connection not configured':this.config.demo?'Scan for a sample photo':busy?'Photo in progress':ready?'Scan. Pose. Save.':'Scan, then face the camera';
  }
}
