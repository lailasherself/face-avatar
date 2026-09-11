const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const roster=JSON.parse(fs.readFileSync('assets/3dai/manifest.json')).characters.map(c=>c.id);
const out='.context/qa/arm-fluidity';fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[],report=[],failures=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>{navigator.mediaDevices.getUserMedia=async()=>{throw new DOMException('Test camera off','NotAllowedError');};});
  await page.route('**/fleet.js',async route=>{
   const response=await route.fetch(),body=await response.text();
   await route.fulfill({response,body:body+`
window.measureFluidity=filtered=>{
 setPose('Standing');const signal=new ArmSignal(),frames=[];let sample={};
 for(let i=0;i<420;i++){
  const t=i/60,angle=i<180?.15:.15+1.3*Math.sin((t-3)*1.3);
  if(i%2===0){
   const noise=.035*Math.sin(i*1.2);
   const upper=[Math.cos(angle+noise),Math.sin(angle+noise),.18];
   const lower=[Math.cos(angle+.4+noise),Math.sin(angle+.4+noise),.3];
   const raw={L:{upper,lower,hand:lower}};sample=filtered?signal.update(raw,t*1000):raw;
  }
  current.arms.update(sample,1/60);current.collisions.update(1/60);
  const p=current.arms.chains.L.map(({bone})=>bone.getWorldPosition(new THREE.Vector3()).toArray());
  frames.push({p,q:current.arms.chains.L.map(({bone})=>bone.getWorldQuaternion(new THREE.Quaternion()).toArray()),penetration:current.collisions.penetration});
 }
 return frames;
};`});
  });
  await page.goto('http://localhost:8014/cockpit.html?qa&assets=3dai');
  await page.waitForFunction(()=>window.fleetQA?.character);
  const metric=frames=>{
   let jitter=0,peakAngle=0,penetration=0;
   for(let i=1;i<frames.length;i++){
    if(i>60&&i<180)jitter+=frames[i].p[2].reduce((s,v,j)=>s+(v-frames[i-1].p[2][j])**2,0);
    if(i>180)for(let j=0;j<3;j++){
     const dot=Math.abs(frames[i].q[j].reduce((s,v,k)=>s+v*frames[i-1].q[j][k],0));
     peakAngle=Math.max(peakAngle,2*Math.acos(Math.min(1,dot))*180/Math.PI);
    }
    penetration=Math.max(penetration,frames[i].penetration);
   }
   return {jitter:Math.sqrt(jitter/119),peakAngle,penetration};
  };
  for(const id of process.env.RIG_IDS?process.env.RIG_IDS.split(','):roster){
   assert(roster.includes(id),'Unknown active character '+id);
   await page.evaluate(index=>document.querySelectorAll('.character')[index].click(),roster.indexOf(id));
   await page.waitForFunction(id=>fleetQA.character===id,id);
   const raw=await page.evaluate(()=>measureFluidity(false)),smooth=await page.evaluate(()=>measureFluidity(true));
   fs.writeFileSync(out+'/'+id+'-frames.json',JSON.stringify({raw,smooth}));
   const before=metric(raw),after=metric(smooth);
   report.push({id,before,after});console.log(id,JSON.stringify({before,after}));
   if(!(after.jitter<before.jitter*.4))failures.push(id+' stationary hand jitter');
   if(!(after.peakAngle<5))failures.push(id+' discontinuity in continuous arm path: '+after.peakAngle);
   if(!(after.penetration<.006))failures.push(id+' collision regression');
   await page.screenshot({path:out+'/'+id+'.png'});
  }
  await page.setViewportSize({width:1080,height:1920});await page.screenshot({path:out+'/portrait.png'});
  fs.writeFileSync(out+'/report.json',JSON.stringify({report,failures,errors,syntheticInput:true,hardwareCertified:false},null,2));
  assert.deepEqual(errors,[]);assert.deepEqual(failures,[]);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
