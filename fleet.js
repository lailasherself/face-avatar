import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/RoomEnvironment.js';
import { attachEyelidSurface, EyeSignalFilter, resolveEyeAperture } from './eyelid-surface.js';
import { AirSwipeTracker } from './air-swipe.js';
import { FleetStage } from './fleet-stage.js';
import { armDirections } from './body-motion.js';
import { ArmSignal } from './arm-signal.js';
import { ArmRetargeter } from './arm-retarget.js';
import { ArmCollisions } from './arm-collisions.js';
import { FingerRetargeter } from './finger-retarget.js';
import { trackedFingerCurls } from './finger-motion.js';
import { PoseCorrectives } from './pose-correctives.js';
import { TongueTracker } from './tongue-tracking.js';
import { FaceTracker } from './face-tracking.js';
import { resolveMouth, oralWeight } from './mouth-signals.js';
import { attachSmileBite } from './smile-rig.js';
import { ZedSource } from './zed-source.js';
import { CameraFraming, cameraConstraints } from './camera-framing.js';
import { VinylPreview } from './vinyl-preview.js';
import { captureAlien, brandAlienPhoto } from './photo-render.js';
import { AlienHeadEffect } from './alien-head-effect.js';
import { photoConfiguration, SpaceshipPhoto } from './spaceship-photo.js';

const $ = (id) => document.getElementById(id);
const clamp = (v, lo=0, hi=1) => Math.min(hi, Math.max(lo, v));
const params=new URLSearchParams(location.search);
const setupMode=params.has('setup');
// The hold/swipe progress cue is an operator aid; the public display stays clean unless ?cue is set.
const showSwipeCue=params.has('cue');
const arMode=params.has('ar')&&!setupMode;
const photoConfig=setupMode||arMode?{enabled:false}:await photoConfiguration();
const photoEnabled=!setupMode&&!arMode&&(photoConfig.enabled&&(photoConfig.mode!=='cloud'||photoConfig.operator)||params.has('photos')&&photoConfig.mode!=='cloud');
let displayView=!setupMode&&['tv','ship','vinyl'].includes(params.get('view'))?params.get('view'):!setupMode&&params.has('vinyl')?'vinyl':'tv';
const zedMode=params.get('tracking')==='zed'||photoConfig.enabled&&photoConfig.tracking==='zed';
const photoDemo=photoEnabled&&(photoConfig.enabled?photoConfig.demo:params.get('photos')==='demo');
let photoBooth=null;
let arControls=null;
const spaceshipPhoto=!setupMode&&!arMode?new SpaceshipPhoto(photoConfig):null;
const framing=new CameraFraming($('camera-preview'),$('camera-framing'),zedMode ? .6 : .8);
const eyeSignals=new EyeSignalFilter();
const scene = new THREE.Scene();
scene.background = new THREE.Color(setupMode?'#edf1ee':'#071b20');
scene.fog = setupMode?new THREE.Fog('#edf1ee',9,24):null;
const renderer = new THREE.WebGLRenderer({canvas:$('scene'),antialias:true,preserveDrawingBuffer:true});
renderer.setPixelRatio(setupMode?Math.min(devicePixelRatio,2):1);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.15;
renderer.shadowMap.enabled = setupMode;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.localClippingEnabled=!setupMode;
const waistClip=new THREE.Plane(new THREE.Vector3(0,1,0),0);
const pmrem = new THREE.PMREMGenerator(renderer);
const room = new RoomEnvironment();
const environment = pmrem.fromScene(room,.04);
scene.environment = environment.texture;
room.dispose();pmrem.dispose();
const camera = new THREE.PerspectiveCamera(36,1,.05,100);
const controls = new OrbitControls(camera,renderer.domElement);
controls.enableDamping = true;
controls.enablePan = false;
controls.enabled = setupMode;
controls.minDistance = 2.7;controls.maxDistance=setupMode?10:100;
controls.minPolarAngle = .35;controls.maxPolarAngle = Math.PI*.54;
controls.touches.ONE = null;
controls.touches.TWO = THREE.TOUCH.DOLLY_ROTATE;
scene.add(new THREE.HemisphereLight(0xffffff,0x6b8171,1.6));
const key = new THREE.DirectionalLight(0xfff7ed,3);
key.position.set(-3,6,5);key.castShadow=true;
key.shadow.mapSize.set(2048,2048);
Object.assign(key.shadow.camera,{left:-4,right:4,top:5,bottom:-4,near:.1,far:20});
key.shadow.bias=-.0003;key.shadow.normalBias=.015;key.shadow.radius=4;
scene.add(key);
const fill=new THREE.DirectionalLight(0xd9edff,1.6);fill.position.set(4,3,-3);scene.add(fill);
const floor = new THREE.Mesh(new THREE.PlaneGeometry(200,200),new THREE.MeshStandardMaterial({color:0xedf1ee,roughness:.95}));
floor.rotation.x=-Math.PI/2;floor.position.y=.02;floor.receiveShadow=true;scene.add(floor);
floor.visible=setupMode;
let vinyl=displayView!=='tv'?new VinylPreview():null;

