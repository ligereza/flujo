// A venue as a DETERMINISTIC orbit: N fixed camera angles, one line-only SVG
// each. The artist had already faked a 360 viewer by hand, frame by frame, over
// a real reference; this industrialises that technique instead of replacing it.
// The frames come out of the SAME projection the live viewer runs (see
// tools/venue3d_contexto.mjs), so the reel and the screen cannot disagree.
//
// Line-only is the point: a plotter and a laser cannot rasterise, but they can
// follow a polyline. Each <g> carries data-confianza, so a laser layer can drop
// everything nobody backs before it costs a single ILDA point.
//
//   node tools/venue_secuencia.mjs                       # 120 cuadros, 1080x1080
//   node tools/venue_secuencia.mjs --cuadros 24 --salida _logs/orbita
//   node tools/venue_secuencia.mjs --venue otra-sala --aristas 400 --alto 0.35
//   node tools/venue_secuencia.mjs --orbita data/orbitas/vuelta-completa.json
//
// --orbita takes a camera path as DATA (schemas/orbita.schema.json): keyframes
// {giro, alto?, dist?} lerped over the frame count, `cerrar` for loops. Without
// it, the default full turn -- which is itself such a path, shipped as
// data/orbitas/vuelta-completa.json.
//
// Output goes wherever --salida says (default _logs/venue_secuencia/, which is
// gitignored: these are frames, not sources -- the source is the venue JSON).
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { isAbsolute, join } from "node:path";
import { correr, RAIZ } from "./venue3d_contexto.mjs";

const arg = (nombre, porDefecto) => {
  const i = process.argv.indexOf("--" + nombre);
  return i > 0 && process.argv[i + 1] ? process.argv[i + 1] : porDefecto;
};

// The orbit file is validated HERE, with numbers, before a single frame is
// cut: node has no jsonschema, and a bad keyframe that slips through would
// surface as 120 subtly wrong SVGs instead of one loud error.
const rutaOrbita = arg("orbita", "");
let orbita = null;
if (rutaOrbita) {
  const abs = isAbsolute(rutaOrbita) ? rutaOrbita : join(RAIZ, rutaOrbita);
  try { orbita = JSON.parse(readFileSync(abs, "utf8")); }
  catch (e) { console.error(`orbita ilegible: ${rutaOrbita}: ${e.message}`); process.exit(1); }
  const fallas = [];
  const puntos = orbita && orbita.puntos;
  if (!Array.isArray(puntos) || puntos.length < 2)
    fallas.push("puntos: se necesitan al menos 2 keyframes");
  else puntos.forEach((k, i) => {
    if (!Number.isFinite(k.giro) || Math.abs(k.giro) > 100)
      fallas.push(`puntos[${i}].giro: falta o esta fuera de [-100, 100] rad`);
    if (k.alto !== undefined && !(Number.isFinite(k.alto) && Math.abs(k.alto) <= 1.45))
      fallas.push(`puntos[${i}].alto: fuera de los topes del visor (±1.45 rad)`);
    if (k.dist !== undefined && !(Number.isFinite(k.dist) && k.dist > 0 && k.dist <= 4000))
      fallas.push(`puntos[${i}].dist: fuera de (0, 4000] m`);
  });
  if (fallas.length) {
    console.error(`orbita invalida (${rutaOrbita}):\n  - ` + fallas.join("\n  - "));
    process.exit(1);
  }
}

const cuadros = Math.max(1, parseInt(arg("cuadros", String((orbita && orbita.cuadros) || 120)), 10));
const lado = Math.max(64, parseInt(arg("lado", String((orbita && orbita.lado) || 1080)), 10));
const inclinacion = parseFloat(arg("alto", "0.45"));
const venue = arg("venue", "");
const aristas = arg("aristas", "");
const salida = join(RAIZ, arg("salida", "_logs/venue_secuencia"));

const query = [
  venue ? `venue=../../../data/venues/${venue}.json` : "",
  aristas ? `aristas=${aristas}` : "",
].filter(Boolean).join("&");

const s = await correr(query ? "?" + query : "", { ancho: lado, alto: lado, cuadros: 2 });
if (s.falla) {
  console.error("el visor no arranco:", s.falla.stack || s.falla);
  process.exit(1);
}
const nombre = s.leer("ESTADO.venue.nombre");
const dibujadas = s.leer("ESTADO.dibujadas");
const omitidas = s.leer("ESTADO.omitidas");
if (!(s.leer("ESTADO.aristas") > 0)) {
  console.error("la sala no trae geometria: no hay secuencia que exportar");
  process.exit(1);
}

mkdirSync(salida, { recursive: true });
const extra = orbita
  ? `, ruta: ${JSON.stringify(orbita.puntos)}, cerrar: ${orbita.cerrar === true}`
  : "";
const svgs = s.leer(
  `secuencia(${cuadros}, {alto_: ${inclinacion}, w: ${lado}, h: ${lado}${extra}})`);
let bytes = 0;
svgs.forEach((svg, i) => {
  const f = join(salida, `cuadro_${String(i).padStart(4, "0")}.svg`);
  writeFileSync(f, svg, "utf8");
  bytes += Buffer.byteLength(svg);
});

// El primero y el segundo NO pueden ser iguales: si lo fueran, la vuelta no
// estaria repartida y el loop se trabaria en un cuadro repetido. Con --orbita
// el chequeo no aplica: una ruta puede legitimamente sostener la camara quieta.
if (!orbita && cuadros > 2 && svgs[0] === svgs[1]) {
  console.error("dos cuadros consecutivos son identicos: la orbita no avanza");
  process.exit(1);
}

console.log(`${nombre} · ${cuadros} cuadros de ${lado}x${lado}` +
            (orbita ? ` · orbita ${rutaOrbita} (${orbita.puntos.length} keyframes` +
                      `${orbita.cerrar === true ? ", loop" : ""})` : "") +
            ` · ${dibujadas} aristas por ` +
            `cuadro${omitidas ? ` (${omitidas} fuera del tope)` : ""} · ` +
            `${(bytes / 1024).toFixed(0)} KB en ${salida}`);
