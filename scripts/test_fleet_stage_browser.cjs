const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const out='.context/qa/fleet-stage';
const count=require('../assets/3dai/manifest.json').characters.length;

(async()=>{
 fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',args:['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream']});
 const report={syntheticCamera:true,physicalHardwareTested:false,views:[],switches:[]};
 try{
  const page=await browser.newPage({viewport:{width:1920,height:1080},hasTouch:true}),errors=[],requests=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(r.url().endsWith('.glb'))requests.push(r.url());});
  await page.route('**/fleet.js',async route=>{
   const response=await route.fetch();
   await route.fulfill({response,body:await response.text()+`
window.stageTest={select:selectCharacter,delayLoad:index=>{const original=characterLoads.get(index);let release;characterLoads.set(index,new Promise(resolve=>{release=()=>resolve(original);}));return window.releaseLoad=()=>{characterLoads.set(index,original);release();};},staticState:()=>[...fleetStage.entries].filter(([i])=>i!==currentIndex).map(([i,e])=>({i,visible:e.rig.visible,position:e.rig.position.toArray(),previewMeshes:e.preview.children.length})),expression:()=>{target.jawOpen=.7;target.tongueOut=.8;demo=true;demoStart=performance.now();},pixels:()=>{
 const gl=renderer.getContext(),w=gl.drawingBufferWidth,h=gl.drawingBufferHeight;
 const capture=()=>{renderer.render(scene,camera);const p=new Uint8Array(w*h*4);gl.readPixels(0,0,w,h,gl.RGBA,gl.UNSIGNED_BYTE,p);return p;};
 const live=capture();current.gltf.scene.visible=false;const empty=capture();current.gltf.scene.visible=true;renderer.render(scene,camera);
 const waist=-waistClip.constant,entry=fleetStage.entries.get(currentIndex);
 const cutoff=new THREE.Vector3(camera.position.x,waist,entry.bounds.min.z).project(camera).y;
 let changed=0,belowWaist=0;
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
  const i=(y*w+x)*4,difference=Math.max(...[0,1,2].map(c=>Math.abs(live[i+c]-empty[i+c])));
  if(difference>8){changed++;if(y<(cutoff+1)*h/2)belowWaist++;}
 }
 return {fraction:changed/(w*h),belowWaist,cutoff};
}};
`});
  });
  await page.goto(`${process.env.INSTALLATION_URL||'http://localhost:8014'}/cockpit.html?qa&character=orbit`);
  await page.waitForFunction(count=>window.fleetQA?.loadedCharacters===count&&fleetQA.cameraActive,count,{timeout:120000});
  await page.waitForTimeout(800);
  const initialRequests=requests.length;
  assert.equal(initialRequests,count,'exactly one download per rig');
  assert(!requests.some(url=>url.includes('coral')),'Coral must not download');
  const frozen=await page.evaluate(()=>stageTest.staticState());
  const before=await page.evaluate(()=>({backdrop:fleetQA.backdropFrames,render:fleetQA.renderFrame}));
  await page.evaluate(()=>stageTest.expression());await page.waitForTimeout(700);
  assert.deepEqual(await page.evaluate(()=>stageTest.staticState()),frozen,'inactive cast stays neutral and stationary');
  assert.equal(await page.evaluate(()=>fleetQA.backdropFrames),before.backdrop,'no background redraws during live tracking');
  assert(await page.evaluate(n=>fleetQA.renderFrame>n+5,before.render),'live rendering continues');
  for(const viewport of [{width:1920,height:1080},{width:390,height:844}]){
   await page.setViewportSize(viewport);await page.waitForTimeout(500);
   for(let index=0;index<count;index++){
    const elapsed=await page.evaluate(async i=>{const t=performance.now();await stageTest.select(i);return performance.now()-t;},index);
    await page.waitForTimeout(400);
    const q=await page.evaluate(()=>fleetQA);
    assert.equal(q.stage.filter(e=>e.active).length,1);assert.equal(q.stage.filter(e=>e.background).length,0);
    assert(q.stage.find(e=>e.index===index).active);
    for(const entry of q.stage.filter(e=>e.active)){
     const s=entry.screen;
     assert(s.left>-.99&&s.right<.99&&s.top<.99,`${q.character}: cropped head ${entry.index}: ${JSON.stringify(s)}`);
    }
    const pixels=await page.evaluate(()=>stageTest.pixels());
    assert(pixels.fraction>.025,`blank or tiny character ${q.character}: ${pixels.fraction}`);
    assert(pixels.cutoff<=-1,`${q.character}: waist must be below the TV edge`);
    assert.equal(pixels.belowWaist,0,`${q.character}: lower body visible`);
    report.switches.push({character:q.character,...viewport,elapsed,drawCalls:q.drawCalls,triangles:q.triangles,pixels});
    await page.screenshot({path:`${out}/${q.character}-${viewport.width}x${viewport.height}.png`});report.views.push({character:q.character,...viewport});
   }
  }
  assert.equal(requests.length,initialRequests,'switching never downloads a rig again');
  await page.evaluate(()=>Promise.all([stageTest.select(1),stageTest.select(2),stageTest.select(0)]));
  assert.equal(await page.evaluate(()=>fleetQA.character),'orbit','latest selection wins');
  await page.evaluate(()=>{stageTest.delayLoad(1);});
  await page.keyboard.press('ArrowRight');
  await page.keyboard.press('ArrowRight');
  await page.waitForFunction(()=>fleetQA.character==='nebula');
  await page.evaluate(()=>releaseLoad());
  await page.waitForTimeout(100);
  assert.equal(await page.evaluate(()=>fleetQA.character),'nebula','navigation while loading accumulates and stale load cannot revert it');
  await page.evaluate(()=>stageTest.select(0));
  await page.keyboard.press('ArrowRight');await page.waitForFunction(()=>fleetQA.character!=='orbit');
  const touch=await page.context().newCDPSession(page);
  await touch.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:80,y:400}]});
  await touch.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:250,y:400}]});
  await touch.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
  await page.waitForFunction(()=>fleetQA.character==='orbit');
  assert.equal(await page.locator('header').isVisible(),false);assert.equal(await page.locator('footer').isVisible(),false);
  assert.equal(await page.locator('#camera-preview').isVisible(),false);
  assert.deepEqual(errors,[]);report.errors=errors;
  fs.writeFileSync(`${out}/report.json`,JSON.stringify(report,null,2));
  console.log('PASS one large alien, concealed lower body, cached switching, keyboard/touch swipes, latest request wins, TV/mobile pixel checks');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