const loader = new GLTFLoader();
const fleetStage=new FleetStage(scene,camera,{solo:!setupMode});
const headEffect=arMode||photoEnabled&&!photoDemo?new AlienHeadEffect(renderer,scene):null;
function photoPerson(){return zedMode?zedSource?.personId==null?null:`${zedSource.session}:${zedSource.personId}`:'webcam';}
renderer.domElement.addEventListener('webglcontextrestored',()=>fleetStage.layout(true));
const characterLoads=new Map();
let manifest, current, currentIndex=0, requestedIndex=0, requestId=0, bodyPose='Standing';
let stream=null, landmarker=null, cameraRequest=0, lastVideoTime=-1, lastFaceTime=0;
let cameraStarting=false,retryTimer=null,cameraWanted=!photoDemo,lastDetectionTime=0;
let handTracker=null,tongueTracker=null;
let zedSource=null;
let latestFaceLandmarks=null;
const trackedArms={};
const armSignal=new ArmSignal();
const trackedFingers={};
let demo=false, demoStart=0, calibration=null, baseline={};
const target={}, smooth={};
const targetRotation = new THREE.Quaternion();
const smoothRotation = new THREE.Quaternion();
const presets={neutral:{},happy:{mouthSmileLeft:.8,mouthSmileRight:.8,jawOpen:.18,cheekSquintLeft:.35,cheekSquintRight:.35},surprised:{jawOpen:.8,eyeWideLeft:.9,eyeWideRight:.9,browInnerUp:.7,browOuterUpLeft:.5,browOuterUpRight:.5},wink:{eyeBlinkLeft:1,mouthSmileLeft:.5,mouthSmileRight:.25}};
const descriptions={orbit:'LILAC / FOUR ANTENNAE',pearl:'PEARLESCENT / SINGLE EYE',juno:'PINK / JESTER ANTENNAE',fuzz:'LAVENDER / YELLOW SNEAKERS',clementine:'TANGERINE / LILAC BEANIE',coral:'ROSE / CORAL CROWN',sprout:'VIOLET / GREEN EYES',atl:'GREEN / ATLANTA KIT'};

function notice(message){$('notice').textContent=message;$('notice').hidden=!message;}
function status(message,live=false){$('tracking-status').textContent=message;$('tracking-status').classList.toggle('live',live);}
function resetView(){
  const ty=bodyPose==='Seated'?1.48:1.7;
  const bounds=fleetStage.entries.get(currentIndex)?.bounds;
  const size=bounds?.getSize(new THREE.Vector3())||new THREE.Vector3(3,3.7,1);
  const center=bounds?.getCenter(new THREE.Vector3())||new THREE.Vector3(0,ty,0);
  const tangent=Math.tan(THREE.MathUtils.degToRad(camera.fov/2));
  if(!setupMode){
    const spine=current?.gltf.scene.getObjectByName('Spine');
    const waist=spine?.getWorldPosition(new THREE.Vector3()).y??((bounds?.min.y||0)+size.y*.46);
    const upperHeight=(bounds?.max.y??3.7)-waist;
    const front=bounds?.max.z||0,back=bounds?.min.z||0;
    // Keep the waist below the TV's bottom edge, even on deep or narrow rigs.
    const d=Math.max((upperHeight/tangent+.84*front+1.03*back)/1.87,
      size.x/(2*tangent*camera.aspect*.9)+front);
    controls.target.set(center.x,waist+1.03*(d-back)*tangent,0);
    camera.position.set(center.x,controls.target.y,d);
    camera.zoom=1;camera.updateProjectionMatrix();controls.update();
    waistClip.constant=-waist;
    return;
  }
  const portrait=camera.aspect<1;
  const fit=Math.max(size.y/(2*tangent*(portrait?.53:.62)),(size.x+.6)/(2*tangent*camera.aspect*.88));
  const d=setupMode?8.3:fit+Math.max(0,bounds?.max.z||0);
  controls.target.set(0,setupMode?ty:center.y+fit*tangent*(portrait?.4:.28),0);
  camera.position.set(setupMode?d*.26:0,controls.target.y+(setupMode?d*.12:0),d);
  camera.zoom=1;
  camera.updateProjectionMatrix();controls.update();
  fleetStage.layout(true);
}
function resize(){
  const {width,height}=$('stage').getBoundingClientRect();
  renderer.setSize(width,height,false);camera.aspect=displayView!=='tv'?16/9:width/height;
  camera.fov=36;
  if(setupMode)camera.setViewOffset(width,height,0,height*.07,width,height);
  else camera.clearViewOffset();
  camera.updateProjectionMatrix();
  resetView();
}
new ResizeObserver(resize).observe($('stage'));
resetView();

