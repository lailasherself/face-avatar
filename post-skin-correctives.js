import * as THREE from 'three';

// Pose-space deltas describe the final deformed surface, not rest-space offsets.
// Keep them out of ordinary pre-skin morphing, including depth and CPU queries.
export function attachPostSkinCorrectives(mesh,samples){
  const first=mesh.morphTargetDictionary[samples[0].key];
  const positions=mesh.geometry.morphAttributes.position;
  if(first===undefined||!mesh.geometry.morphTargetsRelative)throw new Error('Invalid post-skin morph layout');
  const normals=mesh.geometry.morphAttributes.normal||positions.map(()=>new THREE.Float32BufferAttribute(new Float32Array(mesh.geometry.attributes.position.count*3),3));
  for(const [i,sample] of samples.entries()){
    const normal=mesh.geometry.getAttribute(`_psd_n_${i}`);
    if(!normal)throw new Error(`Missing post-skin normal data: ${mesh.name}`);
    normals[mesh.morphTargetDictionary[sample.key]]=normal;
    mesh.geometry.deleteAttribute(`_psd_n_${i}`);mesh.geometry.deleteAttribute(`_psd_p_${i}`);
  }
  mesh.geometry.morphAttributes.normal=normals;
  const patch=material=>{
    material.onBeforeCompile=shader=>{
      shader.vertexShader=shader.vertexShader.replace('#include <morphnormal_vertex>',`
vec3 postSkinNormal = vec3(0.0);
#ifdef USE_MORPHNORMALS
objectNormal *= morphTargetBaseInfluence;
for (int i = 0; i < MORPHTARGETS_COUNT; i++) {
  vec3 delta = getMorph(gl_VertexID, i, 1).xyz * morphTargetInfluences[i];
  if (i >= ${first}) postSkinNormal += delta; else objectNormal += delta;
}
#endif`);
      shader.vertexShader=shader.vertexShader.replace('#include <skinnormal_vertex>',`#include <skinnormal_vertex>
objectNormal = objectNormal / max(length(objectNormal), 0.000001) + postSkinNormal;`);
      shader.vertexShader=shader.vertexShader.replace('#include <morphtarget_vertex>',`
vec3 postSkinPosition = vec3(0.0);
#ifdef USE_MORPHTARGETS
transformed *= morphTargetBaseInfluence;
for (int i = 0; i < MORPHTARGETS_COUNT; i++) {
  vec3 delta = getMorph(gl_VertexID, i, 0).xyz * morphTargetInfluences[i];
  if (i >= ${first}) postSkinPosition += delta; else transformed += delta;
}
#endif`);
      shader.vertexShader=shader.vertexShader.replace('#include <skinning_vertex>',`#include <skinning_vertex>
transformed += postSkinPosition;`);
    };
    material.customProgramCacheKey=()=>`post-skin-correctives-v1-${first}`;material.needsUpdate=true;
  };
  for(const material of Array.isArray(mesh.material)?mesh.material:[mesh.material])patch(material);
  mesh.customDepthMaterial=new THREE.MeshDepthMaterial({depthPacking:THREE.RGBADepthPacking});patch(mesh.customDepthMaterial);
  const offset=new THREE.Vector3();
  mesh.getVertexPosition=function(index,target){
    target.fromBufferAttribute(this.geometry.attributes.position,index);
    for(let i=0;i<first;i++)if(this.morphTargetInfluences[i])target.addScaledVector(offset.fromBufferAttribute(positions[i],index),this.morphTargetInfluences[i]);
    this.applyBoneTransform(index,target);
    for(let i=first;i<positions.length;i++)if(this.morphTargetInfluences[i])target.addScaledVector(offset.fromBufferAttribute(positions[i],index),this.morphTargetInfluences[i]);
    return target;
  };
}
