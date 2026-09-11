import * as ort from './vendor/onnxruntime/ort.wasm.min.mjs';
import {faceCropTransform} from './tongue-signal.js';

export async function createTongueModel(){
  ort.env.wasm.numThreads=1;
  ort.env.wasm.wasmPaths=new URL('./vendor/onnxruntime/',import.meta.url).href;
  const session=await ort.InferenceSession.create(new URL('./vendor/tongue/tongue_detector.onnx',import.meta.url).href,
    {executionProviders:['wasm'],graphOptimizationLevel:'all'});
  const canvas=new OffscreenCanvas(256,256),ctx=canvas.getContext('2d',{willReadFrequently:true});
  return {
    async detect(frame,landmarks){
      const matrix=faceCropTransform(landmarks,frame.width,frame.height);
      if(!matrix)return 0;
      ctx.resetTransform();ctx.fillStyle='#000';ctx.fillRect(0,0,256,256);
      ctx.setTransform(...matrix);ctx.drawImage(frame,0,0);ctx.resetTransform();
      const rgba=ctx.getImageData(0,0,256,256).data,input=new Float32Array(256*256*3);
      for(let i=0,j=0;i<rgba.length;i+=4){input[j++]=rgba[i]/255;input[j++]=rgba[i+1]/255;input[j++]=rgba[i+2]/255;}
      const tensor=new ort.Tensor('float32',input,[1,256,256,3]);
      try{
        const output=await session.run({[session.inputNames[0]]:tensor});
        const value=Number(output[session.outputNames[0]].data[0]);
        for(const result of Object.values(output))result.dispose();
        if(!Number.isFinite(value))throw new Error('Invalid tongue model output');
        return Math.min(1,Math.max(0,value));
      }finally{tensor.dispose();}
    },
    close:()=>session.release(),
  };
}
