self.document??={createElement:tag=>tag==='canvas'?new OffscreenCanvas(1,1):{},body:{appendChild(){}}};
let segmenter;
self.onmessage=async({data})=>{
  try{
    if(data.type==='init'){
      const {FilesetResolver,ImageSegmenter}=await import('./vendor/mediapipe/vision_bundle.mjs');
      const vision=await FilesetResolver.forVisionTasks(new URL('./vendor/mediapipe/wasm',self.location.href).href);
      segmenter=await ImageSegmenter.createFromOptions(vision,{
        baseOptions:{modelAssetPath:new URL('./vendor/mediapipe/model/selfie_segmenter.tflite',self.location.href).href,delegate:'CPU'},
        runningMode:'IMAGE',outputConfidenceMasks:true,outputCategoryMask:false,
      });
      self.postMessage({type:'ready'});return;
    }
    const frame=data.frame,canvas=new OffscreenCanvas(frame.width,frame.height),ctx=canvas.getContext('2d');
    try{
      ctx.drawImage(frame,0,0);
      segmenter.segment(frame,result=>{
        const mask=result.confidenceMasks[0],confidence=mask.getAsFloat32Array();
        const matte=new OffscreenCanvas(mask.width,mask.height),mctx=matte.getContext('2d');
        const pixels=mctx.createImageData(mask.width,mask.height);
        let foreground=0;
        for(let i=0;i<confidence.length;i++){
          pixels.data[i*4+3]=Math.round(Math.max(0,Math.min(1,(confidence[i]-.35)/.3))*255);
          if(confidence[i]>.6)foreground++;
        }
        if(foreground<confidence.length*.01)throw new Error('No visitor cutout found');
        if(data.cleanEdges){
          const alpha=new Uint8ClampedArray(confidence.length);
          for(let row=0;row<mask.height;row++)for(let column=0;column<mask.width;column++){
            let minimum=1;
            for(let offsetY=-1;offsetY<=1;offsetY++)for(let offsetX=-1;offsetX<=1;offsetX++){
              const neighborX=Math.max(0,Math.min(mask.width-1,column+offsetX)),neighborY=Math.max(0,Math.min(mask.height-1,row+offsetY));
              minimum=Math.min(minimum,confidence[neighborY*mask.width+neighborX]);
            }
            alpha[row*mask.width+column]=Math.round(Math.max(0,Math.min(1,(minimum-.55)/.3))*255);
          }
          for(let index=0;index<alpha.length;index++)pixels.data[index*4+3]=alpha[index];
        }
        mctx.putImageData(pixels,0,0);ctx.globalCompositeOperation='destination-in';
        ctx.drawImage(matte,0,0,canvas.width,canvas.height);
      });
      const cutout=canvas.transferToImageBitmap();self.postMessage({type:'cutout',frame:cutout,id:data.id},[cutout]);
    }finally{frame.close();}
  }catch(error){self.postMessage({type:'error',message:error.message,id:data.id});}
};
