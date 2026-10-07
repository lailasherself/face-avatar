// Safari's MediaPipe build avoids OffscreenCanvas and falls back to document.createElement('canvas'),
// which throws "Can't find variable: document" inside a worker. Route that fallback back to OffscreenCanvas.
self.document??={createElement:tag=>tag==='canvas'?new OffscreenCanvas(1,1):{},body:{appendChild(){}}};
let model;
self.onmessage=async({data})=>{
  let frame=data.frame;
  try{
    if(data.type==='init'){
      const {FaceLandmarker,FilesetResolver}=await import('./vendor/mediapipe/vision_bundle.mjs');
      const files=await FilesetResolver.forVisionTasks(new URL('./vendor/mediapipe/wasm',self.location.href).href);
      const options={baseOptions:{modelAssetPath:new URL('./vendor/mediapipe/model/face_landmarker.task',self.location.href).href,delegate:'GPU'},runningMode:'VIDEO',numFaces:data.maxFaces===2?2:1,outputFaceBlendshapes:true,outputFacialTransformationMatrixes:true};
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
