export class ARPhotoControls {
  constructor({canvas,previous,next,capture,retry}){
    this.capture=capture;this.locked=false;this.ready=false;
    document.documentElement.classList.add('ar-photo');
    const style=document.createElement('link');style.rel='stylesheet';style.href=new URL('./ar-photo.css',import.meta.url).href;document.head.append(style);
    document.getElementById('stage').append(canvas);
    const container=document.createElement('section');container.id='ar-controls';container.setAttribute('aria-label','Alien camera');
    container.innerHTML=`<div class="ar-top"><span class="ar-brand">ATL DOWNTOWN</span><div class="ar-picker"><button id="ar-previous" class="icon" title="Previous alien" aria-label="Previous alien"><img src="vendor/lucide/arrow-left.svg" alt=""></button><strong id="ar-name">Loading...</strong><button id="ar-next" class="icon" title="Next alien" aria-label="Next alien"><img src="vendor/lucide/arrow-right.svg" alt=""></button></div></div><div class="ar-bottom"><p id="ar-status" role="status">Starting camera...</p><button id="ar-shutter" disabled><img src="vendor/lucide/camera.svg" alt="">Take photo</button><button id="ar-cancel" hidden>Cancel</button><button id="ar-retry" hidden>Retry camera</button><span id="ar-count" hidden aria-live="polite"></span></div><dialog id="ar-result"><div class="ar-result-heading"><h2 id="ar-result-title">Your alien photo</h2><button id="ar-close" class="icon" title="Close photo" aria-label="Close photo"><img src="vendor/lucide/x.svg" alt=""></button></div><img id="ar-preview" alt="Your real body with the alien head"><div class="ar-result-actions"><a id="ar-save" download="ATL-Downtown.jpg"><img src="vendor/lucide/download.svg" alt="">Save photo</a><button id="ar-retake"><img src="vendor/lucide/rotate-ccw.svg" alt="">Retake</button></div></dialog>`;
    document.getElementById('app').append(container);
    this.$=id=>container.querySelector('#'+id);
    this.$('ar-previous').onclick=previous;this.$('ar-next').onclick=next;
    this.$('ar-shutter').onclick=()=>this.start();this.$('ar-cancel').onclick=()=>this.cancel();this.$('ar-retry').onclick=retry;
    this.$('ar-close').onclick=this.$('ar-retake').onclick=()=>this.$('ar-result').close();
    this.$('ar-result').addEventListener('close',()=>{this.locked=false;this.clearPhoto();});
    document.addEventListener('visibilitychange',()=>{if(document.hidden)this.cancel();});
    addEventListener('pagehide',()=>{this.cancel();this.clearPhoto();});
  }
  clearPhoto(){if(this.url)URL.revokeObjectURL(this.url);this.url=null;this.$('ar-preview').removeAttribute('src');this.$('ar-save').removeAttribute('href');}
  update({ready,name,camera,starting}){
    this.ready=ready;this.$('ar-name').textContent=name||'Loading...';
    this.$('ar-shutter').disabled=!ready||this.locked;
    this.$('ar-previous').disabled=this.$('ar-next').disabled=this.locked;
    this.$('ar-retry').hidden=!!camera||starting;
    if(this.deadline&&!ready){this.cancel();this.$('ar-status').textContent='Face tracking lost. Face the camera and try again.';return;}
    if(this.deadline)return;
    this.$('ar-status').textContent=ready?'Ready for your close-up.':camera?'Face the camera. One person at a time.':starting?'Starting camera...':'Allow camera access to begin.';
  }
  start(){
    if(!this.ready||this.locked)return;
    this.locked=true;this.deadline=performance.now()+5000;this.generation=(this.generation||0)+1;
    this.$('ar-shutter').disabled=true;this.$('ar-previous').disabled=this.$('ar-next').disabled=true;
    this.$('ar-cancel').hidden=false;this.$('ar-count').hidden=false;
    this.$('ar-status').textContent='Look at the camera and pose.';this.tick(this.generation);
  }
  async tick(generation){
    if(generation!==this.generation||!this.deadline)return;
    const seconds=Math.ceil((this.deadline-performance.now())/1000);
    this.$('ar-count').textContent=String(Math.max(1,seconds));
    if(seconds>0){this.timer=setTimeout(()=>this.tick(generation),80);return;}
    this.deadline=null;this.$('ar-count').hidden=true;this.$('ar-cancel').hidden=true;
    try{
      const {canvas,name}=this.capture();
      const blob=await new Promise((resolve,reject)=>canvas.toBlob(b=>b?resolve(b):reject(new Error('Unable to save photo')),'image/jpeg',.94));
      if(generation!==this.generation)return;
      this.clearPhoto();this.url=URL.createObjectURL(blob);
      this.$('ar-preview').src=this.url;this.$('ar-save').href=this.url;
      this.$('ar-result-title').textContent=`You as ${name}`;this.$('ar-result').showModal();
    }catch(error){this.locked=false;this.$('ar-status').textContent=error.message;}
  }
  cancel(){
    clearTimeout(this.timer);this.generation=(this.generation||0)+1;this.deadline=null;
    this.locked=this.$('ar-result').open;
    this.$('ar-count').hidden=true;this.$('ar-cancel').hidden=true;
  }
}
