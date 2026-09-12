import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {previewFiles, validateAssetHeader} from './build_web_preview.mjs';

test('Vercel opens the cockpit and validates assets before publishing', () => {
  const config = JSON.parse(readFileSync(new URL('../vercel.json', import.meta.url)));
  assert.equal(config.buildCommand, 'node scripts/build_web_preview.mjs');
  assert.equal(config.outputDirectory, 'dist');
  assert.equal(config.redirects.find(r => r.source === '/').destination, '/cockpit.html');
  assert.equal(config.redirects.find(r => r.source === '/index.html').destination, '/cockpit.html');
});

test('preview includes tracking workers, binaries and every selectable roster', () => {
  const files = previewFiles();
  for (const file of ['cockpit.html', 'fleet.js', 'smile-rig.js', 'face-tracking-worker.js', 'hand-tracking-worker.js',
    'finger-tracking-worker.js', 'tongue-tracking-worker.js', 'vendor/mediapipe/model/face_landmarker.task',
    'vendor/mediapipe/model/hand_landmarker.task', 'vendor/mediapipe/model/pose_landmarker_lite.task',
    'vendor/mediapipe/wasm/vision_wasm_internal.wasm', 'vendor/mediapipe/wasm/vision_wasm_nosimd_internal.wasm',
    'vendor/onnxruntime/ort-wasm-simd-threaded.wasm', 'vendor/tongue/tongue_detector.onnx']) {
    assert(files.includes(file), file);
  }
  for (const path of files.filter(f => f.endsWith('/manifest.json'))) {
    const manifest = JSON.parse(readFileSync(new URL(`../${path}`, import.meta.url)));
    assert(!manifest.characters.some(c => c.id === 'coral'), path + ': Coral must stay paused');
    for (const character of manifest.pausedCharacters || []) {
      assert(!files.includes(character.url), 'Paused model must not be published');
      assert(!files.includes(character.thumbnail), 'Paused thumbnail must not be published');
    }
    for (const character of manifest.characters) {
      assert(files.includes(character.url));
      assert(files.includes(character.thumbnail));
    }
    if (manifest.vehicle) assert(files.includes(manifest.vehicle));
  }
  assert(!files.some(f => /^(blender|scripts|outputs|papers|\.context)\//.test(f)));
  assert(!files.some(f => /\.(blend\d*|bak)$/.test(f)));
});

test('LFS pointer files fail the build with an actionable error, including models without magic headers', () => {
  const pointer = Buffer.from('version https://git-lfs.github.com/spec/v1\noid sha256:123\nsize 1234\n');
  for (const extension of ['wasm', 'task', 'onnx', 'glb', 'png']) {
    assert.throws(() => validateAssetHeader(`model.${extension}`, pointer), /Enable Git LFS in Vercel/);
  }
});

test('binary validation rejects HTML responses, truncated and empty files', () => {
  for (const extension of ['wasm', 'glb', 'png']) {
    assert.throws(() => validateAssetHeader(`model.${extension}`, Buffer.from('<html>404</html>')), /invalid binary/);
    assert.throws(() => validateAssetHeader(`model.${extension}`, Buffer.alloc(0)), /invalid binary/);
  }
  assert.throws(() => validateAssetHeader('runtime.wasm', Buffer.from([0, 97, 115, 109])), /invalid binary/);
  assert.doesNotThrow(() => validateAssetHeader('runtime.wasm', Buffer.from([0, 97, 115, 109, 1, 0, 0, 0])));
});
