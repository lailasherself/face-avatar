const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const roster=require('../assets/3dai/manifest.json').characters.map(c=>c.id);
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',args:['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream']});
 try{
  const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>{
   const Original=Worker;window.Worker=class extends Original{
    constructor(url,options){super(url,options);if(String(url).includes('hand-tracking-worker.js')){
     window.motionWorker=this;this.addEventListener('message',e=>{if(window.injectMotion&&!e.data.synthetic)e.stopImmediatePropagation();});
    }}
   };
  });
  await page.goto('http://localhost:8014/cockpit.html?qa&assets=3dai',{waitUntil:'networkidle'});
  await page.waitForFunction(()=>window.fleetQA?.handTrackingReady&&fleetQA.handTrackingFrames>2,null,{timeout:60000});
  await page.evaluate(async()=>{
   window.handFixture=(await import('/scripts/finger-fixtures.mjs')).fingerHand;
   window.bodyFixture=(await import('/scripts/motion-fixtures.mjs')).bodyPose;
   window.injectMotion=true;window.motionTime=performance.now();
   window.sendFingerFrame=(left,right)=>{
    const pose=bodyFixture();const world=[handFixture(left),handFixture(right)];
    const landmarks=world.map((points,i)=>points.map(p=>({...p,x:p.x+pose.poseLandmarks[i?15:16].x,y:pose.poseLandmarks[i?15:16].y-p.y})));
    motionWorker.dispatchEvent(new MessageEvent('message',{data:{type:'result',synthetic:true,time:performance.now(),result:{...pose,landmarks,worldLandmarks:world}}}));
   };
   window.setFingers=(left,right)=>{clearInterval(window.fingerInterval);sendFingerFrame(left,right);window.fingerInterval=setInterval(()=>sendFingerFrame(left,right),80);};
  });
  const vehicle=await page.evaluate(()=>fleetQA.vehicleUUID);
  assert.equal(vehicle,null);
  for(const id of roster){
   await page.evaluate(index=>document.querySelectorAll('.character')[index].click(),roster.indexOf(id));
   await page.waitForFunction(id=>fleetQA.character===id,id);
   await page.evaluate(()=>setFingers({Middle:[1.2,1.5,1.2],Ring:[1.2,1.5,1.2],Pinky:[1.2,1.5,1.2]},{Index:[1.2,1.5,1.2]}));
   await page.waitForTimeout(1100);
   const qa=await page.evaluate(()=>fleetQA);
   assert.equal(qa.character,id);assert.equal(qa.vehicleUUID,vehicle);assert.equal(qa.cameraActive,true);
   // Finger-curl values are landmark-derived, so the pointing/curl behaviour holds
   // for whatever finger bones a rig defines; rigs without fingers (e.g. clay) simply
   // expose no curls to check.
   let curled=0;
   for(const [bone,value] of Object.entries(qa.fingerCurls)){
    if(/^Index[123]L$/.test(bone))assert(value<.01,id+' pointing index');
    if(/^Middle[123]L$/.test(bone)||/^Index[123]R$/.test(bone)){curled++;assert(value>.99,id+' independent curls '+JSON.stringify({bone,value,frames:qa.handTrackingFrames,ready:qa.handTrackingReady,renderFrame:qa.renderFrame,notice:await page.locator('#notice').textContent()}));}
   }
   console.log('PASS camera-result finger pipeline',id,'curls='+Object.keys(qa.fingerCurls).length,'checked='+curled);
  }
  await page.evaluate(()=>clearInterval(window.fingerInterval));await page.waitForTimeout(1300);
  assert((await page.evaluate(()=>Object.values(fleetQA.fingerCurls))).every(v=>v<.01),'tracking loss must relax every joint');
  assert.deepEqual(errors,[]);console.log('PASS tracking loss resets fingers; camera preserved and vehicle absent');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
