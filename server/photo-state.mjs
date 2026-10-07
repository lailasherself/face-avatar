import {createHash, randomBytes, timingSafeEqual} from 'node:crypto';

export const PHOTO_TTL=24*60*60*1000,MAX_IMAGE=700*1024,MAX_SESSIONS=256;
export const token=()=>randomBytes(32).toString('base64url');
export const hash=value=>createHash('sha256').update(value).digest('hex');
export const characters=Object.fromEntries(['orbit','cosmic','nebula','kudzu','clay','summer','glass'].map(id=>[id,{
  id,name:id[0].toUpperCase()+id.slice(1),portrait:`/assets/likeness-trials/thumbnails/${id==='orbit'?'orbit-image':id}.png`,
}]));
export class PhotoError extends Error {constructor(status,message){super(message);this.status=status;}}
const fail=(status,message)=>{throw new PhotoError(status,message);};
export function credential(value,expected){
  return typeof value==='string'&&/^[\w-]{43}$/.test(value)&&typeof expected==='string'&&expected.length===64&&
    timingSafeEqual(Buffer.from(hash(value)),Buffer.from(expected));
}
export function newRoom(id,owner){return {id,owner:hash(owner),operator:null,operatorAt:0,active:null,sessions:{}};}
function ready(room,now){return !!room.operator&&now-room.operatorAt<10000&&room.operator.ready===true&&room.operator.people===1&&room.operator.person!==null;}
function cancelActive(room,message){
  const session=room.sessions[room.active];
  if(session){session.state='error';session.message=message;}
  room.active=null;
}
function clean(room,now,remove){
  for(const [id,s] of Object.entries(room.sessions))if(now>=s.expires){delete room.sessions[id];if(s.image)remove.push(s.image);if(room.active===id)room.active=null;}
  const active=room.sessions[room.active];
  if(active&&(now-room.operatorAt>=10000||now-active.seen>15000||(active.state==='arming'?now-active.armedAt>10000:now>active.deadline+15000)))cancelActive(room,'Connection lost. Please try again.');
}
function publicState(room,s,now){
  const online=room.operator&&now-room.operatorAt<10000;
  const character=['arming','countdown','processing','done'].includes(s.state)?s.character:room.operator?.character;
  return {state:s.state,message:s.message,remaining:Math.max(0,((s.deadline||0)-now)/1000),expiresIn:Math.max(0,(s.expires-now)/1000),
    demo:false,retentionHours:24,ready:ready(room,now),busy:!!room.active,character:characters[character]||null,
    availability:!online?'offline':room.operator.people>1?'crowd':!room.operator.ready?'preparing':ready(room,now)?'ready':'no-person'};
}

// Pure room transition. The store commits metadata and image changes atomically.
export function transition(room,role,secret,action,data={},now=Date.now()){
  const remove=[],result={remove};
  if(role==='operator'){
    if(!credential(secret,room.owner))fail(403,'Invalid camera session');
  }else if(!['create','availability'].includes(action)&&(!/^[\w-]{43}$/.test(secret||'')||!room.sessions[hash(secret)]))fail(410,'This private photo session expired. Scan again.');
  clean(room,now,remove);
  if(action==='availability'){result.response={online:!!room.operator&&now-room.operatorAt<10000,ready:ready(room,now),busy:!!room.active};return result;}
  if(role==='operator'){
    if(!/^[\w-]{43}$/.test(data.instance||''))fail(400,'Missing camera identity');
    if(room.instance&&room.instance!==data.instance&&now-room.operatorAt<10000)fail(409,'The camera station is already open in another tab');
    if(action==='heartbeat'){
      if(typeof data.ready!=='boolean'||!Number.isInteger(data.people)||data.people<0||data.people>100||!characters[data.character]||
        !(data.person===null||typeof data.person==='string'&&data.person.length<=160))fail(400,'Invalid camera status');
      room.instance=data.instance;room.operator={ready:data.ready,people:data.people,person:data.person,character:data.character};room.operatorAt=now;
      const s=room.sessions[room.active];
      if(s){
        if(!ready(room,now)||s.person!==data.person||s.character!==data.character)cancelActive(room,'We lost your position. Face the camera and try again.');
        else {
          // Start the five seconds only after the camera acknowledges the request.
          if(s.state==='arming'){s.state='countdown';s.deadline=now+5000;}
          else if(now>=s.deadline)s.state='processing';
          result.response={state:s.state,job:s.job,remaining:Math.max(0,(s.deadline-now)/1000),demo:false};
        }
      }
      result.response??={state:'idle',demo:false};
    }else if(action==='complete'||action==='fail'){
      const s=room.sessions[room.active];
      if(!s||s.job!==data.job)fail(409,'Capture was cancelled');
      if(action==='fail'){cancelActive(room,'Photo could not be made. Please try again.');result.response={ok:true};}
      else{
        if(s.state!=='processing'||!ready(room,now))fail(409,'Capture is no longer valid');
        if(typeof data.imagePath!=='string')fail(400,'Missing photo');
        result.writeImage=data.imagePath;s.state='done';s.message='';s.expires=now+PHOTO_TTL;s.image=data.imagePath;result.imageExpiry=s.expires;
        room.active=null;result.response={saved:true};
      }
    }else fail(404,'Unknown camera action');
    return result;
  }
  let id,s;
  if(action==='create'){
    if(Object.keys(room.sessions).length>=MAX_SESSIONS)fail(429,'This camera is busy. Please try again later.');
    const visitor=token();id=hash(visitor);s={state:'idle',message:'',seen:now,expires:now+600000,lastStart:0};
    room.sessions[id]=s;result.response={...publicState(room,s,now),token:visitor};return result;
  }
  id=hash(secret);s=room.sessions[id];if(!s)fail(410,'Your private photo expired. Scan again.');
  s.seen=now;
  if(action==='start'){
    if(room.active&&room.active!==id)fail(409,'Someone is taking a photo. Please wait.');
    if(room.active!==id){
      if(!ready(room,now))fail(409,'Face the camera. One person at a time.');
      if(now-s.lastStart<3000)fail(429,'Please wait a moment before retaking.');
      if(s.image)remove.push(s.image);
      Object.assign(s,{state:'arming',armedAt:now,deadline:null,expires:now+600000,message:'',person:room.operator.person,character:room.operator.character,job:token(),lastStart:now,image:false});
      room.active=id;
    }
  }else if(action==='cancel'){
    if(room.active===id)room.active=null;
    if(s.image)remove.push(s.image);Object.assign(s,{state:'idle',expires:now+600000,message:'',image:false});
  }else if(action==='delete'){
    if(room.active===id)room.active=null;
    delete room.sessions[id];if(s.image)remove.push(s.image);result.response={deleted:true};return result;
  }else if(action==='image'){
    if(s.state!=='done'||!s.image)fail(404,'Your photo is not ready');result.readImage=s.image;
  }else if(action!=='status')fail(404,'Unknown photo action');
  result.response=publicState(room,s,now);return result;
}
