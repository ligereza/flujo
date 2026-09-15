// Load the executable scripts a static visual tool actually ships.
// The venue context, smoke, and sequence exporter must execute the same local
// script graph as the browser, including shared files.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";

export function scriptsDePiel(html, rutaHtml) {
  const scripts = [];
  for (const m of html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/gi)) {
    const attrs = m[1] || "";
    if (/type\s*=\s*["']application\/json["']/i.test(attrs)) continue;
    const src = attrs.match(/\bsrc\s*=\s*["']([^"']+)["']/i);
    if (src) scripts.push(readFileSync(join(dirname(rutaHtml), src[1]), "utf8"));
    else scripts.push(m[2]);
  }
  if (!scripts.length) throw new Error("no executable visual-tool script found");
  return scripts;
}
