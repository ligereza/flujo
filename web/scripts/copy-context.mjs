import { copyFileSync, existsSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

// Node 18 (the Debian runtime used by MAK) does not expose import.meta.dirname.
// Resolve from the module URL so the copy step stays portable across Node 18+.
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = resolve(root, 'web', 'dist', 'index.html');
const targets = [
  resolve(root, 'context', 'flujo_hub.html'),
  resolve(root, 'context', 'plano_demo.html'),
  resolve(root, 'context', 'svg_visualizer.html'),
];

if (!existsSync(src)) {
  console.error(`Missing build output: ${src}`);
  process.exit(1);
}

for (const dest of targets) {
  mkdirSync(dirname(dest), { recursive: true });
  copyFileSync(src, dest);
  console.log(`copied ${src} -> ${dest}`);
}

const mappingSrc = resolve(root, 'web', 'dist', 'mapping.html');
const mappingDest = resolve(root, 'context', 'mapping.html');
if (!existsSync(mappingSrc)) {
  console.error(`Missing build output: ${mappingSrc}`);
  process.exit(1);
}
mkdirSync(dirname(mappingDest), { recursive: true });
copyFileSync(mappingSrc, mappingDest);
console.log(`copied ${mappingSrc} -> ${mappingDest}`);
