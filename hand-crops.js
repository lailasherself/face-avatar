const visible=p=>p&&[p.x,p.y].every(Number.isFinite)&&p.x>=0&&p.x<=1&&p.y>=0&&p.y<=1&&
  (p.visibility??1)>=.6&&(p.presence??1)>=.6;
export const HAND_TILE=320;

export function handCrops(body,width,height){
  if(!Number.isFinite(width)||!Number.isFinite(height)||Math.min(width,height)<64)return [];
  const pose=body?.poseLandmarks||[],distance=(a,b)=>Math.hypot((a.x-b.x)*width,(a.y-b.y)*height);
  const shoulders=visible(pose[11])&&visible(pose[12])?distance(pose[11],pose[12]):0;
  const crops=[];
  for(const [side,index,elbow,tile] of [['L',16,14,0],['R',15,13,1]]){
    const wrist=pose[index];if(!visible(wrist))continue;
    const forearm=visible(pose[elbow])?distance(wrist,pose[elbow]):0;
    const tip=body?.handHints?.[side],hint=visible(tip)?tip:null;
    // Include the fingertips beyond the wrist, including foreshortened reaches.
    const size=Math.min(width,height,Math.max(80,shoulders*.8,forearm*1.6,hint?distance(wrist,hint)*3:0));
    const elbowPoint=visible(pose[elbow])?pose[elbow]:wrist;
    const cx=hint?(wrist.x+hint.x)*width/2:(wrist.x+(wrist.x-elbowPoint.x)*.25)*width;
    const cy=hint?(wrist.y+hint.y)*height/2:(wrist.y+(wrist.y-elbowPoint.y)*.25)*height;
    const x=Math.max(0,Math.min(width-size,cx-size/2)),y=Math.max(0,Math.min(height-size,cy-size/2));
    crops.push({side,tile,x,y,size,width,height,wrist});
  }
  return crops;
}

export function restoreHands(result,crops){
  const output={landmarks:[],worldLandmarks:[],handedness:[]},candidates=[];
  for(let i=0;i<(result.landmarks?.length||0);i++){
    const points=result.landmarks[i];
    if(points.length!==21||points.some(p=>![p.x,p.y,p.z].every(Number.isFinite)))continue;
    const crop=crops.find(c=>Math.floor(points[0].x*2)===c.tile);
    if(!crop||points.some(p=>p.x*2<crop.tile||p.x*2>crop.tile+1||p.y<0||p.y>1))continue;
    const mapped=points.map(p=>({...p,x:(crop.x+(p.x*2-crop.tile)*crop.size)/crop.width,
      y:(crop.y+p.y*crop.size)/crop.height,z:p.z*2*crop.size/crop.width}));
    const error=Math.hypot(mapped[0].x-crop.wrist.x,mapped[0].y-crop.wrist.y);
    if(error<=.15)candidates.push({i,crop,mapped,error});
  }
  // Overlapping wrist crops can see the same hand. Keep the closest candidate
  // per body wrist, and never let duplicate observations drive both sides.
  const used=new Set();
  for(const c of candidates.sort((a,b)=>a.error-b.error)){
    if(used.has(c.crop.side)||output.landmarks.some(p=>Math.hypot(p[0].x-c.mapped[0].x,p[0].y-c.mapped[0].y)<.025))continue;
    used.add(c.crop.side);output.landmarks.push(c.mapped);
    output.worldLandmarks.push(result.worldLandmarks?.[c.i]);
    output.handedness.push(result.handedness?.[c.i]);
  }
  return output;
}
