const clamp=v=>Number.isFinite(v)?Math.min(1,Math.max(0,v)):0;
const opposite=(v,a,b)=>{const d=v[a]-v[b];v[a]=Math.max(0,d);v[b]=Math.max(0,-d);};

export function resolveMouth(values){
  for(const name of Object.keys(values))if(/^(mouth|jaw|tongue)/.test(name))values[name]=clamp(values[name]);
  const get=name=>values[name]||0;
  for(const [a,b] of [['jawLeft','jawRight'],['mouthLeft','mouthRight'],...['Left','Right'].map(s=>['mouthSmile'+s,'mouthFrown'+s])]){
    values[a]=get(a);values[b]=get(b);opposite(values,a,b);
  }
  // These generated targets are additive displacements, not independent muscle
  // simulations. Share a deformation budget rather than adding several full poses.
  const round=get('mouthFunnel')+get('mouthPucker'),roundScale=round>.8?.8/round:1;
  const tongue=get('tongueOut'),clearance=.65*Math.min(1,tongue/.2);
  values.jawOpen=Math.max(get('jawOpen'),clearance);
  values.mouthClose=Math.min(get('mouthClose'),Math.max(0,values.jawOpen-clearance));
  const open=values.jawOpen-values.mouthClose,exposed=Math.min(1,tongue*5);
  values.mouthFunnel=get('mouthFunnel')*roundScale*(1-exposed*.9);
  values.mouthPucker=get('mouthPucker')*roundScale*(1-exposed);
  const narrowing=values.mouthFunnel+values.mouthPucker;
  for(const side of ['Left','Right']){
    const smile=get('mouthSmile'+side),stretch=get('mouthStretch'+side),budget=Math.max(1,smile+stretch);
    values['mouthSmile'+side]=smile/budget*(1-narrowing*.75);
    values['mouthStretch'+side]=stretch/budget*(1-narrowing*.75);
    values['mouthLowerDown'+side]=get('mouthLowerDown'+side)*.35*(1-open*.75)*(1-exposed);
    values['mouthUpperUp'+side]=get('mouthUpperUp'+side)*.35*(1-exposed);
    values['mouthPress'+side]=get('mouthPress'+side)*(1-open)*(1-exposed);
    values['mouthDimple'+side]=get('mouthDimple'+side)*(1-narrowing);
  }
  for(const lip of ['Upper','Lower']){
    values['mouthRoll'+lip]=get('mouthRoll'+lip)*(1-open)*(1-exposed);
    values['mouthShrug'+lip]=get('mouthShrug'+lip)*.5*(1-open)*(1-exposed);
  }
  return values;
}

export function oralWeight(name,value,material){
  // Lip expressions must not pull the back wall of the mouth out through the
  // opening, or flatten/shorten the long tongue itself.
  if(/oral interior|tongue/i.test(material)&&name.startsWith('mouth')&&name!=='mouthClose')return 0;
  return value;
}
