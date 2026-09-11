const {chromium}=require('playwright');
const fs=require('node:fs');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 try{
  const page=await browser.newPage({viewport:{width:1100,height:650}}),errors=[],external=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(new URL(r.url()).origin!=='http://localhost:8014')external.push(r.url());});
  await page.route('**/hand-test',r=>r.fulfill({contentType:'text/html',body:'<canvas id="frame" width="960" height="540"></canvas>'}));
  await page.goto('http://localhost:8014/hand-test');
  const report=await page.evaluate(async fixtureWidth=>{
   const worker=new Worker('/finger-tracking-worker.js');let pending;
   worker.onmessage=({data})=>data.type==='error'?pending.reject(Error(data.message)):pending.resolve(data);
   const send=data=>new Promise((resolve,reject)=>{
    const timeout=setTimeout(()=>reject(Error('Hand worker timed out')),30000);
    pending={resolve:v=>{clearTimeout(timeout);resolve(v);},reject:e=>{clearTimeout(timeout);reject(e);}};
    worker.postMessage(data,data.frame?[data.frame]:[]);
   });
   try{
    await send({type:'init'});
    const img=new Image();img.src='/.context/qa/right_hands.jpg';await img.decode();
    const original=document.createElement('canvas');original.width=img.width;original.height=img.height;
    original.getContext('2d').drawImage(img,0,0);
    const reference=(await send({type:'frame',time:performance.now(),frame:await createImageBitmap(original)})).result;
    if(reference.landmarks.length!==2)throw Error('Fixture did not detect two reference hands');
    const canvas=document.getElementById('frame'),ctx=canvas.getContext('2d');
    const width=fixtureWidth,height=width*img.height/img.width,x=350,y=190;
    const poseLandmarks=Array.from({length:33},()=>({x:0,y:0,z:0,visibility:0,presence:0}));
    const handHints={};
    const imagePoint=p=>({x:(x+p.x*width)/960,y:(y+p.y*height)/540,z:0,visibility:1,presence:1});
    for(let i=0;i<2;i++){
     const p=reference.landmarks[i],w=imagePoint(p[0]),middle=imagePoint(p[12]);
     const [side,wi,ei,si]=i===0?['L',16,14,12]:['R',15,13,11];
     poseLandmarks[wi]=w;
     poseLandmarks[ei]={...w,x:w.x+(w.x-middle.x)*1.4,y:w.y+(w.y-middle.y)*1.4};
     poseLandmarks[si]={...w,x:w.x+(i?-.08:.08)*width/240};
     handHints[side]=imagePoint(p[9]);
    }
    const body={poseLandmarks,handHints,personId:1};
    const draw=()=>{ctx.fillStyle='#ddd';ctx.fillRect(0,0,960,540);ctx.drawImage(img,x,y,width,height);};
    draw();
    const baseline=[];
    for(let i=0;i<4;i++){
     const frame=await createImageBitmap(canvas,{resizeWidth:480,resizeHeight:270});
     const r=await send({type:'frame',time:performance.now(),frame});
     baseline.push({detected:r.result.landmarks.length,inferenceMs:r.result.handDiagnostics.inferenceMs});
    }
    const {trackedFingerCurls}=await import('/finger-motion.js');
    const results=[];
    for(let i=0;i<8;i++){
     const r=await send({type:'frame',time:performance.now(),frame:await createImageBitmap(canvas),body});
     results.push({diagnostics:r.result.handDiagnostics,matched:Object.keys(trackedFingerCurls(r.result)),wrists:r.result.landmarks.map(p=>p[0])});
    }
    const moving=[];
    for(const dx of [20,40,60]){
     const shifted=structuredClone(body);
     for(const p of [...shifted.poseLandmarks,...Object.values(shifted.handHints)])p.x+=dx/960;
     ctx.fillStyle='#ddd';ctx.fillRect(0,0,960,540);ctx.drawImage(img,x+dx,y,width,height);
     const r=(await send({type:'frame',time:performance.now(),frame:await createImageBitmap(canvas),body:shifted})).result;
     moving.push({dx,matched:Object.keys(trackedFingerCurls(r)),wrists:r.landmarks.map(p=>p[0])});
    }
    draw();
    const {handCrops}=await import('/hand-crops.js');
    for(const c of handCrops(body,960,540)){ctx.strokeStyle=c.side==='L'?'#e02040':'#007eae';ctx.lineWidth=2;ctx.strokeRect(c.x,c.y,c.size,c.size);}
    const empty=(await send({type:'frame',time:performance.now(),frame:await createImageBitmap(canvas),body:{personId:null}})).result;
    return {fixtureWidth,baseline,results,moving,noBody:empty.handDiagnostics,referenceWrists:reference.landmarks.map(p=>imagePoint(p[0])),physicalZedTested:false};
   }finally{worker.terminate();}
  },Number(process.env.HAND_FIXTURE_WIDTH||240));
  fs.writeFileSync('.context/qa/hand-crops-'+report.fixtureWidth+'.json',JSON.stringify(report,null,2));
  await page.screenshot({path:'.context/qa/hand-crops-'+report.fixtureWidth+'.png'});
  console.log(JSON.stringify({width:report.fixtureWidth,baseline:report.baseline,results:report.results.map(r=>({matched:r.matched,inferenceMs:r.diagnostics.inferenceMs}))}));
  assert(report.results.slice(-5).every(r=>r.matched.length===2),'cropped photo hands must drive two independent sides');
  for(const r of report.results){assert.equal(r.diagnostics.sourceWidth,960);assert.equal(r.diagnostics.mode,'wrist-crops');}
  for(const r of report.results.slice(-5))for(const wrist of r.wrists)assert(report.referenceWrists.some(p=>Math.hypot(p.x-wrist.x,p.y-wrist.y)<.035),'crop must preserve camera-space wrist location');
  for(const r of report.moving){
   assert.equal(r.matched.length,2,'moving crops must retain both hands');
   for(const wrist of r.wrists)assert(report.referenceWrists.some(p=>Math.hypot(p.x+r.dx/960-wrist.x,p.y-wrist.y)<.035),'moving crop must not pin the hand in place');
  }
  assert.equal(report.noBody.mode,'no-body');assert.equal(report.noBody.detected,0);
  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
  console.log('PASS real local hand model, two wrist crops, coordinate restoration and body loss');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
