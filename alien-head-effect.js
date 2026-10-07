import * as THREE from 'three';

const point=new THREE.Vector3();

function headGeometry(mesh,head){
  const source=mesh.geometry,weights=source.attributes.skinWeight,indices=source.attributes.skinIndex;
  if(!mesh.isSkinnedMesh||!weights||!indices)return null;
  const family=new Set();head.traverse(o=>{if(o.isBone)family.add(o);});
  const joints=new Set(mesh.skeleton.bones.map((b,i)=>family.has(b)?i:-1));joints.delete(-1);
  const included=new Uint8Array(weights.count);
  for(let i=0;i<weights.count;i++){
    let weight=0;
    for(let k=0;k<4;k++)if(joints.has(indices.getComponent(i,k)))weight+=weights.getComponent(i,k);
    included[i]=weight>=.5?1:0;
  }
  const index=source.index,output=[],groups=[];
  for(const group of source.groups.length?source.groups:[{start:0,count:index?.count??weights.count,materialIndex:0}]){
    const start=output.length;
    for(let i=group.start;i<group.start+group.count;i+=3){
      const a=index?index.getX(i):i,b=index?index.getX(i+1):i+1,c=index?index.getX(i+2):i+2;
      if(included[a]&&included[b]&&included[c])output.push(a,b,c);
    }
    if(output.length>start)groups.push({start,count:output.length-start,materialIndex:group.materialIndex});
  }
  if(!output.length)return null;
  // Share immutable vertex/morph buffers; only the head's triangle index is new.
  const geometry=new THREE.BufferGeometry();
  for(const [name,attribute] of Object.entries(source.attributes))geometry.setAttribute(name,attribute);
  geometry.morphAttributes=source.morphAttributes;geometry.morphTargetsRelative=source.morphTargetsRelative;
  geometry.setIndex(output);geometry.groups=groups;
  return geometry;
}

export function facePlacement(landmarks,width,height){
  if(!landmarks||![10,152,234,454].every(i=>landmarks[i]&&Number.isFinite(landmarks[i].x)&&Number.isFinite(landmarks[i].y)))return null;
  const top=landmarks[10],chin=landmarks[152],left=landmarks[234],right=landmarks[454];
  const distance=(a,b)=>Math.hypot((a.x-b.x)*width,(a.y-b.y)*height);
  const faceWidth=distance(left,right),faceHeight=distance(top,chin);
  if(faceWidth<24||faceHeight<30||faceWidth>width*.9)return null;
  return {x:(top.x+chin.x)*width/2-width/2,y:height/2-(top.y+chin.y)*height/2,
    width:faceWidth,height:faceHeight};
}

