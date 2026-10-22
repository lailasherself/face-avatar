import {isolatePhotoSubject,subjectBounds} from './photo-cutout.js';

let artworkPromise;
const keepsakeMarker=new TextEncoder().encode('FACE-AVATAR-SHIP-V1');

export async function isShipKeepsake(file){
  const header=new Uint8Array(await file.slice(0,6+keepsakeMarker.length).arrayBuffer());
  return header[0]===255&&header[1]===216&&header[2]===255&&header[3]===254&&
    header[4]===0&&header[5]===keepsakeMarker.length+2&&keepsakeMarker.every((value,index)=>header[index+6]===value);
}

export async function encodeShipKeepsake(canvas,quality=.93){
  const jpeg=await new Promise((resolve,reject)=>canvas.toBlob(result=>result?resolve(result):reject(new Error('Photo could not be saved.')),'image/jpeg',quality));
  return new Blob([jpeg.slice(0,2),new Uint8Array([255,254,0,keepsakeMarker.length+2]),keepsakeMarker,jpeg.slice(2)],{type:'image/jpeg'});
}

function loadArtwork(){
  if(!artworkPromise){
    artworkPromise=(async()=>{
      const image=new Image();image.src='/assets/photo-vinyl/ship.png';
      const [response]=await Promise.all([fetch('/assets/photo-vinyl/dome.json',{signal:AbortSignal.timeout(8000)}),image.decode()]);
      if(!response.ok)throw new Error('The spaceship frame could not be loaded.');
      const dome=await response.json();
      return {image,dome:{...dome,path:new Path2D(dome.path)}};
    })().catch(error=>{artworkPromise=null;throw error;});
  }
  return artworkPromise;
}

export function photoContentBounds(image){
  const scale=image.width/1200;
  const source={x:0,y:68*scale,width:image.width,height:image.height-104*scale};
  if(source.height<=0)throw new Error('Photo dimensions are invalid.');
  const scan=document.createElement('canvas');scan.width=240;scan.height=Math.max(1,Math.round(source.height/source.width*240));
  const context=scan.getContext('2d',{willReadFrequently:true});
  context.drawImage(image,source.x,source.y,source.width,source.height,0,0,scan.width,scan.height);
  const pixels=context.getImageData(0,0,scan.width,scan.height).data;
  const columns=new Uint32Array(scan.width),rows=new Uint32Array(scan.height);
  for(let row=0;row<scan.height;row++)for(let column=0;column<scan.width;column++){
    const offset=(row*scan.width+column)*4;
    if(Math.max(pixels[offset],pixels[offset+1],pixels[offset+2])>28){columns[column]++;rows[row]++;}
  }
  const left=columns.findIndex(count=>count>Math.max(2,scan.height*.015));
  const right=columns.findLastIndex(count=>count>Math.max(2,scan.height*.015));
  const top=rows.findIndex(count=>count>Math.max(2,scan.width*.015));
  const bottom=rows.findLastIndex(count=>count>Math.max(2,scan.width*.015));
  if(left<0||right-left<24||bottom-top<24)return source;
  const horizontal=source.width/scan.width,vertical=source.height/scan.height;
  return {x:Math.max(0,left-2)*horizontal,y:source.y+Math.max(0,top-2)*vertical,
    width:Math.min(scan.width-left,right-left+4)*horizontal,height:Math.min(scan.height-top,bottom-top+4)*vertical};
}

export async function createShipKeepsake(file,name){
  if(await isShipKeepsake(file))return file;
  const image=await createImageBitmap(file);
  let cutout;
  try{
    const source=photoContentBounds(image);
    cutout=await isolatePhotoSubject(image,source);
    return await renderShipKeepsake(cutout,name);
  }catch(error){error.name='PhotoCompositionError';throw error;}
  finally{cutout?.close();image.close();}
}

export async function renderShipKeepsake(cutout,name){
  return encodeShipKeepsake(await renderShipCanvas(cutout,name));
}

export async function renderShipCanvas(cutout,name,{demo=false,headBounds=null}={}){
    const artwork=await loadArtwork(),source=subjectBounds(cutout);
    const canvas=document.createElement('canvas');canvas.width=1200;canvas.height=1080;
    const context=canvas.getContext('2d');
    context.fillStyle='#0a121e';context.fillRect(0,0,canvas.width,canvas.height);
    context.save();context.scale(1200/1120,1200/1120);context.translate(0,-193);
    const dome=artwork.dome.bounds;
    const scale=headBounds?Math.min(dome.width*.48/headBounds.width,dome.height*.52/headBounds.height):Math.min(dome.width*.62/source.width,dome.height*.84/(source.height*.72));
    const subjectWidth=source.width*scale,subjectHeight=source.height*scale;
    const subjectX=headBounds?dome.x+dome.width/2-(headBounds.x+headBounds.width/2-source.x)*scale:dome.x+(dome.width-subjectWidth)/2;
    const subjectY=dome.y+30-(headBounds?headBounds.y-source.y:0)*scale;
    context.save();context.clip(artwork.dome.path);
    const interior=context.createRadialGradient(dome.x+dome.width*.5,dome.y+dome.height*.4,10,dome.x+dome.width*.5,dome.y+dome.height*.4,dome.width*.65);
    interior.addColorStop(0,'#294d5b');interior.addColorStop(1,'#07131f');
    context.fillStyle=interior;context.fillRect(dome.x,dome.y,dome.width,dome.height);
    context.drawImage(cutout,source.x,source.y,source.width,source.height,subjectX,subjectY,subjectWidth,subjectHeight);
    context.restore();
    context.drawImage(artwork.image,0,0);
    context.restore();
    context.fillStyle='#0a121e';context.fillRect(0,964,1200,116);
    context.fillStyle='#9fd388';context.font='bold 24px Arial';context.fillText('YOU’RE THE ALIEN.',36,1008);
    context.fillStyle='#fff';context.font='20px Arial';context.fillText(`You as ${name||'an alien'} · Downtown Atlanta`,36,1048);
    context.textAlign='right';context.fillStyle='#b5c6cf';context.font='16px Arial';context.fillText('LAILA JHANÉ & IVAN REYES',1164,1048);
    if(demo){context.textAlign='left';context.fillStyle='#9fd388';context.font='bold 24px Arial';context.fillText('SAMPLE · NO VISITOR CAPTURED',36,40);}
    return canvas;
}
