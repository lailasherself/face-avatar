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
  const page=await browser.newPage({viewport:{width:1920,height:1080}}),errors=[],requests=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(r.url().endsWith('.glb'))requests.push(r.url());});
  await page.route('**/fleet.js',async route=>{
   const response=await route.fetch();
   await route.fulfill({response,body:await response.text()+`
window.stageTest={select:selectCharacter,staticState:()=>[...fleetStage.entries].filter(([i])=>i!==currentIndex).map(([i,e])=>({i,position:e.preview.position.toArray(),meshes:e.preview.children.map(m=>({matrix:m.matrix.toArray(),version:m.geometry.attributes.position.version,morphs:m.morphTargetInfluences,skinned:!!m.isSkinnedMesh}))})),expression:()=>{target.jawOpen=.7;target.tongueOut=.8;demo=true;demoStart=performance.now();}};
`});
  });
  await page.goto('http://localhost:8014/cockpit.html?qa&character=orbit');
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
  for(const viewport of [{width:1920,height:1080},{width:1080,height:1920}]){
   await page.setViewportSize(viewport);await page.waitForTimeout(500);
   for(let index=0;index<count;index++){
    const elapsed=await page.evaluate(async i=>{const t=performance.now();await stageTest.select(i);return performance.now()-t;},index);
    await page.waitForTimeout(400);
    const q=await page.evaluate(()=>fleetQA);
    assert.equal(q.stage.filter(e=>e.active).length,1);assert.equal(q.stage.filter(e=>e.background).length,count-1);
    assert(q.stage.find(e=>e.index===index).active);
    for(const entry of q.stage){
     const s=entry.screen;
     assert(s.left>-.99&&s.right<.99&&s.bottom>-.99&&s.top<.99,`${q.character}: cropped character ${entry.index}: ${JSON.stringify(s)}`);
    }
    const backgrounds=q.stage.filter(e=>e.background);
    for(let a=0;a<backgrounds.length;a++)for(let b=a+1;b<backgrounds.length;b++){
     const x=backgrounds[a].screen,y=backgrounds[b].screen;
     assert(x.right<y.left||y.right<x.left||x.top<y.bottom||y.top<x.bottom,'background characters overlap');
    }
    const pixels=await page.evaluate(()=>{
     const canvas=document.getElementById('scene'),gl=canvas.getContext('webgl2');
     return fleetQA.stage.map(e=>{
      const s=e.screen,x=Math.max(0,Math.floor((s.left+1)*canvas.width/2)),y=Math.max(0,Math.floor((s.bottom+1)*canvas.height/2));
      const w=Math.min(canvas.width-x,Math.ceil((s.right-s.left)*canvas.width/2)),h=Math.min(canvas.height-y,Math.ceil((s.top-s.bottom)*canvas.height/2));
      const p=new Uint8Array(w*h*4);gl.readPixels(x,y,w,h,gl.RGBA,gl.UNSIGNED_BYTE,p);
      let colored=0;for(let i=0;i<p.length;i+=4)if(Math.max(p[i],p[i+1],p[i+2])-Math.min(p[i],p[i+1],p[i+2])>25||Math.max(p[i],p[i+1],p[i+2])<160)colored++;
      return {index:e.index,fraction:colored/(w*h)};
     });
    });
    for(const p of pixels)assert(p.fraction>.015,`blank character ${p.index}: ${p.fraction}`);
    report.switches.push({character:q.character,...viewport,elapsed,drawCalls:q.drawCalls,triangles:q.triangles,pixels});
    if(index===0||index===5){await page.screenshot({path:`${out}/${q.character}-${viewport.width}x${viewport.height}.png`});report.views.push({character:q.character,...viewport});}
   }
  }
  assert.equal(requests.length,initialRequests,'switching never downloads a rig again');
  await page.evaluate(()=>Promise.all([stageTest.select(1),stageTest.select(2),stageTest.select(0)]));
  assert.equal(await page.evaluate(()=>fleetQA.character),'orbit','latest selection wins');
  assert.equal(await page.locator('header').isVisible(),false);assert.equal(await page.locator('footer').isVisible(),false);
  assert.equal(await page.locator('#camera-preview').isVisible(),false);
  assert.deepEqual(errors,[]);report.errors=errors;
  fs.writeFileSync(`${out}/report.json`,JSON.stringify(report,null,2));
  console.log('PASS active roster visible, Coral excluded, stationary cached backgrounds, one live rig, cached switching, latest request wins, landscape/portrait pixel checks');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
