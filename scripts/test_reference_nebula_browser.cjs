const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const out=path.resolve(__dirname,'../.context/qa/reference-characters');
const origin=process.env.REVIEW_ORIGIN||'http://localhost:8014';
const character=process.argv[2]||'nebula';
assert(/^[a-z]+$/.test(character));
const html=`<!doctype html><html><head><style>html,body{margin:0;overflow:hidden}canvas{display:block}</style>
<script type="importmap">{"imports":{"three":"/vendor/three/three.module.js","three/addons/":"/vendor/three/addons/"}}</script></head><body>
<script type="module">
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {FingerRetargeter} from '/finger-retarget.js';
import {ArmRetargeter} from '/arm-retarget.js';
import {ArmCollisions} from '/arm-collisions.js';
const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});
renderer.setPixelRatio(1);document.body.append(renderer.domElement);
const scene=new THREE.Scene();scene.background=new THREE.Color(0x242424);
scene.add(new THREE.HemisphereLight(0xffffff,0x444455,2));
for(const [x,y,z,power] of [[3,5,4,2],[-3,3,2,1]]){const light=new THREE.DirectionalLight(0xffffff,power);light.position.set(x,y,z);scene.add(light);}
const camera=new THREE.OrthographicCamera();camera.near=.01;camera.far=100;
const gltf=await new GLTFLoader().loadAsync('/assets/reference-characters/${character}-review.glb');scene.add(gltf.scene);
const tracker=new FingerRetargeter(gltf.scene);let hands={};
const arms=new ArmRetargeter(gltf.scene);arms.captureNeutral();
const collisions=new ArmCollisions(gltf.scene,arms.chains);
let body={},avoid=false;
function resize(){const aspect=innerWidth/innerHeight,height=Math.max(3.8,2.1/aspect);renderer.setSize(innerWidth,innerHeight);camera.left=-height*aspect/2;camera.right=height*aspect/2;camera.top=height/2;camera.bottom=-height/2;camera.updateProjectionMatrix();camera.position.set(0,1.6,7);camera.lookAt(0,1.6,0);}
resize();addEventListener('resize',resize);
function frame(){arms.update(body,1/60);if(avoid)collisions.update(1/60);tracker.update(hands,1/60);renderer.render(scene,camera);requestAnimationFrame(frame);}frame();
window.review={
 joints:tracker.joints.map(j=>({name:j.bone.name,limit:j.radians})),
 pose(values={},curls={}){hands=curls;gltf.scene.traverse(mesh=>{if(mesh.morphTargetDictionary)for(const [name,index] of Object.entries(mesh.morphTargetDictionary))mesh.morphTargetInfluences[index]=values[name]||0;});},
 armPose(values={},constrain=false){body=values;avoid=constrain;},
 armState(){return {colliders:collisions.colliders.length,penetration:collisions.penetration,adjustments:collisions.adjustments,chains:Object.fromEntries(Object.entries(arms.chains).map(([side,chain])=>[side,chain.map(j=>({name:j.bone.name,angle:j.neutral.clone().normalize().angleTo(j.bone.getWorldQuaternion(new THREE.Quaternion()).normalize()),position:j.bone.getWorldPosition(new THREE.Vector3()).toArray(),quaternion:j.bone.quaternion.toArray()}))]))};},
 pixels(){renderer.render(scene,camera);const gl=renderer.getContext(),data=new Uint8Array(gl.drawingBufferWidth*gl.drawingBufferHeight*4);gl.readPixels(0,0,gl.drawingBufferWidth,gl.drawingBufferHeight,gl.RGBA,gl.UNSIGNED_BYTE,data);let changed=0,hash=2166136261;for(let i=0;i<data.length;i+=4){if(Math.abs(data[i]-data[0])+Math.abs(data[i+1]-data[1])+Math.abs(data[i+2]-data[2])>40)changed++;hash=Math.imul(hash^data[i],16777619);}return {changed,hash};},
 angles(){return tracker.joints.map(j=>({name:j.bone.name,angle:j.rest.clone().normalize().angleTo(j.bone.quaternion.clone().normalize()),limit:j.radians}));}
};
</script></body></html>`;

