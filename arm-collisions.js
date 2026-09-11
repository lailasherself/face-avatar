import * as THREE from 'three';
import RAPIER from './vendor/rapier/rapier.mjs';

await RAPIER.init();
const up=new THREE.Vector3(0,1,0);
const point=bone=>bone.getWorldPosition(new THREE.Vector3());
const limit=(direction,axis,angle)=>{
  const q=new THREE.Quaternion().setFromUnitVectors(axis,direction);
  const actual=axis.angleTo(direction);
  return actual>angle?axis.clone().applyQuaternion(new THREE.Quaternion().slerp(q,angle/actual)):direction;
};

export class ArmCollisions {
  constructor(root,chains){
    this.root=root;this.chains=chains;this.world=new RAPIER.World({x:0,y:0,z:0});
    this.colliders=[];this.adjustments=0;this.penetration=0;this.previous={};this.corrected={};this.previousPose={};this.previousRequested={};
    root.updateWorldMatrix(true,true);
    const head=root.getObjectByName('Head'),chest=root.getObjectByName('Chest');
    // Convex body envelopes exclude arm/leg weights. They follow the actual bones,
    // so head rotation cannot leave an invisible collider behind in the rest pose.
    for(const [region,anchor] of [['head',head],['torso',chest]]){
      if(!anchor)continue;
      const points=[];
      root.traverse(mesh=>{
        if(!mesh.isSkinnedMesh)return;
        let owner=mesh;
        while(owner&&!owner.userData.armCollisionSurface)owner=owner.parent;
        if(!owner&&mesh.morphTargetDictionary?.correctiveSeated===undefined)return;
        mesh.skeleton.update();
        const a=mesh.geometry.attributes;
        if(!a.skinIndex||!a.skinWeight)return;
        for(let i=0;i<a.position.count;i++){
          let weight=0;
          for(let j=0;j<4;j++){
            const name=mesh.skeleton.bones[a.skinIndex.getComponent(i,j)]?.name||'';
            if(region==='head'?name==='Head':/^(Chest|Spine|Hips|Neck)$/.test(name))weight+=a.skinWeight.getComponent(i,j);
          }
          if(weight<.8)continue;
          points.push(anchor.worldToLocal(mesh.localToWorld(mesh.getVertexPosition(i,new THREE.Vector3()))));
        }
      });
      if(points.length<4)continue;
      // Retain extreme points in many directions, bounding the hull's cost without
      // random sampling that can miss a cheek, chin, or jacket edge.
      const hull=new Set();
      for(let y=-3;y<=3;y++)for(let x=-3;x<=3;x++)for(let z=-3;z<=3;z++){
        if(!x&&!y&&!z)continue;
        const d=new THREE.Vector3(x,y,z).normalize();let best=points[0],score=-Infinity;
        for(const p of points){const v=p.dot(d);if(v>score){score=v;best=p;}}
        hull.add(best);
      }
      const vertices=new Float32Array([...hull].flatMap(p=>p.toArray()));
      const descriptor=RAPIER.ColliderDesc.convexHull(vertices);
      if(descriptor)this.colliders.push({anchor,collider:this.world.createCollider(descriptor)});
    }
    this.updateBodies();
  }
  dispose(){this.world.free();}
  updateBodies(){
    this.root.updateWorldMatrix(true,true);
    for(const {anchor,collider} of this.colliders){
      collider.setTranslation(point(anchor));
      collider.setRotation(anchor.getWorldQuaternion(new THREE.Quaternion()));
    }
  }
  contact(start,end,radius,trim=0){
    start=start.clone().lerp(end,trim);
    const direction=end.clone().sub(start),length=direction.length();
    const shape=new RAPIER.Capsule(length/2,radius);
    const center=start.clone().add(end).multiplyScalar(.5);
    const rotation=new THREE.Quaternion().setFromUnitVectors(up,direction.normalize());
    let deepest=null;
    for(const {collider} of this.colliders){
      const contact=collider.contactShape(shape,center,rotation,.004);
      if(contact&&contact.distance<.002&&(!deepest||contact.distance<deepest.distance))deepest=contact;
    }
    return deepest;
  }
  avoid(start,direction,length,radius,trim,side,axis,maxAngle,previous,releasing=false){
    const constrain=d=>{
      // A front-facing kiosk should not send a shoulder behind the torso on an
      // ambiguous depth estimate. Forearms can still bend back toward the visitor.
      if(!axis&&d.z<-.12){
        const xy=Math.hypot(d.x,d.y),span=Math.sqrt(1-.12*.12);
        d.set(xy>d.length()*1e-6?d.x/xy*span:side*span,xy>d.length()*1e-6?d.y/xy*span:0,-.12);
      }
      return axis?limit(d,axis,maxAngle):d;
    };
    const desired=constrain(direction.clone());
    const blocked=d=>this.contact(start,start.clone().addScaledVector(d,length),radius,trim);
    if(!blocked(desired)){
      // Release a prior collision deflection continuously without adding a
      // second filter to motion that was never constrained.
      if(previous&&releasing){
        const origin=constrain(previous.clone());
        const swing=new THREE.Quaternion().setFromUnitVectors(origin,desired);
        const eased=constrain(origin.applyQuaternion(new THREE.Quaternion().slerp(swing,this.responseAlpha??1)));
        if(!blocked(eased))return eased;
      }
      return desired;
    }
    const approach=safe=>{
      if(!previous)return safe;
      const origin=constrain(previous.clone());
      if(blocked(origin)){
        const escape=new THREE.Quaternion().setFromUnitVectors(origin,safe);
        let lo=0,hi=1;
        for(let i=0;i<12;i++){
          const t=(lo+hi)/2,candidate=constrain(origin.clone().applyQuaternion(new THREE.Quaternion().slerp(escape,t)));
          if(blocked(candidate))lo=t;else{hi=t;safe=candidate;}
        }
      }
      // Keep the last feasible side of the hull. Approach the target along that
      // arc instead of selecting a different escape normal on every frame.
      const swing=new THREE.Quaternion().setFromUnitVectors(safe,desired);
      let lo=0,hi=1,result=safe;
      for(let i=0;i<10;i++){
        const t=(lo+hi)/2,candidate=constrain(safe.clone().applyQuaternion(new THREE.Quaternion().slerp(swing,t)));
        if(blocked(candidate))hi=t;else{lo=t;result=candidate;}
      }
      const eased=constrain(origin.clone().applyQuaternion(new THREE.Quaternion().slerp(new THREE.Quaternion().setFromUnitVectors(origin,result),this.responseAlpha??1)));
      return blocked(eased)?result:eased;
    };
    let d=constrain((previous||desired).clone()),best=d.clone(),depth=Infinity,feasible=null,score=Infinity;
    for(let i=0;i<24;i++){
      const end=start.clone().addScaledVector(d,length),hit=this.contact(start,end,radius,trim);
      if(!hit){
        const safe=approach(d);
        if(!previous||safe.angleTo(previous)<.1)return safe;
        feasible=safe;score=safe.angleTo(previous)+safe.angleTo(desired)*.2;break;
      }
      if(-hit.distance<depth){depth=-hit.distance;best=d.clone();}
      const push=new THREE.Vector3(hit.normal1.x,hit.normal1.y,hit.normal1.z);
      // Resolve the measured gap, not a fixed 3cm kick. The old minimum impulse
      // repeatedly overshot the hull boundary as tracking pulled the arm back.
      d=constrain(end.addScaledVector(push,Math.max(.001,-hit.distance+.0025)*1.5).sub(start).normalize());
    }
    // A segment exactly through a hull can have an axial contact normal. Search
    // nearby directions rather than oscillating or stretching the bone to escape.
    for(const bias of [new THREE.Vector3(0,0,1),new THREE.Vector3(side,0,0),new THREE.Vector3(side,-.5,1),new THREE.Vector3(side,1,1)]){
      for(const blend of [.2,.4,.6,.8,1]){
        const candidate=constrain(direction.clone().lerp(bias.clone().normalize(),blend).normalize());
        const hit=this.contact(start,start.clone().addScaledVector(candidate,length),radius,trim);
        if(!hit){
          const safe=approach(candidate),cost=safe.angleTo(previous||desired)+safe.angleTo(desired)*.2;
          if(cost<score){score=cost;feasible=safe;}
          break;
        }
        if(-hit.distance<depth){depth=-hit.distance;best=candidate;}
      }
    }
    return feasible||best;
  }
  update(dt=1/60){
    const started=performance.now();
    this.responseAlpha=1-Math.exp(-Math.min(.1,Math.max(0,dt))*24);
    this.updateBodies();this.adjustments=0;this.penetration=0;
    for(const [side,chain] of Object.entries(this.chains)){
      const history=this.previous[side]??=[];
      const corrected=this.corrected[side]??=[];
      const sign=side==='L'?1:-1;
      const bones=chain.map(c=>c.bone),positions=bones.map(point);
      const lengths=[positions[0].distanceTo(positions[1]),positions[1].distanceTo(positions[2])];
      const rotations=bones.map(bone=>bone.getWorldQuaternion(new THREE.Quaternion()));
      const requested=rotations.map(q=>q.clone()),lastPose=this.previousPose[side];
      const step=4.5*Math.min(.1,Math.max(0,dt)),lastRequested=this.previousRequested[side];
      const trackingStep=lastRequested?Math.max(...requested.map((q,i)=>lastRequested[i].angleTo(q))):0;
      this.previousRequested[side]=requested.map(q=>q.clone());
      // Some flipper rigs intentionally touch the torso at rest. Do not turn that
      // authored contact into movement of the idle arm; moving limbs still solve.
      if(bones[0].userData.armCollisionRestContact===true&&chain.every((joint,i)=>
        joint.neutral&&rotations[i].angleTo(this.root.getWorldQuaternion(new THREE.Quaternion()).multiply(joint.neutral))<.001)){
        delete this.previous[side];
        delete this.corrected[side];
        this.previousPose[side]=rotations.map(q=>q.clone());
        continue;
      }
      const original=chain.map(({axis,rest},i)=>axis.clone().applyQuaternion(rest.clone().invert()).applyQuaternion(rotations[i]).normalize());
      let parentDirection=null;
      for(let i=0;i<3;i++){
        const start=point(bones[i]),length=i<2?lengths[i]:lengths[1]*.48;
        const radius=.2*Math.min(...lengths)+(i===0?.004:0);
        // Reserve room for a forward-pointing hand when placing the forearm.
        // Otherwise the wrist reaches the head first and has to flip to escape.
        const reach=i===1?length+lengths[1]*.48:length;
        const direction=this.avoid(start,original[i],reach,radius,i===0?.35:0,sign,parentDirection,(i===2?65:145)*Math.PI/180,history[i],corrected[i]&&trackingStep<=step);
        history[i]=direction.clone();
        const delta=new THREE.Quaternion().setFromUnitVectors(original[i],direction);
        corrected[i]=delta.angleTo(new THREE.Quaternion())>.001;
        const desired=delta.clone().multiply(bones[i].getWorldQuaternion(new THREE.Quaternion()));
        bones[i].quaternion.copy(bones[i].parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(desired)).normalize();
        bones[i].updateWorldMatrix(false,true);
        // Preserve child world orientation while moving its parent.
        if(i<2){
          const child=bones[i+1];
          if(i===1){
            // Preserve wrist bend relative to the deflected forearm, instead of
            // pointing the hand back into the obstacle the forearm just avoided.
            original[2].applyQuaternion(delta).normalize();
            rotations[2].premultiply(delta).normalize();
          }
          child.quaternion.copy(child.parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(rotations[i+1])).normalize();child.updateWorldMatrix(false,true);
        }
        parentDirection=direction;
      }
      const solved=bones.map(bone=>bone.getWorldQuaternion(new THREE.Quaternion()));
      if(lastPose&&corrected.some(Boolean)&&trackingStep<=step){
        const maxAngle=Math.max(...solved.map((q,i)=>lastPose[i].angleTo(q)));
        if(maxAngle>step&&step>0){
          const apply=amount=>{
            for(let i=0;i<3;i++){
              const world=lastPose[i].clone().slerp(solved[i],amount);
              bones[i].quaternion.copy(bones[i].parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(world)).normalize();
              bones[i].updateWorldMatrix(false,true);
            }
          };
          const feasible=()=>{
            let previousDirection=null;
            for(let i=0;i<3;i++){
              const rotation=bones[i].getWorldQuaternion(new THREE.Quaternion());
              const direction=chain[i].axis.clone().applyQuaternion(chain[i].rest.clone().invert()).applyQuaternion(rotation).normalize();
              if(previousDirection&&previousDirection.angleTo(direction)>(i===2?65:145)*Math.PI/180+1e-6)return false;
              const start=point(bones[i]),length=i<2?lengths[i]:lengths[1]*.48;
              const hit=this.contact(start,start.clone().addScaledVector(direction,length),.2*Math.min(...lengths)+(i===0?.004:0),i===0?.35:0);
              if(hit&&hit.distance<-.0005)return false;
              previousDirection=direction;
            }
            return true;
          };
          // A per-segment escape can jump when its parent moves. Interpolate the
          // whole chain only if Rapier confirms the intermediate pose is safe.
          let accepted=false;
          for(const scale of [1,.5,.25,.125,0]){
            apply(step/maxAngle*scale);
            if(feasible()){accepted=true;break;}
          }
          if(!accepted)apply(1);
        }
      }
      this.previousPose[side]=bones.map(bone=>bone.getWorldQuaternion(new THREE.Quaternion()));
      for(let i=0;i<3;i++){
        history[i]=chain[i].axis.clone().applyQuaternion(chain[i].rest.clone().invert()).applyQuaternion(this.previousPose[side][i]).normalize();
        corrected[i]=requested[i].angleTo(this.previousPose[side][i])>.001;
        if(corrected[i])this.adjustments++;
        const start=point(bones[i]),length=i<2?lengths[i]:lengths[1]*.48;
        const hit=this.contact(start,start.clone().addScaledVector(history[i],length),.2*Math.min(...lengths)+(i===0?.004:0),i===0?.35:0);
        if(hit)this.penetration=Math.max(this.penetration,-hit.distance);
      }
    }
    this.durationMs=performance.now()-started;
  }
}
