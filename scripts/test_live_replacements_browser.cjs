const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const out='.context/qa/live-image-replacements';

(async()=>{
 fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',args:['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream']});
 const report={syntheticCamera:true,hardwareCertified:false,views:[],errors:[]};
 try{
  const page=await browser.newPage();
  page.on('pageerror',error=>report.errors.push(error.message));
  for(const id of ['orbit','coral']){
   const expected='orbit'; // A bookmarked Coral URL must fall back to the active roster.
   for(const viewport of [{width:1920,height:1080},{width:1080,height:1920}]){
    await page.setViewportSize(viewport);
    await page.goto(`http://localhost:8014/cockpit.html?qa&assets=3dai&character=${id}`);
    await page.waitForFunction(id=>window.fleetQA?.character===id&&fleetQA.cameraActive&&fleetQA.renderFrame>10,expected,{timeout:60000});
    assert.equal(await page.locator('header').isVisible(),false);
    assert.equal(await page.locator('footer').isVisible(),false);
    const state=await page.evaluate(()=>{
     const canvas=document.getElementById('scene'),gl=canvas.getContext('webgl2');
     const pixels=new Uint8Array(canvas.width*canvas.height*4);gl.readPixels(0,0,canvas.width,canvas.height,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
     let changed=0;for(let i=0;i<pixels.length;i+=4)if(Math.abs(pixels[i]-pixels[0])+Math.abs(pixels[i+1]-pixels[1])+Math.abs(pixels[i+2]-pixels[2])+Math.abs(pixels[i+3]-pixels[3])>40)changed++;
     return {character:fleetQA.character,cameraActive:fleetQA.cameraActive,vehicle:fleetQA.vehicleUUID,bones:Object.keys(fleetQA.bones).length,drawCalls:fleetQA.drawCalls,triangles:fleetQA.triangles,pixelFraction:changed/(canvas.width*canvas.height)};
    });
    assert.equal(state.vehicle,null);assert.equal(state.bones,39);
    assert.equal(await page.locator('.character').count(),7);
    assert.equal(await page.locator('.character').filter({hasText:'Coral'}).count(),0);
    assert(state.drawCalls>0&&state.triangles>1000);assert(state.pixelFraction>.02,'Blank character canvas');
    await page.screenshot({path:`${out}/${id}-${viewport.width}x${viewport.height}.png`});
    report.views.push({id,...viewport,...state});
   }
  }
  assert.deepEqual(report.errors,[]);fs.writeFileSync(`${out}/report.json`,JSON.stringify(report,null,2));
  console.log('PASS live Orbit and paused Coral URL fallback, seven choices, automatic camera, hidden UI, no vehicle, landscape and portrait canvas checks');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
