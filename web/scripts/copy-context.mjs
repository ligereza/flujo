import { copyFileSync, existsSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';

const root = resolve(import.meta.dirname, '..', '..');
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