(async()=>{
 fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 const report=[];
 try{
  const page=await browser.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error'&&/shader|WebGL|GL_INVALID/i.test(m.text()))errors.push(m.text());});
  await page.route('**/__nebula_review_test',route=>route.fulfill({contentType:'text/html',body:html}));
  for(const viewport of [{width:1280,height:900},{width:390,height:844}]){
   await page.setViewportSize(viewport);await page.goto(origin+'/__nebula_review_test');
   await page.waitForFunction(()=>window.review,{timeout:60000});
   const joints=await page.evaluate(()=>review.joints);if(character==='nebula')assert.equal(joints.length,18);assert(joints.every(j=>j.limit>0&&j.limit<=Math.PI));
   await page.waitForTimeout(500);const neutral=await page.evaluate(()=>review.pixels());assert(neutral.changed>5000,'Blank character');
   await page.screenshot({path:path.join(out,character+'-browser-'+viewport.width+'-neutral.png')});
   await page.evaluate(()=>review.pose({jawOpen:.7,tongueOut:1,eyeBlinkLeft:1},{L:{Thumb:[1,1,1],Index:[1,1,1],Middle:[1,1,1],Ring:[1,1,1],Pinky:[1,1,1]}}));
   await page.waitForTimeout(1100);const posed=await page.evaluate(()=>review.pixels());assert(posed.changed>5000);assert.notEqual(posed.hash,neutral.hash,'Pose did not render');
   const angles=await page.evaluate(()=>review.angles());
   assert(angles.filter(j=>j.name.endsWith('L')).every(j=>Math.abs(j.angle-j.limit)<.002),'Exported limits are not applied');
   assert(angles.filter(j=>j.name.endsWith('R')).every(j=>j.angle<1e-6),'Opposite hand moved');
   await page.screenshot({path:path.join(out,character+'-browser-'+viewport.width+'-posed.png')});
   await page.evaluate(()=>review.pose());await page.waitForTimeout(1100);
   assert((await page.evaluate(()=>review.angles())).every(j=>j.angle<.002),'Tracking loss did not relax fingers');
   await page.evaluate(()=>review.armPose({L:{upper:[1,.5,.2],lower:[.7,.7,.3]}}));await page.waitForTimeout(900);
   const independent=await page.evaluate(()=>review.armState());
   assert(independent.chains.L[0].angle>.1,'Left arm did not move');
   assert(independent.chains.R.every(j=>j.angle<.002),'Opposite arm moved');
   assert.equal(independent.colliders,2,'Missing head/torso collision envelopes');
   const poses=[];
   for(const upper of [[1,0,0],[.2,1,.2],[-.6,.4,.6],[0,-1,0]]){
    await page.evaluate(upper=>review.armPose({L:{upper,lower:[-.5,.3,.7]}},true),upper);await page.waitForTimeout(700);
    const state=await page.evaluate(()=>review.armState());
    assert(Object.values(state.chains).flat().every(j=>[...j.position,...j.quaternion].every(Number.isFinite)),'Nonfinite arm pose');
    assert(Number.isFinite(state.penetration));poses.push({upper,...state});
   }
   await page.screenshot({path:path.join(out,character+'-browser-'+viewport.width+'-arms.png')});
   await page.evaluate(()=>review.armPose());await page.waitForTimeout(900);
   assert(Object.values((await page.evaluate(()=>review.armState())).chains).flat().every(j=>j.angle<.002),'Arm tracking loss did not return to neutral');
   report.push({viewport,joints:joints.length,neutral,posed,independent,poses});
  }
  assert.deepEqual(errors,[]);fs.writeFileSync(path.join(out,character+'-browser-validation.json'),JSON.stringify({report,errors},null,2));
  console.log('PASS '+character+' desktop/portrait GLB rendering, curl limits, independent arms, collision envelopes and release');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