export class AlienHeadEffect {
  constructor(renderer,scene){
    this.renderer=renderer;this.scene=scene;this.records=new WeakMap();
    this.canvas=document.createElement('canvas');this.canvas.id='ar-composite';
    this.context=this.canvas.getContext('2d');this.frame=null;this.sample=null;this.renderedAt=0;this.frames=0;
    this.camera=new THREE.OrthographicCamera(-1,1,1,-1,.1,10000);this.camera.position.z=5000;
    this.target=new THREE.WebGLRenderTarget(1,1);this.target.texture.colorSpace=THREE.SRGBColorSpace;
    this.layer=document.createElement('canvas');this.layerContext=this.layer.getContext('2d');
  }
  accept(result,person){
    this.frame?.close();this.frame=result.frame;this.sample={...result,person};
    if(!this.frame)this.sample=null;
  }
  clear(){this.frame?.close();this.frame=null;this.sample=null;this.renderedAt=0;this.context.clearRect(0,0,this.canvas.width,this.canvas.height);}
  fresh(person,now=performance.now(),maxAge=250){
    return !!this.sample&&this.sample.person===person&&this.sample.faceLandmarks?.length===1&&
      now-this.sample.captureTime>=0&&now-this.sample.captureTime<maxAge&&!!this.sample.facialTransformationMatrixes?.[0]?.data;
  }
  prepare(record){
    if(this.records.has(record))return this.records.get(record);
    const root=record.gltf.scene,head=record.head,entries=[],core=new THREE.Box3(),all=new THREE.Box3();
    if(!head)throw new Error('This alien has no head attachment');
    const rotation=head.quaternion.clone();head.quaternion.copy(record.headRest);root.updateMatrixWorld(true);
    root.traverse(mesh=>{
      if(!mesh.isMesh)return;
      if(mesh.isSkinnedMesh)mesh.skeleton.update();
      const geometry=headGeometry(mesh,head);entries.push({mesh,geometry});
      if(!geometry)return;
      const box=new THREE.Box3();
      for(const i of new Set(geometry.index.array)){
        mesh.getVertexPosition(i,point);point.applyMatrix4(mesh.matrixWorld);box.expandByPoint(point);
      }
      all.union(box);
      let owner=mesh;
      while(owner&&owner!==root){
        if(/(?: head(?: \d+)?$| skin(?: \d+)?$|sourcebody(?: \d+)?$)/i.test(owner.name.replace(/_/g,' '))){core.union(box);break;}
        owner=owner.parent;
      }
    });
    head.quaternion.copy(rotation);root.updateMatrixWorld(true);
    if(core.isEmpty())core.copy(all);
    if(core.isEmpty())throw new Error('This alien has no head geometry');
    const result={entries,center:core.getCenter(new THREE.Vector3()),size:core.getSize(new THREE.Vector3())};
    this.records.set(record,result);return result;
  }
  render(record,person,{mirror=true,fit=1}={}){
    if(!this.fresh(person))return false;
    const {frame,sample,renderer,scene,camera,target}=this;
    const width=frame.width,height=frame.height,placement=facePlacement(sample.faceLandmarks[0],width,height);
    if(!placement)return false;
    const prepared=this.prepare(record),root=record.gltf.scene,head=record.head;
    const scale=Math.max(placement.width*1.5/prepared.size.x,placement.height*1.45/prepared.size.y)*fit;
    const matrix=new THREE.Matrix4().fromArray(sample.facialTransformationMatrixes[0].data);
    const rotation=new THREE.Quaternion().setFromRotationMatrix(matrix).normalize();
    const centerY=placement.y+(prepared.size.y*scale-placement.height)/2-placement.height*.04;
    const transform=new THREE.Matrix4().makeTranslation(placement.x,centerY,0)
      .multiply(new THREE.Matrix4().makeRotationFromQuaternion(rotation))
      .multiply(new THREE.Matrix4().makeScale(scale,scale,scale))
      .multiply(new THREE.Matrix4().makeTranslation(-prepared.center.x,-prepared.center.y,-prepared.center.z));
    root.updateMatrixWorld(true);
    const saved={matrix:root.matrix.clone(),auto:root.matrixAutoUpdate,head:head.quaternion.clone(),
      target:renderer.getRenderTarget(),background:scene.background,clear:renderer.getClearColor(new THREE.Color()),alpha:renderer.getClearAlpha()};
    const meshes=[],materials=new Map();
    scene.traverse(mesh=>{
      if(!mesh.isMesh)return;
      meshes.push({mesh,visible:mesh.visible,geometry:mesh.geometry});mesh.visible=false;
    });
    try{
      for(const {mesh,geometry} of prepared.entries){if(geometry){mesh.geometry=geometry;mesh.visible=true;}}
      for(const {mesh} of meshes)for(const material of Array.isArray(mesh.material)?mesh.material:[mesh.material]){
        if(!materials.has(material)){materials.set(material,material.clippingPlanes);material.clippingPlanes=[];}
      }
      head.quaternion.copy(record.headRest);
      root.matrixAutoUpdate=false;
      root.matrix.copy(root.parent.matrixWorld.clone().invert().multiply(transform).multiply(root.matrixWorld));
      root.updateMatrixWorld(true);
      camera.left=-width/2;camera.right=width/2;camera.top=height/2;camera.bottom=-height/2;camera.updateProjectionMatrix();
      if(target.width!==width||target.height!==height){target.setSize(width,height);this.layer.width=width;this.layer.height=height;
        this.pixels=new Uint8Array(width*height*4);this.imageData=this.layerContext.createImageData(width,height);}
      scene.background=null;renderer.setClearColor(0x000000,0);renderer.setRenderTarget(target);renderer.render(scene,camera);
      renderer.readRenderTargetPixels(target,0,0,width,height,this.pixels);
      for(let y=0;y<height;y++)this.imageData.data.set(this.pixels.subarray((height-1-y)*width*4,(height-y)*width*4),y*width*4);
      this.layerContext.putImageData(this.imageData,0,0);
      if(this.canvas.width!==width||this.canvas.height!==height){this.canvas.width=width;this.canvas.height=height;}
      const ctx=this.context;ctx.save();ctx.clearRect(0,0,width,height);
      if(mirror){ctx.translate(width,0);ctx.scale(-1,1);}
      ctx.drawImage(frame,0,0);ctx.drawImage(this.layer,0,0);ctx.restore();
      this.renderedAt=sample.captureTime;this.character=record.info.id;this.frames++;
      this.placement=placement;return true;
    }finally{
      for(const {mesh,visible,geometry} of meshes){mesh.visible=visible;mesh.geometry=geometry;}
      for(const [material,planes] of materials)material.clippingPlanes=planes;
      head.quaternion.copy(saved.head);root.matrix.copy(saved.matrix);root.matrixAutoUpdate=saved.auto;root.updateMatrixWorld(true);
      scene.background=saved.background;renderer.setRenderTarget(saved.target);renderer.setClearColor(saved.clear,saved.alpha);
    }
  }
  snapshot(record,person,options){
    if(!this.render(record,person,options))throw new Error('Face tracking was lost. Face the camera and try again.');
    const copy=document.createElement('canvas');copy.width=this.canvas.width;copy.height=this.canvas.height;
    copy.getContext('2d').drawImage(this.canvas,0,0);return copy;
  }
  cameraOnly(person){
    const {frame,sample,canvas,context:ctx}=this;
    if(!frame||sample.person!==person||performance.now()-sample.captureTime>250){ctx.clearRect(0,0,canvas.width,canvas.height);return;}
    if(canvas.width!==frame.width||canvas.height!==frame.height){canvas.width=frame.width;canvas.height=frame.height;}
    ctx.save();ctx.translate(canvas.width,0);ctx.scale(-1,1);ctx.drawImage(frame,0,0);ctx.restore();
    this.renderedAt=0;
  }
}
