import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';

// Preserve the shipped face/hand runtime. Only the pose worker uses this copy.
const root=new URL('../vendor/mediapipe/',import.meta.url);
const original=readFileSync(new URL('vision_bundle.mjs',root),'utf8');
let patched=original;
for(const [converter,proto] of [['vo','Hi'],['_o','Vi']]){
  const property=converter==='vo'?'landmarks':'worldLandmarks';
  const from=`this.${property}=[];for(const e of t)t=${converter==='vo'?'$i':'Xi'}(e),this.${property}.push(${converter}(t))`;
  const to=from.replace(`${converter}(t)`,`poseConfidence(t,${proto})`);
  assert.equal(patched.split(from).length-1,1,'Expected one pose-only conversion');
  patched=patched.replace(from,to);
}
patched+='\n// Local patch: retain landmark.proto visibility (4) and presence (5).\n';
patched+='function poseConfidence(t,proto){return bn(t,proto,1).map(n=>({x:Ln(n,1)??0,y:Ln(n,2)??0,z:Ln(n,3)??0,visibility:Ln(n,4)??0,...(Ln(n,5)==null?{}:{presence:Ln(n,5)})}));}\n';
writeFileSync(new URL('vision_pose_bundle.mjs',root),patched);
console.log('Generated pose-only confidence patch; original SHA256:',createHash('sha256').update(original).digest('hex'));
