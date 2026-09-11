const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const rosterIds=JSON.parse(fs.readFileSync('assets/3dai/manifest.json')).characters.map(c=>c.id);
const ids=process.env.RIG_IDS?process.env.RIG_IDS.split(','):rosterIds;
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',args:['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream']});
 const report=[];
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  if(process.env.REWORK_PREVIEW)await page.route('**/assets/3dai/manifest.json',async route=>{
   const response=await route.fetch(),manifest=await response.json();
   for(const c of manifest.characters)if(ids.includes(c.id))c.url='assets/likeness-trials/'+c.id+'-body-rig.glb';
   await route.fulfill({response,json:manifest});
  });
  await page.addInitScript(()=>{
   const Original=Worker;window.Worker=class extends Original{
    constructor(url,options){super(url,options);if(String(url).includes('hand-tracking-worker.js')){
     window.motionWorker=this;this.addEventListener('message',e=>{if(window.injectMotion&&!e.data.synthetic)e.stopImmediatePropagation();});
    }}
   };
  });
  await page.route('**/fleet.js',async route=>{
   const response=await route.fetch(),body=await response.text();
   await route.fulfill({response,body:body+`
window.armError=side=>{
 current.gltf.scene.updateMatrixWorld(true);
 const points=current.arms.chains[side].map(({bone})=>bone.getWorldPosition(new THREE.Vector3()));
 const expected=trackedArms[side].directions,root=current.gltf.scene.getWorldQuaternion(new THREE.Quaternion());
 return ['upper','lower'].map((kind,i)=>points[i+1].clone().sub(points[i]).normalize().angleTo(new THREE.Vector3(...expected[kind]).applyQuaternion(root))*180/Math.PI);
};
window.armState=side=>current.arms.chains[side].flatMap(({bone})=>bone.quaternion.toArray());
`});
  });
  await page.goto('http://localhost:8014/cockpit.html?qa&assets=3dai',{waitUntil:'networkidle'});
  await page.waitForFunction(()=>window.fleetQA?.handTrackingReady&&fleetQA.handTrackingFrames>2,null,{timeout:60000});
  await page.evaluate(async()=>{
   const {bodyPose}=await import('/scripts/motion-fixtures.mjs');window.injectMotion=true;
   window.setMotion=(raised,crossTalk=false)=>{
    clearInterval(window.motionInterval);
    const pose=bodyPose(raised);
    if(crossTalk)pose.poseWorldLandmarks=bodyPose(['left','right']).poseWorldLandmarks;
    const send=()=>motionWorker.dispatchEvent(new MessageEvent('message',{data:{type:'result',synthetic:true,time:performance.now(),result:{...pose,landmarks:[]}}}));
    send();window.motionInterval=setInterval(send,33);
   };
  });
  const car=await page.evaluate(()=>fleetQA.vehicleUUID);
  for(const id of ids){
   await page.evaluate(index=>document.querySelectorAll('.character')[index].click(),rosterIds.indexOf(id));
   await page.waitForFunction(id=>fleetQA.character===id,id);
   await page.evaluate(()=>setMotion([]));await page.waitForTimeout(500);
   const steps=[];
   for(const raised of ['left','right']){
    await page.evaluate(()=>setMotion([]));await page.waitForTimeout(500);
    const idle=raised==='right'?'R':'L';
    const before=await page.evaluate(side=>armState(side),idle);
    await page.evaluate(raised=>setMotion([raised],true),raised);await page.waitForTimeout(160);
    const after=await page.evaluate(side=>armState(side),idle);
    assert(after.every((v,i)=>Math.abs(v-before[i])<.001),id+' opposite arm moved '+JSON.stringify({raised,idle,before,after,qa:await page.evaluate(()=>({frames:fleetQA.poseTrackingFrames,trackedArms:fleetQA.trackedArms,latency:fleetQA.motionLatencyMs,notice:document.getElementById('notice').textContent}))}));
    const errors=await page.evaluate(()=>[...armError('L'),...armError('R')]);
    const guarded=await page.evaluate(()=>fleetQA.armCollisionAdjustments>0&&fleetQA.armPenetration<.006);
    assert(guarded||errors.every(v=>v<12),id+' asymmetric target not reached '+errors);
    await page.screenshot({path:'.context/qa/tongue/'+id+'-only-'+raised+'-arm.png'});
   }
   for(const raised of [['right'],['left'],['left','right'],[]]){
    await page.evaluate(raised=>setMotion(raised),raised);await page.waitForTimeout(160);
    const errors=await page.evaluate(()=>[...armError('L'),...armError('R')]);
    const guarded=await page.evaluate(()=>fleetQA.armCollisionAdjustments>0&&fleetQA.armPenetration<.006);
    assert(guarded||errors.every(v=>v<12),id+' delayed direction '+errors);steps.push({raised,degrees:errors,guarded});
   }
   assert.equal(await page.evaluate(()=>fleetQA.vehicleUUID),car);
   report.push({id,steps});console.log('PASS arm direction changes within 160ms',id);
  }
  await page.evaluate(()=>clearInterval(window.motionInterval));assert.deepEqual(errors,[]);
  assert.equal(await page.locator('header').isVisible(),false);
  assert.equal(await page.locator('footer').isVisible(),false);
  assert.equal(await page.evaluate(()=>fleetQA.vehicleUUID),null);
  fs.writeFileSync('.context/qa/tongue/arm-timing.json',JSON.stringify({report,injectedLandmarks:true,hardwareCertified:false},null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
