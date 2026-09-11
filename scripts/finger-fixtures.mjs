export function fingerHand(curl={}){
  const points=Array.from({length:21},()=>({x:0,y:0,z:0}));
  for(const [digit,base,x] of [['Thumb',1,-.045],['Index',5,-.025],['Middle',9,0],['Ring',13,.025],['Pinky',17,.045]]){
    points[base]={x,y:.06,z:0};let angle=0;
    for(let i=1;i<=3;i++){
      angle+=(curl[digit]?.[i-1]||0);
      const previous=points[base+i-1];
      points[base+i]={x,y:previous.y+.025*Math.cos(angle),z:previous.z-.025*Math.sin(angle)};
    }
  }
  return points;
}
