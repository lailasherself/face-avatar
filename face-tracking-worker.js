let model;
self.onmessage=async({data})=>{
  let frame=data.frame;
  try{
    if(data.type==='init'){
      const {FaceLandmarker,FilesetResolver}=await import('./vendor/mediapipe/vision_bundle.mjs');
      const files=await FilesetResolver.forVisionTasks(new URL('./vendor/mediapipe/wasm',self.location.href).href);
      const options={baseOptions:{modelAssetPath:new URL('./vendor/mediapipe/model/face_landmarker.task',self.location.href).href,delegate:'GPU'},runningMode:'VIDEO',numFaces:1,outputFaceBlendshapes:true,outputFacialTransformationMatrixes:true};
      try{model=await FaceLandmarker.createFromOptions(files,options);}
      catch{options.baseOptions.delegate='CPU';model=await FaceLandmarker.createFromOptions(files,options);}
      self.postMessage({type:'ready',delegate:options.baseOptions.delegate});
    }else if(data.type==='frame'){
      const result=model.detectForVideo(frame,data.time);
      self.postMessage({type:'result',result,frame,time:data.time,videoTime:data.videoTime},[frame]);frame=null;
    }
  }catch(error){self.postMessage({type:'error',message:error.message});}
  finally{frame?.close();}
};
