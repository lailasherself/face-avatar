const {chromium}=require('playwright');
const fs=require('node:fs');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[],requests=[];
  let sequence=0,mode='idle',starts=0,stops=0;
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>requests.push(r.url()));
  await page.addInitScript(()=>{navigator.mediaDevices.getUserMedia=()=>{throw new Error('ZED must own the camera, not getUserMedia');};});
  const image=fs.readFileSync('.context/qa/tongue/portrait.jpg');
  await page.route('**/api/zed/*',route=>{
   if(route.request().url().endsWith('/start')){starts++;return route.fulfill({status:202,body:''});}
   if(route.request().url().endsWith('/stop')){stops++;return route.fulfill({status:204,body:''});}
   const p=(x,y,z)=>({position:[x,y,z],image:[.5,.5],confidence:.95});
   const joints={RIGHT_SHOULDER:p(-.2,0,-2),RIGHT_ELBOW:p(-.25,-.3,-2),RIGHT_WRIST:p(-.3,-.6,-2),
    LEFT_SHOULDER:p(.2,0,-2),LEFT_ELBOW:p(.25,-.3,-2),LEFT_WRIST:p(.3,-.6,-2)};
   if(mode==='raised'){joints.RIGHT_ELBOW=p(-.4,.2,-1.9);joints.RIGHT_WRIST=p(-.4,.5,-1.8);}
   const packet={version:1,session:'test-session',sequence:sequence++,ageMs:mode==='stale'?1000:5,
    coordinates:'RIGHT_HANDED_Y_UP',reference:'CAMERA',units:'meters',body:mode==='lost'?null:{id:4,joints}};
   return route.fulfill({status:200,headers:{'Content-Type':'image/jpeg','X-Zed-Sample':JSON.stringify(packet)},body:image});
  });
  await page.goto('http://localhost:8014/cockpit.html?qa&assets=3dai&tracking=zed');
  await page.waitForFunction(()=>window.fleetQA?.cameraActive&&fleetQA.handTrackingReady&&fleetQA.faceTrackingFrames>3,null,{timeout:60000});
  await page.waitForTimeout(700);
  const idle=await page.evaluate(()=>fleetQA);assert.equal(idle.trackingSource,'zed');
  mode='raised';await page.waitForTimeout(700);const raised=await page.evaluate(()=>fleetQA);
  const notice=await page.evaluate(()=>document.getElementById('notice').textContent);
  console.log('capture status',notice);
  fs.writeFileSync('.context/qa/zed-debug.json',JSON.stringify({idle,raised,errors,notice},null,2));
  assert(raised.bones.HandL[1]>idle.bones.HandL[1]+.15,'native right-arm raise moves avatar L');
  assert(Math.hypot(...raised.bones.HandR.map((v,i)=>v-idle.bones.HandR[i]))<.02,'other arm stays independent');
  assert.equal(raised.poseTrackingFrames,0,'webcam pose model must not run');
  assert(!requests.some(u=>u.endsWith('/pose_landmarker_lite.task')));
  assert.equal(raised.vehicleUUID,null);
  for(const viewport of [{width:1440,height:1080},{width:1080,height:1920}]){
   await page.setViewportSize(viewport);await page.waitForTimeout(100);
   const pixels=await page.evaluate(()=>{
    const canvas=document.createElement('canvas');canvas.width=240;canvas.height=180;
    const ctx=canvas.getContext('2d');ctx.drawImage(document.getElementById('scene'),0,0,240,180);
    return new Set(ctx.getImageData(0,0,240,180).data).size;
   });
   assert(pixels>100,'native-source scene is blank');
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),viewport.width);
   await page.screenshot({path:'.context/qa/zed-native-'+viewport.width+'.png'});
  }
  mode='stale';await page.waitForTimeout(800);
  assert.deepEqual(await page.evaluate(()=>fleetQA.trackedArms),[],'stale native data cannot hold raised arms');
  mode='lost';await page.waitForTimeout(600);assert.equal(await page.evaluate(()=>fleetQA.zedPersonId),null);
  console.log('before stop',await page.evaluate(()=>({active:fleetQA.cameraActive,frames:fleetQA.zedFrames,disabled:document.getElementById('camera-toggle').disabled,notice:document.getElementById('notice').textContent})));
  await page.evaluate(()=>document.getElementById('camera-toggle').click());
  await page.waitForTimeout(150);assert.equal(await page.evaluate(()=>fleetQA.cameraActive),false);assert(stops>=1);
  mode='idle';await page.evaluate(()=>document.getElementById('camera-toggle').click());
  await page.waitForFunction(()=>fleetQA.cameraActive&&fleetQA.zedFrames>3,null,{timeout:60000});
  assert.equal(starts,2);assert.deepEqual(errors,[]);
  fs.writeFileSync('.context/qa/zed-native.json',JSON.stringify({idle,raised,starts,stops,errors,injectedNativePackets:true,physicalZedTested:false},null,2));
  console.log('PASS native-only body input, separate face/fingers, independent arms, stale/loss/stop/restart; hardware packets simulated');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
