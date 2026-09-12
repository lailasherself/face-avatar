import * as THREE from 'three';

// Bake the neutral pose once. Background characters need neither skeleton updates
// nor the live rig's large facial morph buffers on the GPU.
export function freezeCharacter(root) {
  root.updateMatrixWorld(true);
  root.traverse(o=>{if(o.isSkinnedMesh)o.skeleton.update();});
  const group=new THREE.Group(), inverse=root.matrixWorld.clone().invert();
  const vertex=new THREE.Vector3();
  root.traverse(o=>{
    if(!o.isMesh)return;
    const geometry=new THREE.BufferGeometry();
    geometry.setIndex(o.geometry.index?.clone()||null);
    for(const [name,attribute] of Object.entries(o.geometry.attributes)){
      if(name==='skinIndex'||name==='skinWeight'||name.startsWith('corrective'))continue;
      geometry.setAttribute(name,attribute.clone());
    }
    for(const g of o.geometry.groups)geometry.addGroup(g.start,g.count,g.materialIndex);
    geometry.setDrawRange(o.geometry.drawRange.start,o.geometry.drawRange.count);
    const positions=geometry.attributes.position;
    for(let i=0;i<positions.count;i++){
      o.getVertexPosition(i,vertex);positions.setXYZ(i,vertex.x,vertex.y,vertex.z);
    }
    geometry.computeVertexNormals();geometry.computeBoundingBox();geometry.computeBoundingSphere();
    const material=Array.isArray(o.material)?o.material.map(m=>m.clone()):o.material.clone();
    const mesh=new THREE.Mesh(geometry,material);
    mesh.applyMatrix4(inverse.clone().multiply(o.matrixWorld));
    group.add(mesh);
  });
  return group;
}

export class FleetStage {
  constructor(scene,camera){
    this.scene=scene;this.camera=camera;this.entries=new Map();this.selected=-1;this.count=0;
    this.backdrop=new THREE.Scene();
    this.backdrop.environment=scene.environment;
    for(const child of scene.children)if(child.isLight)this.backdrop.add(child.clone());
    this.target=new THREE.WebGLRenderTarget(1,1,{type:THREE.HalfFloatType});
    const material=new THREE.ShaderMaterial({
      uniforms:{map:{value:this.target.texture}},transparent:true,depthWrite:false,
      vertexShader:'varying vec2 vUv; void main(){vUv=uv;gl_Position=vec4(position.xy,1.0,1.0);}',
      fragmentShader:'uniform sampler2D map; varying vec2 vUv; void main(){gl_FragColor=texture2D(map,vUv);\n#include <tonemapping_fragment>\n#include <colorspace_fragment>\n}',
    });
    const background=new THREE.Mesh(new THREE.PlaneGeometry(2,2),material);
    background.frustumCulled=false;background.renderOrder=-1;scene.add(background);
    this.dirty=true;this.backdropFrames=0;
  }
  add(index,rig){
    const preview=freezeCharacter(rig);
    const bounds=new THREE.Box3().setFromObject(preview);
    const entry={rig,preview,bounds,target:new THREE.Vector3(),scale:1};
    this.entries.set(index,entry);this.scene.add(rig);this.backdrop.add(preview);
    rig.visible=index===this.selected;preview.visible=!rig.visible;
    this.layout(true);
  }
  select(index,count){
    this.selected=index;this.count=count;
    for(const [i,e] of this.entries){e.rig.visible=i===index;e.preview.visible=i!==index;}
    this.layout(true);
  }
  layout(snap=false){
    this.dirty=true;
    const {camera,count,selected}=this;if(count<2)return;
    camera.updateMatrixWorld();
    const portrait=camera.aspect<1;
    for(const [index,e] of this.entries){
      if(index===selected)continue;
      const slot=(index-selected-1+count)%count;
      const columns=portrait?4:count-1,row=portrait?Math.floor(slot/columns):0;
      const n=portrait?Math.min(columns,count-1-row*columns):columns;
      const x=((slot%columns+.5)/n*2-1)*.92;
      const y=portrait?.79-row*.31:.66;
      const depth=12;
      const height=2*depth*Math.tan(THREE.MathUtils.degToRad(camera.fov/2));
      const size=e.bounds.getSize(new THREE.Vector3());
      e.scale=Math.min(height*(portrait?.26:.43)/2/size.y,height*camera.aspect*.84/n/size.x);
      const center=new THREE.Vector3(x*height*camera.aspect/2,y*height/2,-depth).applyMatrix4(camera.matrixWorld);
      e.target.copy(center).addScaledVector(e.bounds.getCenter(new THREE.Vector3()),-e.scale);
      if(snap){e.preview.position.copy(e.target);e.preview.scale.setScalar(e.scale);}
    }
  }
  renderBackdrop(renderer){
    const size=renderer.getDrawingBufferSize(new THREE.Vector2());
    if(this.target.width!==size.x||this.target.height!==size.y){this.target.setSize(size.x,size.y);this.dirty=true;}
    if(!this.dirty)return;
    // The cast is motionless between selections. Cache its 3D render, not eight
    // full-resolution draws on every camera frame; leave the GPU for tracking.
    const previous=renderer.getRenderTarget(),alpha=renderer.getClearAlpha();
    renderer.setClearAlpha(0);renderer.setRenderTarget(this.target);renderer.render(this.backdrop,this.camera);
    renderer.setRenderTarget(previous);renderer.setClearAlpha(alpha);
    this.dirty=false;this.backdropFrames++;
  }
  snapshot(){
    return [...this.entries].map(([index,e])=>{
      const box=e.bounds.clone();
      if(index===this.selected)box.translate(e.rig.position);
      else {box.min.multiplyScalar(e.scale).add(e.target);box.max.multiplyScalar(e.scale).add(e.target);}
      const points=[];
      for(const x of [box.min.x,box.max.x])for(const y of [box.min.y,box.max.y])for(const z of [box.min.z,box.max.z])points.push(new THREE.Vector3(x,y,z).project(this.camera));
      return {index,active:e.rig.visible,background:e.preview.visible,
        position:e.preview.position.toArray(),scale:e.scale,meshes:e.preview.children.length,
        screen:{left:Math.min(...points.map(p=>p.x)),right:Math.max(...points.map(p=>p.x)),bottom:Math.min(...points.map(p=>p.y)),top:Math.max(...points.map(p=>p.y))}};
    });
  }
}
