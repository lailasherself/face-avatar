import * as THREE from 'three';

// A grin retracts the lips without opening the dental bite. Keep this correction
// in mesh coordinates so the existing head skinning also moves the teeth.
export function attachSmileBite(root,{centerDrop=0,forward=0}={}){
  root.updateMatrixWorld(true);
  const rows={upper:[],lower:[]},boxes={upper:new THREE.Box3(),lower:new THREE.Box3()};
  const point=new THREE.Vector3();
  root.traverse(mesh=>{
    if(!mesh.isMesh||mesh.morphTargetDictionary?.smileBite!==undefined)return;
    const label=mesh.name+' '+(mesh.material?.name||'');
    if(!/teeth|dental|gingiva|gums/i.test(label))return;
    const row=/upper/i.test(label)?'upper':/lower/i.test(label)?'lower':null;
    if(!row)return;
    mesh.skeleton?.update();rows[row].push(mesh);
    if(/gingiva|gums/i.test(label))return;
    for(let i=0;i<mesh.geometry.attributes.position.count;i++){
      mesh.getVertexPosition(i,point);boxes[row].expandByPoint(point.applyMatrix4(mesh.matrixWorld));
    }
  });
  if(boxes.upper.isEmpty()||boxes.lower.isEmpty())return;
  const gap=boxes.upper.min.y-boxes.lower.max.y;
  const crownHeight=Math.min(boxes.upper.max.y-boxes.upper.min.y,boxes.lower.max.y-boxes.lower.min.y);
  const clearance=crownHeight*.025;
  const drop=Number.isFinite(centerDrop)?THREE.MathUtils.clamp(centerDrop,0,1)*crownHeight:0;
  const advance=Number.isFinite(forward)?THREE.MathUtils.clamp(forward,0,3)*crownHeight:0;
  for(const row of ['upper','lower'])for(const mesh of rows[row]){
    const geometry=mesh.geometry,position=geometry.attributes.position;
    const offset=new THREE.Vector3(0,(gap-clearance)*(row==='upper'?-.5:.5)-drop,advance);
    const inverseWorld=mesh.matrixWorld.clone().invert();
    const data=new Float32Array(position.count*3),skin=new THREE.Matrix4(),bone=new THREE.Matrix4();
    for(let i=0;i<position.count;i++){
      skin.identity();
      if(mesh.isSkinnedMesh){
        skin.elements.fill(0);
        for(let j=0;j<4;j++){
          const index=geometry.attributes.skinIndex.getComponent(i,j),weight=geometry.attributes.skinWeight.getComponent(i,j);
          bone.fromArray(mesh.skeleton.boneMatrices,index*16);
          for(let k=0;k<16;k++)skin.elements[k]+=bone.elements[k]*weight;
        }
        skin.premultiply(mesh.bindMatrixInverse).multiply(mesh.bindMatrix).invert();
      }
      const transform=skin.multiply(inverseWorld);
      point.copy(offset).applyMatrix3(new THREE.Matrix3().setFromMatrix4(transform));
      if(!geometry.morphTargetsRelative)point.add(new THREE.Vector3().fromBufferAttribute(position,i));
      point.toArray(data,i*3);
    }
    const morphs=geometry.morphAttributes.position||[];
    const names=Object.entries(mesh.morphTargetDictionary||{});
    geometry.morphAttributes.position=[...morphs,new THREE.Float32BufferAttribute(data,3)];
    if(geometry.morphAttributes.normal){
      const normal=geometry.morphTargetsRelative?new THREE.Float32BufferAttribute(new Float32Array(data.length),3):geometry.attributes.normal.clone();
      geometry.morphAttributes.normal.push(normal);
    }
    mesh.updateMorphTargets();
    mesh.morphTargetDictionary=Object.fromEntries([...names,['smileBite',morphs.length]]);
  }
}
