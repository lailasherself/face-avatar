const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const asset=process.env.LIKENESS_ASSET||'clay';
const variant=process.env.LIKENESS_VARIANT||'body-rig';
const expected={clay:{bones:18,meshes:11,digits:0},cosmic:{bones:30,meshes:16,digits:12},summer:{bones:30,meshes:16,digits:12},glass:{bones:36,meshes:10,digits:18},kudzu:{bones:36,meshes:23,digits:18},orbit:{bones:39,meshes:19,digits:21},coral:{bones:18,meshes:16,digits:0}}[asset];
assert(expected,'Unsupported likeness fixture: '+asset);
const out=path.resolve(__dirname,'../.context/qa/'+asset+'-complete');
const origin=process.env.REVIEW_ORIGIN||'http://localhost:8014';
const html=`<!doctype html><html><head><style>body{margin:0}canvas{display:block}</style>
<script type="importmap">{"imports":{"three":"/vendor/three/three.module.js","three/addons/":"/vendor/three/addons/"}}</script></head><body>
<script type="module">
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {RoomEnvironment} from 'three/addons/RoomEnvironment.js';
import {ArmRetargeter} from '/arm-retarget.js';
import {ArmCollisions} from '/arm-collisions.js';
import {FingerRetargeter} from '/finger-retarget.js';
import {resolveMouth,oralWeight} from '/mouth-signals.js';
import {resolveEyeAperture} from '/eye-signals.js';
const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setSize(innerWidth,innerHeight);document.body.append(renderer.domElement);
const scene=new THREE.Scene();scene.background=new THREE.Color(0x303030);
const pmrem=new THREE.PMREMGenerator(renderer),room=new RoomEnvironment();scene.environment=pmrem.fromScene(room,.04).texture;room.dispose();pmrem.dispose();
renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;
scene.add(new THREE.HemisphereLight(0xffffff,0x555555,1.7));
for(const [x,y,z,p] of [[-3,6,4,2],[3,4,2,1]]){const l=new THREE.DirectionalLight(0xffffff,p);l.position.set(x,y,z);scene.add(l);}
const camera=new THREE.OrthographicCamera(-2.8,2.8,2.1,-2.1,.01,100);camera.position.set(0,1.8,8);camera.lookAt(0,1.8,0);
const gltf=await new GLTFLoader().loadAsync('/assets/likeness-trials/${asset}-${variant}.glb');scene.add(gltf.scene);
const root=gltf.scene;const meshes=[];root.traverse(o=>{if(o.isMesh)meshes.push(o);});
const arms=new ArmRetargeter(root);arms.captureNeutral();const collisions=new ArmCollisions(root,arms.chains);
const fingers=new FingerRetargeter(root);let hands={};
let body={},constrain=false;
function frame(){arms.update(body,1/60);fingers.update(hands,1/60);if(constrain)collisions.update(1/60);renderer.render(scene,camera);requestAnimationFrame(frame);}frame();
function bounds(o){o.skeleton?.update();const b=new THREE.Box3();for(let i=0;i<o.geometry.attributes.position.count;i++)b.expandByPoint(o.localToWorld(o.getVertexPosition(i,new THREE.Vector3())));return {min:b.min.toArray(),max:b.max.toArray()};}
window.review={
 morphLimits(){return meshes.flatMap(o=>Object.entries(o.morphTargetDictionary||{}).map(([name,i])=>{const p=o.geometry.morphAttributes.position[i];let max=0;for(let j=0;j<p.count;j++)max=Math.max(max,Math.hypot(p.getX(j),p.getY(j),p.getZ(j)));return {mesh:o.name,name,max};}));},
 resize(){const aspect=innerWidth/innerHeight,height=Math.max(4.2,2.7/aspect);camera.left=-height*aspect/2;camera.right=height*aspect/2;camera.top=height/2;camera.bottom=-height/2;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);},
 inventory(){return {meshes:meshes.length,bones:meshes[0].skeleton.bones.length,morphs:[...new Set(meshes.flatMap(o=>Object.keys(o.morphTargetDictionary||{})))],textures:meshes.filter(o=>o.material.map).map(o=>({name:o.name,width:o.material.map.image.width,height:o.material.map.image.height,normal:o.material.normalMap?.image.width})),colliders:collisions.colliders.length};},
 pose(values={}){const v=resolveMouth({...values});resolveEyeAperture(v);for(const o of meshes)if(o.morphTargetDictionary)for(const [name,i] of Object.entries(o.morphTargetDictionary))o.morphTargetInfluences[i]=oralWeight(name,v[name]||0,o.material.name);root.updateMatrixWorld(true);},
 tongue(){return bounds(meshes.find(o=>o.name.includes('LongTongue')||o.name.includes('Long_Tongue')||o.name.includes('Long Tongue')));},
 armPose(values={},avoid=false){body=values;constrain=avoid;},
 handPose(values={}){hands=values;},
 handState(){return fingers.joints.map(j=>({name:j.bone.name,side:j.side,digit:j.digit,limit:j.radians,angle:j.rest.clone().normalize().angleTo(j.bone.quaternion.clone().normalize())}));},
 armState(){return {penetration:collisions.penetration,adjustments:collisions.adjustments,angles:Object.fromEntries(Object.entries(arms.chains).map(([side,chain])=>[side,chain.map(j=>j.neutral.clone().normalize().angleTo(j.bone.getWorldQuaternion(new THREE.Quaternion()).normalize()))]))};},
 pixels(){renderer.render(scene,camera);const gl=renderer.getContext(),a=new Uint8Array(innerWidth*innerHeight*4);gl.readPixels(0,0,innerWidth,innerHeight,gl.RGBA,gl.UNSIGNED_BYTE,a);let changed=0,hash=2166136261;for(let i=0;i<a.length;i+=4){if(Math.abs(a[i]-a[0])+Math.abs(a[i+1]-a[1])+Math.abs(a[i+2]-a[2])>40)changed++;hash=Math.imul(hash^a[i],16777619);}return {changed,hash};}
};
</script></body></html>`;

