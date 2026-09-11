import { OneEuroFilter } from './vendor/one-euro/OneEuroFilter.js';

// Filter only new camera samples, never repeated render frames. Separate axes
// and sides prevent one visitor arm from affecting the other's filter history.
export class ArmSignal {
  constructor(){this.reset();}
  reset(){this.sides={};}
  update(arms,time){
    if(!Number.isFinite(time))return {};
    const result={};
    for(const [side,directions] of Object.entries(arms)){
      let state=this.sides[side];
      if(state&&time<=state.time)continue;
      if(!state||time-state.time>400)state={filters:{}};
      state.time=time;
      result[side]={};
      for(const kind of ['upper','lower','hand']){
        const value=directions[kind];
        if(!Array.isArray(value)||value.length!==3||!value.every(Number.isFinite)||Math.hypot(...value)<1e-6){
          delete state.filters[kind];result[side][kind]=null;continue;
        }
        const length=Math.hypot(...value);
        const filters=state.filters[kind]??=value.map(()=>new OneEuroFilter(30,1.5,4,1));
        const filtered=value.map((v,i)=>filters[i].filter(v/length,time/1000));
        const norm=Math.hypot(...filtered);
        result[side][kind]=norm>1e-6?filtered.map(v=>v/norm):value.map(v=>v/length);
      }
      this.sides[side]=state;
    }
    return result;
  }
}
