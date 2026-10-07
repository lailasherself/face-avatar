// Full phone-triggered AR capture using actual face inference on a public fixture.
const {chromium}=require('playwright');
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');

(async()=>{
  const output=path.resolve('.context/qa/spaceship-photo');fs.mkdirSync(output,{recursive:true});
  const fixture=process.env.AR_FIXTURE||'.context/qa/photo-flow/segmentation-fixture.jpg';
  const source='data:image/jpeg;base64,'+fs.readFileSync(fixture).toString('base64');
  const base=process.env.INSTALLATION_URL||'http://127.0.0.1:8030';
  const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
  const errors=[];
  try{
    const installation=await browser.newPage({viewport:{width:1440,height:900}});
    if(process.env.CLOUD_PHOTO_OPERATOR)await installation.addInitScript(owner=>localStorage.setItem('alien-photo-owner',owner),process.env.CLOUD_PHOTO_OPERATOR);
    installation.on('pageerror',e=>errors.push(e.message));
    installation.on('console',message=>{if(message.type()==='warning'||message.type()==='error')console.log('Installation:',message.text());});
    let previousCommand='';
    installation.on('response',async response=>{
      if(!response.url().includes('action=heartbeat'))return;
      try{const data=await response.json(),key=JSON.stringify({state:data.state,error:data.error});if(key!==previousCommand){previousCommand=key;console.log('Camera command:',key);}}catch{}
    });
    await installation.addInitScript(({source})=>{
      navigator.mediaDevices.getUserMedia=async()=>{
        const img=new Image();img.src=source;await img.decode();
        const canvas=document.createElement('canvas');canvas.width=960;canvas.height=720;
        const ctx=canvas.getContext('2d');window.fixtureVisible=true;
        function draw(){
          ctx.fillStyle='#679caa';ctx.fillRect(0,0,960,720);
          if(window.fixtureVisible){const scale=720/img.height;ctx.drawImage(img,480-img.width*scale/2,0,img.width*scale,720);}
          requestAnimationFrame(draw);
        }
        draw();return canvas.captureStream(30);
      };
    },{source});
    // No photos query parameter: the station discovers the enabled service.
    await installation.goto(`${base}/cockpit.html?assets=3dai&view=ship&character=orbit&qa`);
    await installation.waitForFunction(()=>window.fleetQA?.ar?.fresh&&fleetQA.vinylReady,{},{timeout:90000});
    const freshness=await installation.evaluate(async()=>{
      const {AlienHeadEffect}=await import('./alien-head-effect.js');
      const sample={person:'visitor',captureTime:500,faceLandmarks:[[]],facialTransformationMatrixes:[{data:[1]}]};
      const effect={sample};
      return {shutter:AlienHeadEffect.prototype.fresh.call(effect,'visitor',1000),
        countdown:AlienHeadEffect.prototype.fresh.call(effect,'visitor',1000,750),
        wrongPerson:AlienHeadEffect.prototype.fresh.call(effect,'other',1000,750),
        expired:AlienHeadEffect.prototype.fresh.call(effect,'visitor',1300,750)};
    });
    assert.deepEqual(freshness,{shutter:false,countdown:true,wrongPerson:false,expired:false});
    const link=installation.locator('#spaceship-photo a');await link.waitFor({state:'visible'});
    const phoneURL=await link.getAttribute('href');assert.ok(phoneURL&&!phoneURL.includes('127.0.0.1'));
    const cloud=new URL(phoneURL).searchParams.has('station');
    assert.equal(await installation.locator('#spaceship-photo img').evaluate(img=>img.naturalWidth>100),true);
    await installation.screenshot({path:path.join(output,'spaceship-qr.png')});
    await installation.locator('#view-tv').click();assert.equal(await link.isVisible(),false);
    await installation.locator('#view-vinyl').click();assert.equal(await link.isVisible(),false);
    await installation.locator('#view-ship').click();await link.waitFor({state:'visible'});
    await installation.locator('#view-ship').evaluate(tab=>tab.blur());
    const phone=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
    phone.on('pageerror',e=>errors.push(e.message));
    await phone.goto(phoneURL);await phone.waitForFunction(()=>!document.querySelector('#take').disabled);
    assert.equal(await phone.locator('#demo').isVisible(),false,'Real capture, not sample mode');
    await phone.screenshot({path:path.join(output,'phone-ready.png')});
    await phone.locator('#take').click();await phone.locator('#countdown').waitFor({state:'visible'});
    assert.match(await phone.locator('#countdown').innerText(),/Lower your phone/);
    try{await installation.getByText('Lower your phone. Look at the camera.',{exact:true}).waitFor({state:'visible'});}
    catch(error){console.log(await phone.locator('body').innerText());console.log(await installation.evaluate(()=>fleetQA.ar));await phone.screenshot({path:path.join(output,'countdown-failure.png')});throw error;}
    await installation.keyboard.press('ArrowRight');await installation.waitForTimeout(200);
    assert.equal(await installation.evaluate(()=>fleetQA.character),'orbit','Selection stays locked during capture');
    await phone.screenshot({path:path.join(output,'phone-countdown.png')});
    try{await phone.waitForFunction(()=>document.querySelector('#preview').naturalWidth===1200,{},{timeout:20000});}
    catch(error){console.log(await phone.locator('body').innerText());console.log(await installation.evaluate(()=>fleetQA.ar));await phone.screenshot({path:path.join(output,'failure.png')});throw error;}
    await phone.screenshot({path:path.join(output,'phone-result.png')});
    const image=await phone.locator('#preview').evaluate(img=>({width:img.naturalWidth,height:img.naturalHeight}));
    const download=phone.waitForEvent('download');await phone.locator('#save').click();await(await download).saveAs(path.join(output,'alien-on-body.jpg'));
    assert.ok(await installation.evaluate(()=>fleetQA.ar.frames>0),'Live head render captured');
    await phone.locator('#retake').click();await phone.waitForFunction(()=>!document.querySelector('#take').disabled);
    await phone.locator('#take').click();await phone.locator('#countdown').waitFor({state:'visible'});
    await installation.evaluate(()=>window.fixtureVisible=false);
    await phone.waitForFunction(()=>document.querySelector('#welcome').hidden===false);
    assert.equal(await phone.locator('#preview').isVisible(),false,'Tracking loss cannot return a photo');
    const heartbeat=cloud?'**/api/photos?action=heartbeat&*':'**/api/photo-operator/heartbeat';
    await installation.route(heartbeat,route=>route.abort());
    await installation.waitForFunction(()=>document.querySelector('#spaceship-photo p').textContent==='Photo station offline');
    assert.equal(await link.isVisible(),cloud,'Public QR stays visible offline; local-only QR hides');
    await installation.unroute(heartbeat);await link.waitFor({state:'visible'});
    for(const width of [390,768]){
      await installation.setViewportSize({width,height:900});await installation.waitForTimeout(500);
      assert.equal(await installation.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
      const box=await installation.locator('#spaceship-photo').boundingBox();assert.ok(box.x>=0&&box.x+box.width<=width&&box.y+box.height<=900);
      await installation.screenshot({path:path.join(output,`spaceship-${width}.png`)});
    }
    assert.deepEqual(errors,[]);
    const report={actualFaceInference:true,physicalVisitorTested:false,phoneURL,image,errors,checks:['spaceship-only QR','real AR photo delivered to phone','countdown instructions','download','character lock','tracking loss cancels','offline QR policy','390/768/1440 layout']};
    fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2));console.log(report);
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
