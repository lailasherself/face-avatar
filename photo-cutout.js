export async function isolatePhotoSubject(image,source){
  const frame=await createImageBitmap(image,Math.round(source.x),Math.round(source.y),Math.round(source.width),Math.round(source.height));
  return new Promise((resolve,reject)=>{
    let worker;
    const finish=error=>{clearTimeout(timer);worker?.terminate();frame.close();if(error)reject(error);};
    const timer=setTimeout(()=>finish(new Error('Preparing your spaceship photo took too long. Please reconnect to try again.')),30000);
    try{
      worker=new Worker('/photo-segment-worker.js');
      worker.onerror=()=>finish(new Error('The photo background could not be removed. Please reconnect to try again.'));
      worker.onmessage=({data})=>{
        if(data.type==='ready')worker.postMessage({type:'segment',frame,id:'keepsake',cleanEdges:true},[frame]);
        else if(data.type==='cutout'){finish();resolve(data.frame);}
        else if(data.type==='error')finish(new Error('We could not isolate you in this photo. Please take another with your head and shoulders visible.'));
      };
      worker.postMessage({type:'init'});
    }catch(error){finish(error);}
  });
}

export function subjectBounds(image){
  const canvas=document.createElement('canvas');canvas.width=image.width;canvas.height=image.height;
  const context=canvas.getContext('2d',{willReadFrequently:true});context.drawImage(image,0,0);
  const pixels=context.getImageData(0,0,canvas.width,canvas.height).data;
  let left=canvas.width,right=-1,top=canvas.height,bottom=-1;
  for(let row=0;row<canvas.height;row++)for(let column=0;column<canvas.width;column++){
    if(pixels[(row*canvas.width+column)*4+3]<160)continue;
    left=Math.min(left,column);right=Math.max(right,column);top=Math.min(top,row);bottom=Math.max(bottom,row);
  }
  if(right-left<20||bottom-top<20)throw new Error('No clear person was found. Please take another photo.');
  return {x:left,y:top,width:right-left+1,height:bottom-top+1};
}
