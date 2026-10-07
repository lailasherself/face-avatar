import assert from 'node:assert/strict';
import {test} from 'node:test';
import {newRoom,transition,token,hash,PHOTO_TTL} from '../server/photo-state.mjs';

function fixture(){
  const owner=token(),instance=token(),room=newRoom('atl-downtown',owner),now=100000;
  const beat={instance,ready:true,people:1,person:'visitor',character:'orbit'};
  transition(room,'operator',owner,'heartbeat',beat,now);
  const visitor=transition(room,'visitor',null,'create',{},now).response.token;
  return {owner,instance,room,now,beat,visitor};
}
test('one fixed station, separate private visitors, no public image access',()=>{
  const f=fixture();
  const second=transition(f.room,'visitor',null,'create',{},f.now).response.token;
  assert.notEqual(second,f.visitor);
  assert.throws(()=>transition(f.room,'visitor',f.owner,'status',{},f.now),{status:410});
  assert.throws(()=>transition(f.room,'operator',f.visitor,'heartbeat',f.beat,f.now),{status:403});
  assert.throws(()=>transition(f.room,'visitor',second,'image',{},f.now),{status:404});
});
test('single operator lease rejects a competing camera',()=>{
  const f=fixture();
  assert.throws(()=>transition(f.room,'operator',f.owner,'heartbeat',{...f.beat,instance:token()},f.now+1),{status:409});
});
test('concurrent visitor starts have only one winner',()=>{
  const f=fixture(),other=transition(f.room,'visitor',null,'create',{},f.now).response.token;
  transition(f.room,'visitor',f.visitor,'start',{},f.now);
  assert.throws(()=>transition(f.room,'visitor',other,'start',{},f.now),{status:409});
});
function capture(f){
  transition(f.room,'visitor',f.visitor,'start',{},f.now);
  const command=transition(f.room,'operator',f.owner,'heartbeat',f.beat,f.now+5001).response;
  assert.equal(command.state,'processing');
  transition(f.room,'operator',f.owner,'complete',{instance:f.instance,job:command.job,imagePath:'test.jpg'},f.now+5002);
}
test('capture expires after 24 hours, and deletion queues storage removal',()=>{
  const f=fixture();capture(f);
  assert.equal(f.room.sessions[hash(f.visitor)].expires,f.now+5002+PHOTO_TTL);
  assert.equal(transition(f.room,'visitor',f.visitor,'image',{},f.now+6000).readImage,'test.jpg');
  assert.deepEqual(transition(f.room,'visitor',f.visitor,'delete',{},f.now+7000).remove,['test.jpg']);
  assert.throws(()=>transition(f.room,'visitor',f.visitor,'image',{},f.now+8000),{status:410});
});
test('expired access denied; cleanup discovers expired paths',()=>{
  const f=fixture();capture(f);
  const cleaned=transition(f.room,'visitor',null,'availability',{},f.now+5003+PHOTO_TTL);
  assert.deepEqual(cleaned.remove,['test.jpg']);
  assert.throws(()=>transition(f.room,'visitor',f.visitor,'image',{},f.now+5003+PHOTO_TTL),{status:410});
});
test('lost tracking or changed person cancels capture',()=>{
  for(const change of [{ready:false},{person:'other'},{people:2},{character:'cosmic'}]){
    const f=fixture();transition(f.room,'visitor',f.visitor,'start',{},f.now);
    transition(f.room,'operator',f.owner,'heartbeat',{...f.beat,...change},f.now+1);
    assert.equal(f.room.active,null);assert.equal(f.room.sessions[hash(f.visitor)].state,'error');
  }
});
test('retake revokes the old photo before another countdown',()=>{
  const f=fixture();capture(f);
  const result=transition(f.room,'visitor',f.visitor,'cancel',{},f.now+6000);
  assert.deepEqual(result.remove,['test.jpg']);
  assert.throws(()=>transition(f.room,'visitor',f.visitor,'image',{},f.now+6100),{status:404});
});
