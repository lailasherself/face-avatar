const validAt=min=>p=>p&&Array.isArray(p.position)&&p.position.length===3&&p.position.every(Number.isFinite)&&
  Number.isFinite(p.confidence)&&p.confidence>=min&&Array.isArray(p.image)&&p.image.length===2&&p.image.every(v=>Number.isFinite(v)&&v>=0&&v<=1);
// Arm directions need confident joints. Gesture matching (wrist crops and the
// raised-palm body side) accepts lower-confidence wrists: the FAST body model
// reports a raised arm's wrist around 40-70%, so a 60% cut made it flicker.
const valid=validAt(.6),validHint=validAt(.3);

export function zedMotion(packet){
  if(packet?.version!==1||packet.coordinates!=='RIGHT_HANDED_Y_UP'||packet.reference!=='CAMERA'||packet.units!=='meters')throw new Error('Unsupported ZED coordinate contract');
  const joints=packet.body?.joints||{},arms={},handHints={};
  const poseLandmarks=Array.from({length:33},()=>({x:0,y:0,z:0,visibility:0,presence:0}));
  const direction=(a,b)=>{
    if(!valid(a)||!valid(b))return null;
    const v=b.position.map((value,i)=>value-a.position[i]),length=Math.hypot(...v);
    if(length<.025||length>1.2)return null;
    // Mirror camera X only. ZED OpenGL coordinates already have Y up and Z
    // toward the camera, unlike MediaPipe image/world landmark conventions.
    return [-v[0]/length,v[1]/length,v[2]/length];
  };
  for(const [human,avatar,indices] of [['RIGHT','L',[12,14,16]],['LEFT','R',[11,13,15]]]){
    const chain=['SHOULDER','ELBOW','WRIST','HAND'].map(name=>joints[human+'_'+name]);
    if(validHint(chain[3]))handHints[avatar]={x:chain[3].image[0],y:chain[3].image[1],visibility:chain[3].confidence,presence:chain[3].confidence};
    chain.slice(0,3).forEach((p,i)=>{if(validHint(p))poseLandmarks[indices[i]]={x:p.image[0],y:p.image[1],z:0,visibility:p.confidence,presence:p.confidence};});
    const upper=direction(chain[0],chain[1]),lower=direction(chain[1],chain[2]);
    if(upper&&lower)arms[avatar]={upper,lower,hand:direction(chain[2],chain[3])};
  }
  return {arms,poseLandmarks,poseWorldLandmarks:[],handHints,personId:packet.body?.id??null};
}
