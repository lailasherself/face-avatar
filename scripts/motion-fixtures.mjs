export function hand(x=.3,y=.3,closed=false){
  const p=Array.from({length:21},()=>({x,y,z:0}));p[0]={x,y:y+.1,z:0};
  for(const [j,offset] of [[5,-.06],[9,-.02],[13,.02],[17,.06]]){
    for(let k=0;k<4;k++)p[j+k]={x:x+offset,y:y-k*.055,z:0};
    if(closed)p[j+3].y=y+.02;
  }
  return p;
}
export function bodyPose(raised=[]){
  // Match this installation's bundled tracker, which omits confidence properties.
  const p=Array.from({length:33},()=>({x:.5,y:.5,z:0}));
  for(const [side,s,e,w,i,l,x] of [['left',11,13,15,19,17,.62],['right',12,14,16,20,18,.38]]){
    const outward=x>.5?.18:-.18;
    p[s]={...p[s],x,y:.52};
    p[e]={...p[e],x:x+outward,y:raised.includes(side)?.52:.7};
    p[w]={...p[w],x:x+outward,y:raised.includes(side)?.25:.9};
    for(const n of [i,l])p[n]={...p[w],y:p[w].y+(raised.includes(side)?-.06:.06)};
  }
  return {poseLandmarks:p,poseWorldLandmarks:structuredClone(p)};
}
export function motionFrame({x=.3,y=.3,closed=false,both=false,noPose=false,unmatched=false,wrist=16}={}){
  const pose=bodyPose();
  if(!unmatched)pose.poseLandmarks[wrist]={x,y:y+.1,z:0};
  if(both)pose.poseLandmarks[wrist===16?15:16]={x:.7,y:y+.1,z:0};
  return {...pose,poseLandmarks:noPose?[]:pose.poseLandmarks,
    landmarks:both?[hand(x,y),hand(.7,y)]:[hand(x,y,closed)],handedness:[[{categoryName:'Left'}]]};
}
