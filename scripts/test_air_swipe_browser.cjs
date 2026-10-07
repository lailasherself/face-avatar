const {chromium}=require('playwright');
const fs=require('node:fs');
const assert=require('node:assert/strict');
const nextCharacter=JSON.parse(fs.readFileSync('assets/3dai/manifest.json')).characters[1].id;
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[];
  fs.mkdirSync('.context/qa',{recursive:true});
  await page.route('**/.context/qa/right_hands.jpg',route=>route.fulfill({path:process.env.HAND_FIXTURE||'.context/qa/right_hands.jpg',contentType:'image/jpeg'}));
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
  await page.goto(`${process.env.INSTALLATION_URL||'http://localhost:8014'}/cockpit.html?qa&assets=3dai&character=orbit`);
  await page.waitForFunction(()=>window.fleetQA?.handTrackingReady,null,{timeout:60000});
  await page.evaluate(async()=>{
   window.injectMotion=true;window.swipeSamples=[];
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
   window.sendPhotoHands=async(x,lowered=false,drop=false)=>{
    const time=performance.now(),y=lowered?330:100;
    ctx.fillStyle='#ddd';ctx.fillRect(0,0,960,540);
    ctx.drawImage(image,sw,0,sw,image.height,x,y,100,image.height*scale);
    ctx.drawImage(image,0,0,sw,image.height,650,320,100,image.height*scale);
    const poseLandmarks=Array.from({length:33},()=>({x:0,y:0,z:0,visibility:0,presence:0})),handHints={};
    for(const [points,sx,px,py,side,w,e,s] of [[active,sw,x,y,'L',16,14,12],[resting,0,650,320,'R',15,13,11]]){
     const mapped=points.map(p=>({x:(px+(p.x*image.width-sx)*scale)/960,y:(py+p.y*image.height*scale)/540,z:0,visibility:.99,presence:.99}));
     poseLandmarks[w]=mapped[0];poseLandmarks[e]={...mapped[0],x:mapped[0].x+(mapped[0].x-mapped[12].x)*1.3,y:mapped[0].y+(mapped[0].y-mapped[12].y)*1.3};
     poseLandmarks[s]={x:side==='L'?.5:.65,y:.5,z:0,visibility:.99,presence:.99};handHints[side]=mapped[9];
    }
    const data=await send({type:'frame',time,frame:await createImageBitmap(canvas),body:{poseLandmarks,poseWorldLandmarks:[],handHints}});
    if(drop)data.result.landmarks=[];
    motionWorker.dispatchEvent(new MessageEvent('message',{data:{...data,synthetic:true}}));
    const sample={x,lowered,drop,time,detected:data.result.landmarks.length,ageMs:performance.now()-time,state:fleetQA.swapState,reason:fleetQA.swapReason,character:fleetQA.character};
    swipeSamples.push(sample);return sample;
   };
  });
  const sample=(x,lowered=false,drop=false)=>page.evaluate(({x,lowered,drop})=>sendPhotoHands(x,lowered,drop),{x,lowered,drop});
  const hold=async x=>{
   for(let i=0;i<25;i++){
    const state=await sample(x);if(state.state==='armed')return;
    await page.waitForTimeout(40);
   }
   throw Error('Real photo palm never armed: '+JSON.stringify(await page.evaluate(()=>swipeSamples.slice(-10))));
  };
  // A casual lateral move without holding must not switch characters.
  for(const x of [300,360,420,480,540]){await sample(x);await page.waitForTimeout(30);}
  assert.equal(await page.evaluate(()=>fleetQA.character),'orbit');
  for(let i=0;i<5;i++){await sample(300,true);await page.waitForTimeout(60);}
  await hold(300);
  for(const x of [350,400,450,500,550]){
   const state=await sample(x,false,x===400);
   if(x===400){assert.equal(state.state,'armed',JSON.stringify(await page.evaluate(()=>swipeSamples.slice(-6))));assert.equal(state.reason,'tracking-gap');}
   await page.waitForTimeout(30);
  }
  await page.waitForFunction(id=>fleetQA.character===id,nextCharacter,{timeout:15000}).catch(async error=>{
   fs.writeFileSync('.context/qa/air-swipe-failure.json',JSON.stringify(await page.evaluate(()=>({samples:swipeSamples,qa:fleetQA,notice:document.getElementById('notice').textContent})),null,2));
   throw error;
  });
  // Holding/recoil cannot cause a second switch without release.
  for(const x of [550,500,450,400,350,300]){await sample(x);await page.waitForTimeout(40);}
  assert.equal(await page.evaluate(()=>fleetQA.character),nextCharacter);
  for(let i=0;i<8;i++){await sample(550,true);await page.waitForTimeout(80);}
  await hold(550);
  for(const x of [500,450,400,350,300]){await sample(x);await page.waitForTimeout(30);}
  await page.waitForFunction(()=>fleetQA.character==='orbit',null,{timeout:15000});
  assert.equal(await page.evaluate(()=>cameraRequests),1);
  assert.equal(await page.locator('header').isVisible(),false);
  assert.equal(await page.locator('footer').isVisible(),false);
  assert.equal(await page.evaluate(()=>fleetQA.vehicleUUID),null);
  const samples=await page.evaluate(()=>{photoWorker.terminate();return swipeSamples;});
  assert(samples.some(s=>s.detected===2&&s.state==='armed'),'both visible hands must allow one raised palm');
  assert.deepEqual(errors,[]);
  fs.writeFileSync('.context/qa/air-swipe.json',JSON.stringify({samples,errors,realHandModel:true,simulatedBodyHints:true,physicalCameraTested:false},null,2));
  await page.screenshot({path:'.context/qa/swipe-complete.png'});
  console.log('PASS real hand-model replay switches Orbit -> '+nextCharacter+' -> Orbit; missed detection recovery, resting hand, recoil guard and one camera');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
