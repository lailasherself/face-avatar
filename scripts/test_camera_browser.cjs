// NODE_PATH=.context/qa/node_modules node scripts/test_camera_browser.cjs
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const base=process.env.INSTALLATION_URL||'http://localhost:8014/cockpit.html';
const output='.context/qa/camera-eyes';
fs.mkdirSync(output,{recursive:true});
const weight=(sample,name)=>sample.morphs.find(m=>m.names.includes(name))?.weights[
  sample.morphs.find(m=>m.names.includes(name)).names.indexOf(name)]||0;

(async()=>{
  const browser=await chromium.launch({headless:true,
    executablePath:process.env.CHROME_PATH||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    args:['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream']});
  const errors=[],external=[],results=[];
  try{
    const page=await browser.newPage({viewport:{width:1920,height:1080}});
    page.on('pageerror',e=>errors.push(e.message));
    page.on('request',r=>{if(/^https?:/.test(r.url())&&new URL(r.url()).origin!==new URL(base).origin)external.push(r.url());});
    // Inject detector results at the camera boundary, without a mutable production API.
    await page.route('**/fleet.js',async route=>{
      const response=await route.fetch();
      const original=await response.text();
      const needle='const results=landmarker.detectForVideo(video,time);';
      assert(original.includes(needle));
      await route.fulfill({response,body:original.replace(needle,
        'const results=window.nextFaceResult?window.nextFaceResult():landmarker.detectForVideo(video,time);')});
    });
    await page.addInitScript(()=>{
      window.faceDefault={};
      window.nextFaceResult=()=>{
        const sequence=window.faceSequence;
        const raw=sequence?.frames.shift()??window.faceDefault;
        if(sequence)setTimeout(()=>{
          sequence.samples.push(fleetQA);
          if(!sequence.frames.length){window.faceSequence=null;sequence.resolve(sequence.samples);}
        },0);
        if(raw===false)return {faceBlendshapes:[]};
        return {faceBlendshapes:[{categories:Object.entries(raw).map(([categoryName,score])=>({categoryName,score}))}]};
      };
      window.runFaceSequence=frames=>new Promise(resolve=>{
        window.faceSequence={frames,samples:[],resolve};
        window.faceDefault=frames.at(-1);
      });
    });
    await page.goto(base+'?setup&qa&assets=3dai',{waitUntil:'networkidle'});
    await page.waitForFunction(()=>window.fleetQA?.cameraActive&&fleetQA.handTrackingReady,null,{timeout:60000});
    console.log('PASS operator mode starts camera and all local tracking models without a click.');
    const car=await page.evaluate(()=>fleetQA.vehicleUUID);
    assert.equal(car,null);assert.equal(await page.evaluate(()=>fleetQA.vehicleVisible),false);
    const sequence=frames=>page.evaluate(frames=>runFaceSequence(frames),frames);
    for(const id of ['orbit','pearl','juno','fuzz','clementine','coral','sprout','atl']){
      await page.evaluate(id=>document.querySelectorAll('.character')[[
        'orbit','pearl','juno','fuzz','clementine','coral','sprout','atl'].indexOf(id)].click(),id);
      await page.waitForFunction(id=>fleetQA.character===id,id);
      await sequence(Array(12).fill({}));
      const samples=await sequence([{}, {eyeBlinkLeft:1,eyeBlinkRight:1,eyeWideLeft:1}, {}, {}, {}]);
      assert(samples.every(s=>weight(s,'eyeBlinkLeft')<.002&&weight(s,'eyeWideLeft')<.002),id+' isolated spike');
      const blink=await sequence(Array(8).fill({eyeBlinkLeft:1,eyeBlinkRight:1,eyeSquintLeft:.9,eyeWideLeft:.9}));
      assert(weight(blink.at(-1),'eyeBlinkLeft')>.98,id+' blink closure');
      assert.equal(weight(blink.at(-1),'eyeWideLeft'),0,id+' competing aperture');
      if(['pearl','juno'].includes(id))assert.equal(weight(blink.at(-1),'eyeBlinkRight'),0,id+' cyclops alias');
      const dropout=await sequence([false,{eyeBlinkLeft:1,eyeBlinkRight:1},{eyeBlinkLeft:1,eyeBlinkRight:1}]);
      assert(dropout.every(s=>weight(s,'eyeBlinkLeft')>.98),id+' short tracking gap');
      await page.screenshot({path:output+'/'+id+'-closed.png'});
      await sequence(Array(15).fill({}));
      await page.screenshot({path:output+'/'+id+'-open.png'});
      const pixels=await page.evaluate(()=>{
        const canvas=document.createElement('canvas');canvas.width=240;canvas.height=180;
        const ctx=canvas.getContext('2d');ctx.drawImage(document.getElementById('scene'),0,0,240,180);
        return new Set(ctx.getImageData(0,0,240,180).data).size;
      });
      assert(pixels>100,id+' blank canvas');
      assert.equal(await page.evaluate(()=>fleetQA.vehicleUUID),car);
      assert.equal(await page.evaluate(()=>fleetQA.cameraActive),true);
      results.push({id,spikeRejected:true,blinkClosed:true,shortGapStable:true,pixelValues:pixels});
    }
    console.log('PASS all eight rendered source rigs: isolated spikes rejected, full blinks, stable short tracking gaps, no vehicle.');
    await page.getByRole('button',{name:'Stop camera',exact:true}).click();
    await page.waitForTimeout(4200);
    assert.equal(await page.evaluate(()=>fleetQA.cameraActive),false);
    await page.reload({waitUntil:'networkidle'});
    await page.waitForFunction(()=>window.fleetQA?.cameraActive&&fleetQA.handTrackingReady,null,{timeout:60000});
    console.log('PASS explicit stop stays stopped; reopening automatically starts camera.');
    for(const viewport of [{width:1920,height:1080},{width:1080,height:1920}]){
      await page.setViewportSize(viewport);
      await page.goto(base+'?qa&assets=3dai',{waitUntil:'networkidle'});
      await page.waitForFunction(()=>window.fleetQA?.cameraActive&&fleetQA.handTrackingReady,null,{timeout:60000});
      assert.equal(await page.locator('header').isVisible(),false);
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),viewport.width);
      await page.screenshot({path:output+'/installation-'+viewport.width+'.png'});
    }
    for(const errorName of ['NotAllowedError','NotReadableError']){
      const unavailable=await browser.newPage();
      await unavailable.addInitScript(errorName=>{
        window.cameraAttempts=0;
        navigator.mediaDevices.getUserMedia=async()=>{
          window.cameraAttempts++;
          throw new DOMException('Synthetic camera failure',errorName);
        };
      },errorName);
      await unavailable.goto(base+'?setup&qa',{waitUntil:'networkidle'});
      await unavailable.waitForFunction(()=>window.fleetQA&&!document.getElementById('camera-retry').hidden);
      assert.equal(await unavailable.evaluate(()=>cameraAttempts),1);
      if(errorName==='NotReadableError')await unavailable.locator('#blink').fill('0.5');
      await unavailable.waitForTimeout(4200);
      assert.equal(await unavailable.evaluate(()=>cameraAttempts),1,errorName+' unexpected retry');
      if(errorName==='NotReadableError'){
        const qa=await unavailable.evaluate(()=>fleetQA);
        assert(Math.abs(weight(qa,'eyeBlinkLeft')-.5)<.01,'retry interrupted manual inspection');
      }
      await unavailable.close();
    }
    console.log('PASS denied permission does not loop; manual inspection cancels pending camera retries.');
    assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
    fs.writeFileSync(output+'/report.json',JSON.stringify({passed:true,syntheticCamera:true,injectedFaceSignals:true,
      automaticOperatorCamera:true,automaticInstallationCamera:true,localRequestsOnly:true,results,errors},null,2));
    console.log('PASS local-only fullscreen installation in landscape and portrait display orientations.');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
