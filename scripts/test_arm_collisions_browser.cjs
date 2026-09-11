const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const ids=(process.env.RIG_IDS||'orbit,pearl,juno,fuzz,clementine,coral,sprout,atl').split(',');
const out='.context/qa/'+(process.env.ARM_PASS||'arm-collisions');fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[],requests=[],report=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>requests.push(r.url()));
  if(process.env.RIG_STAGE)await page.route('**/assets/3dai/manifest.json',async route=>{
   const response=await route.fetch(),manifest=await response.json();
   for(const c of manifest.characters)if(ids.includes(c.id))c.url='assets/3dai/'+process.env.RIG_STAGE+'/'+c.id+'.glb';
   await route.fulfill({response,json:manifest});
  });
  await page.addInitScript(()=>{navigator.mediaDevices.getUserMedia=async()=>{throw new DOMException('Test camera off','NotAllowedError');};});
  await page.route('**/fleet.js',async route=>{
   const response=await route.fetch(),body=await response.text();
   await route.fulfill({response,body:body.replace('current?.arms.update(arms,dt);','current?.arms.update(window.testArms||arms,dt);')+`
window.surfaceStrain=()=>{
 const ratios=[],worst=[];
 for(const m of current.meshes.filter(m=>m.morphTargetDictionary.correctiveSeated!==undefined)){
  m.skeleton.update();const a=m.geometry.attributes;
  const rest=Array.from({length:a.position.count},(_,i)=>new THREE.Vector3().fromBufferAttribute(a.position,i));
  const moved=rest.map((_,i)=>m.getVertexPosition(i,new THREE.Vector3()));
  const limb=rest.map((_,i)=>{let weight=0;for(let j=0;j<4;j++)if(/^(UpperArm|Forearm|Hand)/.test(m.skeleton.bones[a.skinIndex.getComponent(i,j)].name))weight+=a.skinWeight.getComponent(i,j);return weight>.05;});
  const ids=m.geometry.index.array;
  for(let i=0;i<ids.length;i+=3)for(let j=0;j<3;j++){
   const x=ids[i+j],y=ids[i+(j+1)%3];if(limb[x]||limb[y]){
    const ratio=moved[x].distanceTo(moved[y])/Math.max(.006,rest[x].distanceTo(rest[y]));ratios.push(ratio);
    if(ratio>5)worst.push({ratio,points:[x,y].map(i=>({rest:rest[i].toArray(),moved:moved[i].toArray(),weights:Array.from({length:4},(_,j)=>[m.skeleton.bones[a.skinIndex.getComponent(i,j)].name,a.skinWeight.getComponent(i,j)])}))});
   }
  }
 }
 ratios.sort((a,b)=>a-b);worst.sort((a,b)=>b.ratio-a.ratio);return {max:ratios.at(-1),p99:ratios[Math.floor(ratios.length*.99)],over2:ratios.filter(r=>r>2).length,worst:worst.slice(0,4)};
};
window.collisionState=()=>({surface:${process.env.MEASURE_SURFACE?'surfaceStrain()':'null'},hulls:current.collisions.colliders.length,penetration:current.collisions.penetration,adjustments:current.collisions.adjustments,milliseconds:current.collisions.durationMs,
 arms:Object.fromEntries(Object.entries(current.arms.chains).map(([side,c])=>{
  const p=c.map(({bone})=>bone.getWorldPosition(new THREE.Vector3()));
  const upper=p[1].clone().sub(p[0]),lower=p[2].clone().sub(p[1]);
  return [side,{lengths:[upper.length(),lower.length()],elbow:upper.angleTo(lower)*180/Math.PI}];
 }))});`});
  });
  await page.goto('http://localhost:8014/cockpit.html?qa&assets=3dai');
  await page.waitForFunction(()=>window.fleetQA?.character);
  for(const id of ids){
   await page.evaluate(id=>{window.testArms={};document.querySelectorAll('.character')[['orbit','pearl','juno','fuzz','clementine','coral','sprout','atl'].indexOf(id)].click();},id);
   await page.waitForFunction(id=>fleetQA.character===id,id);await page.waitForTimeout(500);
   const rest=await page.evaluate(()=>collisionState()),states=[];
   assert.equal(rest.hulls,2,id+' body envelopes');
   for(const [name,upper,lower] of [
    ['cross-chest',[-1,0,0],[-1,0,0]],['through-head',[0,1,0],[-.6,.8,0]],
    ['reach-forward',[.1,0,1],[0,0,1]],['backward',[0,0,-1],[0,0,-1]],
    ['overfold',[1,0,0],[-1,0,0]],['down',[.1,-1,0],[0,-1,0]],
   ]){
    await page.evaluate(({upper,lower})=>{window.testArms={L:{upper,lower,hand:lower},R:{upper:[-upper[0],upper[1],upper[2]],lower:[-lower[0],lower[1],lower[2]],hand:[-lower[0],lower[1],lower[2]]}};},{upper,lower});
    await page.waitForTimeout(600);
    const state=await page.evaluate(()=>collisionState());states.push({name,...state});
    assert(Number.isFinite(state.penetration)&&state.penetration<.006,id+' unresolved body collision '+JSON.stringify(state));
    for(const side of ['L','R']){
     assert(state.arms[side].elbow<=145.1,id+' elbow limit '+JSON.stringify(state));
     assert(state.arms[side].lengths.every((v,i)=>Math.abs(v-rest.arms[side].lengths[i])<.0001),id+' bone stretched '+JSON.stringify({name,side,rest:rest.arms[side],current:state.arms[side]}));
    }
    await page.screenshot({path:out+'/'+id+'-'+name+'.png'});
   }
   await page.evaluate(()=>window.testArms={});await page.waitForTimeout(700);
   const idle=await page.evaluate(()=>fleetQA.bones.HandR);
   await page.evaluate(()=>window.testArms={L:{upper:[1,0,0],lower:[0,1,0],hand:[0,1,0]}});await page.waitForTimeout(400);
   const after=await page.evaluate(()=>fleetQA.bones.HandR);
   assert(after.every((v,i)=>Math.abs(v-idle[i])<.003),id+' idle arm moved with opposite arm');
   report.push({id,rest,states});console.log(id,JSON.stringify(states.map(s=>[s.name,s.penetration,s.adjustments])));
  }
  await page.setViewportSize({width:1080,height:1920});await page.screenshot({path:out+'/portrait.png'});
  assert(!requests.some(url=>/silver-vehicle\.glb|silver-coupe\.glb/.test(url)),'vehicle still fetched');
  assert.deepEqual(errors,[]);
  fs.writeFileSync(out+'/report.json',JSON.stringify(report,null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
