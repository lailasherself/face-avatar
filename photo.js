const $=id=>document.getElementById(id);
const room=new URLSearchParams(location.search).get('station');
const cloud=!!room;
const tokenKey=cloud?`alien-photo-token:${room}`:'alien-photo-token';
let token=sessionStorage.getItem(tokenKey),state=null,blob=null,objectURL=null;
if(cloud)$('privacy-notice').textContent='By tapping Take my photo, you agree to capture and private storage in Supabase for 24 hours. You can delete it sooner. Nothing is posted automatically.';
let pending=false,polling=false,connected=false,remaining=0,received=0,lastView='';
const characterCopy={
  orbit:{line:'A new friend. A very Atlanta encounter.',accent:'#e4bcdf'},
  cosmic:{line:'One small pose. One cosmic encounter.',accent:'#d8f660'},
  nebula:{line:'A moment from another world.',accent:'#a3e2e6'},
  kudzu:{line:'A little wild. A little otherworldly.',accent:'#c5e69e'},
  clay:{line:'A down-to-earth encounter.',accent:'#efbbad'},
  summer:{line:'Take a little sunshine with you.',accent:'#f4d36d'},
  glass:{line:'A moment worth keeping.',accent:'#b4e5ed'},
};

async function api(action){
  const read=['status','image'].includes(action);
  const endpoint=cloud?`/api/photos?action=${action}&room=${encodeURIComponent(room||'')}`:`/api/photo/${action}`;
  const secret=action==='create'?null:token;
  const response=await fetch(endpoint,{method:read?'GET':'POST',cache:'no-store',
    headers:{'X-Face-Avatar':'photo',...(secret?{Authorization:`Bearer ${secret}`}:{})},signal:AbortSignal.timeout(8000)});
  if(!response.ok){const data=await response.json();const error=new Error(data.error||'Connection interrupted.');error.status=response.status;throw error;}
  return action==='image'?response.blob():response.json();
}
function message(text=''){$('message').textContent=text;$('message').hidden=!text;}
function releaseImage(){if(objectURL)URL.revokeObjectURL(objectURL);objectURL=null;blob=null;$('preview').removeAttribute('src');$('save').removeAttribute('href');}
function render(data){
  state=data;remaining=data.remaining;received=performance.now();connected=true;
  $('demo').hidden=!data.demo;
  const character=data.character,copy=characterCopy[character?.id];
  if(character){
    if($('portrait').getAttribute('src')!==character.portrait)$('portrait').src=character.portrait;
    $('portrait').alt=`${character.name}, your alien at the window`;
    $('portrait-label').textContent=`WITH ${character.name.toUpperCase()} IN ATLANTA`;
    $('welcome-title').textContent=`You as ${character.name}`;
    $('character-line').textContent=copy?.line||'Your moment at the window.';
    $('countdown-title').textContent=`${character.name.toUpperCase()} IS READY`;
    $('look-at').textContent='Look at the camera.';
    $('result-title').textContent=`You as ${character.name}`;
    document.documentElement.style.setProperty('--character-accent',copy?.accent||'#d8f660');
  }
  const view=data.state==='countdown'?'countdown':data.state==='processing'?'processing':data.state==='done'?'result':'welcome';
  for(const id of ['welcome','countdown','processing','result'])$(id).hidden=id!==view;
  const availability={offline:'The window is offline. Please try again shortly.',preparing:'The window camera is getting ready...',crowd:'One person at a time. Leave a little space around you.',ready:'Ready when you are. You will have 5 seconds to pose.','no-person':'Stand in front of the window so the camera can see you.'};
  $('availability').textContent=data.busy?'Someone is taking a photo. Please wait.':availability[data.availability]||availability['no-person'];
  $('take').disabled=pending||!data.ready||data.busy;
  $('retake').disabled=pending;
  $('reconnect').hidden=true;
  $('expiry').textContent=data.expiresIn>3600?`Private preview expires in ${Math.ceil(data.expiresIn/3600)} hours.`:`Preview expires in ${Math.max(1,Math.ceil(data.expiresIn/60))} min.`;
  if(data.state==='error')message(data.message);
  if(view!==lastView){
    if(view==='countdown')navigator.vibrate?.(80);
    lastView=view;
  }
  if(view!=='result'&&blob)releaseImage();
}
async function loadResult(){
  if(blob)return;
  const session=token,fileBlob=await api('image');
  if(token!==session||state?.state!=='done')return;
  blob=fileBlob;objectURL=URL.createObjectURL(blob);
  $('preview').src=objectURL;$('save').href=objectURL;
  const file=new File([blob],'ATL-Downtown.jpg',{type:'image/jpeg'});
  $('share').hidden=!(navigator.canShare?.({files:[file]}));
}
async function connect(){
  if(pending)return;pending=true;
  try{
    message();
    let data;
    if(token){try{data=await api('status');}catch(e){if(e.status!==410)throw e;token=null;sessionStorage.removeItem(tokenKey);}}
    if(!token){data=await api('create');token=data.token;sessionStorage.setItem(tokenKey,token);}
    render(data);if(data.state==='done')await loadResult();
  }catch(error){offline(error);}finally{pending=false;if(state&&connected)render(state);}
}
function offline(error){
  connected=false;$('take').disabled=true;$('reconnect').hidden=false;
  message(error.status===410?'Your private photo expired. Reconnect to start again.':error.status===429?error.message:'Connection interrupted. Reconnect before taking another photo.');
  if(error.status===410){token=null;sessionStorage.removeItem(tokenKey);releaseImage();}
  if(lastView==='countdown'||lastView==='processing'){$(lastView).hidden=true;$('welcome').hidden=false;lastView='welcome';}
}
async function command(action){
  if(pending)return;pending=true;$('take').disabled=true;$('retake').disabled=true;
  try{message();const data=await api(action);render(data);if(data.state==='done')await loadResult();}
  catch(error){message(error.message);if(!error.status||error.status===410)offline(error);}
  finally{pending=false;if(state&&connected)render(state);}
}
$('take').onclick=()=>command('start');
$('cancel').onclick=$('cancel-processing').onclick=()=>command('cancel');
$('retake').onclick=()=>command('cancel');
$('reconnect').onclick=connect;
$('delete').onclick=async()=>{
  if(pending)return;
  pending=true;
  try{await api('delete');token=null;sessionStorage.removeItem(tokenKey);releaseImage();pending=false;await connect();message('Your photo has been deleted.');}
  catch(e){message(e.message);}finally{pending=false;}
};
$('share').onclick=async()=>{
  if(!blob)return;
  try{await navigator.share({files:[new File([blob],'ATL-Downtown.jpg',{type:'image/jpeg'})],title:`Me as ${state?.character?.name||'an alien'} in Atlanta`,text:'My alien look in Downtown Atlanta. Only in Atlanta.'});}
  catch(e){if(e.name!=='AbortError')message('Sharing is unavailable here. Use Save photo instead.');}
};
setInterval(async()=>{
  if(polling||pending||!token||document.hidden||!connected)return;
  polling=true;
  try{const data=await api('status');if(!pending){render(data);if(data.state==='done')await loadResult();}}
  catch(e){offline(e);}finally{polling=false;}
},cloud?1000:400);
setInterval(()=>{if(state?.state==='countdown'&&connected)$('number').textContent=String(Math.max(1,Math.ceil(remaining-(performance.now()-received)/1000)));},100);
addEventListener('pagehide',()=>{
  if(token&&['countdown','processing'].includes(state?.state))fetch(cloud?`/api/photos?action=cancel&room=${encodeURIComponent(room)}`:'/api/photo/cancel',{method:'POST',headers:{'X-Face-Avatar':'photo',Authorization:`Bearer ${token}`},keepalive:true}).catch(()=>{});
});
document.addEventListener('visibilitychange',()=>{if(!document.hidden)connect();});
connect();
