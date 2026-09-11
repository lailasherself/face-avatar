const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',args:['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream']});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  for(const file of ['face-tracking-worker.js','hand-tracking-worker.js']){
   await page.route('**/'+file,async route=>{
    const response=await route.fetch(),body=await response.text();
    const delayed=file==='face-tracking-worker.js'?body.replace("}else if(data.type==='frame'){","}else if(data.type==='frame'){ const until=performance.now()+150;while(performance.now()<until){}"):
     body.replace('hands.onmessage=({data})=>{','hands.onmessage=async({data})=>{').replace('clearTimeout(handWatchdog);handBusy=false;','await new Promise(resolve=>setTimeout(resolve,150));clearTimeout(handWatchdog);handBusy=false;');
    await route.fulfill({response,body:delayed});
   });
  }
  await page.goto('http://localhost:8014/cockpit.html?qa&assets=3dai');
  await page.waitForFunction(()=>window.fleetQA?.faceTrackingFrames>5&&fleetQA.handTrackingFrames>5,null,{timeout:60000});
  const timing=await page.evaluate(()=>new Promise(resolve=>{
   const intervals=[],start=performance.now(),initial=fleetQA;let previous=start;
   const sample=time=>{
    intervals.push(time-previous);previous=time;
    if(time-start<2500){requestAnimationFrame(sample);return;}
    const end=fleetQA;
    resolve({intervals,poseFrames:end.poseTrackingFrames-initial.poseTrackingFrames,
     handFrames:end.handTrackingFrames-initial.handTrackingFrames,faceFrames:end.faceTrackingFrames-initial.faceTrackingFrames,
     renderFrames:end.renderFrame-initial.renderFrame,faceLatencyMs:end.faceLatencyMs,motionLatencyMs:end.motionLatencyMs});
   };requestAnimationFrame(sample);
  }));
  const sorted=timing.intervals.slice(2).sort((a,b)=>a-b);timing.p95=sorted[Math.floor(sorted.length*.95)];
  console.log(JSON.stringify({...timing,intervals:undefined}));
  assert(timing.p95<100,'150ms face inference must not stall the render loop');
  assert(timing.renderFrames>timing.faceFrames*2,'rendering must advance between face samples');
  assert(timing.poseFrames>timing.handFrames*2,'pose must not wait for 150ms finger inference');
  assert.deepEqual(errors,[]);
  fs.writeFileSync('.context/qa/worker-pacing.json',JSON.stringify({timing,injectedFaceWorkMs:150,injectedFingerResultDelayMs:150,hardwareCertified:false},null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
