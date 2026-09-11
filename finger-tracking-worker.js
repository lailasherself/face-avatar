let tracker,cropTools,atlas,context;
self.onmessage=async({data})=>{
  try{
    if(data.type==='init'){
      cropTools=await import('./hand-crops.js');
      atlas=new OffscreenCanvas(cropTools.HAND_TILE*2,cropTools.HAND_TILE);
      context=atlas.getContext('2d');
      const {HandLandmarker,FilesetResolver}=await import('./vendor/mediapipe/vision_bundle.mjs');
      const files=await FilesetResolver.forVisionTasks(new URL('./vendor/mediapipe/wasm',self.location.href).href);
      tracker=await HandLandmarker.createFromOptions(files,{
        baseOptions:{modelAssetPath:new URL('./vendor/mediapipe/model/hand_landmarker.task',self.location.href).href,delegate:'CPU'},
        runningMode:'VIDEO',numHands:2,minHandDetectionConfidence:.65,minHandPresenceConfidence:.65,minTrackingConfidence:.6,
      });
      self.postMessage({type:'ready'});
    }else if(data.type==='frame'){
      const start=performance.now(),crops=cropTools.handCrops(data.body,data.frame.width,data.frame.height);
      const noBody=data.body&&Object.hasOwn(data.body,'personId')&&data.body.personId===null;
      let image=data.frame;
      if(crops.length){
        context.fillStyle='#000';context.fillRect(0,0,atlas.width,atlas.height);
        for(const c of crops)context.drawImage(data.frame,c.x,c.y,c.size,c.size,c.tile*cropTools.HAND_TILE,0,cropTools.HAND_TILE,cropTools.HAND_TILE);
        image=atlas;
      }
      const raw=noBody?{landmarks:[]}:tracker.detectForVideo(image,data.time);
      const result=crops.length?cropTools.restoreHands(raw,crops):raw;
      const diagnostics={mode:noBody?'no-body':crops.length?'wrist-crops':'full-frame',wristHints:crops.length,
        sourceWidth:data.frame.width,sourceHeight:data.frame.height,detected:raw.landmarks?.length||0,
        mapped:result.landmarks?.length||0,inferenceMs:performance.now()-start,
        crops:crops.map(({side,x,y,size})=>({side,x,y,size}))};
      self.postMessage({type:'result',time:data.time,result:{landmarks:result.landmarks,worldLandmarks:result.worldLandmarks,handedness:result.handedness,...data.body,handDiagnostics:diagnostics}});
    }
  }catch(error){self.postMessage({type:'error',message:error.message});}
  finally{data.frame?.close();}
};
