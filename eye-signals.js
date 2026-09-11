const clamp=value=>Math.min(1,Math.max(0,value));

export class EyeSignalFilter {
  constructor(){this.reset();}
  reset(){this.values={};this.samples={};}
  update(name,value,dt){
    const previous=this.values[name]||0;
    if(!Number.isFinite(value)||!Number.isFinite(dt)||dt<=0)return previous;
    // A three-frame median rejects isolated tracking spikes in either direction.
    // Seed at neutral so the first camera frame cannot create a false blink.
    const samples=this.samples[name]||(this.samples[name]=[0,0]);
    samples.push(clamp(value));
    const median=[...samples].sort((a,b)=>a-b)[1];
    samples.shift();
    const blink=name.startsWith('eyeBlink');
    const threshold=blink?.10:name.startsWith('eyeLook')?.06:.10;
    value=clamp((median-threshold)/(1-threshold));
    if(Math.abs(value-previous)<.025&&value!==0&&value!==1)return previous;
    const rate=blink?(value>previous?35:22):10;
    return this.values[name]=previous+(value-previous)*(1-Math.exp(-Math.min(dt,.15)*rate));
  }
}

export function resolveEyeAperture(values){
  for(const side of ['Left','Right']){
    const blink=clamp(values['eyeBlink'+side]||0);
    // Opposing aperture signals must not pull the same lid in both directions.
    const aperture=(values['eyeWide'+side]||0)-(values['eyeSquint'+side]||0);
    values['eyeWide'+side]=Math.max(0,aperture)*(1-blink);
    values['eyeSquint'+side]=Math.max(0,-aperture)*(1-blink);
  }
}
