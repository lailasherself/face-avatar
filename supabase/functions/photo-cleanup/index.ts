import {createClient} from 'npm:@supabase/supabase-js@2';

Deno.serve(async request=>{
  const expected=Deno.env.get('PHOTO_CLEANUP_SECRET');
  if(request.method!=='POST'||!expected||request.headers.get('x-cleanup-token')!==expected)return new Response('Forbidden',{status:403});
  const client=createClient(Deno.env.get('SUPABASE_URL')!,Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!);
  const now=new Date().toISOString();
  const {data,error}=await client.from('photo_objects').select('path').lte('expires_at',now).limit(1000);
  if(error)return new Response('Cleanup query failed',{status:503});
  const paths=data.map(row=>row.path);
  if(paths.length){
    const removed=await client.storage.from('alien-photos').remove(paths);
    if(removed.error)return new Response('Storage cleanup failed',{status:503});
    const deleted=await client.from('photo_objects').delete().in('path',paths).lte('expires_at',now);
    if(deleted.error)return new Response('Cleanup registry failed',{status:503});
  }
  await client.from('photo_rate_limits').delete().lt('expires_at',new Date(Date.now()-86400000).toISOString());
  // Temporary cameras expire after 48 hours without a heartbeat. Their photos
  // have already expired after 24 hours; the permanent installation has no expiry.
  const stations=await client.from('photo_stations').delete().lte('expires_at',now);
  if(stations.error)return new Response('Station cleanup failed',{status:503});
  return Response.json({removed:paths.length});
});
