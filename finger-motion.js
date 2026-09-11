import {visible} from './body-motion.js';
const clamp=value=>Math.max(0,Math.min(1,value));
const sub=(a,b)=>[a.x-b.x,a.y-b.y,a.z-b.z];
const dot=(a,b)=>a.reduce((sum,v,i)=>sum+v*b[i],0);
const unit=a=>{const length=Math.hypot(...a);return length>1e-6?a.map(v=>v/length):null;};
const angle=(a,b)=>{a=unit(a);b=unit(b);return a&&b?Math.acos(Math.max(-1,Math.min(1,dot(a,b)))):0;};

export function fingerCurls(points){
  if(!Array.isArray(points)||points.length!==21||points.some(p=>!p||![p.x,p.y,p.z].every(Number.isFinite)))return null;
  const forward=unit(sub(points[9],points[0]));
  const across=unit(sub(points[17],points[5]));
  if(!forward||!across)return null;
  const normal=unit([forward[1]*across[2]-forward[2]*across[1],forward[2]*across[0]-forward[0]*across[2],forward[0]*across[1]-forward[1]*across[0]]);
  if(!normal)return null;
  const curls={};
  for(const [digit,base] of [['Thumb',1],['Index',5],['Middle',9],['Ring',13],['Pinky',17]]){
    const bones=[sub(points[base],points[0]),sub(points[base+1],points[base]),sub(points[base+2],points[base+1]),sub(points[base+3],points[base+2])];
    if(bones.some(v=>Math.hypot(...v)<1e-6))return null;
    const bend=digit==='Thumb'?Math.max(0,angle(bones[0],bones[1])-.25):Math.abs(Math.atan2(dot(bones[1],normal),dot(bones[1],forward)));
    curls[digit]=[clamp(bend/1.2),clamp(angle(bones[1],bones[2])/1.5),clamp(angle(bones[2],bones[3])/1.2)];
  }
  // The source aliens have a thumb and three fingers. Their outer finger combines
  // the visitor's ring and little fingers without coupling index or middle curls.
  curls.Ring=curls.Ring.map((v,i)=>(v+curls.Pinky[i])/2);delete curls.Pinky;
  return curls;
}

export function trackedFingerCurls(result){
  const hands=result?.landmarks||[],pose=result?.poseLandmarks;
  if(pose?.length!==33)return {};
  const out={};
  for(let i=0;i<hands.length;i++){
    const wrist=hands[i]?.[0];if(!visible(wrist))continue;
    const matches=[['L',16],['R',15]].map(([side,index])=>({side,point:pose[index]}))
      .filter(({point})=>visible(point)&&point.x>=0&&point.x<=1&&point.y>=0&&point.y<=1)
      .map(m=>({...m,distance:Math.hypot(wrist.x-m.point.x,wrist.y-m.point.y)})).sort((a,b)=>a.distance-b.distance);
    if(!matches.length||matches[0].distance>.15||out[matches[0].side])continue;
    const curls=fingerCurls(result.worldLandmarks?.[i]||hands[i]);
    if(curls)out[matches[0].side]=curls;
  }
  return out;
}
