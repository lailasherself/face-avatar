import * as THREE from 'three';

export function brandAlienPhoto(frame,name){
  const canvas=document.createElement('canvas');canvas.width=1200;
  const height=Math.round(frame.height/frame.width*1200);canvas.height=height+104;
  const ctx=canvas.getContext('2d');ctx.fillStyle='#d8f660';ctx.fillRect(0,0,1200,68);
  ctx.fillStyle='#17231d';ctx.font='bold 26px Arial';ctx.fillText('ATL DOWNTOWN',28,44);
  ctx.textAlign='right';ctx.fillText(`YOU AS ${name.toUpperCase()}`,1172,44);
  ctx.drawImage(frame,0,68,1200,height);ctx.fillStyle='#111c1b';ctx.fillRect(0,height+68,1200,36);
  ctx.fillStyle='#dce8de';ctx.font='16px Arial';ctx.fillText('ONLY IN ATLANTA',1172,height+92);return canvas;
}

// A separate render target leaves the installation size, framing and vinyl intact.
export function captureAlien(renderer,scene,camera){
  const width=600,height=780,target=new THREE.WebGLRenderTarget(width,height);
  target.texture.colorSpace=THREE.SRGBColorSpace;
  const photoCamera=camera.clone();photoCamera.aspect=width/height;photoCamera.clearViewOffset();photoCamera.updateProjectionMatrix();
  const previous=renderer.getRenderTarget(),background=scene.background,alpha=renderer.getClearAlpha();
  const clear=renderer.getClearColor(new THREE.Color());
  try{
    scene.background=null;renderer.setClearColor(0x000000,0);renderer.setRenderTarget(target);
    renderer.render(scene,photoCamera);
    const pixels=new Uint8Array(width*height*4);renderer.readRenderTargetPixels(target,0,0,width,height,pixels);
    const canvas=document.createElement('canvas');canvas.width=width;canvas.height=height;
    const ctx=canvas.getContext('2d'),data=ctx.createImageData(width,height);
    for(let y=0;y<height;y++)data.data.set(pixels.subarray((height-1-y)*width*4,(height-y)*width*4),y*width*4);
    ctx.putImageData(data,0,0);return canvas;
  }finally{
    scene.background=background;renderer.setRenderTarget(previous);renderer.setClearColor(clear,alpha);target.dispose();
  }
}
