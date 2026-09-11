const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const out=process.env.SMILE_OUT||'.context/qa/smile-teeth';
const count=require('../assets/3dai/manifest.json').characters.length;
const ids=process.env.RIG_IDS?.split(',');

(async()=>{
 fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 const report=[],errors=[];
 try{
  const page=await browser.newPage({viewport:{width:800,height:600}});
  page.on('pageerror',e=>errors.push(e.message));
  if(process.env.MOUTH_CANDIDATE)await page.route('**/assets/3dai/manifest.json',async route=>{
   const response=await route.fetch(),manifest=await response.json();
   for(const c of manifest.characters)if(ids?.includes(c.id))c.url='/.context/qa/mouth-interiors/'+c.id+'-candidate.glb';
   await route.fulfill({response,json:manifest});
  });
  await page.addInitScript(()=>{navigator.mediaDevices.getUserMedia=async()=>{throw new DOMException('Synthetic expression test','NotAllowedError');};});
  await page.route('**/fleet.js',async route=>{
   const response=await route.fetch();
   await route.fulfill({response,body:await response.text()+`
const priorMouth=await import('/scripts/fixtures/pre-smile-bite.mjs');
window.smileTest={
 async select(index){
  await selectCharacter(index);renderer.setAnimationLoop(null);
  current.gltf.scene.updateMatrixWorld(true);
  const teeth=[];current.gltf.scene.traverse(o=>{if(o.isMesh&&/teeth|dental/i.test(o.material?.name||o.name))teeth.push(o);});
  if(!teeth.length)throw Error('Missing dental geometry: '+current.info.id);
  const box=new THREE.Box3(),v=new THREE.Vector3();
  for(const mesh of teeth){mesh.skeleton?.update();for(let i=0;i<mesh.geometry.attributes.position.count;i++){mesh.getVertexPosition(i,v);box.expandByPoint(v.applyMatrix4(mesh.matrixWorld));}}
  const center=box.getCenter(new THREE.Vector3()),size=box.getSize(new THREE.Vector3());
  this.center=center;this.distance=Math.max(.5,size.x*2.5);this.view('front');
  return current.info.id;
 },
 view(name){
  const angle=name==='quarter'?Math.PI/6:name==='side'?Math.PI/2:0;
  controls.target.copy(this.center);camera.position.copy(this.center).add(new THREE.Vector3(Math.sin(angle)*this.distance,0,Math.cos(angle)*this.distance));camera.lookAt(this.center);camera.updateMatrixWorld();
 },
 render(input,old=false){
  const values=old?priorMouth.resolveMouth({...input}):resolveMouth({...input});
  if(old){
   for(const mesh of current.meshes)for(const [name,i] of Object.entries(mesh.morphTargetDictionary))
    mesh.morphTargetInfluences[i]=priorMouth.oralWeight(name,values[name]||0,mesh.material?.name||'');
  }else{
   for(const name of manifest.channels){target[name]=input[name]||0;smooth[name]=input[name]||0;}
   driveFace(1,performance.now());
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
  const rows={};
  for(const row of ['upper','lower']){
   for(const [mesh,original] of materials)mesh.material=/teeth|dental/i.test(original?.name||mesh.name)&&new RegExp(row,'i').test(mesh.name+' '+original?.name)?white:black;
   renderer.render(scene,camera);gl.readPixels(0,0,800,600,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
   rows[row]=0;for(let i=0;i<pixels.length;i+=4)if(pixels[i]>240&&pixels[i+1]>240&&pixels[i+2]>240)rows[row]++;
  }
  for(const [mesh,material] of materials)mesh.material=material;for(const [mesh,visible] of hidden)mesh.visible=visible;
  scene.background=background;black.dispose();white.dispose();
  return {visible,rows,values,image};
 }
};`});
  });
  await page.goto('http://localhost:8014/cockpit.html?qa');
  await page.waitForFunction(count=>window.smileTest&&fleetQA.loadedCharacters===count,count,{timeout:120000});
  for(let i=0;i<count;i++){
   if(ids&&!ids.includes(require('../assets/3dai/manifest.json').characters[i].id))continue;
   const id=await page.evaluate(i=>smileTest.select(i),i);
   const input=process.env.SMILE_PHOTO?require('./fixtures/smile-photo-scores.json'):{mouthSmileLeft:.8,mouthSmileRight:.8,jawOpen:.04,mouthUpperUpLeft:.25,mouthUpperUpRight:.25};
   const before=await page.evaluate(v=>smileTest.render(v,true),input),after=await page.evaluate(v=>smileTest.render(v),input);
   for(const [name,result] of [['before',before],['after',after]])fs.writeFileSync(out+'/'+id+'-'+name+'.png',Buffer.from(result.image.split(',')[1],'base64'));
   report.push({id,before:before.visible,after:after.visible,beforeRows:before.rows,afterRows:after.rows,values:after.values});
   console.log(id,JSON.stringify({before:before.visible,after:after.visible,rows:after.rows}));
   const neutralBefore=await page.evaluate(()=>smileTest.render({},true)),neutralAfter=await page.evaluate(()=>smileTest.render({}));
   assert.equal(neutralAfter.visible,neutralBefore.visible,id+' neutral changed');
   for(const [label,extra] of [['closed',{mouthClose:1}],['talking',{jawOpen:.8}],['tongue',{tongueOut:1}]]){
    const result=await page.evaluate(v=>smileTest.render(v),{...input,...extra});
    assert.equal(result.values.smileBite,0,id+' '+label+' must release dental correction');
    fs.writeFileSync(out+'/'+id+'-'+label+'.png',Buffer.from(result.image.split(',')[1],'base64'));
   }
   for(const view of ['quarter','side']){
    const result=await page.evaluate(({view,input})=>{smileTest.view(view);return smileTest.render(input);},{view,input});
    fs.writeFileSync(out+'/'+id+'-'+view+'.png',Buffer.from(result.image.split(',')[1],'base64'));
   }
  }
  fs.writeFileSync(out+'/report.json',JSON.stringify({report,errors,syntheticExpressions:true,physicalSmileTested:false},null,2));
  assert.deepEqual(errors,[]);
  for(const r of report){
   assert(r.after>r.before&&r.after>30,r.id+' teeth visibility did not improve');
   for(const row of ['upper','lower'])assert(r.afterRows[row]>500,r.id+' '+row+' crowns hidden');
  }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
