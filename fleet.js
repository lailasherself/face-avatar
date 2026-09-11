import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/RoomEnvironment.js';
import { attachEyelidSurface, EyeSignalFilter, resolveEyeAperture } from './eyelid-surface.js';
import { AirSwipeTracker } from './air-swipe.js';
import { HoldGesture } from './dwell-gestures.js';
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
import { ZedSource } from './zed-source.js';
import { CameraFraming, cameraConstraints } from './camera-framing.js';

const $ = (id) => document.getElementById(id);
const clamp = (v, lo=0, hi=1) => Math.min(hi, Math.max(lo, v));
const params=new URLSearchParams(location.search);
const setupMode=params.has('setup');
const zedMode=params.get('tracking')==='zed';
const framing=new CameraFraming($('camera-preview'),$('camera-framing'),zedMode ? .6 : .8);
const eyeSignals=new EyeSignalFilter();
const scene = new THREE.Scene();
scene.background = new THREE.Color('#edf1ee');
scene.fog = new THREE.Fog('#edf1ee',9,24);
const renderer = new THREE.WebGLRenderer({canvas:$('scene'),antialias:true,preserveDrawingBuffer:true});
renderer.setPixelRatio(setupMode?Math.min(devicePixelRatio,2):1);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.15;
renderer.shadowMap.enabled = setupMode;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
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
controls.minDistance = 2.7;controls.maxDistance=10;
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

const loader = new GLTFLoader();
let manifest, current, currentIndex=0, requestId=0, bodyPose='Standing';
let stream=null, landmarker=null, cameraRequest=0, lastVideoTime=-1, lastFaceTime=0;
let cameraStarting=false,retryTimer=null,cameraWanted=true,lastDetectionTime=0;
let handTracker=null,tongueTracker=null;
// Browse vs embodied. In browse you swipe to change the character you already drive; raising
// both palms (a deliberate, low-false-trigger confirm) commits and dollies the avatar forward.
// While embodied, one flat palm held still steps back to browse — stillness is the discriminator
// that keeps it from firing during expressive puppeteering (see research brief).
const COMMIT_HOLD_MS=1200, CHANGE_HOLD_MS=800;
let mode='browse', modeFrame=0;
const commitGesture=new HoldGesture(2,COMMIT_HOLD_MS);
const changeGesture=new HoldGesture(1,CHANGE_HOLD_MS);
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
  const base=setupMode?8.3:Math.max(6.7,4.7/camera.aspect);
  // Embodied framing steps the avatar forward (closer, slightly higher) so committing reads
  // as "you are now this character". modeFrame eases 0→1 between browse and embodied.
  const d=base*THREE.MathUtils.lerp(1,.74,modeFrame);
  controls.target.set(0,ty+THREE.MathUtils.lerp(0,.06,modeFrame),0);
  camera.position.set(d*.26,controls.target.y+d*.12,d*.97);
  camera.zoom=1;
  camera.updateProjectionMatrix();controls.update();
}
const dwellFill=$('dwell-cue').querySelector('.dwell-fill');
const dwellLabel=$('dwell-cue').querySelector('.dwell-label');
const DWELL_CIRC=2*Math.PI*21;
function showDwell(progress,label){
  $('dwell-cue').hidden=false;
  dwellFill.style.strokeDashoffset=DWELL_CIRC*(1-clamp(progress));
  if(dwellLabel.textContent!==label)dwellLabel.textContent=label;
}
function hideDwell(){if(!$('dwell-cue').hidden)$('dwell-cue').hidden=true;}
function updateModeUI(){
  document.body.classList.toggle('embodied',mode==='embodied');
  const prompt=$('mode-prompt');
  if(!stream||setupMode){prompt.hidden=true;return;}
  prompt.hidden=false;
  prompt.innerHTML=mode==='browse'
    ? 'Hold up <b>one hand</b> and swipe to change &nbsp;·&nbsp; raise <b>both hands</b> to become this one'
    : `You're <b>${current?.info.name||'this character'}</b> &nbsp;·&nbsp; hold up <b>one hand</b> to switch`;
}
function setMode(next){
  if(mode===next)return;
  mode=next;
  commitGesture.reset();changeGesture.reset();handTracker?.detector.reset();
  $('swap-cue').hidden=true;hideDwell();updateModeUI();
}
function resize(){
  const {width,height}=$('stage').getBoundingClientRect();
  renderer.setSize(width,height,false);camera.aspect=width/height;
  camera.fov=36;
  camera.setViewOffset(width,height,0,setupMode?height*.07:0,width,height);
  camera.updateProjectionMatrix();
  resetView();
}
new ResizeObserver(resize).observe($('stage'));
resetView();

