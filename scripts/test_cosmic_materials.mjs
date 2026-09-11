import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';

const bytes=readFileSync(new URL('../assets/likeness-trials/cosmic-body-rig.glb',import.meta.url));
const length=bytes.readUInt32LE(12);
const gltf=JSON.parse(bytes.toString('utf8',20,20+length));
const binary=bytes.subarray(28+length);
const skin=gltf.materials.find(m=>m.name==='Cosmic Galaxy Clay - Runtime PBR');
const eye=gltf.materials.find(m=>m.name==='Cosmic Eye');

test('Cosmic clay has matte nonmetallic skin and an embedded grain normal map',()=>{
  assert(skin);
  assert(skin.pbrMetallicRoughness.roughnessFactor>=.85);
  assert.equal(skin.pbrMetallicRoughness.metallicFactor,0);
  assert(skin.extensions.KHR_materials_specular.specularFactor<=.3);
  const image=gltf.images[gltf.textures[skin.normalTexture.index].source];
  const view=gltf.bufferViews[image.bufferView];
  assert.equal(image.mimeType,'image/png');
  const embedded=binary.subarray(view.byteOffset,view.byteOffset+view.byteLength);
  assert.deepEqual(embedded,readFileSync(new URL('../assets/likeness-trials/cosmic-clay-normal.png',import.meta.url)));
  assert.equal(embedded.readUInt32BE(16),1024);
});

test('Cosmic retains separate polished black eyes without clay grain',()=>{
  assert(eye.pbrMetallicRoughness.baseColorFactor.slice(0,3).every(v=>v<.002));
  assert(eye.pbrMetallicRoughness.roughnessFactor<.04);
  assert.equal(eye.pbrMetallicRoughness.metallicFactor,0);
  assert.equal(eye.extensions.KHR_materials_clearcoat.clearcoatFactor,1);
  assert(eye.extensions.KHR_materials_clearcoat.clearcoatRoughnessFactor<.05);
  assert.equal(eye.normalTexture,undefined);
});

test('Cosmic review manifest identifies the active movement-test export',()=>{
  const manifest=JSON.parse(readFileSync(new URL('../blender/likeness-trials/roster-review.json',import.meta.url)));
  const cosmic=manifest.characters.find(c=>c.name==='cosmic');
  assert.equal(manifest.status,'active_for_movement_testing');
  assert.equal(cosmic.bytes,bytes.length);
  assert.equal(cosmic.sha256,createHash('sha256').update(bytes).digest('hex'));
  assert.equal(cosmic.materialRevision,'cosmic-clay-surface-glossy-eyes-1');
});
