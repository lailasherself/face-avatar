import * as THREE from 'three';
export {EyeSignalFilter,resolveEyeAperture} from './eye-signals.js';

// Linear morph interpolation cuts through an ellipsoid. Reproject only tagged lid
// vertices after morphing, before skinning, to keep every intermediate pose outside it.
export function attachEyelidSurface(mesh,surfaces){
  if(!mesh.geometry.getAttribute('_lid_index')||!surfaces?.length)return false;
  const centers=surfaces.map(s=>new THREE.Vector3(...s.center));
  const radii=surfaces.map(s=>new THREE.Vector3(...s.radii));
  function patch(material,normals){
    material.onBeforeCompile=shader=>{
      shader.uniforms.lidCenters={value:centers};shader.uniforms.lidRadii={value:radii};
      shader.vertexShader=`attribute float _lid_index;
uniform vec3 lidCenters[${centers.length}];
uniform vec3 lidRadii[${centers.length}];
`+shader.vertexShader;
      shader.vertexShader=shader.vertexShader.replace('#include <morphtarget_vertex>',`#include <morphtarget_vertex>
vec3 lidSurfaceNormal = vec3(0.0);
if (_lid_index > 0.5) {
  int lid = int(_lid_index + 0.5) - 1;
  vec3 radial = normalize((transformed - lidCenters[lid]) / lidRadii[lid]);
  transformed = lidCenters[lid] + radial * lidRadii[lid];
  lidSurfaceNormal = normalize(radial / lidRadii[lid]);
}`);
      if(normals)shader.vertexShader=shader.vertexShader.replace('#include <skinning_vertex>',`#include <skinning_vertex>
if (_lid_index > 0.5) {
  #ifdef USE_SKINNING
    lidSurfaceNormal = (skinMatrix * vec4(lidSurfaceNormal, 0.0)).xyz;
  #endif
  #ifndef FLAT_SHADED
    vNormal = normalize(normalMatrix * lidSurfaceNormal);
  #endif
}`);
    };
    material.customProgramCacheKey=()=>`fleet-lid-surface-${centers.length}-${normals}`;
    material.needsUpdate=true;
  }
  const materials=Array.isArray(mesh.material)?mesh.material:[mesh.material];
  for(const m of materials)patch(m,true);
  mesh.customDepthMaterial=new THREE.MeshDepthMaterial({depthPacking:THREE.RGBADepthPacking});
  patch(mesh.customDepthMaterial,false);
  return true;
}
