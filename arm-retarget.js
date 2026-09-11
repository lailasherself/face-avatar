import * as THREE from 'three';

export class ArmRetargeter {
  constructor(root){
    this.root=root;this.chains={};
    root.updateWorldMatrix(true,true);
    const rootInverse=root.getWorldQuaternion(new THREE.Quaternion()).invert();
    for(const side of ['L','R']){
      const find=name=>root.getObjectByName(`${name}.${side}`)||root.getObjectByName(`${name}${side}`);
      const bones=['UpperArm','Forearm','Hand'].map(find);
      if(bones.some(b=>!b))continue;
      this.chains[side]=bones.map((bone,i)=>{
        const child=bones[i+1]||find('Finger2');
        const rest=rootInverse.clone().multiply(bone.getWorldQuaternion(new THREE.Quaternion())).normalize();
        const axis=child?child.position.clone().normalize():new THREE.Vector3(0,1,0);
        return {bone,rest,axis:axis.applyQuaternion(rest)};
      });
    }
  }
  captureNeutral(){
    const inverse=this.root.getWorldQuaternion(new THREE.Quaternion()).invert();
    for(const chain of Object.values(this.chains))for(const joint of chain){
      joint.neutral=inverse.clone().multiply(joint.bone.getWorldQuaternion(new THREE.Quaternion())).normalize();
      joint.filtered=joint.bone.getWorldQuaternion(new THREE.Quaternion());
    }
  }
  update(arms,dt){
    const alpha=1-Math.exp(-Math.min(dt,.1)*30);
    this.root.updateWorldMatrix(true,true);
    const rootRotation=this.root.getWorldQuaternion(new THREE.Quaternion());
    for(const [side,chain] of Object.entries(this.chains)){
      // Snapshot before moving parents: filtering local joints in sequence makes
      // each child chase an already-filtered parent and adds a second phase lag.
      const previous=chain.map(({bone,filtered})=>filtered?.clone()||bone.getWorldQuaternion(new THREE.Quaternion()));
      for(const [i,joint] of chain.entries()){
        const {bone,rest,axis,neutral}=joint;
        const direction=arms?.[side]?.[['upper','lower','hand'][i]]||(i===2?arms?.[side]?.lower:null);
        let target=(neutral||rest).clone();
        if(direction?.length===3&&direction.every(Number.isFinite)&&Math.hypot(...direction)>1e-6){
          const desired=new THREE.Vector3(...direction).normalize();
          const absolute=rest.clone().premultiply(new THREE.Quaternion().setFromUnitVectors(axis,desired));
          const previous=joint.solved||neutral||rest;
          const previousAxis=axis.clone().applyQuaternion(rest.clone().invert()).applyQuaternion(previous).normalize();
          target.copy(previous).premultiply(new THREE.Quaternion().setFromUnitVectors(previousAxis,desired));
          // Transport roll continuously through the rest-axis antipode, where a
          // fresh shortest-arc rotation is ambiguous. Recenter twist slowly only
          // away from that singularity and while moving, never on an idle arm.
          // Both quaternions share the same direction.
          if(axis.dot(desired)>-.8&&previousAxis.angleTo(desired)>.002)target.slerp(absolute,1-Math.exp(-dt*3));
          if(i===2&&!arms?.[side]?.hand&&chain[1].solved){
            target.copy(chain[1].solved).multiply(chain[1].rest.clone().invert()).multiply(rest);
            const inherited=axis.clone().applyQuaternion(rest.clone().invert()).applyQuaternion(target).normalize();
            target.premultiply(new THREE.Quaternion().setFromUnitVectors(inherited,desired));
          }
        }
        joint.solved=target.clone().normalize();
        target.premultiply(rootRotation);
        const world=previous[i].normalize().slerp(target.normalize(),alpha).normalize();
        // Collision corrections are output constraints, not new tracking input.
        // Feeding them back here made the wrist chase a deflected forearm.
        chain[i].filtered=world.clone();
        bone.quaternion.copy(bone.parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(world)).normalize();
        bone.updateWorldMatrix(false,true);
      }
    }
  }
}
