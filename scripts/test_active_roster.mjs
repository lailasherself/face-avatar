import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';

const root=new URL('../',import.meta.url);
const manifest=JSON.parse(readFileSync(new URL('assets/3dai/manifest.json',root)));
test('default cockpit roster contains seven active rigs with Coral paused',()=>{
  assert.deepEqual(manifest.characters.map(c=>c.id),['orbit','cosmic','nebula','kudzu','clay','summer','glass']);
  assert.deepEqual(manifest.pausedCharacters.map(c=>c.id),['coral']);
  assert.equal(manifest.vehicle,null);
  for(const c of manifest.characters){
    assert(existsSync(new URL(c.url,root)),c.id+' model missing');
    assert(existsSync(new URL(c.thumbnail,root)),c.id+' thumbnail missing');
    assert(!c.cyclops,c.id+' inherited old character metadata');
    const bytes=readFileSync(new URL(c.url,root));
    assert.equal(bytes.readUInt32LE(0),0x46546c67);
    const gltf=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
    assert(gltf.skins?.length,c.id+' is not rigged');
    const names=gltf.meshes.flatMap(m=>m.extras?.targetNames||[]);
    for(const channel of ['eyeBlinkLeft','eyeBlinkRight','jawOpen','tongueOut'])assert(names.includes(channel),c.id+' missing '+channel);
  }
});

test('Orbit and Coral use the exact supplied-image builds, not the rejected old bases',()=>{
  const lock=JSON.parse(readFileSync(new URL('scripts/reference-source-lock.json',root)));
  for(const [id,bones,reference] of [['orbit',39,'8gfKpO'],['coral',18,'ZWD70v']]){
    const character=[...manifest.characters,...manifest.pausedCharacters].find(c=>c.id===id);
    assert.equal(character.url,`assets/likeness-trials/${id}-image-rig.glb`);
    assert.equal(character.bones,bones);
    assert.equal(character.reference,reference);
    assert.equal(character.sourceMethod,'supplied_image_contour_blender');
    assert.equal(character.revision,'reference_painted_sculpt_4');
    assert.equal(character.sourceTaskId,undefined);
    assert.equal(createHash('sha256').update(readFileSync(new URL(lock[id].archivedImage||lock[id].image,root))).digest('hex'),lock[id].sha256);
  }
});

test('refined Orbit and Coral export distinct skin finishes and higher-resolution normals',()=>{
  for(const id of ['orbit','coral']){
    const bytes=readFileSync(new URL(`assets/likeness-trials/${id}-image-rig.glb`,root));
    const gltf=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
    const materials=gltf.materials;
    const name=id==='orbit'?'Orbit':'Coral';
    const skin=materials.find(m=>m.name.includes(`Reference painted ${name} Head skin`));
    assert(skin,'Missing reference-specific skin material');
    assert.equal(skin.pbrMetallicRoughness.metallicFactor,0);
    assert(skin.pbrMetallicRoughness.metallicRoughnessTexture,'Missing variable skin roughness');
    assert(Math.abs(skin.normalTexture.scale-(id==='orbit'?.60:.40))<1e-5);
    const lip=materials.find(m=>m.name.includes(`Reference painted ${name} Head lips`));
    assert(lip?.normalTexture,'Missing sculpted lip texture');
    const body=materials.find(m=>m.name.includes(`Reference painted ${name} Body skin`));
    assert(body?.normalTexture,'Missing body texture');
    assert.notEqual(body.normalTexture.index,skin.normalTexture.index,'Head must not share its atlas with the body');
    const image=gltf.images[gltf.textures[skin.normalTexture.index].source];
    const view=gltf.bufferViews[image.bufferView];
    const binaryStart=20+bytes.readUInt32LE(12)+8;
    const png=bytes.subarray(binaryStart+(view.byteOffset||0),binaryStart+(view.byteOffset||0)+view.byteLength);
    assert.equal(png.readUInt32BE(16),2048);
    assert.equal(png.readUInt32BE(20),2048);
  }
});
