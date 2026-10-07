const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');

(async()=>{
  const base=process.env.INSTALLATION_URL||'http://127.0.0.1:8042';
  const live=process.env.LIVE_QR==='1';
  const output=path.resolve('.context/qa/permanent-qr');fs.mkdirSync(output,{recursive:true});
  const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:900}}),errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    if(live)await page.addInitScript(()=>{navigator.mediaDevices.getUserMedia=async()=>{throw new DOMException('Camera disabled for public QR test','NotAllowedError');};});
    if(!live){
      await page.route('**/qr-test',route=>route.fulfill({contentType:'text/html',body:'<!doctype html><body style="margin:0"><main id="app" style="height:100vh;position:relative;background:#172b2b"></main></body>'}));
      await page.route('**/api/photos?action=availability&*',route=>route.fulfill({json:{online:false,ready:false,busy:false}}));
      await page.goto(`${base}/qr-test`);
      await page.evaluate(async()=>{
        const {SpaceshipPhoto}=await import('/spaceship-photo.js');
        window.panel=new SpaceshipPhoto({enabled:true,mode:'cloud',network:'public',room:'atl-downtown',phoneURL:'https://face-avatar.vercel.app/photo.html?station=atl-downtown'});
        panel.setView('ship');
      });
    }else{
      await page.goto(`${base}/cockpit.html?view=ship&character=orbit&qa`);
      assert.equal(await page.evaluate(()=>localStorage.getItem('alien-photo-owner')),null,'No operator pairing required');
      console.log('Live page loaded; checking QR without waiting for background character downloads.');
    }
    const qr=page.locator('#spaceship-photo a');await qr.waitFor({state:'visible',timeout:30000});
    // Scene loading is a separate, optional check: the QR must be usable first.
    if(live&&process.env.VERIFY_SCENE==='1')await page.locator('#loading').waitFor({state:'hidden',timeout:90000});
    const phoneURL=await qr.getAttribute('href');
    if(live){
      assert.match(new URL(phoneURL).searchParams.get('station'),/^test-[a-f0-9]{32}$/);
      assert.equal(new URL(phoneURL).origin,new URL(base).origin);
      const other=await browser.newPage();
      await other.addInitScript(()=>{navigator.mediaDevices.getUserMedia=async()=>{throw new DOMException('Camera disabled','NotAllowedError');};});
      await other.goto(`${base}/cockpit.html?view=ship&character=orbit&qa`);
      const otherQR=other.locator('#spaceship-photo a');await otherQR.waitFor({state:'visible',timeout:30000});
      assert.notEqual(await otherQR.getAttribute('href'),phoneURL,'Different browsers get different cameras');
      await other.close();
      await page.reload();await qr.waitFor({state:'visible',timeout:30000});
      assert.equal(await qr.getAttribute('href'),phoneURL,'Reload keeps the same QR');
    }else assert.equal(phoneURL,'https://face-avatar.vercel.app/photo.html?station=atl-downtown');
    assert.equal(await qr.locator('img').evaluate(img=>img.naturalWidth>100),true);
    if(!live){
      for(const state of [{online:false},{online:true,ready:true},{online:true,busy:true}]){
        await page.evaluate(state=>panel.update(state),state);assert.equal(await qr.isVisible(),true);
      }
      await page.evaluate(()=>panel.update({online:false}));
      assert.equal(await page.locator('#spaceship-photo p').textContent(),'Photo station offline');
      for(const view of ['tv','vinyl']){await page.evaluate(view=>panel.setView(view),view);assert.equal(await qr.isVisible(),false);}
      await page.evaluate(()=>panel.setView('ship'));
      // Retain the local LAN policy, where an unavailable address is not useful.
      await page.evaluate(()=>{panel.config.network=undefined;panel.update({online:false});});
      assert.equal(await qr.isVisible(),false);
      await page.evaluate(()=>{panel.config.network='public';panel.update({online:false});});
    }else{
      for(const view of ['tv','vinyl']){await page.locator(`#view-${view}`).click();assert.equal(await qr.isVisible(),false);}
      await page.locator('#view-ship').click();await qr.waitFor({state:'visible'});
    }
    for(const width of [1440,768,390]){
      await page.setViewportSize({width,height:900});await page.waitForTimeout(300);
      const box=await page.locator('#spaceship-photo').boundingBox();
      assert.ok(box.x>=0&&box.y>=0&&box.x+box.width<=width&&box.y+box.height<=900);
      await page.screenshot({path:path.join(output,`${live?'live':'component'}-${width}.png`)});
    }
    if(live){
      const phone=await browser.newPage({viewport:{width:390,height:844}});
      await phone.goto(phoneURL);
      await phone.waitForFunction(()=>document.querySelector('#availability').textContent!=='Connecting to the window...');
      const availability=await phone.locator('#availability').textContent();
      assert.equal(await phone.locator('#take').isDisabled(),true,'Denied camera cannot capture');
      await phone.screenshot({path:path.join(output,'live-phone.png')});
      console.log({phoneAvailability:availability});
    }
    assert.deepEqual(errors,[]);
    console.log({live,publicQRVisible:true,operatorPairingRequired:false,phoneURL,viewports:[1440,768,390],errors});
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
