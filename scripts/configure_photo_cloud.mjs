// Explicit provisioning for this installation only. Secrets never enter Git or stdout.
import {execFileSync} from 'node:child_process';
import {randomBytes} from 'node:crypto';
import {writeFileSync} from 'node:fs';
import {newRoom} from '../server/photo-state.mjs';
import {supabase,STATION} from '../server/photo-store.mjs';

process.on('uncaughtException',()=>{console.error('Cloud provisioning failed. Inspect project setup without printing secrets.');process.exit(1);});

const ref='ysxjztjiajszyvxfzfhn';
const url=`https://${ref}.supabase.co`;
const run=(cmd,args,options={})=>execFileSync(cmd,args,{encoding:'utf8',stdio:['pipe','pipe','pipe'],...options});
const keys=JSON.parse(run('supabase',['projects','api-keys','--project-ref',ref,'--output','json']));
process.env.SUPABASE_URL=url;
process.env.SUPABASE_SERVICE_ROLE_KEY=keys.find(k=>k.name==='service_role').api_key;
function secret(name){
  try{return run('security',['find-generic-password','-a','face-avatar','-s',name,'-w']).trim();}
  catch{
    const value=randomBytes(32).toString('base64url');
    run('security',['add-generic-password','-a','face-avatar','-s',name,'-w',value]);return value;
  }
}
const owner=secret('face-avatar.photo-owner');
const cleanup=secret('face-avatar.photo-cleanup');
const existing=await supabase(`/rest/v1/photo_stations?id=eq.${STATION}&select=id`);
if(!existing.length)await supabase('/rest/v1/photo_stations',{method:'POST',body:{id:STATION,state:newRoom(STATION,owner)}});
run('supabase',['secrets','set',`PHOTO_CLEANUP_SECRET=${cleanup}`,'--project-ref',ref]);
run('supabase',['functions','deploy','photo-cleanup','--project-ref',ref,'--no-verify-jwt','--use-api']);
const sql=`
create extension if not exists pg_cron;
create extension if not exists pg_net with schema extensions;
do $$ begin
  if exists(select 1 from vault.secrets where name='photo_cleanup_secret') then
    perform vault.update_secret((select id from vault.secrets where name='photo_cleanup_secret'),'${cleanup}');
  else perform vault.create_secret('${cleanup}','photo_cleanup_secret'); end if;
end $$;
select cron.schedule('photo-storage-cleanup','* * * * *',$job$
  select net.http_post(url:='${url}/functions/v1/photo-cleanup',
    headers:=jsonb_build_object('Content-Type','application/json','x-cleanup-token',
      (select decrypted_secret from vault.decrypted_secrets where name='photo_cleanup_secret')),
    body:='{}'::jsonb,timeout_milliseconds:=10000);
$job$);
`;
run('supabase',['db','query','--linked',sql,'--output','json']);
for(const [name,value] of Object.entries({SUPABASE_URL:url,SUPABASE_SERVICE_ROLE_KEY:process.env.SUPABASE_SERVICE_ROLE_KEY})){
  run('npx',['--yes','vercel@latest','env','add',name,'production','--yes','--sensitive','--force','--scope','lailasherselfs-projects'],{input:value,cwd:'.context/release-photos'});
}
const stationURL=`https://face-avatar.vercel.app/cockpit.html?assets=3dai&view=ship&character=orbit#photo-owner=${owner}`;
writeFileSync('.context/photo-station-launch.html',`<!doctype html><meta name="referrer" content="no-referrer"><title>Open camera station</title><a href="${stationURL}">Open private camera station</a>`,{mode:0o600});
console.log('Provisioned private station, cleanup schedule, and production environment. Private launch link: .context/photo-station-launch.html');
