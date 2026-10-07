const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');

(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',args:['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream']});
 const out='.context/qa/vinyl-preview';fs.mkdirSync(out,{recursive:true});
 try{
  const page=await browser.newPage(),errors=[],models=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',request=>{if(request.url().endsWith('.glb'))models.push(request.url());});
  await page.addInitScript(()=>{
    const getUserMedia=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    window.cameraRequests=0;
    navigator.mediaDevices.getUserMedia=(...args)=>{window.cameraRequests++;return getUserMedia(...args);};
  });
  await page.route('**/fleet.js',async route=>{
   const response=await route.fetch();
   await route.fulfill({response,body:await response.text()+`
window.vinylTest={select:selectCharacter,check:()=>{
 const gl=renderer.getContext(),w=gl.drawingBufferWidth,h=gl.drawingBufferHeight;
 const capture=()=>{vinyl.render(renderer,scene,camera,displayView==='ship');const p=new Uint8Array(w*h*4);gl.readPixels(0,0,w,h,gl.RGBA,gl.UNSIGNED_BYTE,p);return p;};
 const live=capture();current.gltf.scene.visible=false;const empty=capture();current.gltf.scene.visible=true;
 const canvas=document.createElement('canvas');canvas.width=1908;canvas.height=1312;
 const ctx=canvas.getContext('2d');ctx.drawImage(vinyl.material.uniforms.artwork.value.image,0,0);
 const original=ctx.getImageData(0,0,1908,1312).data,closeUp=displayView==='ship',scale=closeUp?h/664:Math.min(w/1908,h/1312),left=closeUp?w/2-590*scale:(w-1908*scale)/2,top=closeUp?h/2-792*scale:(h-1312*scale)/2;
 let changed=0,outside=0;
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
  const i=(y*w+x)*4;
  if(Math.max(Math.abs(live[i]-empty[i]),Math.abs(live[i+1]-empty[i+1]),Math.abs(live[i+2]-empty[i+2]))<8)continue;
  changed++;
  const ix=Math.floor((x-left)/scale),iy=Math.floor((h-1-y-top)/scale),j=(iy*1908+ix)*4;
  if(ix<310||ix>880||iy<540||iy>805||Math.min(original[j],original[j+1],original[j+2])<180)outside++;
 }
 target.jawOpen=.85;driveFace(1,performance.now());const expression=capture();let animated=0;
 for(let i=0;i<live.length;i+=4)if(Math.abs(live[i]-expression[i])+Math.abs(live[i+1]-expression[i+1])+Math.abs(live[i+2]-expression[i+2])>24)animated++;
 target.jawOpen=0;driveFace(1,performance.now());capture();
 return {changed,outside,animated};
}};`});
  });
  await page.goto(`${process.env.INSTALLATION_URL||'http://localhost:8014'}/cockpit.html?qa`);
  await page.waitForFunction(()=>window.fleetQA?.loadedCharacters===7&&fleetQA.cameraActive,null,{timeout:120000});
  const requests=models.length,cameraRequests=await page.evaluate(()=>window.cameraRequests);
  assert.equal(await page.getByRole('tab',{name:'TV close-up'}).getAttribute('aria-selected'),'true');
  await page.getByRole('tab',{name:'Full vinyl',exact:true}).click();
  await page.waitForFunction(()=>fleetQA.vinylReady);
  const report=[];
  for(const viewport of [{width:1920,height:1080},{width:390,height:844}]){
   await page.setViewportSize(viewport);await page.waitForTimeout(300);
   for(const view of ['vinyl','ship']){
    await page.locator(`[data-view="${view}"]`).click();
    assert.equal(await page.locator('[role=tab][aria-selected=true]').count(),1);
    assert.equal(new URL(page.url()).searchParams.get('view'),view);
    const bounds=await page.locator('#scene-tabs').boundingBox();
    assert(bounds.x>=0&&bounds.x+bounds.width<=viewport.width,'tabs fit viewport');
    for(const index of [0,2,6]){
    await page.evaluate(i=>vinylTest.select(i),index);await page.waitForTimeout(300);
    const pixels=await page.evaluate(()=>vinylTest.check());
    assert(pixels.changed>viewport.width*viewport.height*.001,'alien must render in dome');
    assert.equal(pixels.outside,0,'alien must never cover printed hull or background');
    assert(pixels.animated>2,'facial movement must reach the visible dome');
    const character=await page.evaluate(()=>fleetQA.character);
    await page.screenshot({path:out+'/'+view+'-'+character+'-'+viewport.width+'.png'});
    if(view==='ship')assert(pixels.changed>report.find(r=>r.character===character&&r.width===viewport.width&&r.view==='vinyl').changed*2,'spaceship tab visibly enlarges the alien');
    report.push({view,character,...viewport,...pixels});
    }
   }
  }
  const character=await page.evaluate(()=>fleetQA.character);
  await page.locator('[role=tab][aria-selected=true]').focus();
  for(const [key,view] of [['Home','tv'],['ArrowRight','ship'],['End','vinyl']]){
    await page.keyboard.press(key);
    assert.equal(await page.evaluate(()=>fleetQA.displayView),view);
    assert.equal(await page.evaluate(()=>fleetQA.character),character,'tab arrows must not select another alien');
    assert.equal(await page.locator('[role=tab]:focus').getAttribute('data-view'),view);
  }
  assert.equal(models.length,requests,'tabs reuse loaded characters');
  assert.equal(await page.evaluate(()=>window.cameraRequests),cameraRequests,'tabs retain camera stream');
  await page.reload();
  await page.waitForFunction(()=>window.fleetQA?.vinylReady,null,{timeout:120000});
  assert.equal(await page.evaluate(()=>fleetQA.displayView),'vinyl','selected tab survives reload');
  assert.deepEqual(errors,[]);fs.writeFileSync(out+'/report.json',JSON.stringify(report,null,2));
  console.log('PASS live view tabs, enlarged spaceship, keyboard navigation, retained camera/character, reload persistence, dome-only animated pixels, desktop/mobile screenshots');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
