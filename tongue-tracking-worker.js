import {createTongueModel} from './tongue-model.js';
let model;
self.onmessage=async({data})=>{
  try{
    if(data.type==='init'){model=await createTongueModel();self.postMessage({type:'ready'});}
    else if(data.type==='frame'){
      if(!model)throw new Error('Tongue tracker is not initialized');
      const start=performance.now();
      const score=await model.detect(data.frame,data.landmarks);
      self.postMessage({type:'result',time:data.time,score,inferenceMs:performance.now()-start,cropAgeMs:data.cropAgeMs??0});
    }
  }catch(error){self.postMessage({type:'error',message:error.message});}
  finally{data.frame?.close();}
};
