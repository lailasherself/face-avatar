// Functional test for the browse/embodied mode machine and its dwell gestures.
// Reuses the real MediaPipe hand model (replaying .context/qa/right_hands.jpg) exactly like
// test_air_swipe_browser.cjs, but drives each hand's raise independently so we can exercise:
//   - two raised palms held still  -> COMMIT (browse -> embodied), avatar dollies in
//   - one raised palm held still   -> CHANGE (embodied -> browse)
//   - moving palms never fire the dwell (stillness is the discriminator)
//   - swipe is disabled while embodied
const {chromium}=require('playwright');
const fs=require('node:fs');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>{
   const Original=Worker;
   window.Worker=class extends Original{
    constructor(url,options){super(url,options);if(String(url).includes('hand-tracking-worker.js')){
     window.motionWorker=this;this.addEventListener('message',e=>{if(window.injectMotion&&!e.data.synthetic)e.stopImmediatePropagation();});
    }}
   };
   window.cameraRequests=0;
   navigator.mediaDevices.getUserMedia=async()=>{
    window.cameraRequests++;const c=document.createElement('canvas');c.width=960;c.height=540;
    const ctx=c.getContext('2d');ctx.fillStyle='#ddd';ctx.fillRect(0,0,960,540);
    window.cameraTimer=setInterval(()=>ctx.fillRect(0,0,960,540),33);return c.captureStream(30);
   };
  });
  await page.goto('http://localhost:8014/cockpit.html?qa&assets=3dai&character=orbit');
  await page.waitForFunction(()=>window.fleetQA?.handTrackingReady,null,{timeout:60000});
  await page.evaluate(async()=>{
   window.injectMotion=true;window.gestureSamples=[];
   const worker=new Worker('/finger-tracking-worker.js');window.photoWorker=worker;
   let pending;
   worker.onmessage=({data})=>data.type==='error'?pending.reject(Error(data.message)):pending.resolve(data);
   const send=data=>new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>reject(Error('Photo hand worker timeout')),30000);
    pending={resolve:v=>{clearTimeout(timer);resolve(v);},reject:e=>{clearTimeout(timer);reject(e);}};
    worker.postMessage(data,data.frame?[data.frame]:[]);
   });
   await send({type:'init'});
   const image=new Image();image.src='/.context/qa/right_hands.jpg';await image.decode();
   const original=document.createElement('canvas');original.width=image.width;original.height=image.height;original.getContext('2d').drawImage(image,0,0);
   const reference=(await send({type:'frame',time:performance.now(),frame:await createImageBitmap(original)})).result.landmarks;
   const active=reference.find(p=>p[0].x>.5),resting=reference.find(p=>p[0].x<.5);
   if(!active||!resting)throw Error('Reference hands not found');
   const canvas=document.createElement('canvas');canvas.width=960;canvas.height=540;
   const ctx=canvas.getContext('2d'),sw=image.width/2,scale=100/sw;
   // Draw two real open-palm hand images and synthesise a body pose whose shoulders sit
   // below or above each wrist so raisedPalmBodySide treats that hand as raised or lowered.
   window.sendHands=async({leftX=300,rightX=680,y=90,raiseLeft=true,raiseRight=false})=>{
    const time=performance.now();
    ctx.fillStyle='#ddd';ctx.fillRect(0,0,960,540);
    ctx.drawImage(image,sw,0,sw,image.height,leftX,y,100,image.height*scale);
    ctx.drawImage(image,0,0,sw,image.height,rightX,y,100,image.height*scale);
    const poseLandmarks=Array.from({length:33},()=>({x:0,y:0,z:0,visibility:0,presence:0})),handHints={};
    for(const [points,sx,px,side,w,e,s,raise] of [[active,sw,leftX,'L',16,14,12,raiseLeft],[resting,0,rightX,'R',15,13,11,raiseRight]]){
     const mapped=points.map(p=>({x:(px+(p.x*image.width-sx)*scale)/960,y:(y+p.y*image.height*scale)/540,z:0,visibility:.99,presence:.99}));
     poseLandmarks[w]=mapped[0];
     poseLandmarks[e]={...mapped[0],x:mapped[0].x+(mapped[0].x-mapped[12].x)*1.3,y:mapped[0].y+(mapped[0].y-mapped[12].y)*1.3};
     // raised: shoulder BELOW the wrist (larger y); lowered: shoulder ABOVE the wrist.
     poseLandmarks[s]={x:side==='L'?.42:.62,y:mapped[0].y+(raise?.22:-.22),z:0,visibility:.99,presence:.99};
     handHints[side]=mapped[9];
    }
    const data=await send({type:'frame',time,frame:await createImageBitmap(canvas),body:{poseLandmarks,poseWorldLandmarks:[],handHints}});
    motionWorker.dispatchEvent(new MessageEvent('message',{data:{...data,synthetic:true}}));
    const q=fleetQA,sample={detected:data.result.landmarks.length,mode:q.mode,commit:+q.commitProgress.toFixed(2),change:+q.changeProgress.toFixed(2),commitState:q.commitState,changeState:q.changeState,character:q.character,modeFrame:+q.modeFrame.toFixed(2)};
    gestureSamples.push(sample);return sample;
   };
  });
  const send=opts=>page.evaluate(o=>sendHands(o),opts);
  // Pump the same held pose until `pred(sample)` holds, or fail after `tries` frames.
  const holdUntil=async(opts,pred,label,tries=60)=>{
   for(let i=0;i<tries;i++){const s=await send(opts);if(pred(s))return s;await page.waitForTimeout(40);}
   throw Error(label+' never happened: '+JSON.stringify(await page.evaluate(()=>gestureSamples.slice(-8))));
  };

  // Sanity: start in browse, character loaded.
  assert.equal(await page.evaluate(()=>fleetQA.mode),'browse');
  assert.equal(await page.evaluate(()=>fleetQA.character),'orbit');

  // 1) Two raised palms held still -> both detected, commit progress climbs, mode -> embodied.
  const committed=await holdUntil({raiseLeft:true,raiseRight:true},s=>s.mode==='embodied','commit (two palms held)');
  assert.equal(committed.detected,2,'both palms must be seen during commit');
  assert.equal(committed.mode,'embodied');
  // Camera dollies forward (modeFrame eases toward 1).
  await page.waitForFunction(()=>fleetQA.modeFrame>.5,null,{timeout:4000});

  // 2) While embodied, a one-hand lateral SWEEP must not switch characters (swipe disabled)
  //    and must not fire the change dwell (it is moving, not still).
  for(const x of [300,360,420,480,540,600]){await send({raiseLeft:true,raiseRight:false,leftX:x});await page.waitForTimeout(30);}
  assert.equal(await page.evaluate(()=>fleetQA.character),'orbit','swipe must be disabled while embodied');
  assert.equal(await page.evaluate(()=>fleetQA.mode),'embodied','a moving palm must not step back to browse');

  // Drop hands so the change detector is unlatched before the deliberate hold.
  for(let i=0;i<4;i++){await send({raiseLeft:false,raiseRight:false});await page.waitForTimeout(40);}

  // 3) One raised palm held still -> change dwell fires, mode -> browse, avatar dollies back.
  const returned=await holdUntil({raiseLeft:true,raiseRight:false,leftX:360},s=>s.mode==='browse','change (one palm held)');
  assert.equal(returned.mode,'browse');
  await page.waitForFunction(()=>fleetQA.modeFrame<.5,null,{timeout:4000});

  // 4) In browse, two palms that keep MOVING must NOT commit (stillness resets the dwell).
  for(let i=0;i<4;i++){await send({raiseLeft:false,raiseRight:false});await page.waitForTimeout(40);}
  let moved=null;
  for(const x of [260,300,340,380,420,460,500,540,500,460,420,380]){moved=await send({raiseLeft:true,raiseRight:true,leftX:x,rightX:x+340});await page.waitForTimeout(40);}
  assert.equal(await page.evaluate(()=>fleetQA.mode),'browse','moving two palms must not commit');
  assert.ok(moved.commit<1,'commit dwell must not complete while palms are moving');

  const samples=await page.evaluate(()=>{photoWorker.terminate();return gestureSamples;});
  assert(samples.some(s=>s.detected===2&&s.commitState==='holding'),'commit dwell must engage with two raised palms');
  assert(samples.some(s=>s.changeState==='holding'),'change dwell must engage with one raised palm');
  assert.equal(await page.evaluate(()=>cameraRequests),1,'exactly one camera start');
  assert.deepEqual(errors,[],'no page errors');
  fs.writeFileSync('.context/qa/mode-gestures.json',JSON.stringify({samples,errors,realHandModel:true,simulatedBodyHints:true,physicalCameraTested:false},null,2));
  console.log('PASS browse->(two-palm commit)->embodied; swipe disabled + moving palm ignored; (one-palm hold)->browse; moving two palms never commit');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
