const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const out='.context/qa/mouth-combinations/'+(process.env.MOUTH_PASS||'before');fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 try{
  const page=await browser.newPage({viewport:{width:1000,height:1000}}),errors=[],report=[];
  page.on('pageerror',e=>errors.push(e.message));
  if(process.env.RIG_STAGE)await page.route('**/assets/3dai/manifest.json',async route=>{
   const response=await route.fetch(),manifest=await response.json();
   for(const c of manifest.characters)if((process.env.RIG_IDS||'').split(',').includes(c.id))c.url='assets/3dai/'+process.env.RIG_STAGE+'/'+c.id+'.glb';
   await route.fulfill({response,json:manifest});
  });
  await page.addInitScript(()=>{navigator.mediaDevices.getUserMedia=async()=>{throw new DOMException('QA camera off','NotAllowedError');};});
  await page.route('**/fleet.js',async route=>{
   const response=await route.fetch();await route.fulfill({response,body:await response.text()+`
window.setMouth=values=>{stopCamera();resetExpression();Object.assign(target,values);};
window.mouthView=()=>{
 current.gltf.scene.traverse(o=>{if(o.isMesh&&/tongue/i.test(o.material?.name)){
  o.skeleton.update();const p=o.localToWorld(o.getVertexPosition(0,new THREE.Vector3()));
  controls.target.copy(p).add(new THREE.Vector3(0,.08,0));camera.position.copy(controls.target).add(new THREE.Vector3(.08,.03,2.7));controls.update();
 }});
};
window.captureMouth=()=>{
 const meshes=current.meshes.filter(m=>m.morphTargetDictionary?.correctiveSeated!==undefined);
 return meshes.map(m=>{m.skeleton.update();return {points:Array.from({length:m.geometry.attributes.position.count},(_,i)=>m.getVertexPosition(i,new THREE.Vector3()).toArray()),indices:Array.from(m.geometry.index.array)};});
};`});
  });
  await page.goto('http://localhost:8014/cockpit.html?qa&assets=3dai');await page.waitForFunction(()=>window.fleetQA?.character);
  const cases={jaw:{jawOpen:1},smile:{jawOpen:.3,mouthSmileLeft:1,mouthSmileRight:1},
   talking:{jawOpen:.8,mouthLowerDownLeft:.8,mouthLowerDownRight:.8,mouthUpperUpLeft:.65,mouthUpperUpRight:.65,mouthFunnel:.65,mouthPucker:.55,mouthSmileLeft:.4,mouthSmileRight:.4},
   tongue:{tongueOut:.5,jawOpen:.25,mouthClose:.4,mouthPucker:.6,mouthFunnel:.5,mouthRollLower:.5,mouthPressLeft:.5,mouthPressRight:.5}};
  const metric=(base,pose)=>{
   let flipped=0,changed=0,stretched=0;
   const sub=(a,b)=>a.map((v,i)=>v-b[i]),cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]],len=a=>Math.hypot(...a);
   for(let m=0;m<base.length;m++)for(let i=0;i<base[m].indices.length;i+=3){
    const ids=base[m].indices.slice(i,i+3),a=ids.map(j=>base[m].points[j]),b=ids.map(j=>pose[m].points[j]);
    if(a.every((p,j)=>len(sub(p,b[j]))<.0001))continue;changed++;
    const n=cross(sub(a[1],a[0]),sub(a[2],a[0])),q=cross(sub(b[1],b[0]),sub(b[2],b[0]));
    if(n.reduce((s,v,j)=>s+v*q[j],0)<0)flipped++;
    if(a.some((p,j)=>len(sub(b[j],b[(j+1)%3]))>Math.max(.002,len(sub(p,a[(j+1)%3])))*2))stretched++;
   }
   return {flipped,changed,stretched};
  };
  for(const id of (process.env.RIG_IDS||'orbit,pearl,juno,fuzz,clementine,coral,sprout,atl').split(',')){
   await page.evaluate(id=>document.querySelectorAll('.character')[['orbit','pearl','juno','fuzz','clementine','coral','sprout','atl'].indexOf(id)].click(),id);
   await page.waitForFunction(id=>fleetQA.character===id,id);await page.evaluate(()=>setMouth({}));await page.waitForTimeout(600);
   await page.evaluate(()=>mouthView());const base=await page.evaluate(()=>captureMouth());
   await page.screenshot({path:out+'/'+id+'-neutral.png'});
   for(const [name,values] of Object.entries(cases)){
    await page.evaluate(values=>setMouth(values),values);await page.waitForTimeout(500);
    const result=metric(base,await page.evaluate(()=>captureMouth()));report.push({id,name,...result});
    await page.screenshot({path:out+'/'+id+'-'+name+'.png'});console.log(id,name,JSON.stringify(result));
   }
  }
  assert.deepEqual(errors,[]);
  if(process.env.MOUTH_PASS==='final'&&!process.env.RIG_IDS){
   const talking=report.filter(r=>r.name==='talking');
   assert(talking.reduce((s,r)=>s+r.flipped,0)<120,'combined talking fold regression');
   assert(talking.reduce((s,r)=>s+r.stretched,0)<220,'combined talking stretch regression');
  }
  fs.writeFileSync(out+'/report.json',JSON.stringify(report,null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
