export class TongueSignal {
  constructor(){this.reset();}
  reset(){this.value=0;this.active=false;this.hits=0;this.time=-Infinity;}
  update(score,time){
    if(!Number.isFinite(score)||!Number.isFinite(time)||time<=this.time)return this.value;
    if(time-this.time>350){this.active=false;this.hits=0;this.value=0;}
    this.time=time;
    if(score>=.55)this.hits++;else this.hits=0;
    if(score>=.8||this.hits>=2)this.active=true;
    if(score<.35)this.active=false;
    // The model predicts presence, not physical tongue length. Confirmed presence
    // drives the full cartoon extension; driveFace smooths the actual morph.
    this.value=this.active?1:0;
    return this.value;
  }
  current(time){return time-this.time<=350?this.value:0;}
}

// Eye-aligned crop as in FoxyFace, with proportional padding so distance from the
// installation camera does not change the face's scale inside the model input.
export function faceCropTransform(landmarks,width,height,size=256){
  if(landmarks?.length!==478||!Number.isFinite(width)||!Number.isFinite(height)||width<=0||height<=0||
     landmarks.some(p=>![p.x,p.y].every(Number.isFinite)))return null;
  const a=landmarks[33],b=landmarks[263],dx=(b.x-a.x)*width,dy=(b.y-a.y)*height;
  if(Math.hypot(dx,dy)<16)return null;
  const angle=Math.atan2(dy,dx),c=Math.cos(angle),s=Math.sin(angle);
  const xs=landmarks.map(p=>c*p.x*width+s*p.y*height);
  const ys=landmarks.map(p=>-s*p.x*width+c*p.y*height);
  const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);
  const px=(maxX-minX)*.125,py=(maxY-minY)*.125;
  if(px<2||py<2)return null;
  const sx=size/(maxX-minX+2*px),sy=size/(maxY-minY+2*py);
  return [c*sx,-s*sy,s*sx,c*sy,-(minX-px)*sx,-(minY-py)*sy];
}