function setDisplayView(view,updateURL=true){
  displayView=view;
  spaceshipPhoto?.setView(view);
  if(view!=='tv'&&!vinyl)vinyl=new VinylPreview();
  for(const tab of $('scene-tabs').querySelectorAll('[role=tab]')){
    const selected=tab.dataset.view===view;
    tab.setAttribute('aria-selected',String(selected));tab.tabIndex=selected?0:-1;
  }
  $('stage').setAttribute('aria-labelledby',`view-${view}`);
  if(updateURL){
    const url=new URL(location);url.searchParams.delete('vinyl');url.searchParams.set('view',view);
    history.replaceState(null,'',url);
  }
  resize();
}
$('scene-tabs').hidden=setupMode;
$('scene-tabs').addEventListener('click',event=>{
  const tab=event.target.closest('[role=tab]');if(tab)setDisplayView(tab.dataset.view);
});
$('scene-tabs').addEventListener('keydown',event=>{
  const tabs=[...$('scene-tabs').querySelectorAll('[role=tab]')],index=tabs.indexOf(document.activeElement);
  if(index<0||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
  event.preventDefault();event.stopPropagation();
  const next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(index+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;
  setDisplayView(tabs[next].dataset.view);tabs[next].focus();
});
setDisplayView(displayView,false);

function setPose(name){
  bodyPose=name;
  if(current)preparePose(current,name);
  document.querySelectorAll('[data-pose]').forEach(b=>b.classList.toggle('selected',b.dataset.pose===name));
}
function preparePose(record,name){
  const clip=THREE.AnimationClip.findByName(record.gltf.animations,name);
  record.mixer.stopAllAction();
  for(const [bone,position,rotation,scale] of record.rest){bone.position.copy(position);bone.quaternion.copy(rotation);bone.scale.copy(scale);}
  if(clip){record.mixer.clipAction(clip).play();record.mixer.update(0);}
  record.headRest=record.head?.quaternion.clone();
  record.arms=new ArmRetargeter(record.gltf.scene);
  record.collisions?.dispose();record.correctives.update(name);
  record.collisions=new ArmCollisions(record.gltf.scene,record.arms.chains);
  record.collisions.update();record.arms.captureNeutral();
  record.fingers=new FingerRetargeter(record.gltf.scene);record.pose=name;
}
function loadCharacter(index){
  if(characterLoads.has(index))return characterLoads.get(index);
  const pending=(async()=>{
    const info=manifest.characters[index],gltf=await loader.loadAsync(info.url);
    attachSmileBite(gltf.scene,info.smileBiteFit);
    const meshes=[],rest=[];let head=null;
    gltf.scene.traverse(o=>{
      if(o.isMesh){
        o.castShadow=true;o.receiveShadow=true;
        if(o.isSkinnedMesh)o.frustumCulled=false;
        if(!setupMode)for(const material of Array.isArray(o.material)?o.material:[o.material])material.clippingPlanes=[waistClip];
        if(o.morphTargetDictionary){o.morphTargetInfluences.fill(0);meshes.push(o);}
        let owner=o;while(owner&&!owner.userData.eyelidSurfaces)owner=owner.parent;
        if(owner)attachEyelidSurface(o,owner.userData.eyelidSurfaces);
      }
      if(o.isBone){rest.push([o,o.position.clone(),o.quaternion.clone(),o.scale.clone()]);if(o.name==='Head')head=o;}
    });
    const record={gltf,info,meshes,head,rest,mixer:new THREE.AnimationMixer(gltf.scene),correctives:new PoseCorrectives(gltf.scene,gltf.animations)};
    preparePose(record,'Standing');fleetStage.add(index,gltf.scene);
    return record;
  })();
  characterLoads.set(index,pending);
  pending.catch(()=>characterLoads.delete(index));
  return pending;
}
async function preloadCharacters(){
  // Load the characters a swipe can reach next before the rest of the roster, and
  // re-evaluate after every load so a browsing visitor rarely hits "Loading".
  const count=manifest.characters.length;
  for(;;){
    await new Promise(resolve=>setTimeout(resolve,150));
    const pending=[...Array(count).keys()].filter(i=>!characterLoads.has(i));
    if(!pending.length)return;
    const ahead=i=>(i-currentIndex+count)%count,rank=i=>Math.min(ahead(i)*2-1,(count-ahead(i))*2);
    const next=pending.sort((a,b)=>rank(a)-rank(b))[0];
    try{await loadCharacter(next);}catch(error){console.warn(`Background character unavailable: ${manifest.characters[next].name}`,error);}
  }
}
async function selectCharacter(index){
  if(photoBooth?.locked||arControls?.locked)return;
  if(!manifest)return;
  index=((index%manifest.characters.length)+manifest.characters.length)%manifest.characters.length;
  requestedIndex=index;
  const generation=++requestId;
  const info=manifest.characters[index];
  $('loading').hidden=false;$('loading').textContent=`Loading ${info.name}...`;
  try{
    const record=await loadCharacter(index);
    if(generation!==requestId)return;
    current=record;currentIndex=index;
    if(record.pose!==bodyPose)preparePose(record,bodyPose);
    headEffect?.prepare(record);
    fleetStage.select(index,manifest.characters.length);
    resetView();
    const meshes=record.meshes,boneCount=record.rest.length;
    $('character-name').textContent=info.name;
    $('character-detail').textContent=descriptions[info.id]||info.name;
    $('character-number').textContent=`${String(index+1).padStart(2,'0')} / ${String(manifest.characters.length).padStart(2,'0')}`;
    $('download-model').href=info.url;
    const facialChannels=new Set(meshes.flatMap(m=>Object.keys(m.morphTargetDictionary).filter(n=>!n.startsWith('corrective'))));
    $('rig-status').textContent=`${boneCount} BONES / ${facialChannels.size} FACIAL CONTROLS`;
    document.querySelectorAll('.character').forEach((b,i)=>{b.classList.toggle('selected',i===index);b.setAttribute('aria-current',i===index?'true':'false');});
    const roster=$('roster'),button=roster.children[index];
    if(button.offsetLeft<roster.scrollLeft||button.offsetLeft+button.offsetWidth>roster.scrollLeft+roster.clientWidth)roster.scrollTo({left:button.offsetLeft-roster.offsetLeft-roster.clientWidth/2+button.offsetWidth/2,behavior:'smooth'});
    const url=new URL(location);url.searchParams.set('character',info.id);history.replaceState(null,'',url);
    notice('');
  }catch(error){
    if(generation!==requestId)return;
    requestedIndex=currentIndex;console.error(error);notice(`Could not load ${info.name}. ${error.message}`);
  }
  finally{if(generation===requestId)$('loading').hidden=true;}
}

function resetExpression(){
  demo=false;updateDemoButton();
  for(const name of manifest?.channels||[])target[name]=0;
  targetRotation.identity();
  document.querySelectorAll('[data-preset]').forEach(b=>b.classList.toggle('selected',b.dataset.preset==='neutral'));
  syncSliders();
}
function syncSliders(){
  document.querySelectorAll('[data-channels]').forEach(input=>{
    const value=target[input.dataset.channels.split(',')[0]]||0;
    input.value=value;$(input.id+'-value').textContent=`${Math.round(value*100)}%`;
  });
  const value=target[$('channel').value]||0;
  $('channel-strength').value=value;$('channel-value').textContent=`${Math.round(value*100)}%`;
}
function updateDemoButton(){
  $('demo').innerHTML=`<img src="vendor/lucide/${demo?'pause':'play'}.svg" alt="">${demo?'Pause reel':'Expression reel'}`;
  $('demo').setAttribute('aria-pressed',String(demo));
}
function driveFace(dt,time){
  if(!current)return;
  if(demo&&!stream){
    const step=(time-demoStart)/2500;
    const values=Object.values(presets)[1+Math.floor(step)%3];
    const intensity=Math.sin((step%1)*Math.PI)**2;
    for(const name of manifest.channels)target[name]=(values[name]||0)*intensity;
  }
  const alpha=1-Math.exp(-dt*17);
  for(const name of manifest.channels){
    // Live eye samples are already filtered at camera cadence. Filtering them a
    // second time here slows deliberate blinks, especially at low FPS.
    const weight=name==='tongueOut'?1-Math.exp(-dt*45):stream&&time-lastFaceTime<=650&&name.startsWith('eye')?1:alpha;
    smooth[name]=THREE.MathUtils.lerp(smooth[name]||0,target[name]||0,weight);
  }
  const values={...smooth};
  if(current.info.cyclops){
    // Anatomical left/right channels are retained in the file, but one physical eye
    // receives one averaged signal. Applying both deltas would over-close its lid.
    for(const kind of ['Blink','Squint','Wide','LookUp','LookDown','LookIn','LookOut']){
      values[`eye${kind}Left`]=((smooth[`eye${kind}Left`]||0)+(smooth[`eye${kind}Right`]||0))/2;
      values[`eye${kind}Right`]=0;
    }
  }
  resolveEyeAperture(values);
  resolveMouth(values);
  for(const mesh of current.meshes){
    for(const [name,i] of Object.entries(mesh.morphTargetDictionary))mesh.morphTargetInfluences[i]=oralWeight(name,values[name]||0,mesh.material?.name||'',values);
  }
  smoothRotation.slerp(targetRotation,alpha);
  if(current.head&&current.headRest){
    const parent=current.head.parent.getWorldQuaternion(new THREE.Quaternion());
    current.head.quaternion.copy(parent.clone().invert().multiply(smoothRotation).multiply(parent).multiply(current.headRest));
  }
}

async function startCamera(){
  if(cameraStarting||stream||document.hidden)return;
  cameraWanted=true;cameraStarting=true;clearTimeout(retryTimer);
  const generation=++cameraRequest;
  let cancelled=false;
  $('camera-toggle').disabled=true;status('Starting camera');notice('');
  try{
    let candidate;
    if(zedMode){
      zedSource=new ZedSource((body,capturedAt,changed)=>{
        if(changed){
          headEffect?.clear();
          resetMotion();resetExpression();eyeSignals.reset();latestFaceLandmarks=null;
          handTracker?.detector.reset();landmarker?.invalidate(capturedAt);
          tongueTracker?.sample($('camera-preview'),null,performance.now());
        }
        framing.update(body,capturedAt);
        const arms=armSignal.update(body.arms,capturedAt);
        for(const [side,directions] of Object.entries(arms))trackedArms[side]={directions,time:capturedAt};
      },error=>{stopCamera(true);notice(error.message);scheduleCameraRetry();});
      candidate=await zedSource.start();
    }else{
      if(!navigator.mediaDevices?.getUserMedia)throw new Error('Camera access requires localhost or HTTPS.');
      candidate=await navigator.mediaDevices.getUserMedia(cameraConstraints(navigator.mediaDevices.getSupportedConstraints?.()));
    }
    if(generation!==cameraRequest){cancelled=true;candidate.getTracks().forEach(t=>t.stop());return;}
    stream=candidate;$('camera-preview').srcObject=stream;await $('camera-preview').play();
    for(const track of stream.getVideoTracks())track.onended=()=>{
      if(cameraWanted){stopCamera(true);notice('Camera disconnected. Reconnecting...');scheduleCameraRetry();}
    };
    if(!landmarker){
      status('Loading face tracker');
      landmarker=new FaceTracker({maxFaces:headEffect?2:1});await landmarker.ready;
    }
    if(generation!==cameraRequest){cancelled=true;return;}
    resetExpression();eyeSignals.reset();lastVideoTime=-1;lastFaceTime=0;lastDetectionTime=0;baseline={};
    $('camera-preview').hidden=false;$('calibrate').disabled=false;
    $('camera-toggle').innerHTML='<img src="vendor/lucide/video-off.svg" alt="">Stop camera';
    status('Looking for a face');
    $('camera-retry').hidden=true;
    handTracker=new AirSwipeTracker(direction=>{
      if(stream)selectCharacter(requestedIndex+direction);
    },error=>{
      console.warn('Motion tracking unavailable:',error);
      notice('Motion tracking unavailable. Retry camera.');$('camera-retry').hidden=false;
      resetMotion();
    },(result,gesture,capturedAt)=>{
      if(zedMode&&result.personId!==zedSource?.personId)return;
      framing.update(result,capturedAt,gesture);
      if(!zedMode){
        const arms=armSignal.update(armDirections(result.poseLandmarks,result.poseWorldLandmarks,result.aspectRatio),capturedAt);
        for(const [side,directions] of Object.entries(arms))if(capturedAt>(trackedArms[side]?.time??-Infinity))trackedArms[side]={directions,time:capturedAt};
      }
      for(const [side,curls] of Object.entries(trackedFingerCurls(result)))trackedFingers[side]={curls,time:capturedAt};
      const cue=$('swap-cue');
      cue.hidden=!showSwipeCue||!['holding','armed'].includes(gesture.state);
      cue.dataset.state=gesture.state;cue.style.setProperty('--progress',gesture.progress);
      cue.setAttribute('aria-label',gesture.state==='armed'?'Character switching ready':'Preparing character switch');
    },{nativeBody:zedMode,acceptResult:result=>!zedMode||result.personId===zedSource?.personId});
    tongueTracker=new TongueTracker(error=>{
      console.warn('Tongue tracking unavailable:',error);
      notice('Tongue tracking unavailable. Retry camera.');$('camera-retry').hidden=false;
    });
  }catch(error){
    if(generation!==cameraRequest){cancelled=true;return;}
    stopCamera(true);notice(error.name==='NotAllowedError'?'Allow camera access for this installation, then retry.':`Camera unavailable: ${error.message}`);
    $('camera-retry').hidden=false;
    if(error.name!=='NotAllowedError'&&error.name!=='SecurityError')scheduleCameraRetry();
  }finally{
    cameraStarting=false;$('camera-toggle').disabled=false;
    if(cancelled&&cameraWanted)scheduleCameraRetry();
  }
}
function scheduleCameraRetry(){clearTimeout(retryTimer);if(cameraWanted&&!document.hidden)retryTimer=setTimeout(startCamera,4000);}
function stopCamera(preserveIntent=false){
  headEffect?.clear();
  zedSource?.stop();zedSource=null;
  latestFaceLandmarks=null;
  landmarker?.close();landmarker=null;
  tongueTracker?.stop();tongueTracker=null;
  handTracker?.stop();handTracker=null;
  resetMotion();
  if(!preserveIntent)cameraWanted=false;
  clearTimeout(retryTimer);
  cameraRequest++;stream?.getTracks().forEach(t=>t.stop());stream=null;
  $('camera-preview').srcObject=null;$('camera-preview').hidden=true;
  $('calibrate').disabled=true;$('calibrate').innerHTML='<img src="vendor/lucide/scan-face.svg" alt="">Calibrate';calibration=null;
  $('camera-toggle').innerHTML='<img src="vendor/lucide/video.svg" alt="">Start camera';
  status('Camera off');resetExpression();
}
function resetMotion(){
  framing.reset();
  armSignal.reset();
  for(const side of Object.keys(trackedArms))delete trackedArms[side];
  for(const side of Object.keys(trackedFingers))delete trackedFingers[side];
  $('swap-cue').hidden=true;
  handTracker?.detector.reset();
}
function trackFace(time){
  const video=$('camera-preview');
  if(!stream||!landmarker||video.readyState<2)return;
  if(zedMode)time=Math.min(time,zedSource?.capturedAt??time);
  lastVideoTime=video.currentTime;
  const results=landmarker.detectForVideo(video,time);
  if(!results){
    if(time-lastFaceTime>650){for(const name of manifest.channels)target[name]=0;targetRotation.identity();eyeSignals.reset();status('Looking for a face');}
    return;
  }
  time=results.captureTime??time;
  latestFaceLandmarks=results.faceLandmarks?.[0]||null;
  // The returned bitmap predates face inference. Use its landmarks to locate a
  // fresh camera image, not to queue tongue inference on the same old pixels.
  if(headEffect)headEffect.accept(results,photoPerson());else results.frame?.close();
  tongueTracker?.sampleLatest(video,latestFaceLandmarks,time,performance.now(),zedSource?.capturedAt);
  const dt=lastDetectionTime?clamp((time-lastDetectionTime)/1000,.001,.15):1/30;
  lastDetectionTime=time;
  if(results.faceBlendshapes?.[0]){
    lastFaceTime=time;status('Face connected',true);
    const raw=Object.fromEntries(results.faceBlendshapes[0].categories.map(c=>[c.categoryName,c.score]));
    if(calibration){
      for(const [name,value] of Object.entries(raw))calibration.sum[name]=(calibration.sum[name]||0)+value;
      calibration.frames++;
      if(calibration.frames>=30){
        baseline=Object.fromEntries(Object.entries(calibration.sum).map(([k,v])=>[k,v/calibration.frames]));calibration=null;
        $('calibrate').innerHTML='<img src="vendor/lucide/check.svg" alt="">Calibrated';
      }
    }
    for(const name of manifest.channels){
      const base=baseline[name]||0;const value=clamp(((raw[name]||0)-base)/Math.max(.1,1-base));
      target[name]=name.startsWith('eye')?eyeSignals.update(name,value,dt):value;
    }
    const matrix=results.facialTransformationMatrixes?.[0]?.data;
    if(matrix){
      const q=new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().fromArray(matrix));
      const e=new THREE.Euler().setFromQuaternion(q,'YXZ');
      targetRotation.setFromEuler(new THREE.Euler(clamp(e.x,-.5,.5),clamp(-e.y,-.65,.65),clamp(-e.z,-.45,.45),'YXZ'));
    }
  }else if(time-lastFaceTime>650){
    status('Looking for a face');for(const name of manifest.channels)target[name]=0;targetRotation.identity();
    if(calibration){calibration.frames=0;calibration.sum={};}
    eyeSignals.reset();
  }
}

document.querySelectorAll('[data-preset]').forEach(b=>b.onclick=()=>{
  if(cameraWanted)stopCamera();resetExpression();Object.assign(target,presets[b.dataset.preset]);
  document.querySelectorAll('[data-preset]').forEach(p=>p.classList.toggle('selected',p===b));syncSliders();
});
document.querySelectorAll('[data-channels]').forEach(input=>input.oninput=()=>{
  const value=Number(input.value);
  if(cameraWanted)stopCamera();demo=false;updateDemoButton();
  for(const name of input.dataset.channels.split(','))target[name]=value;
  document.querySelectorAll('[data-preset]').forEach(b=>b.classList.remove('selected'));syncSliders();
});
$('channel').onchange=syncSliders;
$('channel-strength').oninput=()=>{
  const value=Number($('channel-strength').value);
  if(cameraWanted)stopCamera();demo=false;updateDemoButton();target[$('channel').value]=value;syncSliders();
};
$('reset-expression').onclick=resetExpression;
$('previous').onclick=()=>selectCharacter(requestedIndex-1);
$('next').onclick=()=>selectCharacter(requestedIndex+1);
$('camera-toggle').onclick=()=>stream?stopCamera():startCamera();
$('camera-framing-toggle').onclick=()=>{$('camera-framing').showModal();framing.draw(performance.now());};
$('close-framing').onclick=()=>$('camera-framing').close();
$('save-trace').onclick=()=>{
  const trace={savedAt:new Date().toISOString(),framing:framing.snapshot(),diagnostics:handTracker?.handDiagnostics||null,trace:handTracker?.trace||[]};
  const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(trace)],{type:'application/json'}));
  a.download=`swipe-trace-${Date.now()}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);
};
$('camera-framing').addEventListener('close',()=>{
  const url=new URL(location.href);url.searchParams.delete('framing');history.replaceState(null,'',url);
});
$('camera-retry').onclick=()=>{if(stream)stopCamera(true);startCamera();};
$('demo').onclick=()=>{if(cameraWanted)stopCamera();demo=!demo;demoStart=performance.now();updateDemoButton();if(!demo)resetExpression();};
$('calibrate').onclick=()=>{calibration={frames:0,sum:{}};$('calibrate').textContent='Hold neutral...';};
$('reset-view').onclick=resetView;
document.querySelectorAll('[data-pose]').forEach(b=>b.onclick=()=>setPose(b.dataset.pose));
$('panel-toggle').onclick=()=>{const open=$('expression-panel').classList.toggle('open');$('panel-toggle').setAttribute('aria-expanded',String(open));};
$('fullscreen').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await $('app').requestFullscreen();}catch(e){notice(e.message);}};
$('screenshot').onclick=()=>{renderer.render(scene,camera);const a=document.createElement('a');a.href=renderer.domElement.toDataURL('image/png');a.download=`${current?.info.id||'avatar'}-${bodyPose.toLowerCase()}.png`;a.click();};
let swipe=null;
renderer.domElement.addEventListener('pointerdown',e=>{if(e.pointerType==='touch'&&e.isPrimary)swipe={x:e.clientX,y:e.clientY,time:performance.now(),id:e.pointerId};else if(e.pointerType==='touch')swipe=null;});
renderer.domElement.addEventListener('pointerup',e=>{
  if(!swipe||e.pointerId!==swipe.id)return;
  const dx=e.clientX-swipe.x,dy=e.clientY-swipe.y;
  if(Math.abs(dx)>55&&Math.abs(dx)>Math.abs(dy)*1.5&&performance.now()-swipe.time<700)selectCharacter(requestedIndex+(dx<0?1:-1));
  swipe=null;
});
renderer.domElement.addEventListener('pointercancel',()=>{swipe=null;});
addEventListener('keydown',e=>{if(/INPUT|SELECT|TEXTAREA/.test(e.target.tagName))return;if(e.key==='ArrowLeft'){e.preventDefault();selectCharacter(requestedIndex-1);}if(e.key==='ArrowRight'){e.preventDefault();selectCharacter(requestedIndex+1);}if(e.key==='Escape'){$('expression-panel').classList.remove('open');$('panel-toggle').setAttribute('aria-expanded','false');}});
addEventListener('pagehide',()=>{stopCamera();landmarker?.close();});
document.addEventListener('visibilitychange',()=>{
  if(document.hidden){if(stream||cameraStarting)stopCamera(true);}
  else if(cameraWanted)startCamera();
});
navigator.mediaDevices?.addEventListener('devicechange',()=>{if(cameraWanted&&!stream)startCamera();});

let previousTime=performance.now();
renderer.setAnimationLoop(time=>{
  const dt=Math.min(.05,(time-previousTime)/1000);previousTime=time;
  framing.draw(time);
  if(stream)handTracker?.sample($('camera-preview'),zedSource?.capturedAt??performance.now(),zedSource?.body);
  try{trackFace(time);}catch(error){stopCamera(true);landmarker?.close();landmarker=null;notice(`Face tracker restarting: ${error.message}`);scheduleCameraRetry();}
  if(stream&&latestFaceLandmarks)tongueTracker?.sampleLatest($('camera-preview'),latestFaceLandmarks,lastFaceTime,performance.now(),zedSource?.capturedAt);
  const arms={};
  for(const [side,sample] of Object.entries(trackedArms))if(stream&&time-sample.time<400)arms[side]=sample.directions;
  current?.arms.update(arms,dt);
  const fingers={};
  for(const [side,sample] of Object.entries(trackedFingers))if(stream&&time-sample.time<400)fingers[side]=sample.curls;
  current?.fingers.update(fingers,dt);
  if(stream)target.tongueOut=tongueTracker?.value(time)||0;
  if(!handTracker?.ready||time-handTracker.lastResultTime>400)$('swap-cue').hidden=true;
  driveFace(dt,time);current?.collisions.update(dt);current?.correctives.update(bodyPose);controls.update();
  if(arMode&&current){
    const ready=!!stream&&headEffect.fresh(photoPerson());
    if(ready&&(headEffect.renderedAt!==headEffect.sample.captureTime||headEffect.character!==current.info.id)){
      try{headEffect.render(current,photoPerson());}catch(error){notice(`Alien camera: ${error.message}`);}
    }
    if(!ready)headEffect.cameraOnly(photoPerson());
    arControls?.update({ready:ready&&headEffect.character===current.info.id&&!!headEffect.renderedAt,name:current.info.name,camera:!!stream,starting:cameraStarting});
    return;
  }
  // Compile the head-only render before the phone can start a timed capture.
  if(photoEnabled&&!photoDemo&&current&&headEffect.character!==current.info.id&&headEffect.fresh(photoPerson())){
    headEffect.render(current,photoPerson());
  }
  if(setupMode)fleetStage.layout(true);
  fleetStage.renderBackdrop(renderer);
  if(displayView!=='tv')vinyl.render(renderer,scene,camera,displayView==='ship');else renderer.render(scene,camera);
});

try{
  const response=await fetch('assets/fleet/manifest.json');
  if(!response.ok)throw new Error('Fleet manifest is unavailable.');
  manifest=await response.json();
  if(params.get('assets')!=='fleet'){
    const localReview=params.get('assets')==='local';
    const libraryResponse=await fetch(localReview?'assets/local-characters/manifest.json':params.get('rigs')==='refined'?'assets/3dai/refined/manifest.json':'assets/3dai/manifest.json');
    if(!libraryResponse.ok)throw new Error('Character asset manifest is unavailable.');
    const library=await libraryResponse.json();
    manifest.vehicle=library.vehicle;
    manifest.characters=library.characters;
  }
  $('channel').replaceChildren(...manifest.channels.map(name=>{const option=document.createElement('option');option.value=name;option.textContent=name;return option;}));
  $('roster').replaceChildren(...manifest.characters.map((c,i)=>{
    const button=document.createElement('button');button.className='character';button.setAttribute('aria-label',c.name);button.onclick=()=>selectCharacter(i);
    const img=document.createElement('img');img.src=c.thumbnail;img.alt='';const label=document.createElement('span');label.textContent=c.name;button.append(img,label);return button;
  }));
  const initial=manifest.characters.findIndex(c=>c.id===new URLSearchParams(location.search).get('character'));
  await selectCharacter(Math.max(0,initial));
  if(arMode){
    const {ARPhotoControls}=await import('./ar-photo-controls.js');
    arControls=new ARPhotoControls({canvas:headEffect.canvas,
      previous:()=>selectCharacter(requestedIndex-1),next:()=>selectCharacter(requestedIndex+1),retry:startCamera,
      capture:()=>({canvas:brandAlienPhoto(headEffect.snapshot(current,photoPerson()),current.info.name),name:current.info.name})});
  }
  if(photoEnabled){
    const {PhotoBooth}=await import('./photo-booth.js');
    photoBooth=new PhotoBooth({demo:photoDemo,connection:photoConfig,onStatus:state=>spaceshipPhoto?.update(state),
      captureReady:()=>photoDemo||headEffect.fresh(photoPerson()),
      state:()=>({ready:!!current&&$('loading').hidden&&(photoDemo||!!stream&&headEffect.character===current.info.id&&(!zedMode||performance.now()-(zedSource?.capturedAt??0)<250)&&headEffect.fresh(photoPerson(),performance.now(),750)),
        character:current?.info.id,characterName:current?.info.name,
        person:photoDemo?'demo':photoPerson(),
        people:photoDemo?1:zedMode?zedSource?.peopleCount??0:headEffect.sample?.faceLandmarks?.length??0}),
      capture:()=>{
        if(!photoDemo)return {composite:headEffect.snapshot(current,photoPerson()),name:current.info.name};
        return {alien:captureAlien(renderer,scene,camera),name:current.info.name};
      }});
  }
  const cameraReady=photoDemo?Promise.resolve():startCamera();
  void preloadCharacters();
  await cameraReady;
  if(params.has('framing'))$('camera-framing').showModal();
}catch(error){console.error(error);$('loading').hidden=true;notice(error.message);}

// Read-only diagnostics for automated export/render checks, enabled explicitly.
if(new URLSearchParams(location.search).has('qa'))Object.defineProperty(window,'fleetQA',{get:()=>({
  character:current?.info.id,vehicleUUID:null,vehicleVisible:false,pose:bodyPose,displayView,vinylReady:vinyl?.ready??false,
  ar:headEffect?{frames:headEffect.frames,fresh:headEffect.fresh(photoPerson()),character:headEffect.character,placement:headEffect.placement,
    headBounds:current&&headEffect.records.get(current)?{center:headEffect.records.get(current).center.toArray(),size:headEffect.records.get(current).size.toArray()}:null}:null,
  armCollisionAdjustments:current?.collisions.adjustments,armPenetration:current?.collisions.penetration,armCollisionMs:current?.collisions.durationMs,
  animations:current?.gltf.animations.map(a=>a.name),
  morphs:current?.meshes.map(m=>({names:Object.keys(m.morphTargetDictionary),weights:[...m.morphTargetInfluences]})),
  bones:(()=>{const b={};current?.gltf.scene.traverse(o=>{if(o.isBone)b[o.name]=o.getWorldPosition(new THREE.Vector3()).toArray();});return b;})(),
  drawCalls:renderer.info.render.calls,triangles:renderer.info.render.triangles,cameraActive:!!stream,
  cameraFraming:framing.snapshot(),
  trackingSource:zedMode?'zed':'webcam',zedFrames:zedSource?.frames||0,zedLatencyMs:zedSource?.latencyMs||0,
  zedPersonId:zedSource?.personId??null,zedDroppedFrames:zedSource?.droppedFrames||0,
  faceTrackingFrames:landmarker?.frames||0,faceLatencyMs:landmarker?.latencyMs||0,faceDelegate:landmarker?.delegate,
  fingerCurls:{...current?.fingers.values},
  handTrackingReady:!!handTracker?.ready,handTrackingFrames:handTracker?.frames||0,
  handDiagnostics:handTracker?{...handTracker.handDiagnostics,lastResultAgeMs:handTracker.lastResultTime?performance.now()-handTracker.lastResultTime:null}:null,
  poseTrackingFrames:handTracker?.poseFrames||0,
  motionLatencyMs:handTracker?.latencyMs||0,motionDroppedFrames:handTracker?.droppedFrames||0,
  tongueTrackingReady:!!tongueTracker?.ready,tongueTrackingFrames:tongueTracker?.frames||0,
  tongueScore:tongueTracker?.raw||0,tongueLatencyMs:tongueTracker?.latencyMs||0,
  tongueInferenceMs:tongueTracker?.inferenceMs||0,tongueCropAgeMs:tongueTracker?.cropAgeMs||0,
  tongueDroppedFrames:tongueTracker?.droppedFrames||0,
  swapState:handTracker?.detector.state||'idle',swapReason:handTracker?.detector.reason||'waiting',swipeTrace:handTracker?.trace||[],trackedArms:Object.keys(trackedArms).filter(s=>performance.now()-trackedArms[s].time<400),
  stage:fleetStage.snapshot(),loadedCharacters:fleetStage.entries.size,backdropFrames:fleetStage.backdropFrames,
  cameraPosition:camera.position.toArray(),renderFrame:renderer.info.render.frame
})});
