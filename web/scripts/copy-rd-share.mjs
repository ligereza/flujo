import { copyFileSync, existsSync, mkdirSync, statSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

// Node 18 (the Debian runtime used by MAK) does not expose import.meta.dirname.
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = resolve(root, 'web', 'dist-rd', 'rd.html');
const dest = resolve(root, 'dist_compartir', 'herramientas_rd.html');

if (!existsSync(src)) {
  console.error(`Missing build output: ${src}`);
  process.exit(1);
}

mkdirSync(dirname(dest), { recursive: true });
copyFileSync(src, dest);
const kb = (statSync(dest).size / 1024).toFixed(1);
console.log(`copied ${src} -> ${dest} (${kb} KB)`);
