import * as THREE from 'three';

export class FingerRetargeter {
  constructor(root){
    this.joints=[];this.values={};
    root.traverse(bone=>{
      if(!bone.isBone)return;
      const match=/^(Thumb|Index|Middle|Ring)([123])\.?([LR])$/.exec(bone.name);
      if(!match)return;
      const rest=bone.userData.fingerRest?new THREE.Quaternion().fromArray(bone.userData.fingerRest):bone.quaternion.clone();
      bone.userData.fingerRest=rest.toArray();
      const joint=Number(match[2])-1,limit=bone.userData.fingerCurlRadians;
      const radians=Number.isFinite(limit)&&limit>=0&&limit<=Math.PI?limit:[1.15,1.45,1.05][joint];
      this.joints.push({bone,rest,digit:match[1],joint,side:match[3],radians});
    });
  }
  update(hands,dt){
    const alpha=1-Math.exp(-Math.min(dt,.1)*14);
    for(const {bone,rest,digit,joint,side,radians} of this.joints){
      const sample=hands?.[side]?.[digit]?.[joint];
      const target=Number.isFinite(sample)?THREE.MathUtils.clamp(sample,0,1):0;
      const value=(this.values[bone.name]||0)+(target-(this.values[bone.name]||0))*alpha;
      this.values[bone.name]=value;
      const rotation=new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1,0,0),value*radians);
      bone.quaternion.copy(rest).multiply(rotation);
    }
  }
}
