const {chromium}=require('playwright');
const fs=require('node:fs');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>{
   window.cameraRequests=0;
   navigator.mediaDevices.getUserMedia=async constraints=>{
    window.cameraRequests++;window.requestedCamera=constraints;
    const c=document.createElement('canvas');c.width=1280;c.height=720;const ctx=c.getContext('2d');
    const draw=()=>{
     ctx.fillStyle='#eee';ctx.fillRect(0,0,1280,720);
     for(const [x,y,color] of [[0,0,'#ff0000'],[1180,0,'#00ff00'],[0,620,'#0000ff'],[1180,620,'#ffff00']]){ctx.fillStyle=color;ctx.fillRect(x,y,100,100);}
    };
    draw();window.sourceTimer=setInterval(draw,33);return c.captureStream(30);
   };
  });
  await page.route('**/fleet.js',async route=>{
   const response=await route.fetch();await route.fulfill({response,body:await response.text()+`
window.framingPose=state=>{
 const pose=Array.from({length:33},()=>({x:.5,y:.5,z:0,visibility:1,presence:1}));
 pose[15].x=state==='near'?.02:state==='outside'?-.1:.3;pose[16].x=.7;
 framing.update({poseLandmarks:pose},performance.now());framing.lastDraw=-Infinity;framing.draw(performance.now());
};`});
  });
  await page.goto('http://localhost:8014/cockpit.html?setup&framing&qa&assets=3dai');
  await page.waitForFunction(()=>window.fleetQA?.cameraActive&&document.getElementById('camera-framing').open,null,{timeout:60000});
  const clean=async()=>{
   for(const selector of ['header','.character-info','#expression-panel','.view-tools','footer','#camera-preview'])assert.equal(await page.locator(selector).isVisible(),false,selector+' leaked into installation');
  };
  await clean();
  assert.equal(new URL(page.url()).searchParams.has('setup'),false,'legacy framing link must remove setup');
  assert.equal(new URL(page.url()).searchParams.get('assets'),'3dai');
  assert.equal(await page.evaluate(()=>cameraRequests),1);
  assert.deepEqual(await page.evaluate(()=>requestedCamera.video.resizeMode),{exact:'none'});
  assert.equal(await page.evaluate(()=>getComputedStyle(document.getElementById('camera-preview')).objectFit),'contain');
  const colors=await page.evaluate(()=>{
   const c=document.querySelector('#camera-framing canvas'),ctx=c.getContext('2d');
   return [[10,10],[1270,10],[10,710],[1270,710]].map(([x,y])=>Array.from(ctx.getImageData(x,y,1,1).data).slice(0,3));
  });
  assert.deepEqual(colors,[[255,0,0],[0,255,0],[0,0,255],[255,255,0]],'all four camera edges must remain visible');
  for(const [state,label] of [['near','Near edge'],['outside','Outside frame'],['in','In frame']]){
   const labels=await page.evaluate(state=>{framingPose(state);return [...document.querySelectorAll('[data-arm]')].map(e=>e.textContent);},state);
   assert.deepEqual(labels,[label,'In frame']);
  }
  for(const viewport of [{width:1440,height:1080},{width:1080,height:1920},{width:390,height:844}]){
   await page.setViewportSize(viewport);await page.evaluate(()=>framingPose('near'));
   const dimensions=await page.locator('#camera-framing').evaluate(d=>({width:d.getBoundingClientRect().width,scroll:d.scrollWidth,client:d.clientWidth}));
   assert(dimensions.width<=viewport.width);assert.equal(dimensions.scroll,dimensions.client);
   await page.screenshot({path:'.context/qa/framing-'+viewport.width+'.png'});
  }
  await page.getByRole('button',{name:'Close camera framing',exact:true}).click();
  assert.equal(await page.evaluate(()=>fleetQA.cameraActive),true);
  await clean();assert.equal(new URL(page.url()).searchParams.has('framing'),false);
  assert.equal(await page.evaluate(()=>cameraRequests),1);
  for(const viewport of [{width:1440,height:1080},{width:1080,height:1920}]){
   await page.setViewportSize(viewport);await clean();
   assert.equal(await page.locator('#camera-framing').isVisible(),false);
   const pixels=await page.evaluate(()=>{
    const c=document.createElement('canvas');c.width=240;c.height=180;const ctx=c.getContext('2d');
    ctx.drawImage(document.getElementById('scene'),0,0,240,180);return new Set(ctx.getImageData(0,0,240,180).data).size;
   });
   assert(pixels>100,'avatar scene is blank');
   await page.screenshot({path:'.context/qa/installation-clean-'+viewport.width+'.png'});
  }
  await page.reload();
  await page.waitForFunction(()=>window.fleetQA?.cameraActive,null,{timeout:60000});
  await clean();assert.equal(await page.locator('#camera-framing').isVisible(),false,'refresh must stay avatar-only');
  // Dedicated operator access remains explicit, never a side effect of framing.
  await page.goto('http://localhost:8014/cockpit.html?setup&qa&assets=3dai');
  await page.waitForFunction(()=>window.fleetQA?.cameraActive,null,{timeout:60000});
  await page.getByRole('button',{name:'Camera framing',exact:true}).click();
  assert.equal(await page.evaluate(()=>cameraRequests),1);
  await page.keyboard.press('Escape');
  await page.getByRole('button',{name:'Stop camera',exact:true}).click();
  await page.getByRole('button',{name:'Camera framing',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('[data-capture]').textContent==='Camera off');
  assert.deepEqual(errors,[]);
  fs.writeFileSync('.context/qa/camera-framing.json',JSON.stringify({colors,oneCamera:true,allEdgesVisible:true,legacyLinkStaysClean:true,cleanAfterCloseAndReload:true,errors,physicalCameraTested:false},null,2));
  console.log('PASS standalone framing, legacy-link migration, avatar-only close/reload, full-frame pixels, operator access and one camera');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
