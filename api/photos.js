const state=import('../server/photo-state.mjs');
const service=import('../server/photo-store.mjs');

async function readBody(req,max){
  if(req.body!==undefined){
    const bytes=Buffer.isBuffer(req.body)?req.body:Buffer.from(typeof req.body==='string'?req.body:JSON.stringify(req.body));
    if(bytes.length>max)throw Object.assign(new Error('Request too large'),{status:413});return bytes;
  }
  const chunks=[];let size=0;
  for await(const chunk of req){size+=chunk.length;if(size>max)throw Object.assign(new Error('Request too large'),{status:413});chunks.push(chunk);}
  return Buffer.concat(chunks);
}
module.exports=async(req,res)=>{
  res.setHeader('Cache-Control','private, no-store');res.setHeader('Referrer-Policy','no-referrer');res.setHeader('X-Content-Type-Options','nosniff');
  try{
    const {PhotoError,MAX_IMAGE}=await state;
    const {configured,perform,provision,rateLimit,STATION}=await service;
    const origin=(process.env.VERCEL?'https://':'http://')+req.headers.host;
    if((req.headers.origin&&req.headers.origin!==origin)||(req.headers['sec-fetch-site']&&!['none','same-origin'].includes(req.headers['sec-fetch-site'])))throw new PhotoError(403,'Open the photo page first');
    const url=new URL(req.url,origin),action=url.searchParams.get('action');
    const read=['config','availability','status','image'].includes(action);
    if(req.method!==(read?'GET':'POST'))throw new PhotoError(405,'Invalid method');
    if(action==='config')return res.status(200).json({enabled:configured(),mode:'cloud',testStations:true,demo:false,tracking:'webcam',network:'public',room:STATION,phoneURL:`${origin}/photo.html?station=${STATION}`,retentionHours:24});
    if(!configured())throw new PhotoError(503,'Photo station is not configured');
    if(!read&&req.headers['x-face-avatar']!=='photo')throw new PhotoError(403,'Missing photo header');
    if(!['provision','availability','heartbeat','complete','fail','create','status','start','cancel','delete','image'].includes(action))throw new PhotoError(404,'Unknown action');
    const role=['heartbeat','complete','fail'].includes(action)?'operator':'visitor';
    const room=url.searchParams.get('room'),secret=(req.headers.authorization||'').replace(/^Bearer /,'');
    const ip=req.headers['x-forwarded-for']?.split(',')[0]?.trim()||req.socket?.remoteAddress||'unknown';
    if(action==='provision'){
      const station=await provision(secret,ip);
      return res.status(200).json({...station,phoneURL:`${origin}/photo.html?station=${station.room}`});
    }
    if(action==='create'){
      await rateLimit('visitor:'+room+':'+ip,20,600);
      await rateLimit('visitors:'+room,120,600);
    }
    let data={},image;
    if(action==='complete'){
      image=await readBody(req,MAX_IMAGE);
      if(req.headers['content-type']!=='image/jpeg'||image.length<5||image[0]!==255||image[1]!==216||image.at(-2)!==255||image.at(-1)!==217)throw new PhotoError(400,'Invalid photo');
      data={job:req.headers['x-photo-job'],instance:req.headers['x-photo-instance']};
    }else if(!read){
      const bytes=await readBody(req,2048);
      try{data=bytes.length?JSON.parse(bytes):{};}catch{throw new PhotoError(400,'Invalid request');}
      if(!data||typeof data!=='object'||Array.isArray(data))throw new PhotoError(400,'Invalid request');
    }
    const result=await perform(room,role,secret,action,data,image);
    if(Buffer.isBuffer(result)){
      res.setHeader('Content-Type','image/jpeg');res.setHeader('Content-Disposition','attachment; filename="ATL-Downtown.jpg"');return res.status(200).send(result);
    }
    res.status(200).json(result);
  }catch(error){res.status(error.status||503).json({error:error.status?error.message:'Photo service temporarily unavailable'});}
};
