import {PhotoError,transition,hash,token} from './photo-state.mjs';

export const STATION='atl-downtown';
export function configured(){return !!(process.env.SUPABASE_URL&&process.env.SUPABASE_SERVICE_ROLE_KEY);}
export async function supabase(path,{method='GET',body,raw=false}={}){
  const key=process.env.SUPABASE_SERVICE_ROLE_KEY;
  if(!configured())throw new PhotoError(503,'Photo station is not configured');
  const response=await fetch(`${process.env.SUPABASE_URL}${path}`,{
    method,headers:{apikey:key,Authorization:`Bearer ${key}`,
      ...(body?{'Content-Type':Buffer.isBuffer(body)?'image/jpeg':'application/json'}:{})},
    body:body?(Buffer.isBuffer(body)?body:JSON.stringify(body)):undefined,
    signal:AbortSignal.timeout(10000),
  });
  if(!response.ok)throw new PhotoError(503,'Photo storage is temporarily unavailable');
  if(raw)return Buffer.from(await response.arrayBuffer());
  const text=await response.text();return text?JSON.parse(text):null;
}
export async function rateLimit(key,limit,seconds){
  const count=await supabase('/rest/v1/rpc/photo_rate_limit',{method:'POST',body:{rate_key:hash(key),seconds}});
  if(count>limit)throw new PhotoError(429,'Please wait before trying again');
}
async function removeObjects(paths){
  if(!paths.length)return;
  await supabase('/storage/v1/object/alien-photos',{method:'DELETE',body:{prefixes:paths}});
  for(const path of paths)await supabase(`/rest/v1/photo_objects?path=eq.${encodeURIComponent(path)}`,{method:'DELETE'});
}
export async function perform(id,role,secret,action,data={},image){
  if(id!==STATION)throw new PhotoError(404,'Unknown photo station');
  let staged=null;
  // A staged upload is never deleted on an ambiguous commit response. Its
  // registry deadline lets cleanup reclaim it without racing a successful save.
  for(let attempt=0;attempt<10;attempt++){
      const [record]=await supabase(`/rest/v1/photo_stations?id=eq.${STATION}&select=version,state`);
      if(!record)throw new PhotoError(503,'Photo station is not configured');
      const imagePath=staged||`${STATION}/${token()}.jpg`;
      const result=transition(record.state,role,secret,action,{...data,imagePath},Date.now());
      if(result.writeImage&&!staged){
        if(!Buffer.isBuffer(image))throw new PhotoError(400,'Missing photo');
        staged=imagePath;
        // Register before upload so interrupted requests are reclaimed by cleanup.
        await supabase('/rest/v1/photo_objects',{method:'POST',body:{path:staged}});
        await supabase(`/storage/v1/object/alien-photos/${staged}`,{method:'POST',body:image});
      }
      const committed=await supabase('/rest/v1/rpc/photo_commit',{method:'POST',body:{
        station_id:id,expected_version:record.version,next_state:record.state,
        remove_paths:result.remove,live_path:result.writeImage||null,
        live_expiry:result.imageExpiry?new Date(result.imageExpiry).toISOString():null,
      }});
      if(!committed){await new Promise(r=>setTimeout(r,20+Math.random()*60));continue;}
      staged=null;
      // The DB has already revoked access; failed physical deletion is retried by cron.
      await removeObjects(result.remove).catch(()=>{});
      if(result.readImage)return supabase(`/storage/v1/object/alien-photos/${result.readImage}`,{raw:true});
      return result.response;
  }
  throw new PhotoError(409,'The camera is busy. Please try again');
}
