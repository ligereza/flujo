import { copyFileSync, existsSync, mkdirSync, statSync } from 'node:fs';
import { dirname, resolve } from 'node:path';

const root = resolve(import.meta.dirname, '..', '..');
const src = resolve(root, 'web', 'dist-plano', 'plano.html');
const dest = resolve(root, 'dist_compartir', 'plano_rd.html');

if (!existsSync(src)) {
  console.error(`Missing build output: ${src}`);
  process.exit(1);
}

mkdirSync(dirname(dest), { recursive: true });
copyFileSync(src, dest);
const kb = (statSync(dest).size / 1024).toFixed(1);
console.log(`copied ${src} -> ${dest} (${kb} KB)`);
