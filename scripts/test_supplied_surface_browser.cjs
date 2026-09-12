const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const roster=require('../assets/3dai/manifest.json');
const ids=process.env.RIG_IDS?process.env.RIG_IDS.split(','):roster.characters.filter(c=>['orbit','coral'].includes(c.id)).map(c=>c.id);
const out=process.env.SURFACE_DIR||'.context/qa/supplied-lip-surface-v3';
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 try{
  const page=await browser.newPage({viewport:{width:1200,height:1200}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>{navigator.mediaDevices.getUserMedia=async()=>{throw new DOMException('Offline rig review','NotAllowedError');};});
  if(process.env.SURFACE_CANDIDATE||process.env.SURFACE_BEFORE)await page.route('**/assets/3dai/manifest.json',async route=>{
   const response=await route.fetch(),manifest=await response.json();
   for(const c of manifest.characters)if(ids.includes(c.id))c.url='/'+out+'/'+(process.env.SURFACE_BEFORE?'before-'+c.id+'-image-rig.glb':c.id+'-candidate.glb');
   await route.fulfill({response,json:manifest});
  });
  await page.route('**/fleet.js',async route=>{
   const response=await route.fetch();
   await route.fulfill({response,body:await response.text()+`
window.surfaceQA={async select(id){
 await selectCharacter(manifest.characters.findIndex(c=>c.id===id));renderer.setAnimationLoop(null);notice('');$('camera-retry').hidden=true;
 for(const child of scene.children)if(child.isMesh&&child.material?.isShaderMaterial)child.visible=false;
},render(values={},close=false,angle=0){
 for(const name of manifest.channels){target[name]=values[name]||0;smooth[name]=values[name]||0;}
 driveFace(1,performance.now());current.gltf.scene.updateMatrixWorld(true);
 const box=new THREE.Box3();
 if(close){current.gltf.scene.traverse(o=>{if(!o.isBone&&/Head/.test(o.name))box.expandByObject(o);});}
 else box.setFromObject(current.gltf.scene);
 const size=box.getSize(new THREE.Vector3()),center=box.getCenter(new THREE.Vector3());
 if(box.isEmpty())throw new Error('Missing head bounds');
 const radius=box.max.z-center.z+Math.max(size.x,size.y)*1.8;
 camera.clearViewOffset();camera.position.set(center.x+Math.sin(angle)*radius,center.y,center.z+Math.cos(angle)*radius);camera.lookAt(center);camera.updateProjectionMatrix();
 renderer.render(scene,camera);
 const canvas=document.createElement('canvas');canvas.width=canvas.height=100;
 const ctx=canvas.getContext('2d');ctx.drawImage(renderer.domElement,0,0,100,100);
 const p=ctx.getImageData(0,0,100,100).data;let occupied=0;
 for(let i=0;i<p.length;i+=4)if(Math.abs(p[i]-p[0])+Math.abs(p[i+1]-p[1])+Math.abs(p[i+2]-p[2])>40)occupied++;
 if(occupied<300)throw new Error('Blank or badly framed rig: '+occupied);
 return renderer.domElement.toDataURL('image/png');
}};`});
  });
  await page.goto('http://localhost:8014/cockpit.html?qa&character='+ids[0]);
  await page.waitForFunction(count=>window.surfaceQA&&fleetQA.loadedCharacters===count,roster.characters.length,{timeout:120000});
  for(const id of ids){
   await page.evaluate(id=>surfaceQA.select(id),id);
   assert.equal(await page.evaluate(()=>Object.keys(fleetQA.bones).length),id==='orbit'?39:18);
   for(const [label,values,close] of [['neutral',{},false],['face',{},true],['blink',{eyeBlinkLeft:1,eyeBlinkRight:1},true],['wink',{eyeBlinkLeft:1},true],['smile',{mouthSmileLeft:.8,mouthSmileRight:.8,jawOpen:.04},true],['jaw',{jawOpen:1},true],['tongue',{tongueOut:1},true]]){
    const image=await page.evaluate(([v,c])=>surfaceQA.render(v,c),[values,close]);
    fs.writeFileSync(out+'/'+(process.env.SURFACE_BEFORE?'before-':'')+id+'-browser-'+label+'.png',Buffer.from(image.split(',')[1],'base64'));
   }
   if(process.env.SURFACE_ANGLES)for(const [label,angle] of [['three-quarter',Math.PI/4],['back',Math.PI]]){
    const image=await page.evaluate(angle=>surfaceQA.render({},false,angle),angle);
    fs.writeFileSync(out+'/'+id+'-browser-'+label+'.png',Buffer.from(image.split(',')[1],'base64'));
   }
   console.log('PASS',id,'nonblank neutral, blink, wink and smile renders; expected bone count');
  }
  assert.deepEqual(errors,[]);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
