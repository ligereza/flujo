// Smoke-run of the venue skin's inline JS with DOM stubs. Same reason as
// tools/iskvw_piel_smoke.mjs: a skin whose JS nobody executes ships dead with
// a green CI (PR #403). This one goes further because the viewer's whole job
// is arithmetic: it also checks that the hand-rolled 4x4 projection actually
// MOVES when the camera orbits, and that a cap smaller than the venue crops
// LOUDLY -- cropping in silence is the one defect that looks perfect on a
// screenshot. Invoked by tests/test_venue3d_smoke.py. Node >= 18.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { correr, RAIZ } from "./venue3d_contexto.mjs";

const problemas = [];
const exigir = (cond, msg) => { if (!cond) problemas.push(msg); };

// ── 1. the viewer with its default budget ───────────────────────────────
const a = await correr("");
if (a.falla) {
  console.error("VENUE SKIN SMOKE FAILED (boot):", a.falla.stack || a.falla);
  process.exit(1);
}
const aristas = a.leer("ESTADO.aristas");
const dibujadas = a.leer("ESTADO.dibujadas");
const omitidas = a.leer("ESTADO.omitidas");
const tope = a.leer("TOPE");

exigir(aristas > 0, `no geometry loaded (aristas=${aristas}): the demo venue never reached the viewer`);
exigir(dibujadas + omitidas === aristas, `the budget lost edges: ${dibujadas}+${omitidas} != ${aristas}`);
exigir(dibujadas <= tope, `budget overrun: ${dibujadas} drawn over a cap of ${tope}`);
exigir(omitidas === 0, `the demo venue does not fit its own default cap (${omitidas} cropped)`);
// per-edge draw work really happened: an empty canvas is a silently green smoke
exigir(a.conteo.segmentos > 0, "no lineTo was ever issued: the loop drew nothing");
exigir(a.conteo.trazos > 0, "stroke() never ran");
// every confianza tier present in the file got its own styled pass
const niveles = a.leer("Object.keys(ESTADO.porNivel).length");
exigir(niveles >= 3, `only ${niveles} confianza tiers rendered: the demo should exercise at least 3`);

// ── 2. the hand-rolled projection moves with the gesture ────────────────
if (!problemas.length) {
  const antes = a.leer("JSON.stringify(proyectar(camara(), ESTADO.lineas[0].pl.puntos[0]))");
  a.leer("orbitar(120, 40)");
  const despues = a.leer("JSON.stringify(proyectar(camara(), ESTADO.lineas[0].pl.puntos[0]))");
  exigir(antes !== despues, `orbit did not change the projection (${antes}): drag is inert`);
  // El zoom no salta: fija un destino y la camara lo persigue por cuadro. Se
  // comprueban las dos mitades, porque si la segunda falta el zoom queda inerte.
  const d0 = a.leer("CAM.dist");
  a.leer("acercar(0.5)");
  exigir(a.leer("CAM.destino") < d0, "zoom did not move the camera target");
  a.leer("for (let i = 0; i < 30; i++) inercia();");
  exigir(a.leer("CAM.dist") < d0, "the camera never followed its zoom target");

  // La inercia del giro frena sola: una sala que sigue girando para siempre es
  // un defecto, no un tacto.
  a.leer("punteros.clear(); orbitar(90, 0);");
  const vArranque = Math.abs(a.leer("CAM.vGiro"));
  a.leer("for (let i = 0; i < 5; i++) inercia();");
  const vDespues = Math.abs(a.leer("CAM.vGiro"));
  exigir(vArranque > 0 && vDespues < vArranque, "the orbit has no momentum, or it never decays");
  a.leer("for (let i = 0; i < 400; i++) inercia();");
  exigir(a.leer("CAM.vGiro") === 0, "the venue never stops spinning: momentum has no floor");
}

// ── 3. a cap under the venue size crops, and the screen SAYS it ─────────
const b = await correr("?aristas=120");
if (b.falla) {
  console.error("VENUE SKIN SMOKE FAILED (cap run):", b.falla.stack || b.falla);
  process.exit(1);
}
const bDib = b.leer("ESTADO.dibujadas"), bOm = b.leer("ESTADO.omitidas");
exigir(bDib <= 120, `cap ignored: drew ${bDib} with a cap of 120`);
exigir(bOm > 0, "a cap of 120 over a 503-edge venue cropped nothing: the cap is decorative");
exigir(bDib + bOm === aristas, `cap run lost edges: ${bDib}+${bOm} != ${aristas}`);
// what is cropped first is what nobody backs
const primero = b.leer("ESTADO.lineas.every(l => l.nivel === 'medido' || l.nivel === 'ajustado')");
exigir(primero === true, "cropping did not respect the confianza order: unbacked lines survived measured ones");
const medidor = b.elements.get("medidor");
exigir(/fuera del tope/.test(medidor && medidor.innerHTML || ""),
       "the cropped edges were never reported on screen: silent cropping");

