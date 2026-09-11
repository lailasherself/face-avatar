import * as THREE from 'three';
import {attachPostSkinCorrectives} from './post-skin-correctives.js';

// Independent arm neighborhoods prevent one raised arm from applying the other
// shoulder's correction. The neutral sample has zero additive displacement.
export class PoseCorrectives {
  constructor(root,clips){
    this.root=root;this.meshes=[];
    const poses=new Map(clips.map(clip=>[clip.name,new Map(clip.tracks.filter(t=>t.name.endsWith('.quaternion')).map(t=>[t.name.slice(0,-11),new THREE.Quaternion().fromArray(t.values)]))]));
    root.traverse(mesh=>{
      if(!mesh.morphTargetDictionary)return;
      let owner=mesh;
      while(owner&&!owner.userData.correctiveSamples)owner=owner.parent;
      if(!owner)return;
      const samples=owner.userData.correctiveSamples.map(sample=>({...sample,index:mesh.morphTargetDictionary[sample.key]}));
      if(owner.userData.correctiveSpace==='postSkin')attachPostSkinCorrectives(mesh,samples);
      const standing=samples.filter(s=>s.basePose==='Standing'&&s.region!=='Base');
      if(owner.userData.correctiveSpace==='postSkin'){
        // Rebase the seated upper-body deltas onto Standing without transferring
        // seated leg corrections. Original GLB morphs remain unchanged.
        const geometry=mesh.geometry,a=geometry.attributes;
        const seated=mesh.morphTargetDictionary.correctiveSeated,stand=mesh.morphTargetDictionary.correctiveStanding;
        for(const sample of [...samples].filter(s=>s.region!=='Base'&&s.basePose!=='Standing'&&!standing.some(t=>t.region===s.region))){
          const key=sample.key+'Standing',index=geometry.morphAttributes.position.length;
          for(const kind of ['position','normal']){
            const attrs=geometry.morphAttributes[kind],data=new Float32Array(a.position.count*3);
            for(let i=0;i<a.position.count;i++){
              let upper=0;
              for(let j=0;j<4;j++){
                const name=mesh.skeleton.bones[a.skinIndex.getComponent(i,j)]?.name||'';
                if(sample.region==='Head'?/^(Head|Neck)$/.test(name):/^(Head|Neck|Chest|Spine|UpperArm|Forearm|Hand)/.test(name))upper+=a.skinWeight.getComponent(i,j);
              }
              const side=sample.region==='Head'?1:THREE.MathUtils.clamp((a.position.getX(i)*(sample.region==='L'?1:-1)+.03)/.06,0,1);
              for(let k=0;k<3;k++)data[i*3+k]=(attrs[sample.index].getComponent(i,k)+
                (attrs[seated].getComponent(i,k)-attrs[stand].getComponent(i,k))*side)*upper;
            }
            attrs.push(new THREE.Float32BufferAttribute(data,3));
          }
          mesh.morphTargetDictionary[key]=index;mesh.morphTargetInfluences.push(0);
          standing.push({...sample,key,index});
        }
      }
      const regions={};
      for(const region of ['L','R','Head']){
        const bones=[];
        root.traverse(bone=>{if(bone.isBone&&(region==='Head'?bone.name==='Head':new RegExp(`^(UpperArm|Forearm|Hand)\\.?${region}$`).test(bone.name)))bones.push(bone);});
        const make=sample=>({...sample,targets:bones.map(bone=>({bone,q:poses.get(sample.clip)?.get(bone.name)})).filter(t=>t.q)});
        for(const base of ['Seated','Standing'])regions[base+region]=[{clip:base,index:null},...(base==='Standing'?standing:samples.filter(s=>s.basePose!=='Standing')).filter(s=>s.region===region)].map(make).filter(s=>s.targets.length===bones.length&&bones.length);
      }
      samples.push(...standing.filter(s=>!samples.includes(s)));
      this.meshes.push({mesh,samples,regions});
    });
  }
  update(basePose){
    for(const {mesh,samples,regions} of this.meshes){
      for(const sample of samples)mesh.morphTargetInfluences[sample.index]=sample.region==='Base'&&sample.clip===basePose?1:0;
      if(!['Seated','Standing'].includes(basePose))continue;
      for(const [region,neighbors] of Object.entries(regions)){
        if(!region.startsWith(basePose)||!neighbors.length)continue;
        const weights=neighbors.map(sample=>{
          const distance=sample.targets.reduce((sum,{bone,q})=>sum+1-Math.min(1,bone.quaternion.dot(q)**2),0)/sample.targets.length;
          return 1/(distance+.0001)**2;
        });
        const total=weights.reduce((sum,v)=>sum+v,0);
        neighbors.forEach((sample,i)=>{if(sample.index!=null)mesh.morphTargetInfluences[sample.index]=weights[i]/total;});
      }
    }
  }
}