function disposeModel(gltf){
  gltf.scene.traverse(o=>{
    if(o.geometry)o.geometry.dispose();
    const materials=Array.isArray(o.material)?o.material:[o.material];
    for(const m of materials)if(m){
      for(const v of Object.values(m))if(v?.isTexture)v.dispose();
      m.dispose();
    }
    if(o.skeleton)o.skeleton.dispose();
    o.customDepthMaterial?.dispose();
  });
}
function setPose(name){
  bodyPose=name;
  if(current){
    const clip=THREE.AnimationClip.findByName(current.gltf.animations,name);
    current.mixer.stopAllAction();
    if(clip){const action=current.mixer.clipAction(clip);action.play();current.mixer.update(0);}
    current.headRest=current.head?.quaternion.clone();
    current.arms=new ArmRetargeter(current.gltf.scene);
    current.collisions?.dispose();
    current.correctives.update(bodyPose);
    current.collisions=new ArmCollisions(current.gltf.scene,current.arms.chains);
    current.collisions.update();current.arms.captureNeutral();
    current.fingers=new FingerRetargeter(current.gltf.scene);
  }
  document.querySelectorAll('[data-pose]').forEach(b=>b.classList.toggle('selected',b.dataset.pose===name));
}
async function selectCharacter(index){
  if(!manifest)return;
  index=(index+manifest.characters.length)%manifest.characters.length;
  const generation=++requestId;
  const info=manifest.characters[index];
  $('loading').hidden=false;$('loading').textContent=`Loading ${info.name}...`;
  try{
    const gltf=await loader.loadAsync(info.url);
    if(generation!==requestId){disposeModel(gltf);return;}
    const meshes=[];let head=null;let boneCount=0;
    gltf.scene.traverse(o=>{
      if(o.isMesh){
        o.castShadow=true;o.receiveShadow=true;
        if(o.isSkinnedMesh)o.frustumCulled=false;
        if(o.morphTargetDictionary){o.morphTargetInfluences.fill(0);meshes.push(o);}
        let owner=o;
        while(owner&&!owner.userData.eyelidSurfaces)owner=owner.parent;
        if(owner)attachEyelidSurface(o,owner.userData.eyelidSurfaces);
      }
      if(o.isBone){boneCount++;if(o.name==='Head')head=o;}
    });
    if(current){current.collisions?.dispose();scene.remove(current.gltf.scene);current.mixer.stopAllAction();current.mixer.uncacheRoot(current.gltf.scene);disposeModel(current.gltf);}
    current={gltf,info,meshes,head,mixer:new THREE.AnimationMixer(gltf.scene),correctives:new PoseCorrectives(gltf.scene,gltf.animations)};
    currentIndex=index;scene.add(gltf.scene);setPose(bodyPose);
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
  }catch(error){console.error(error);notice(`Could not load ${info.name}. ${error.message}`);}
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
    for(const [name,i] of Object.entries(mesh.morphTargetDictionary))mesh.morphTargetInfluences[i]=oralWeight(name,values[name]||0,mesh.material?.name||'');
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
      landmarker=new FaceTracker();await landmarker.ready;
    }
    if(generation!==cameraRequest){cancelled=true;return;}
    resetExpression();eyeSignals.reset();lastVideoTime=-1;lastFaceTime=0;lastDetectionTime=0;baseline={};
    mode='browse';commitGesture.reset();changeGesture.reset();
    $('camera-preview').hidden=false;$('calibrate').disabled=false;
    $('camera-toggle').innerHTML='<img src="vendor/lucide/video-off.svg" alt="">Stop camera';
    status('Looking for a face');
    $('camera-retry').hidden=true;
    handTracker=new AirSwipeTracker(direction=>{
      if(stream&&$('loading').hidden&&mode==='browse')selectCharacter(currentIndex+direction);
    },error=>{
      console.warn('Motion tracking unavailable:',error);
      notice('Motion tracking unavailable. Retry camera.');$('camera-retry').hidden=false;
      resetMotion();
    },(result,gesture,capturedAt)=>{
      if(zedMode&&result.personId!==zedSource?.personId)return;
      framing.update(result,capturedAt);
      if(!zedMode){
        const arms=armSignal.update(armDirections(result.poseLandmarks,result.poseWorldLandmarks,result.aspectRatio),capturedAt);
        for(const [side,directions] of Object.entries(arms))if(capturedAt>(trackedArms[side]?.time??-Infinity))trackedArms[side]={directions,time:capturedAt};
      }
      for(const [side,curls] of Object.entries(trackedFingerCurls(result)))trackedFingers[side]={curls,time:capturedAt};
      const cue=$('swap-cue');
      if(mode==='browse'){
        cue.hidden=!['holding','armed'].includes(gesture.state);
        cue.dataset.state=gesture.state;cue.style.setProperty('--progress',gesture.progress);
        cue.setAttribute('aria-label',gesture.state==='armed'?'Character switching ready':'Preparing character switch');
        // Two palms held still = commit. Distinct palm count keeps it clear of the one-palm swipe.
        const commit=commitGesture.update(result,capturedAt);
        if(commit.fired)setMode('embodied');
        else if(commit.progress>0)showDwell(commit.progress,`Becoming ${current?.info.name||'this one'}…`);
        else hideDwell();
      }else{
        cue.hidden=true;
        // One flat palm held still steps back to browse — orthogonal to expressive puppeteering.
        const change=changeGesture.update(result,capturedAt);
        if(change.fired)setMode('browse');
        else if(change.progress>0)showDwell(change.progress,'Switch character…');
        else hideDwell();
      }
    },{nativeBody:zedMode,acceptResult:result=>!zedMode||result.personId===zedSource?.personId});
    tongueTracker=new TongueTracker(error=>{
      console.warn('Tongue tracking unavailable:',error);
      notice('Tongue tracking unavailable. Retry camera.');$('camera-retry').hidden=false;
    });
    updateModeUI();
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
  $('mode-prompt').hidden=true;
  status('Camera off');resetExpression();
}
function resetMotion(){
  framing.reset();
  armSignal.reset();
  for(const side of Object.keys(trackedArms))delete trackedArms[side];
  for(const side of Object.keys(trackedFingers))delete trackedFingers[side];
  $('swap-cue').hidden=true;
  commitGesture.reset();changeGesture.reset();
  mode='browse';hideDwell();updateModeUI();
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
  results.frame?.close();
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
$('previous').onclick=()=>selectCharacter(currentIndex-1);
$('next').onclick=()=>selectCharacter(currentIndex+1);
$('camera-toggle').onclick=()=>stream?stopCamera():startCamera();
$('camera-framing-toggle').onclick=()=>{$('camera-framing').showModal();framing.draw(performance.now());};
$('close-framing').onclick=()=>$('camera-framing').close();
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
  if(Math.abs(dx)>55&&Math.abs(dx)>Math.abs(dy)*1.5&&performance.now()-swipe.time<700)selectCharacter(currentIndex+(dx<0?1:-1));
  swipe=null;
});
renderer.domElement.addEventListener('pointercancel',()=>{swipe=null;});
addEventListener('keydown',e=>{if(/INPUT|SELECT|TEXTAREA/.test(e.target.tagName))return;if(e.key==='ArrowLeft'){e.preventDefault();selectCharacter(currentIndex-1);}if(e.key==='ArrowRight'){e.preventDefault();selectCharacter(currentIndex+1);}if(e.key==='Escape'){$('expression-panel').classList.remove('open');$('panel-toggle').setAttribute('aria-expanded','false');}});
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
  if(!handTracker?.ready||time-handTracker.lastResultTime>400){$('swap-cue').hidden=true;hideDwell();}
  // Ease the browse↔embodied camera dolly (installation only; setup mode keeps orbit control).
  if(!setupMode){
    const goal=mode==='embodied'?1:0;
    if(Math.abs(goal-modeFrame)>.001){modeFrame+=(goal-modeFrame)*(1-Math.exp(-dt*6));resetView();}
  }
  driveFace(dt,time);current?.collisions.update(dt);current?.correctives.update(bodyPose);controls.update();renderer.render(scene,camera);
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
  await startCamera();
  if(params.has('framing'))$('camera-framing').showModal();
}catch(error){console.error(error);$('loading').hidden=true;notice(error.message);}

// Read-only diagnostics for automated export/render checks, enabled explicitly.
if(new URLSearchParams(location.search).has('qa'))Object.defineProperty(window,'fleetQA',{get:()=>({
  character:current?.info.id,vehicleUUID:null,vehicleVisible:false,pose:bodyPose,
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
  swapState:handTracker?.detector.state||'idle',swapReason:handTracker?.detector.reason||'waiting',trackedArms:Object.keys(trackedArms).filter(s=>performance.now()-trackedArms[s].time<400),
  mode,modeFrame,commitState:commitGesture.state,commitProgress:commitGesture.progress,changeState:changeGesture.state,changeProgress:changeGesture.progress,
  cameraPosition:camera.position.toArray(),renderFrame:renderer.info.render.frame
})});
