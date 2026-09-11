import {copyFileSync, existsSync, mkdirSync, openSync, closeSync, readSync, readFileSync, readdirSync, rmSync, statSync} from 'node:fs';
import {dirname, extname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const manifests = [
  'assets/fleet/manifest.json',
  'assets/3dai/manifest.json',
  'assets/3dai/refined/manifest.json',
  'assets/local-characters/manifest.json',
];
const signatures = {
  '.wasm': Buffer.from([0, 97, 115, 109, 1, 0, 0, 0]),
  '.glb': Buffer.from('glTF'),
  '.png': Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
};

export function validateAssetHeader(path, header) {
  if (header.toString('utf8').startsWith('version https://git-lfs.github.com/spec/v1')) {
    throw new Error(`${path}: Git LFS placeholder, not an asset. Enable Git LFS in Vercel Settings > Git and redeploy (locally: git lfs pull).`);
  }
  const signature = signatures[extname(path)];
  if (!header.length || (signature && !header.subarray(0, signature.length).equals(signature))) {
    throw new Error(`${path}: empty or invalid binary asset.`);
  }
}

export function previewFiles(source = root) {
  const files = new Set(['cockpit.html', ...manifests]);
  for (const entry of readdirSync(source, {withFileTypes: true})) {
    if (entry.isFile() && /\.(js|css)$/.test(entry.name)) files.add(entry.name);
  }
  function includeDirectory(directory) {
    for (const entry of readdirSync(join(source, directory), {withFileTypes: true})) {
      if (entry.name.startsWith('.')) continue;
      const path = `${directory}/${entry.name}`;
      if (entry.isDirectory()) includeDirectory(path);
      else if (entry.isFile()) files.add(path);
    }
  }
  // Runtime libraries only; vendor's top-level GLBs are legacy authoring iterations.
  for (const directory of ['three', 'mediapipe', 'onnxruntime', 'tongue', 'rapier', 'one-euro', 'lucide', 'fonts']) {
    includeDirectory(`vendor/${directory}`);
  }
  for (const path of manifests) {
    const manifest = JSON.parse(readFileSync(join(source, path), 'utf8'));
    for (const asset of [manifest.vehicle, ...manifest.characters.flatMap(c => [c.url, c.thumbnail])]) {
      if (!asset) continue;
      if (!asset.startsWith('assets/') || asset.split('/').includes('..')) throw new Error(`Invalid manifest asset: ${asset}`);
      files.add(asset);
    }
  }
  return [...files].sort();
}

export function buildPreview(source = root) {
  const output = join(source, 'dist');
  // A failed build must never leave a previous, apparently successful bundle.
  rmSync(output, {recursive: true, force: true});
  const files = previewFiles(source);
  let bytes = 0;
  for (const path of files) {
    const input = join(source, path);
    if (!existsSync(input)) throw new Error(`Missing preview asset: ${path}`);
    const fd = openSync(input, 'r');
    try {
      const header = Buffer.alloc(256);
      const length = readSync(fd, header, 0, header.length, 0);
      validateAssetHeader(path, header.subarray(0, length));
    } finally {
      closeSync(fd);
    }
    bytes += statSync(input).size;
  }
  for (const path of files) {
    mkdirSync(dirname(join(output, path)), {recursive: true});
    copyFileSync(join(source, path), join(output, path));
  }
  return {files: files.length, bytes};
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const result = buildPreview();
    console.log(`Web preview: ${result.files} validated files, ${(result.bytes / 1024 / 1024).toFixed(1)} MiB in dist/`);
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
