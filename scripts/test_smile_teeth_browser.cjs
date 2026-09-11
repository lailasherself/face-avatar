const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const out='.context/qa/smile-teeth';
const count=require('../assets/3dai/manifest.json').characters.length;

(async()=>{
 fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 const report=[],errors=[];
 try{
  const page=await browser.newPage({viewport:{width:800,height:600}});
  page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>{navigator.mediaDevices.getUserMedia=async()=>{throw new DOMException('Synthetic expression test','NotAllowedError');};});
  await page.route('**/fleet.js',async route=>{
   const response=await route.fetch();
   await route.fulfill({response,body:await response.text()+`
window.smileTest={
 async select(index){
  await selectCharacter(index);renderer.setAnimationLoop(null);
  current.gltf.scene.updateMatrixWorld(true);
  const teeth=[];current.gltf.scene.traverse(o=>{if(o.isMesh&&/teeth|dental/i.test(o.material?.name||o.name))teeth.push(o);});
  if(!teeth.length)throw Error('Missing dental geometry: '+current.info.id);
  const box=new THREE.Box3(),v=new THREE.Vector3();
  for(const mesh of teeth){mesh.skeleton?.update();for(let i=0;i<mesh.geometry.attributes.position.count;i++){mesh.getVertexPosition(i,v);box.expandByPoint(v.applyMatrix4(mesh.matrixWorld));}}
  const center=box.getCenter(new THREE.Vector3()),size=box.getSize(new THREE.Vector3());
  controls.target.copy(center);camera.position.copy(center).add(new THREE.Vector3(0,0,Math.max(.5,size.x*2.5)));camera.lookAt(center);camera.updateMatrixWorld();
  return current.info.id;
 },
 render(input,old=false){
  const values=old?{...input}:resolveMouth({...input});
  for(const mesh of current.meshes)for(const [name,i] of Object.entries(mesh.morphTargetDictionary)){
   const material=mesh.material?.name||'',value=values[name]||0;
   mesh.morphTargetInfluences[i]=old&&/oral interior|tongue/i.test(material)&&name.startsWith('mouth')&&name!=='mouthClose'?0:oralWeight(name,value,material);
  }
  current.gltf.scene.updateMatrixWorld(true);
  const materials=[],hidden=[];
  for(const child of scene.children)if(child.isMesh&&child.material?.isShaderMaterial){hidden.push([child,child.visible]);child.visible=false;}
  renderer.render(scene,camera);const image=renderer.domElement.toDataURL('image/png');
  const black=new THREE.MeshBasicMaterial({color:0,side:THREE.DoubleSide,toneMapped:false}),white=new THREE.MeshBasicMaterial({color:0xffffff,side:THREE.DoubleSide,toneMapped:false});
  scene.traverse(o=>{if(o.isMesh){materials.push([o,o.material]);o.material=/teeth|dental/i.test(o.material?.name||o.name)?white:black;}});
  const background=scene.background;scene.background=new THREE.Color(0);renderer.render(scene,camera);
  const gl=renderer.getContext(),pixels=new Uint8Array(800*600*4);gl.readPixels(0,0,800,600,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
  let visible=0;for(let i=0;i<pixels.length;i+=4)if(pixels[i]>240&&pixels[i+1]>240&&pixels[i+2]>240)visible++;
  for(const [mesh,material] of materials)mesh.material=material;for(const [mesh,visible] of hidden)mesh.visible=visible;
  scene.background=background;black.dispose();white.dispose();
  return {visible,values,image};
 }
};`});
  });
  await page.goto('http://localhost:8014/cockpit.html?qa');
  await page.waitForFunction(count=>window.smileTest&&fleetQA.loadedCharacters===count,count,{timeout:120000});
  for(let i=0;i<count;i++){
   const id=await page.evaluate(i=>smileTest.select(i),i);
   const input={mouthSmileLeft:.8,mouthSmileRight:.8,jawOpen:.04,mouthUpperUpLeft:.25,mouthUpperUpRight:.25};
   // Recorded output of the previous mixer for this smile: lip lift was scaled
   // to 35%, and the .04 jaw opening was unchanged by the corner smile.
   const previous={...input,mouthUpperUpLeft:.0875,mouthUpperUpRight:.0875};
   const before=await page.evaluate(v=>smileTest.render(v,true),previous),after=await page.evaluate(v=>smileTest.render(v),input);
   for(const [name,result] of [['before',before],['after',after]])fs.writeFileSync(out+'/'+id+'-'+name+'.png',Buffer.from(result.image.split(',')[1],'base64'));
   report.push({id,before:before.visible,after:after.visible,values:after.values});
   console.log(id,JSON.stringify({before:before.visible,after:after.visible}));
   const neutralBefore=await page.evaluate(()=>smileTest.render({},true)),neutralAfter=await page.evaluate(()=>smileTest.render({}));
   assert.equal(neutralAfter.visible,neutralBefore.visible,id+' neutral changed');
  }
  fs.writeFileSync(out+'/report.json',JSON.stringify({report,errors,syntheticExpressions:true,physicalSmileTested:false},null,2));
  assert.deepEqual(errors,[]);
  for(const r of report)assert(r.after>r.before&&r.after>30,r.id+' teeth visibility did not improve');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
