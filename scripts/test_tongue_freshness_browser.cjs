const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const legacy=process.env.TONGUE_LEGACY_FRAMES==='1';
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  // Optional benchmark recreates the previous old-pixel fallback, without
  // modifying installation files or substituting model results.
  if(legacy)await page.route('**/fleet.js',async route=>{
   const response=await route.fetch(),body=await response.text();
   const match='results.frame?.close();\n  tongueTracker?.sampleLatest(video,latestFaceLandmarks,time,performance.now(),zedSource?.capturedAt);';
   assert(body.includes(match));
   await route.fulfill({response,body:body.replace(match,
    'if(results.frame)tongueTracker?.sampleFrame(results.frame,latestFaceLandmarks,time,results.videoTime);else tongueTracker?.sample(video,latestFaceLandmarks,time);')
    .replace('if(stream&&latestFaceLandmarks)tongueTracker?.sampleLatest',
     'if(stream&&latestFaceLandmarks&&time-lastFaceTime<100)tongueTracker?.sampleLatest')});
  });
  await page.route('**/face-tracking-worker.js',async route=>{
   const response=await route.fetch(),body=await response.text();
   const match="}else if(data.type==='frame'){";
   assert(body.includes(match));
   await route.fulfill({response,body:body.replace(match,match+' const until=performance.now()+110;while(performance.now()<until){}')});
  });
  await page.addInitScript(()=>{
   navigator.mediaDevices.getUserMedia=async()=>{
    const img=new Image();img.src='/.context/qa/tongue/foxyface-example.png';await img.decode();
    const canvas=document.createElement('canvas');canvas.width=640;canvas.height=480;
    const ctx=canvas.getContext('2d'),s=Math.min(640/614,480/img.height);
    const draw=()=>{ctx.fillStyle='#000';ctx.fillRect(0,0,640,480);ctx.drawImage(img,0,0,614,img.height,(640-614*s)/2,(480-img.height*s)/2,614*s,img.height*s);};
    draw();setInterval(draw,33);return canvas.captureStream(30);
   };
  });
  await page.goto('http://localhost:8014/cockpit.html?qa&assets=3dai&character=juno');
  await page.waitForFunction(()=>window.fleetQA?.tongueTrackingFrames>8,null,{timeout:60000});
  const samples=await page.evaluate(()=>new Promise(resolve=>{
   const samples=[],start=performance.now();let last=-1;
   function sample(){
    const q=fleetQA;
    if(q.tongueTrackingFrames!==last){last=q.tongueTrackingFrames;samples.push({faceMs:q.faceLatencyMs,tongueMs:q.tongueLatencyMs,cropMs:q.tongueCropAgeMs,inferenceMs:q.tongueInferenceMs,score:q.tongueScore,extension:Math.max(...q.morphs.map(m=>m.weights[m.names.indexOf('tongueOut')]||0))});}
    if(performance.now()-start<2500)requestAnimationFrame(sample);else resolve(samples);
   }sample();
  }));
  assert(samples.length>10,'tongue should advance between slow face results');
  const median=key=>samples.map(s=>s[key]).sort((a,b)=>a-b)[Math.floor(samples.length/2)];
  const report={samples,legacy,medianFaceMs:median('faceMs'),medianTongueMs:median('tongueMs'),injectedFaceWorkMs:110,hardwareCertified:false};
  fs.writeFileSync(`.context/qa/tongue/freshness${legacy?'-legacy':''}.json`,JSON.stringify(report,null,2));
  console.log(JSON.stringify({...report,samples:samples.length}));
  assert(report.medianFaceMs>=110,'face delay must be exercised');
  if(legacy)assert(report.medianTongueMs>=110,'old frames should expose serial face latency');
  else{
   assert(samples.some(s=>s.cropMs>100),'test must exercise the old serial fallback range');
   assert(report.medianTongueMs<80,'fresh tongue pixels must not inherit 110ms face delay');
  }
  assert(samples.some(s=>s.extension>.9),'real tongue model must still extend the rendered tongue');
  assert.deepEqual(errors,[]);
  await page.screenshot({path:`.context/qa/tongue/freshness${legacy?'-legacy':''}.png`});
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
