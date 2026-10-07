// Safari's MediaPipe build avoids OffscreenCanvas and falls back to document.createElement('canvas'),
// which throws "Can't find variable: document" inside a worker. Route that fallback back to OffscreenCanvas.
self.document??={createElement:tag=>tag==='canvas'?new OffscreenCanvas(1,1):{},body:{appendChild(){}}};
let poseTracker=null,hands=null,handBusy=false,handWatchdog,pendingHand=null;
// Hand inference takes about as long as pose inference, so refusing frames while
// busy halved the hand sample rate. Queue the newest frame instead (depth one):
// the hand model stays continuously fed at most one pose frame behind.
function sendHand(frame,time,body){
  handBusy=true;
  handWatchdog=setTimeout(()=>self.postMessage({type:'error',message:'Finger tracking frame timed out'}),10000);
  try{hands.postMessage({type:'frame',frame,time,body},[frame]);}
  catch(error){frame.close();handBusy=false;throw error;}
}
function queueHand(frame,time,body){
  if(!handBusy){sendHand(frame,time,body);return;}
  pendingHand?.frame.close();pendingHand={frame,time,body};
}
self.onmessage=async({data})=>{
  try{
    if(data.type==='init'){
      const handReady=new Promise((resolve,reject)=>{
        hands=new Worker(new URL('./finger-tracking-worker.js',self.location.href));
        hands.onmessage=({data})=>{
          if(data.type==='ready'){resolve();return;}
          clearTimeout(handWatchdog);handBusy=false;
          if(data.type==='error'){reject(new Error(data.message));self.postMessage(data);return;}
          self.postMessage({...data,independentHands:true});
          if(pendingHand){
            const next=pendingHand;pendingHand=null;
            try{sendHand(next.frame,next.time,next.body);}catch(error){self.postMessage({type:'error',message:error.message});}
          }
        };
        hands.onerror=e=>{e.preventDefault();reject(new Error(e.message));self.postMessage({type:'error',message:e.message});};
        hands.postMessage({type:'init'});
      });
      // Attach a rejection handler immediately while the pose model initializes.
      handReady.catch(()=>{});
      const {PoseLandmarker,FilesetResolver}=await import('./vendor/mediapipe/vision_pose_bundle.mjs');
      const files=await FilesetResolver.forVisionTasks(new URL('./vendor/mediapipe/wasm',self.location.href).href);
      poseTracker=await PoseLandmarker.createFromOptions(files,{
        baseOptions:{modelAssetPath:new URL('./vendor/mediapipe/model/pose_landmarker_lite.task',self.location.href).href,delegate:'CPU'},
        runningMode:'VIDEO',numPoses:1,minPoseDetectionConfidence:.6,minPosePresenceConfidence:.6,minTrackingConfidence:.6,
        outputSegmentationMasks:false,
      });
      await handReady;self.postMessage({type:'ready'});
    }else if(data.type==='frame'){
      if(!poseTracker)throw new Error('Pose tracker is not initialized');
      const small=await createImageBitmap(data.frame,{resizeWidth:480,resizeHeight:Math.round(480*data.frame.height/data.frame.width)});
      let pose;
      try{pose=poseTracker.detectForVideo(small,data.time);}finally{small.close();}
      const body={poseLandmarks:pose.landmarks[0]||[],poseWorldLandmarks:pose.worldLandmarks[0]||[],aspectRatio:data.frame.width/data.frame.height};
      queueHand(await createImageBitmap(data.frame),data.time,body);
      self.postMessage({type:'pose',time:data.time,result:body,complete:true});
    }
  }catch(error){self.postMessage({type:'error',message:error.message});}
  finally{data.frame?.close();}
};
