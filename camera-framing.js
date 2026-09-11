export function cameraConstraints(supported={}){
  const video={facingMode:'user',width:{ideal:1280},height:{ideal:720},frameRate:{ideal:30}};
  if(supported.resizeMode)video.resizeMode={exact:'none'};
  return {video,audio:false};
}

const usable=(p,confidence=.6)=>p&&[p.x,p.y,p.z].every(Number.isFinite)&&(p.visibility??1)>=confidence&&(p.presence??1)>=confidence;
export function armFraming(pose,time,now,confidence=.8){
  const result={};
  for(const [side,ids] of [['left',[11,13,15]],['right',[12,14,16]]]){
    const points=ids.map(i=>pose?.[i]);
    result[side]=!Number.isFinite(time)||now-time>400||now<time?'not-tracked':
      points.some(p=>usable(p,confidence)&&(p.x<0||p.x>1||p.y<0||p.y>1))?'outside-frame':
      points.some(p=>!usable(p,confidence))?'not-tracked':
      points.some(p=>Math.min(p.x,p.y,1-p.x,1-p.y)<.08)?'near-edge':'in-frame';
  }
  return result;
}

export class CameraFraming {
  constructor(video,dialog,confidence=.8){
    this.confidence=confidence;
    this.video=video;this.dialog=dialog;this.canvas=dialog.querySelector('canvas');
    this.ctx=this.canvas.getContext('2d');this.reset();
  }
  reset(){this.pose=null;this.poseTime=-Infinity;this.lastDraw=-Infinity;}
  update(body,time){
    if(body?.poseLandmarks&&Number.isFinite(time)&&time>=this.poseTime){this.pose=body.poseLandmarks;this.poseTime=time;}
  }
  snapshot(now=performance.now()){
    const settings=this.video.srcObject?.getVideoTracks()[0]?.getSettings()||{};
    return {width:this.video.videoWidth,height:this.video.videoHeight,resizeMode:settings.resizeMode??'unreported',
      ...armFraming(this.pose,this.poseTime,now,this.confidence)};
  }
  draw(now){
    if(!this.dialog.open||now-this.lastDraw<100)return;
    this.lastDraw=now;
    const {video,canvas,ctx}=this,active=video.srcObject&&video.readyState>=2;
    const width=active?video.videoWidth:960,height=active?video.videoHeight:540;
    if(canvas.width!==width||canvas.height!==height){canvas.width=width;canvas.height=height;}
    ctx.fillStyle='#101413';ctx.fillRect(0,0,width,height);
    if(active)ctx.drawImage(video,0,0,width,height);
    const report=this.snapshot(now);
    const names={'in-frame':'In frame','near-edge':'Near edge','outside-frame':'Outside frame','not-tracked':'Not tracked'};
    for(const side of ['left','right']){
      const output=this.dialog.querySelector('[data-arm="'+side+'"]');
      output.textContent=active?names[report[side]]:'Camera off';output.dataset.state=report[side];
    }
    this.dialog.querySelector('[data-capture]').textContent=active?`${width} x ${height}`:'Camera off';
    if(!active)return;
    ctx.lineWidth=Math.max(2,width/400);
    ctx.setLineDash([width/100,width/100]);ctx.strokeStyle='#e8c15b';
    ctx.strokeRect(width*.08,height*.08,width*.84,height*.84);ctx.setLineDash([]);
    if(!Number.isFinite(this.poseTime)||now<this.poseTime||now-this.poseTime>400)return;
    for(const [side,ids] of [['left',[11,13,15]],['right',[12,14,16]]]){
      ctx.strokeStyle=report[side]==='in-frame'?'#62dbac':'#f5bd5c';ctx.fillStyle=ctx.strokeStyle;
      const points=ids.map(i=>this.pose?.[i]);
      for(let i=0;i<points.length;i++){
        const p=points[i];if(!usable(p))continue;
        if(i&&usable(points[i-1])){ctx.beginPath();ctx.moveTo(points[i-1].x*width,points[i-1].y*height);ctx.lineTo(p.x*width,p.y*height);ctx.stroke();}
        ctx.beginPath();ctx.arc(p.x*width,p.y*height,Math.max(3,width/150),0,Math.PI*2);ctx.fill();
      }
    }
  }
}
