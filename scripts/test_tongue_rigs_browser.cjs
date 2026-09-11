const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 const report=[];
 try{
  const page=await browser.newPage({viewport:{width:1000,height:1000}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/fleet.js',async route=>{
   const response=await route.fetch(),body=await response.text();
   await route.fulfill({response,body:body+`
window.testTongue=(value,jaw=0)=>{
 stopCamera();resetExpression();target.tongueOut=value;target.jawOpen=jaw;
};
window.inspectTongue=()=>{
 const meshes=[];
 current.gltf.scene.traverse(o=>{if(o.isMesh&&/tongue/i.test(o.material?.name))meshes.push(o);});
 if(!meshes.length)throw new Error('No tongue mesh');
 const mesh=meshes[0];mesh.skeleton.update();
 const point=mesh.getVertexPosition(0,new THREE.Vector3());mesh.localToWorld(point);
 controls.target.copy(point).add(new THREE.Vector3(0,.12,0));
 camera.position.copy(controls.target).add(new THREE.Vector3(.15,.05,2.4));controls.update();
 return meshes.map(o=>({name:o.name,skinned:o.isSkinnedMesh,index:o.morphTargetDictionary?.tongueOut}));
};
window.showTongue=visible=>current.gltf.scene.traverse(o=>{if(o.isMesh&&/tongue/i.test(o.material?.name))o.visible=visible;});
window.tongueDimensions=()=>{
 let dimensions;
 current.gltf.scene.traverse(o=>{
  if(!o.isMesh||!/tongue/i.test(o.material?.name))return;
  const box=new THREE.Box3(),base=new THREE.Box3();o.skeleton.update();
  for(let i=0;i<o.geometry.attributes.position.count;i++){
   box.expandByPoint(o.localToWorld(o.getVertexPosition(i,new THREE.Vector3())));
   base.expandByPoint(new THREE.Vector3().fromBufferAttribute(o.geometry.attributes.position,i));
  }
  dimensions={extended:box.getSize(new THREE.Vector3()).toArray(),base:base.getSize(new THREE.Vector3()).toArray()};
 });return dimensions;
};
window.tongueFullView=()=>resetView();
`});
  });
  await page.goto('http://localhost:8014/cockpit.html?setup&qa&assets=3dai',{waitUntil:'networkidle'});
  await page.waitForFunction(()=>window.fleetQA?.character==='orbit');
  for(const id of (process.env.RIG_IDS||'orbit,pearl,juno,fuzz,clementine,coral,sprout,atl').split(',')){
   await page.evaluate(id=>document.querySelectorAll('.character')[['orbit','pearl','juno','fuzz','clementine','coral','sprout','atl'].indexOf(id)].click(),id);
   await page.waitForFunction(id=>fleetQA.character===id,id);
   await page.evaluate(()=>testTongue(0));await page.waitForTimeout(500);
   const meshes=await page.evaluate(()=>inspectTongue());assert(meshes.every(o=>o.skinned&&o.index!==undefined));
   for(const value of [0,.5,1]){
    await page.evaluate(value=>testTongue(value),value);await page.waitForTimeout(700);
    await page.screenshot({path:'.context/qa/tongue/'+id+'-'+value+'.png'});
   }
   await page.evaluate(()=>{
    const canvas=document.createElement('canvas');canvas.width=1000;canvas.height=1000;
    window.tc=canvas;const ctx=canvas.getContext('2d');ctx.drawImage(document.getElementById('scene'),0,0,1000,1000);
    window.tonguePixels=ctx.getImageData(0,0,1000,1000).data;showTongue(false);
   });await page.waitForTimeout(150);
   const difference=await page.evaluate(()=>{
    const ctx=tc.getContext('2d');ctx.drawImage(document.getElementById('scene'),0,0,1000,1000);
    return ctx.getImageData(0,0,1000,1000).data.reduce((sum,v,i)=>sum+(Math.abs(v-tonguePixels[i])>12),0);
   });
   assert(difference>1000,id+' long tongue must visibly protrude');await page.evaluate(()=>showTongue(true));
   const dimensions=await page.evaluate(()=>tongueDimensions());
   assert(dimensions.extended[2]>dimensions.base[2]*2.5,id+' tongue length must exceed 2.5x resting length');
   await page.evaluate(()=>tongueFullView());await page.waitForTimeout(250);
   await page.screenshot({path:'.context/qa/tongue/'+id+'-full-view.png'});
   report.push({id,meshes,visiblePixels:difference,dimensions});console.log('PASS tongue render',id,difference,JSON.stringify(dimensions));
  }
  assert.deepEqual(errors,[]);fs.writeFileSync('.context/qa/tongue/rig-test.json',JSON.stringify({report,errors},null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