module.exports={html};

if(require.main===module)(async()=>{
 fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 const report={errors:[],poses:[],arms:[]};
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1080}});
  page.on('pageerror',e=>report.errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error'&&/shader|WebGL|GL_INVALID/i.test(m.text()))report.errors.push(m.text());});
  await page.route('**/__clay_likeness_test',route=>route.fulfill({contentType:'text/html',body:html}));
  await page.goto(origin+'/__clay_likeness_test');await page.waitForFunction(()=>window.review,{timeout:60000});
  report.inventory=await page.evaluate(()=>review.inventory());assert.equal(report.inventory.bones,expected.bones);assert.equal(report.inventory.meshes,expected.meshes);assert.equal(report.inventory.colliders,2);
  report.morphLimits=await page.evaluate(()=>review.morphLimits());assert(report.morphLimits.every(m=>Number.isFinite(m.max)&&m.max<1.5),'Unbounded or inherited expression target');
  for(const name of ['jawOpen','mouthSmileLeft','mouthSmileRight','eyeBlinkLeft','eyeBlinkRight','tongueOut'])assert(report.inventory.morphs.includes(name),name);
  const normalSize=['orbit','coral'].includes(asset)&&variant==='image-rig'?2048:1024;
  assert(report.inventory.textures.every(t=>t.width===2048&&t.height===2048&&t.normal===normalSize));
  const neutral=await page.evaluate(()=>review.pixels());assert(neutral.changed>50000,'Blank export');
  await page.screenshot({path:path.join(out,'runtime-neutral.png')});
  const restTongue=await page.evaluate(()=>review.tongue());
  for(const [name,values] of [['jaw',{jawOpen:1}],['smile',{jawOpen:.25,mouthSmileLeft:1,mouthSmileRight:1}],['blink',{eyeBlinkLeft:1}],['tongue',{tongueOut:1,jawOpen:.8,eyeBlinkLeft:1}]]){
   await page.evaluate(v=>review.pose(v),values);await page.waitForTimeout(100);
   const pixels=await page.evaluate(()=>review.pixels());assert.notEqual(pixels.hash,neutral.hash,name+' did not render');report.poses.push({name,pixels});
   await page.screenshot({path:path.join(out,'runtime-'+name+'.png')});
  }
  const extended=await page.evaluate(()=>review.tongue());assert(extended.max[2]-restTongue.max[2]>.8,'Tongue does not extend');
  await page.evaluate(()=>review.pose());await page.waitForTimeout(100);
  const retracted=await page.evaluate(()=>review.tongue());assert(Math.abs(retracted.max[2]-restTongue.max[2])<1e-6,'Tongue did not retract');
  report.tongue={restTongue,extended,retracted};
  await page.evaluate(()=>review.armPose({L:{upper:[1,.3,.2],lower:[.5,.2,.8]}}));await page.waitForTimeout(700);
  report.independent=await page.evaluate(()=>review.armState());assert(report.independent.angles.L[0]>.1);assert(report.independent.angles.R.every(a=>a<.002),'Other arm moved');
  for(const upper of [[1,0,0],[.3,1,.3],[-.4,.2,.8],[0,-1,0]]){
   await page.evaluate(upper=>review.armPose({L:{upper,lower:[-.4,.3,.8]}},true),upper);await page.waitForTimeout(750);
   const state=await page.evaluate(()=>review.armState());assert(Object.values(state.angles).flat().every(Number.isFinite));
   assert(state.angles.R.every(a=>a<.002),'Collision solver moved the resting opposite arm');
   assert(state.penetration<.01,'Moving arm penetrated the collision envelopes');report.arms.push({upper,...state});
  }
  await page.screenshot({path:path.join(out,'runtime-arm-clearance.png')});
  await page.evaluate(()=>review.armPose());await page.waitForTimeout(900);assert(Object.values((await page.evaluate(()=>review.armState())).angles).flat().every(a=>a<.002));
  if(expected.digits){
   const joints=await page.evaluate(()=>review.handState());assert.equal(joints.length,expected.digits);assert(joints.every(j=>j.limit>=.4&&j.limit<=.55));
   await page.evaluate(()=>review.handPose({L:{Thumb:[1,1,1],Index:[1,1,1],Middle:[1,1,1],Ring:[1,1,1]}}));await page.waitForTimeout(700);
   report.fingers=await page.evaluate(()=>review.handState());assert(report.fingers.filter(j=>j.side==='L').every(j=>j.angle>.35));assert(report.fingers.filter(j=>j.side==='R').every(j=>j.angle<.001));
   await page.screenshot({path:path.join(out,'runtime-hand-curl.png')});
   await page.evaluate(()=>review.handPose({L:{Thumb:[1,1,1],Index:[0,0,0]}}));await page.waitForTimeout(700);
   const pointing=await page.evaluate(()=>review.handState());assert(pointing.filter(j=>j.side==='L'&&j.digit==='Index').every(j=>j.angle<.001));
   await page.screenshot({path:path.join(out,'runtime-hand-point.png')});
   await page.evaluate(()=>review.handPose());await page.waitForTimeout(900);assert((await page.evaluate(()=>review.handState())).every(j=>j.angle<.001));
  }
  report.viewports=[];
  for(const viewport of [{width:1920,height:1080},{width:1080,height:1920},{width:390,height:844}]){
   await page.setViewportSize(viewport);await page.evaluate(()=>review.resize());await page.waitForTimeout(150);
   const pixels=await page.evaluate(()=>review.pixels());assert(pixels.changed>viewport.width*viewport.height*.07,'Blank or incorrectly framed resized canvas');report.viewports.push({...viewport,pixels});
   await page.screenshot({path:path.join(out,'runtime-'+viewport.width+'x'+viewport.height+'.png')});
  }
  assert.deepEqual(report.errors,[]);
  fs.writeFileSync(path.join(out,'runtime-validation.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify({status:'PASS',inventory:report.inventory,tongueExtension:extended.max[2]-restTongue.max[2],collisionPenetrations:report.arms.map(a=>a.penetration)},null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
