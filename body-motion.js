// The pose worker retains confidence. Also accept older coordinate-only callers;
// hand landmarks legitimately omit this metadata.
export const visible=p=>!!p&&[p.x,p.y,p.z].every(Number.isFinite)&&
  (p.visibility??1)>=.6&&(p.presence??1)>=.6;
const inFrame=p=>visible(p)&&p.x>=0&&p.x<=1&&p.y>=0&&p.y<=1;
const armVisible=p=>inFrame(p)&&(p.visibility??1)>=.8&&(p.presence??1)>=.8;

export function armDirections(pose,world,aspectRatio=4/3){
  if(pose?.length!==33||world?.length!==33)return {};
  if(!Number.isFinite(aspectRatio)||aspectRatio<=0)return {};
  const arms={};
  // Mirror the visitor: their right arm drives the avatar's screen-right arm.
  for(const [side,shoulder,elbow,wrist,index,pinky] of [['L',12,14,16,20,18],['R',11,13,15,19,17]]){
    if(![shoulder,elbow,wrist].every(i=>armVisible(pose[i])&&visible(world[i])))continue;
    const direction=(a,b,screenA,screenB)=>{
      const length=Math.hypot(a.x-b.x,a.y-b.y,a.z-b.z);
      if(length<=.025||length>=1.2)return null;
      // Use the observed arm's image-plane direction, not the model's inferred
      // 3D XY (which can lift a resting arm during depth/occlusion ambiguity).
      const x=(screenA.x-screenB.x)*aspectRatio,y=screenA.y-screenB.y;
      const projected=Math.hypot(x,y);
      if(projected<.015)return null;
      const z=Math.max(-.92,Math.min(.92,(a.z-b.z)/length));
      const xy=Math.sqrt(1-z*z);
      return [x/projected*xy,y/projected*xy,z];
    };
    const upper=direction(world[shoulder],world[elbow],pose[shoulder],pose[elbow]);
    const lower=direction(world[elbow],world[wrist],pose[elbow],pose[wrist]);
    if(!upper||!lower)continue;
    let hand=null;
    if([index,pinky].every(i=>inFrame(pose[i])&&visible(world[i]))){
      const tip=Object.fromEntries(['x','y','z'].map(k=>[k,(world[index][k]+world[pinky][k])/2]));
      const screenTip={x:(pose[index].x+pose[pinky].x)/2,y:(pose[index].y+pose[pinky].y)/2};
      hand=direction(world[wrist],tip,pose[wrist],screenTip);
    }
    arms[side]={upper,lower,hand};
  }
  return arms;
}

// Shoulder span in normalized image units: the visitor's size in frame. Every
// gesture distance scales with it so swipes work the same at 1.2m and 3m.
export const shoulderWidth=pose=>{
  const l=pose?.[11],r=pose?.[12];
  return inFrame(l)&&inFrame(r)?Math.hypot(l.x-r.x,l.y-r.y):null;
};
// How far below the shoulder line a palm may sit and still count as raised.
// A natural "stop" palm (elbow bent, forearm vertical) keeps the wrist near the
// shoulder, so allow about half a shoulder span of slack rather than a fixed 4%.
export const raisedSlack=pose=>Math.max(.04,(shoulderWidth(pose)||0)*.6);
export const handLowered=(pose,side)=>{
  const shoulder=pose?.[side==='L'?12:11],wrist=pose?.[side==='L'?16:15];
  return visible(shoulder)&&visible(wrist)&&wrist.y>=shoulder.y+raisedSlack(pose);
};
export function raisedPalmBodySide(hand,pose){
  if(pose?.length!==33||!inFrame(hand?.[0]))return null;
  const slack=raisedSlack(pose),reach=Math.max(.12,(shoulderWidth(pose)||0)*.5);
  const matches=[['R',11,15],['L',12,16]].filter(([,s,w])=>inFrame(pose[s])&&inFrame(pose[w])&&
    hand[0].y<pose[s].y+slack).map(([side,,w])=>({side,distance:Math.hypot(hand[0].x-pose[w].x,hand[0].y-pose[w].y)}))
    .filter(m=>m.distance<reach).sort((a,b)=>a.distance-b.distance);
  if(matches.length>1&&matches[1].distance-matches[0].distance<.025)return null;
  return matches[0]?.side??null;
}
export const raisedPalmMatchesBody=(hand,pose)=>raisedPalmBodySide(hand,pose)!==null;
