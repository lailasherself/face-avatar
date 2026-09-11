const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[],external=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(/^https?:/.test(r.url())&&new URL(r.url()).hostname!=='localhost')external.push(r.url());});
  await page.addInitScript(()=>{
   window.cameraRequests=0;
   navigator.mediaDevices.getUserMedia=async()=>{
    window.cameraRequests++;
    const images=await Promise.all(['foxyface-example.png','portrait.jpg'].map(async name=>{const img=new Image();img.src='/.context/qa/tongue/'+name;await img.decode();return img;}));
    const canvas=document.createElement('canvas');canvas.width=640;canvas.height=480;
    const ctx=canvas.getContext('2d');window.fixture=0;
    const draw=()=>{
     ctx.fillStyle='#000';ctx.fillRect(0,0,640,480);
     if(window.fixture===-1)return;
     const img=images[window.fixture];
     // Only the human half of the upstream example, fit without stretching.
     const sw=window.fixture===0?614:img.width,sh=img.height,s=Math.min(640/sw,480/sh);
     ctx.drawImage(img,0,0,sw,sh,(640-sw*s)/2,(480-sh*s)/2,sw*s,sh*s);
    };
    draw();window.fixtureTimer=setInterval(draw,33);return canvas.captureStream(30);
   };
  });
  await page.goto('http://localhost:8014/cockpit.html?qa&assets=3dai',{waitUntil:'networkidle'});
  await page.waitForFunction(()=>window.fleetQA?.tongueTrackingReady&&fleetQA.tongueTrackingFrames>3,null,{timeout:60000});
  const value=()=>page.evaluate(()=>Math.max(...fleetQA.morphs.filter(m=>m.names.includes('tongueOut')).map(m=>m.weights[m.names.indexOf('tongueOut')])));
  try{await page.waitForFunction(()=>fleetQA.morphs.some(m=>m.weights[m.names.indexOf('tongueOut')]>.4),null,{timeout:15000});}
  catch(error){console.log(await page.evaluate(()=>({ready:fleetQA.tongueTrackingReady,frames:fleetQA.tongueTrackingFrames,raw:fleetQA.tongueScore,latency:fleetQA.tongueLatencyMs})));throw error;}
  const extended=await page.evaluate(()=>fleetQA),car=extended.vehicleUUID;
  assert.equal(car,null);assert.equal(extended.vehicleVisible,false);
  await page.screenshot({path:'.context/qa/tongue/live-extended.png'});
  await page.evaluate(()=>window.fixture=1);await page.waitForTimeout(1600);
  assert(await value()<.05,'neutral image retracts tongue');
  const neutral=await page.evaluate(()=>fleetQA);
  const pacing=[];
  for(const fixture of [0,1,0,1]){
   const start=await page.evaluate(fixture=>{window.fixture=fixture;return performance.now();},fixture);
   try{await page.waitForFunction(fixture=>{
    const tongue=Math.max(...fleetQA.morphs.filter(m=>m.names.includes('tongueOut')).map(m=>m.weights[m.names.indexOf('tongueOut')]));
    return fixture===0?tongue>.9:tongue<.1;
   },fixture,{timeout:3000,polling:'raf'});}catch(error){
    const state=await page.evaluate(()=>({qa:fleetQA,fixture:window.fixture,notice:document.getElementById('notice').textContent}));
    fs.writeFileSync('.context/qa/tongue/pacing-failure.json',JSON.stringify({state,pacing},null,2));
    console.log('Tongue timing failure',JSON.stringify({fixture,pacing,notice:state.notice,
     diagnostics:Object.fromEntries(Object.entries(state.qa).filter(([key])=>/tongue|faceTracking|cameraActive/.test(key)))}));
    throw error;
   }
   const milliseconds=await page.evaluate(start=>performance.now()-start,start);pacing.push({fixture,milliseconds});
   await page.waitForTimeout(200);
  }
  console.log('Tongue fixture pacing',JSON.stringify(pacing));
  assert(pacing.every(p=>p.milliseconds<500),'fixture tongue response exceeds half a second');
  await page.evaluate(()=>window.fixture=-1);await page.waitForTimeout(1000);
  assert(await value()<.01,'face loss retracts tongue');
  assert.equal(await page.evaluate(()=>fleetQA.vehicleUUID),car);assert.equal(await page.evaluate(()=>cameraRequests),1);
  await page.evaluate(()=>document.getElementById('camera-toggle').click());
  assert.equal(await page.evaluate(()=>fleetQA.tongueTrackingReady),false);
  assert.equal(await page.evaluate(()=>fleetQA.cameraActive),false);
  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
  fs.writeFileSync('.context/qa/tongue/camera-test.json',JSON.stringify({extended,neutral,pacing,errors,external,injectedScores:false},null,2));
  console.log('PASS real local tongue inference extends/retracts rig, loss/stop reset, one camera, shared car, no external requests');
  const unavailable=await browser.newPage();
  await unavailable.addInitScript(()=>navigator.mediaDevices.getUserMedia=async()=>{
   const canvas=document.createElement('canvas');canvas.width=640;canvas.height=480;
   const ctx=canvas.getContext('2d');ctx.fillRect(0,0,640,480);
   setInterval(()=>ctx.fillRect(0,0,640,480),80);return canvas.captureStream(15);
  });
  await unavailable.route('**/tongue_detector.onnx',route=>route.abort());
  await unavailable.goto('http://localhost:8014/cockpit.html?qa&assets=3dai',{waitUntil:'networkidle'});
  await unavailable.waitForFunction(()=>document.getElementById('notice').textContent.includes('Tongue tracking unavailable'),null,{timeout:60000});
  assert.equal(await unavailable.evaluate(()=>fleetQA.cameraActive),true);
  await unavailable.unroute('**/tongue_detector.onnx');
  await unavailable.getByRole('button',{name:'Retry camera',exact:true}).click();
  await unavailable.waitForFunction(()=>fleetQA.tongueTrackingReady,null,{timeout:60000});
  console.log('PASS tongue model failure preserves camera; retry reloads detector');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
