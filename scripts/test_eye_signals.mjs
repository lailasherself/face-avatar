import test from 'node:test';
import assert from 'node:assert/strict';
import {EyeSignalFilter,resolveEyeAperture} from '../eye-signals.js';

const blink='eyeBlinkLeft';
function feed(filter,name,value,frames=10,dt=1/30){
  return Array.from({length:frames},()=>filter.update(name,value,dt));
}

test('resting-eye noise and isolated spikes do not move lids or gaze',()=>{
  for(const name of [blink,'eyeSquintLeft','eyeWideLeft','eyeLookInLeft']){
    const filter=new EyeSignalFilter();
    for(const value of [0,.03,.01,1,.02,0,.04,0])assert.equal(filter.update(name,value,1/30),0,name);
  }
});

test('a held closed eye ignores an isolated open sample',()=>{
  const filter=new EyeSignalFilter();
  feed(filter,blink,1,30);
  for(const value of [0,1,1])assert(filter.update(blink,value,1/30)>.999);
});

test('deliberate blinks remain responsive at 20, 30 and 60 camera FPS',()=>{
  for(const fps of [20,30,60]){
    const filter=new EyeSignalFilter();
    feed(filter,blink,0,5,1/fps);
    const closed=feed(filter,blink,1,Math.ceil(fps*.1),1/fps).at(-1);
    assert(closed>.8,`${fps} FPS close: ${closed}`);
    const open=feed(filter,blink,0,Math.ceil(fps*.2),1/fps).at(-1);
    assert(open<.05,`${fps} FPS reopen: ${open}`);
  }
});

test('half blinks remain proportional and independent left/right',()=>{
  const filter=new EyeSignalFilter();
  const half=feed(filter,blink,.55,30).at(-1);
  assert(Math.abs(half-.5)<.025);
  assert.equal(filter.update('eyeBlinkRight',0,1/30),0);
  assert.equal(filter.values[blink],half);
});

test('invalid frames hold the last signal and reset clears sample history',()=>{
  const filter=new EyeSignalFilter();
  const previous=feed(filter,blink,.8).at(-1);
  for(const [value,dt] of [[NaN,.03],[Infinity,.03],[0,NaN],[0,0],[0,-1]]){
    assert.equal(filter.update(blink,value,dt),previous);
  }
  filter.reset();
  assert.equal(filter.update(blink,0,1/30),0);
  assert.equal(filter.update(blink,1,1/30),0);
});

test('opposing eyelid signals cancel and full blinks dominate',()=>{
  for(const blinkValue of [0,.5,1]){
    const values={eyeBlinkLeft:blinkValue,eyeWideLeft:.8,eyeSquintLeft:.6,
      eyeBlinkRight:blinkValue,eyeWideRight:.1,eyeSquintRight:.9};
    resolveEyeAperture(values);
    assert(Math.abs(values.eyeWideLeft-.2*(1-blinkValue))<1e-9);
    assert.equal(values.eyeSquintLeft,0);
    assert.equal(values.eyeWideRight,0);
    assert(Math.abs(values.eyeSquintRight-.8*(1-blinkValue))<1e-9);
    assert(values.eyeSquintRight+blinkValue<=1);
  }
});
