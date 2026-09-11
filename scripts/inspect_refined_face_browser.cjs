const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 try{
  const page=await browser.newPage({viewport:{width:1200,height:1000}});
  page.on('pageerror',console.error);
  await page.route('**/fleet.js',async route=>{
   const response=await route.fetch();const source=await response.text();
   await route.fulfill({response,body:source+`\nwindow.inspectFace=part=>{
    vehicle.visible=false;
    const meshes=[];current.gltf.scene.traverse(o=>{if(o.isMesh){
     let owner=o;while(owner&&!owner.name.toLowerCase().includes(part))owner=owner.parent;
     o.visible=part.startsWith('all')||!!owner;o.receiveShadow=!part.includes('no-shadow');meshes.push([o.name,o.parent?.name]);
    }});
    camera.position.set(.7,2.2,3.7);controls.target.set(0,1.95,.3);camera.lookAt(controls.target);
    return meshes;
   };`});
  });
  await page.goto('http://localhost:8014/cockpit.html?qa&assets=3dai&rigs=refined&character=pearl',{waitUntil:'networkidle'});
  await page.waitForFunction(()=>window.fleetQA?.character==='pearl');
  for(const part of ['all','sourcebody','eyesandmouth','articulated','teeth','all-no-shadow']){
   console.log(part,await page.evaluate(part=>inspectFace(part),part));await page.waitForTimeout(350);
   await page.screenshot({path:'.context/qa/refinement/pearl-isolate-'+part+'.png'});
  }
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
