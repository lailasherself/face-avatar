const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const ids=(process.env.RIG_IDS||'orbit,pearl,juno,fuzz,clementine,coral,sprout,atl').split(',');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 const report=[];
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',message=>{if(message.type()==='error'&&/shader|WebGL|GL_INVALID|THREE/i.test(message.text()))errors.push(message.text());});
  await page.route('**/assets/3dai/manifest.json',async route=>{
   const response=await route.fetch(),data=await response.json();
   for(const c of data.characters)if(ids.includes(c.id)){c.url=`assets/3dai/refined/${c.id}.glb`;c.bones=c.id==='pearl'?50:c.id==='fuzz'?45:42;}
   await route.fulfill({response,json:data});
  });
  await page.route('**/fleet.js',async route=>{
   const response=await route.fetch();let body=await response.text();
   body=body.replace('current?.fingers.update(fingers,dt);','if(!window.rigPoseTest)current?.fingers.update(fingers,dt);');
   body=body.replace('current?.correctives.update(bodyPose);',()=>`if(window.rigPoseTest&&current){
    const request=window.rigPoseTest;
    const clip=THREE.AnimationClip.findByName(current.gltf.animations,typeof request==='string'?request:'Seated');
    current.mixer.stopAllAction();current.mixer.clipAction(clip).play();current.mixer.update(0);
    if(typeof request==='object')for(const [region,sample] of Object.entries(request)){
     const pose=THREE.AnimationClip.findByName(current.gltf.animations,sample.clip);
     for(const track of pose.tracks){
      if(!track.name.endsWith('.quaternion'))continue;
      const name=track.name.slice(0,-11);
      if(region==='Head'?name!=='Head':!new RegExp('^(UpperArm|Forearm|Hand)'+region+'$').test(name))continue;
      const bone=current.gltf.scene.getObjectByName(name);
      bone.quaternion.slerp(new THREE.Quaternion().fromArray(track.values),sample.weight??1);
     }
    }
    current.fingers.update(window.rigFingerTest||{},.1);
   }current?.correctives.update(bodyPose);`);
   body+=`\nwindow.measureRigStrain=()=>{
    const ratios=[],p=new THREE.Vector3(),a=new THREE.Vector3(),b=new THREE.Vector3();
    current.gltf.scene.updateMatrixWorld(true);
    current.gltf.scene.traverse(mesh=>{
     if(!mesh.isSkinnedMesh||!mesh.morphTargetDictionary?.correctiveSeated)return;
     mesh.skeleton.update();
     const geometry=mesh.geometry,rest=geometry.attributes.position,index=geometry.index;
     const moved=Array.from({length:rest.count},(_,i)=>mesh.getVertexPosition(i,p).clone());
     const edges=new Set();
     for(let i=0;i<index.count;i+=3)for(const [u,v] of [[0,1],[1,2],[2,0]]){
      const ia=index.getX(i+u),ib=index.getX(i+v),key=Math.min(ia,ib)*rest.count+Math.max(ia,ib);
      if(edges.has(key))continue;edges.add(key);
      const length=a.fromBufferAttribute(rest,ia).distanceTo(b.fromBufferAttribute(rest,ib));
      ratios.push(moved[ia].distanceTo(moved[ib])/Math.max(.006,length));
     }
    });
    ratios.sort((a,b)=>a-b);
    return {max:ratios.at(-1),p99:ratios[Math.floor(ratios.length*.99)],over4:ratios.filter(r=>r>4).length};
   };`;
   await route.fulfill({response,body});
  });
  await page.goto('http://localhost:8014/cockpit.html?qa&assets=3dai',{waitUntil:'networkidle'});
  await page.waitForFunction(()=>window.fleetQA?.character==='orbit');
  // These source-clip deformation checks were baked around the seated base.
  await page.evaluate(()=>document.querySelector('[data-pose="Seated"]').click());
  const vehicle=await page.evaluate(()=>fleetQA.vehicleUUID);
  for(const id of ids){
   await page.evaluate(id=>{window.rigPoseTest='Seated';window.rigFingerTest={};document.querySelectorAll('.character')[['orbit','pearl','juno','fuzz','clementine','coral','sprout','atl'].indexOf(id)].click();},id);
   await page.waitForFunction(id=>fleetQA.character===id,id);
   await page.waitForTimeout(700);
   const initial=await page.evaluate(()=>fleetQA);
   assert.equal(Object.keys(initial.bones).filter(n=>/^(Thumb|Index|Middle|Ring)[123]/.test(n)).length,24,id);
   assert.equal(initial.vehicleUUID,vehicle);
   const strain={};
   for(const [state,pose,curls] of [
    ['open','Seated',{}],
    ['fist','ArmsForward',{Thumb:[.7,.8,.8],Index:[1,1,1],Middle:[1,1,1],Ring:[1,1,1]}],
    ['point','ArmsForward',{Thumb:[.5,.5,.5],Index:[0,0,0],Middle:[1,1,1],Ring:[1,1,1]}],
    ['overhead','ArmsUp',{}],['neck','HeadLeft',{}],
    ['mixed',{L:{clip:'ArmsUp'},R:{clip:'ArmsForward'},Head:{clip:'HeadLeft'}},{}],
    ['halfway',{L:{clip:'ArmsUp',weight:.5},R:{clip:'ArmsOut',weight:.5}},{}]
   ]){
    await page.evaluate(({pose,curls})=>{window.rigPoseTest=pose;window.rigFingerTest={L:curls,R:curls};},{pose,curls});
    await page.waitForTimeout(650);
    const qa=await page.evaluate(()=>fleetQA);
    strain[state]=await page.evaluate(()=>measureRigStrain());
    assert(Number.isFinite(strain[state].max),id+' nonfinite deformation');
    // Regression bounds, not artistic approval; Fuzz has one 4.46x intermediate edge.
    assert(strain[state].p99<2.1,id+' widespread deformation regression');
    assert(strain[state].max<5&&strain[state].over4<=1,id+' isolated deformation regression');
    assert(Object.values(qa.bones).flat().every(Number.isFinite),id+' nonfinite bones');
    if(state==='overhead'){
     const body=qa.morphs.find(m=>m.names.includes('correctiveArmsUpL'));
     assert(body,id+' missing corrective metadata');
     assert(body.weights[body.names.indexOf('correctiveArmsUpL')]>.99,id+' left pose driver');
     assert(body.weights[body.names.indexOf('correctiveArmsUpR')]>.99,id+' right pose driver');
    }
    if(state==='point'){
     assert(Object.entries(qa.fingerCurls).filter(([n])=>n.startsWith('Index')).every(([,v])=>v<.01));
     assert(Object.entries(qa.fingerCurls).filter(([n])=>n.startsWith('Middle')).every(([,v])=>v>.99));
    }
    const colors=await page.evaluate(()=>{
     const canvas=document.createElement('canvas');canvas.width=144;canvas.height=108;
     const ctx=canvas.getContext('2d');ctx.drawImage(document.getElementById('scene'),0,0,144,108);
     return new Set(Array.from(ctx.getImageData(0,0,144,108).data).filter((_,i)=>i%4!==3)).size;
    });
    assert(colors>80,id+' blank canvas');
    await page.screenshot({path:`.context/qa/refinement/${id}-${state}-runtime.png`});
   }
   report.push({id,fingerBones:24,correctives:true,rendered:true,strain});console.log('PASS refined rig',id,JSON.stringify(strain));
  }
  await page.setViewportSize({width:1080,height:1920});
  await page.screenshot({path:'.context/qa/refinement/portrait-installation.png'});
  assert.deepEqual(errors,[]);
  fs.writeFileSync('.context/qa/refinement/browser-validation.json',JSON.stringify({controlAndRenderChecksPassed:true,visualApproval:false,report,errors},null,2));
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
