import {raisedPalmBodySide} from './body-motion.js';
import {openPalm} from './air-swipe.js';

// A deliberate "hold still" dwell gesture: exactly `count` raised open palms, held
// steady for `holdMs`, fires once. Stillness is the discriminator that keeps this from
// firing during expressive avatar puppeteering (see research brief) — motion resets the
// dwell; only a held flat palm completes it. Latches until the palms drop, so a single
// sustained pose triggers exactly one action.
export class HoldGesture {
  constructor(count, holdMs, moveTolerance = .06){
    this.count = count; this.holdMs = holdMs; this.moveTolerance = moveTolerance;
    this.reset();
  }
  reset(){
    this.since = null; this.progress = 0; this.latched = false;
    this.absentSince = null; this.anchor = null; this.state = 'idle';
  }
  moved(bySide){
    for(const side in this.anchor){
      const a = this.anchor[side], b = bySide[side];
      if(!b) return true;
      if(Math.hypot(a.x - b.x, a.y - b.y) > this.moveTolerance) return true;
    }
    return false;
  }
  update(result, time){
    // Pose-only frames (no hand landmarks) carry no palm data — leave state untouched
    // rather than treat them as "palms absent", which would flicker the dwell.
    if(!Array.isArray(result?.landmarks)) return {progress: this.progress, fired: false, state: this.state};
    const bySide = {};
    for(const hand of result.landmarks){
      const side = raisedPalmBodySide(hand, result.poseLandmarks);
      const point = openPalm(hand);
      if(side && point) bySide[side] = point;
    }
    const active = Object.keys(bySide).length === this.count;
    if(!active){
      this.anchor = null; this.progress = 0; this.state = 'idle';
      this.absentSince ??= time;
      if(time - this.absentSince >= 250) this.latched = false;
      return {progress: 0, fired: false, state: 'idle'};
    }
    this.absentSince = null;
    if(this.latched){ this.state = 'cooldown'; this.progress = 0; return {progress: 0, fired: false, state: 'cooldown'}; }
    if(!this.anchor || this.moved(bySide)){ this.anchor = {...bySide}; this.since = time; }
    this.progress = Math.min(1, (time - this.since) / this.holdMs);
    this.state = 'holding';
    if(this.progress >= 1){
      this.latched = true; this.progress = 0; this.state = 'cooldown';
      return {progress: 1, fired: true, state: 'fired'};
    }
    return {progress: this.progress, fired: false, state: 'holding'};
  }
}
