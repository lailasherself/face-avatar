import test from 'node:test';
import assert from 'node:assert/strict';
import {photoConfiguration} from '../spaceship-photo.js';
import {testStation} from '../server/photo-store.mjs';

function storage(){const data=new Map();return {getItem:key=>data.get(key)||null,setItem:(key,value)=>data.set(key,value)};}
const cloud={enabled:true,mode:'cloud',testStations:true,room:'atl-downtown',phoneURL:'https://example.com/photo.html?station=atl-downtown'};
function browser(url='https://example.com/cockpit.html?view=ship'){
  globalThis.location=new URL(url);globalThis.sessionStorage=storage();globalThis.localStorage=storage();
  globalThis.history={replaceState:(_state,_title,url)=>{globalThis.location=new URL(url,location);}};
}
test('automatic camera registration is isolated, repeatable, and never exposes the owner in the QR',async()=>{
  const original=globalThis.fetch;
  try{
    let provisions=0;
    globalThis.fetch=async(url,options)=>{
      if(url.endsWith('config'))return Response.json(cloud);
      assert.equal(options.method,'POST');assert.equal(options.headers['X-Face-Avatar'],'photo');
      const owner=options.headers.Authorization.slice(7),room=testStation(owner);provisions++;
      return Response.json({room,phoneURL:`https://example.com/photo.html?station=${room}`});
    };
    browser();localStorage.setItem('alien-photo-owner','A'.repeat(43));
    const a=await photoConfiguration(),reload=await photoConfiguration();
    assert.equal(a.operator,true);assert.equal(reload.owner,a.owner);assert.equal(reload.room,a.room);
    assert.notEqual(a.instance,reload.instance);assert.notEqual(a.owner,localStorage.getItem('alien-photo-owner'));
    assert.ok(!a.phoneURL.includes(a.owner));
    browser();const b=await photoConfiguration();assert.notEqual(a.room,b.room);
    browser('https://example.com/cockpit.html?station=atl-downtown');
    const viewer=await photoConfiguration();assert.equal(viewer.operator,false);assert.equal(viewer.room,'atl-downtown');
    browser('https://example.com/cockpit.html#photo-owner='+'A'.repeat(43));
    const fixed=await photoConfiguration();assert.equal(fixed.room,'atl-downtown');assert.equal(fixed.owner,'A'.repeat(43));
    assert.equal(location.hash,'');assert.equal(location.search,'?station=atl-downtown');assert.equal(provisions,3);
    browser('http://localhost:8014/cockpit.html');
    globalThis.fetch=async url=>{assert.equal(url,'/api/photo-config');return Response.json({enabled:true,mode:'local'});};
    assert.deepEqual(await photoConfiguration(),{enabled:true,mode:'local'});
    browser();globalThis.fetch=async url=>url.endsWith('config')?Response.json(cloud):new Response(null,{status:429});
    assert.deepEqual(await photoConfiguration(),{enabled:false},'Never fall back to somebody else\'s camera');
  }finally{
    globalThis.fetch=original;
    for(const key of ['location','sessionStorage','localStorage','history'])delete globalThis[key];
  }
});