// ── 4. the exported sequence is the same drawing, frozen at fixed angles ──
if (!problemas.length) {
  const svgs = a.leer("secuencia(8, {w: 600, h: 600})");
  exigir(svgs.length === 8, `secuencia(8) returned ${svgs.length} frames`);
  exigir(svgs.every(s => s.startsWith("<svg") && s.includes("</svg>")),
         "a sequence frame is not a whole SVG");
  exigir(new Set(svgs).size === 8, "the orbit repeats a frame: the turn is not evenly spread");
  // line-only, and the confianza survives into the export (the laser reads it)
  exigir(!/<(image|rect [^>]*fill="(?!#08080a)|circle|text)/.test(svgs[0]),
         "the export is not line-only: it carries something a plotter cannot draw");
  exigir(/data-confianza="medido"/.test(svgs[0]) && /stroke-dasharray/.test(svgs[0]),
         "the export lost the confianza layers or their dashes");
  const trazos = (svgs[0].match(/[ML]/g) || []).length;
  exigir(trazos > 100, `the exported frame is nearly empty (${trazos} path commands)`);
}

// ── 5. the camera is data: URL params, bare-id venues, orbit paths ───────
// the untouched run kept its shipped defaults (run b never got a gesture)
exigir(b.leer("CAM.giro") === -0.45 && b.leer("CAM.alto") === 0.62,
       "the default starting camera drifted from the shipped values");
const c = await correr("?venue=scd-plaza-egana&giro=1.2&alto=0.3&dist=12");
if (c.falla) {
  console.error("VENUE SKIN SMOKE FAILED (param run):", c.falla.stack || c.falla);
  process.exit(1);
}
exigir(c.leer("ESTADO.aristas") === aristas,
       "a bare ?venue=<id> did not resolve against data/venues/: the registry form is dead");
exigir(c.leer("CAM.giro") === 1.2 && c.leer("CAM.alto") === 0.3,
       "?giro/?alto did not reach the camera");
exigir(c.leer("CAM.dist") === 12 && c.leer("CAM.destino") === 12,
       "?dist did not override the auto-framing (or missed the zoom target)");

if (!problemas.length) {
  // the shipped example orbit reproduces the default turn FRAME FOR FRAME:
  // that is the whole claim of "the orbit is data", so it is measured, not told
  const ejemplo = JSON.parse(
    readFileSync(join(RAIZ, "data", "orbitas", "vuelta-completa.json"), "utf8"));
  const base = "w: 400, h: 400, alto_: 0.45, dist: 30";
  const porDefecto = a.leer(`JSON.stringify(secuencia(6, {${base}}))`);
  const porArchivo = a.leer(
    `JSON.stringify(secuencia(6, {${base}, ruta: ${JSON.stringify(ejemplo.puntos)}, ` +
    `cerrar: ${ejemplo.cerrar === true}}))`);
  exigir(porDefecto === porArchivo,
         "data/orbitas/vuelta-completa.json does not reproduce the default turn frame for frame");

  // an OPEN path lands exactly on its first and last keyframes
  const abierta = `secuencia(5, {${base}, ruta: [{giro: 0}, {giro: Math.PI / 2}]})`;
  exigir(a.leer(`${abierta}[0] === svgDeCuadro(0, 0.45, 400, 400, 30)`),
         "an open path does not start at its first keyframe");
  exigir(a.leer(`${abierta}[4] === svgDeCuadro(Math.PI / 2, 0.45, 400, 400, 30)`),
         "an open path does not end at its last keyframe");
  exigir(a.leer(`new Set(${abierta}).size`) === 5,
         "an open path repeats frames: the lerp is not spreading");

  // dist keyframes move the camera even with the azimuth held still
  exigir(a.leer(`new Set(secuencia(3, {${base}, ` +
                "ruta: [{giro: 0.3, dist: 12}, {giro: 0.3, dist: 30}]})).size") === 3,
         "dist keyframes did not move the camera: the path ignores dist");
}

if (problemas.length) {
  console.error("VENUE SKIN SMOKE FAILED:\n  - " + problemas.join("\n  - "));
  process.exit(1);
}
console.log(`OK: ${aristas} aristas · ${dibujadas}/${tope} dibujadas · ${omitidas} fuera del tope ` +
            `· ${a.conteo.segmentos} segmentos en ${a.conteo.trazos} strokes`);
console.log(`OK: con tope 120 -> ${bDib} dibujadas, ${bOm} recortadas y reportadas en pantalla`);
