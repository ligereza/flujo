// Smoke-run of the campo skin's inline JS with DOM stubs. Exists because a
// scope refactor (PR #403) shipped `destino`/`dy` referenced outside the
// function that defined them: green CI, dead portfolio -- the draw loop threw
// on frame one and no test executed the JS. This runs the real script in node
// and fails on ANY uncaught error during boot + the first animation frames.
//
// Since the effects patch (datos/tablero.json) it also MEASURES the patch,
// because a master flag that is off by default is exactly the kind of code
// that rots unseen: the skin is booted three times -- without a board, with
// the board that ships (flag off) and with the flag on -- and the drawing
// trace of the first two has to be identical while the third has to differ.
// "Off changes nothing" stops being a claim and becomes a number.
//
// Invoked by tests/test_iskvw_piel_smoke.py. Node >= 18 (global fetch not
// needed: fetch is stubbed).
import { readFileSync } from "node:fs";
import vm from "node:vm";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const raiz = join(dirname(fileURLToPath(import.meta.url)), "..");

// Which skin. It used to be the literal string "campo", and that is why
// `terminal` (772 lines) and `venue` (505) had NO verification at all: this
// tool and the meter both pointed at one of the three skins, so two of them
// could have been broken for months and nothing would have said so. `campo`
// stays the default so CI and every existing invocation keep working.
//   node tools/iskvw_piel_smoke.mjs [piel]
const PIEL = process.argv[2] || "campo";
const rutaPiel = join(raiz, "iskvw", "piel", PIEL, "index.html");
let html;
try {
  html = readFileSync(rutaPiel, "utf8");
} catch {
  console.error(`no existe la piel ${PIEL} (${rutaPiel})`);
  process.exit(2);
}
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
if (!scripts.length) { console.error("no inline <script> found"); process.exit(2); }

// El manifiesto: lo que la piel DECLARA que pide y como se mide lo que dibujo.
// Sin esto la bateria tendria que adivinar el nombre de sus variables, y por eso
// antes solo servia para `campo`: asumia `NODOS`, que es un global de esa piel.
let MANIFIESTO = null;
try {
  MANIFIESTO = JSON.parse(readFileSync(join(raiz, "iskvw", "piel", PIEL, "piel.json"), "utf8"));
} catch {
  console.error(`la piel ${PIEL} no declara piel.json -- una piel sin manifiesto `
                + `no se puede verificar (ver schemas/piel.schema.json)`);
  process.exit(2);
}
const CAPACIDADES = new Set(MANIFIESTO.capacidades || []);
const SMOKE_ARCHIVO_LIMIT = 240;

function dataParaSmoke(abs, txt) {
  if (PIEL === "campo") return JSON.parse(txt);
  if (abs.slice(-3).join("/") !== "iskvw/datos/archivo.json") return JSON.parse(txt);
  const datos = JSON.parse(txt);
  const piezas = (datos.piezas || []).slice(0, SMOKE_ARCHIVO_LIMIT);
  const ids = new Set(piezas.map(p => p.id));
  return {
    ...datos,
    piezas,
    vinculos: (datos.vinculos || []).filter(v => ids.has(v.a) && ids.has(v.b)),
    smoke_sample: true,
  };
}

const noop = () => {};

// -- one boot of the skin, with its own sandbox and its own drawing trace --
// `tablero` is what datos/tablero.json answers (null = the file is not there,
// which is the path every visitor took before the patch existed).
// `antes` runs inside the sandbox right before the frames, so a test can poke
// state the real data does not carry.
async function correr({ tablero = null, cuadros = 30, caminar = true, antes = null } = {}) {
  let trabajoDeNodo = 0;       // per-node draw work actually executed
  const traza = [];            // every mark: what, where, in which colour
  const pedidos = [];          // every URL the skin asked for, to prove wiring ran
  let pincel = "";             // current fillStyle
  let fuente = "";             // current font -- the SIZE of a glyph mark
  // The bloom changes HOW a mark is painted, not just its colour: `lighter`
  // makes two translucent strokes SUM light where they overlap instead of
  // painting over each other, which is exactly what turns a flat line or
  // glyph into a laser halo. Without this the bench is blind to the blend
  // mode -- the same defect already fixed once for the arc's radius and the
  // glyph's font size: an effect that only changes HOW something is drawn,
  // never WHERE, measured as if it did not exist.
  let mezcla = "source-over";  // current globalCompositeOperation
  let grosor = 1;               // current lineWidth -- the halo is WIDER than the core
  // Los px de la fuente actual, o undefined si no hay. Se lee del estado del
  // contexto en vez de re-parsear en cada marca.
  const fuentePx = () => {
    const m = /^([\d.]+)px/.exec(fuente);
    return m ? parseFloat(m[1]) : undefined;
  };
  // `r` is optional and only `arc` carries it. It is recorded because the
  // trace used to keep position and colour ONLY, which made the instrument
  // blind to a whole class of effect: anything that changes SIZE drew a
  // different field and measured as "identical". `luz` was written, wired and
  // reported inert by this very smoke for exactly that reason. Position and
  // colour still compare on their own (`movidas`, `tonos`), so a size change
  // shows up in `difs` without ever being mistaken for a displacement.
  const marca = (x, y, r) => {
    // Rounded: the point is whether the patch MOVED something, not float noise.
    // `m:` and `w` only appear when they differ from the plain-paint default,
    // so every trace recorded before the bloom existed reads byte-identical
    // to what this produces today -- the exact-equality comparisons below
    // (`igual()`) never cared about blend mode or stroke width, so they must
    // not start seeing a difference where there is none.
    const m = mezcla !== "source-over" ? `,m:${mezcla}` : "";
    const w = grosor !== 1 ? `,w${grosor.toFixed(2)}` : "";
    traza.push(`${x.toFixed(2)},${y.toFixed(2)},${pincel}${m}${w}`
      + (r === undefined ? "" : `,r${r.toFixed(2)}`));
  };

  const ctx2d = new Proxy({}, {
    get: (t, k) => {
      if (k === "canvas") return canvas;
      // The radial gradient is how a node is actually painted in the default
      // regime -- `arc` only runs on other paths. Its radii are arguments 3
      // and 6, and dropping them is what made the trace blind to size.
      if (k === "createRadialGradient")
        return (x, y, r0, x1, y1, r1) => {
          trabajoDeNodo++;
          marca(x, y, r1 === undefined ? r0 : r1);
          return { addColorStop: (o, c) => traza.push(`g:${c}`) };
        };
      if (k === "createLinearGradient")
        return (x, y) => { trabajoDeNodo++; marca(x, y); return { addColorStop: (o, c) => traza.push(`g:${c}`) }; };
      // El TAMANO del glifo entra en la traza igual que el radio del circulo.
      // Sin esto el banco vuelve a ser ciego al tamano por la otra mitad: bajo
      // `nodo_glifo` -- que es como se publica -- el nodo se pinta con
      // `fillText`, no con un arco, asi que un efecto que solo dilata dibujaba
      // un campo distinto y la traza lo daba por identico. Es exactamente el
      // mismo defecto que se arreglo para `arc`, en el camino que de verdad
      // corre en produccion.
      if (k === "fillText")
        return (g, x, y) => { trabajoDeNodo++; marca(x, y, fuentePx()); };
      // `font` se LEE, como en un canvas de verdad. Sin esto el stub devolvia
      // un noop y cualquier codigo que guarde la fuente para restaurarla
      // despues -- que es lo correcto cuando se la cambia por un nodo --
      // restauraba `undefined` y el banco medía un estado que el navegador no
      // tiene.
      if (k === "font") return fuente;
      if (k === "arc") return (x, y, r) => marca(x, y, r);
      if (k === "moveTo" || k === "lineTo") return (x, y) => marca(x, y);
      if (k === "measureText") return () => ({ width: 10 });
      if (k === "getImageData") return () => ({ data: new Uint8ClampedArray(4) });
      return noop;
    },
    set: (t, k, v) => {
      if (k === "fillStyle" || k === "strokeStyle") pincel = String(v);
      // La fuente se sigue igual que el pincel, y por la misma razon: es
      // estado del contexto que decide COMO sale la marca.
      if (k === "font") fuente = String(v);
      // El bloom del laser (vinculos y glifos) se declara con estos dos, no
      // con un color nuevo: seguidos igual que el resto del estado del
      // contexto, por la misma razon que `pincel` y `fuente`.
      if (k === "globalCompositeOperation") mezcla = String(v);
      if (k === "lineWidth") grosor = Number(v) || 1;
      return true;
    },
  });
  const canvas = {
    getContext: () => ctx2d, width: 800, height: 600,
    clientWidth: 800, clientHeight: 600,
    style: {}, addEventListener: noop, removeEventListener: noop,
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 800, height: 600 }),
  };
  // A generic element, and generic is the point. The first version returned a
  // canvas ONLY for the id "c" and an element with six methods for anything
  // else -- which is exactly why this battery could never be pointed at another
  // skin. Measured 2026-07-31 the moment it was: `terminal` died on
  // `canvas.getContext is not a function` (its canvas has a different id) and
  // `venue` on `L.querySelectorAll is not a function` (element-level query was
  // not stubbed at all). Neither was a defect of the skin: the instrument was
  // shaped like one skin and called that a verification.
  //
  // So every element can be a canvas and every element answers the DOM surface
  // a skin plausibly touches. An over-generous stub can hide a real DOM bug,
  // and that trade is deliberate: the alternative was two skins with no
  // verification whatsoever.
  const el = () => {
    const nodo = {
      classList: { add: noop, remove: noop, toggle: noop, contains: () => false },
      style: {}, dataset: {},
      addEventListener: noop, removeEventListener: noop, dispatchEvent: noop,
      textContent: "", innerHTML: "", value: "", checked: false, id: "",
      width: 800, height: 600, clientWidth: 800, clientHeight: 600,
      offsetWidth: 800, offsetHeight: 600, scrollTop: 0, scrollHeight: 600,
      children: [], childNodes: [], firstChild: null, parentNode: null,
      getContext: () => ctx2d,
      appendChild: (h) => h, removeChild: (h) => h, insertBefore: (h) => h,
      replaceChildren: noop, remove: noop, cloneNode: () => el(),
      setAttribute: noop, removeAttribute: noop, getAttribute: () => null,
      hasAttribute: () => false,
      querySelector: () => el(), querySelectorAll: () => [],
      closest: () => null, contains: () => false,
      focus: noop, blur: noop, click: noop, scrollIntoView: noop,
      getBoundingClientRect: () => ({ left: 0, top: 0, right: 800, bottom: 600,
                                      width: 800, height: 600, x: 0, y: 0 }),
      toDataURL: () => "data:,",
    };
    return nodo;
  };
  const elements = new Map();
  const getEl = id => {
    if (id === "c") return canvas;
    if (!elements.has(id)) elements.set(id, el());
    return elements.get(id);
  };

  let rafQueue = [];
  const sandbox = {
    console, Math, JSON, Date, Number, Array, String, Object,
    Float64Array, Int32Array, Uint8ClampedArray, Map, Set, URLSearchParams,
    performance: { now: () => rafQueue.length * 16.7 },
    requestAnimationFrame: cb => { rafQueue.push(cb); return rafQueue.length; },
    cancelAnimationFrame: noop,
    setTimeout: (cb) => 0, clearTimeout: noop, setInterval: () => 0, clearInterval: noop,
    // fetch: resolve datos/* against the repo so the REAL data shapes are what
    // the loop chews on; anything else 404s like the fallback path expects.
    fetch: async (url) => {
      const s = String(url);
      pedidos.push(s);
      if (/datos\/tablero\.json$/.test(s)) {
        return tablero
          ? { ok: true, json: async () => tablero }
          : { ok: false, json: async () => ({}) };
      }
      // Any repo-relative path, not just `datos/*.json`. The first version
      // matched three filenames by name, so the `venue` skin -- which asks for
      // `../../../data/venues/scd-plaza-egana.json` -- got a 404 from the
      // instrument and its loader was never exercised. A battery that only
      // serves the files one skin happens to want is not a battery.
      // `..` segments are resolved and then REFUSED if they escape the repo:
      // this reads real files, and a skin should not be able to make it read
      // outside the checkout.
      // Se resuelve DESDE `iskvw/piel/<piel>/`, que es de donde la piel cuelga.
      // Los `..` no se colapsan antes de combinar -- ese fue el error de la
      // primera version: `../../datos/archivo.json` se comia a si mismo contra
      // una lista vacia y campo se quedaba sin sustrato (NODOS=8, el respaldo).
      const limpio = String(url).replace(/[?#].*$/, "");
      const abs = ["iskvw", "piel", PIEL];
      let escapa = false;
      for (const p of limpio.split("/")) {
        if (p === "" || p === ".") continue;
        if (p === "..") { if (!abs.length) { escapa = true; break; } abs.pop(); }
        else abs.push(p);
      }
      // Un pedido que se sale del checkout no se sirve: esto lee archivos
      // REALES y una piel no puede usar la sonda para mirar fuera del repo.
      if (escapa) return { ok: false, json: async () => ({}), text: async () => "" };
      try {
        const txt = readFileSync(join(raiz, ...abs), "utf8");
        return { ok: true, json: async () => dataParaSmoke(abs, txt), text: async () => txt };
      } catch { return { ok: false, json: async () => ({}), text: async () => "" }; }
    },
    addEventListener: noop, removeEventListener: noop, history: { replaceState: noop },
    location: { hash: "", href: "http://smoke.local/" },
    navigator: { maxTouchPoints: 0 },
    devicePixelRatio: 1, innerWidth: 800, innerHeight: 600,
  };
  sandbox.window = sandbox;
  sandbox.document = {
    getElementById: getEl,
    querySelector: () => el(), querySelectorAll: () => [],
    addEventListener: noop, removeEventListener: noop,
    body: el(), documentElement: el(), hidden: false,
    createElement: () => el(),
    // Namespaced: una piel que arma SVG lo usa, y sin esto moria en el primer
    // gesto que tocara esa rama -- que era justo la que nunca se ejercitaba.
    createElementNS: () => el(),
    createTextNode: () => el(),
  };

  const context = vm.createContext(sandbox);
  let failed = null;
  // arrancar() is async and fire-and-forget: its crash surfaces as an
  // unhandled rejection on the shared microtask queue, not as a sync throw.
  const onRejection = (e) => { failed = failed || e; };
  process.on("unhandledRejection", onRejection);
  try {
    for (const src of scripts) vm.runInContext(src, context, { timeout: 10000 });
  } catch (e) { failed = e; }

  // drain microtasks (the loader is async) then pump frames: the #403 bug threw
  // inside the FIRST frame, so frames are the point, not the parse.
  await new Promise(r => setTimeout(r, 50));
  if (!failed && antes) {
    try { vm.runInContext(antes, context); } catch (e) { failed = e; }
  }
  if (!failed) {
    try {
      // Without a gesture every node can sit outside d.alcance and the loop
      // body -- where the #403 bug lived -- silently never runs. Walk the
      // field: each frame, park the view on a different node so the per-node
      // code executes for real.
      for (let i = 0; i < cuadros && rafQueue.length; i++) {
        // Caminar el campo es un gesto de `campo`: mueve E.pos para que el
        // codigo por-nodo se ejecute de verdad. En una piel que no lo tiene,
        // la expresion no hace nada y no molesta.
        if (caminar)
          vm.runInContext(
            "if (typeof E!=='undefined' && typeof NODOS!=='undefined' && NODOS.length)" +
            `{ E.pos = NODOS[${i % 41} % NODOS.length].y; }`,
            context);
        const batch = rafQueue; rafQueue = [];
        for (const cb of batch) cb(i * 16.7);
      }
    } catch (e) { failed = e; }
  }
  process.off("unhandledRejection", onRejection);

  const leer = (expr, porDefecto) => {
    try { return vm.runInContext(expr, context); } catch { return porDefecto; }
  };
  return {
    failed, traza, trabajoDeNodo, pedidos,
    // La medida que la PIEL declara, no la que esta sonda supone.
    medida: MANIFIESTO.medida ? leer(MANIFIESTO.medida, -1) : null,
    nodos: leer("typeof NODOS !== 'undefined' && NODOS ? NODOS.length : -1", -1),
    pos: leer("typeof E !== 'undefined' ? E.pos : null", null),
    emisores: leer("typeof EMIS !== 'undefined' ? EMIS.n : -1", -1),
    patchOn: leer("typeof PATCH !== 'undefined' ? PATCH.on : null", null),
    // The venue layer's observables: whether the sala link exists after boot,
    // and a hatch to call capaVenue() again inside this run's sandbox.
    salaVisible: leer("typeof SALA_VISIBLE !== 'undefined' ? SALA_VISIBLE : null", null),
    evaluar: (expr, porDefecto) => leer(expr, porDefecto),
  };
}

function morir(msg) {
  console.error("SKIN SMOKE FAILED:", msg && msg.stack || msg);
  process.exit(1);
}

// ── 1. EL NUCLEO: lo que se le exige a CUALQUIER piel ─────────────────────
// Todo lo de aca abajo vale para una piel de una capa o de mil, y no supone ni
// una sola variable suya. Lo especifico de `campo` viene despues y solo si su
// manifiesto lo declara: exigirle a `terminal` las pruebas de `campo` seria
// medirla con la forma de otra, que es exactamente el error que tenia esta
// herramienta cuando la ruta era el literal "campo".
const base = await correr({});
if (base.failed) morir(base.failed);

// 1.a Dibujo de verdad. La traza la cuenta ESTA sonda sobre el canvas, asi que
// no depende de como la piel llame a sus cosas ni de COMO dibuje. Cero marcas
// es el modo clasico de sonda verde que no probo nada.
//
// `trabajoDeNodo` NO sirve aca aunque lo parezca: cuenta gradientes y glifos,
// que es como dibuja `campo`. Medido al apuntar la bateria a la tercera piel:
// `venue` dibuja polilineas -- moveTo/lineTo/stroke, ni un gradiente -- y daba
// cero. La metrica tambien estaba con forma de una sola piel.
if (!base.traza.length)
  morir(new Error("la piel no dibujo una sola marca: arranco sin material"));

// 1.b Pidio lo que declaro. Los `obligatorio: true` tienen que aparecer en los
// pedidos reales; declarar de mas hace FALLAR, no pasar.
for (const d of (MANIFIESTO.datos || [])) {
  const pedido = base.pedidos.some(u => String(u).includes(d.ruta.replace(/^\.\.\//, "")));
  if (d.obligatorio && !pedido)
    morir(new Error(`el manifiesto declara ${d.ruta} como obligatorio y la piel `
                    + `nunca lo pidio`));
}

// 1.c La medida que la piel declara. Es lo unico que permite exigirle lo mismo
// a pieles que no comparten una variable.
if (MANIFIESTO.medida) {
  if (!(base.medida > 0))
    morir(new Error(`la medida declarada (${MANIFIESTO.medida}) dio `
                    + `${base.medida}: la piel arranco sin material`));
  console.log(`OK: nucleo -- ${base.medida} segun su propia medida, `
              + `${base.traza.length} marcas, ${base.pedidos.length} pedidos`);
} else {
  console.log(`OK: nucleo -- ${base.traza.length} marcas, `
              + `${base.pedidos.length} pedidos (no declara medida propia)`);
}

// ── 2. lo especifico de campo, solo si lo declara ─────────────────────────
if (!CAPACIDADES.has("patch_efectos") && !CAPACIDADES.has("posiciones_medidas")) {
  console.log(`OK: ${PIEL} paso la bateria comun (no declara capacidades extra)`);
  process.exit(0);
}
if (base.nodos < 1) morir(new Error(`field is empty (NODOS=${base.nodos}): data did not load, loop untested`));
if (base.trabajoDeNodo < 1)
  morir(new Error("per-node draw code never executed: the smoke proved nothing"));
if (base.patchOn !== false) morir(new Error(`without a board the patch must stay off, got ${base.patchOn}`));
console.log(`OK: boot + frames ran without throwing (NODOS=${base.nodos}, marcas=${base.traza.length})`);

// A piece that CARRIES a measured position must be drawn at it. The skin used
// to decide that for the WHOLE field from `obras[0]`, true while campo.json
// was the only source and false the moment archivo.json arrived carrying 219
// projected works next to 260 that are not. The field then fell back to
// hashes, stretched to ~220.000 px and drew 203 marks per frame instead of
// 7647 -- with the whole suite green, because CI never generated the
// substrate. This compares the drawn field against the data on disk, which is
// the only way that class of defect stops being invisible.
{
  let d = null;
  try {
    d = JSON.parse(readFileSync(join(raiz, "iskvw", "datos", "archivo.json"), "utf8"));
  } catch (e) {
    // Sin sustrato en disco no hay nada que exigir: es el caso del clon limpio.
    if (!e || e.code !== "ENOENT") throw e;
  }
  const esperadas = new Map();
  for (const p of ((d && d.piezas) || []))
    if (p.posicion && typeof p.posicion.y === "number")
      esperadas.set(p.id, (p.posicion.y + 1) * 2600);
  if (esperadas.size) {
    const ys = base.evaluar("NODOS.map(n => [n.obra && n.obra.id, n.y])", []);
    let colocadas = 0, mal = null;
    for (const [id, y] of ys) {
      const q = esperadas.get(id);
      if (q === undefined) continue;
      if (Math.abs(y - q) < 0.5) colocadas++;
      else mal = mal || `${id}: dibujada en ${y.toFixed(0)}, medida en ${q.toFixed(0)}`;
    }
    if (colocadas !== esperadas.size)
      morir(new Error(`the substrate carries ${esperadas.size} measured positions `
        + `and the field honours ${colocadas} (${mal || "id missing from the field"})`));
    console.log(`OK: ${colocadas} works drawn at their measured position`);
  }
}

// ── 2. the board that actually ships, whatever it says ────────────────────
const tableroReal = JSON.parse(readFileSync(join(raiz, "iskvw", "datos", "tablero.json"), "utf8"));
const conArchivo = await correr({ tablero: tableroReal });
if (conArchivo.failed) morir(conArchivo.failed);
const igual = (a, b) => a.traza.length === b.traza.length && a.traza.every((v, i) => v === b.traza[i]);
// La comparacion es contra el MISMO tablero con `patch_efectos` apagado, no
// contra "sin tablero". Lo que se afirma es que el patch apagado dibuja como si
// no existiera -- y eso tiene que seguir siendo cierto aunque el tablero traiga
// OTRAS llaves encendidas.
//
// Hasta el 2026-08-01 el baseline era el run SIN tablero, que funcionaba
// mientras `patch_efectos` era la unica mejora. Al encender `nodo_glifo` el
// dibujo cambio por una llave distinta y este control acuso al patch. Un
// control que atribuye un cambio a la llave equivocada es una falsa alarma, y
// una falsa alarma cuesta lo mismo que un descarte callado.
const sinPatch = JSON.parse(JSON.stringify(tableroReal));
sinPatch.mejoras = { ...(sinPatch.mejoras || {}), patch_efectos: false };
const basePatch = await correr({ tablero: sinPatch });
if (basePatch.failed) morir(basePatch.failed);
if (tableroReal.mejoras && tableroReal.mejoras.patch_efectos) {
  console.log("OK: datos/tablero.json ships with the patch ON (by the artist's hand)");
} else if (!igual(basePatch, conArchivo)) {
  morir(new Error("tablero.json has patch_efectos=false and the drawing CHANGED "
    + "against the same board with the patch off"));
} else {
  console.log(`OK: patch off draws exactly as the same board without it `
    + `(${basePatch.traza.length} marks identical)`);
}
// Y lo que el tablero publicado SI cambia respecto de no tener tablero, se
// dice: es la diferencia que el artista encendio a mano.
if (!igual(base, conArchivo)) {
  console.log(`OK: el tablero publicado cambia el dibujo `
    + `(${base.traza.length} -> ${conArchivo.traza.length} marcas), que es lo que `
    + `sus llaves encendidas afirman hacer`);
}

// ── 2b. the venue layer, behind its own flag on the SAME tablero fetch ─────
// Ported from the venue branch's smoke into this architecture: the shipped
// boot above ran against the REAL tablero.json, so the sala link must mirror
// exactly what mejoras.venue3d says; forcing the flag on must create it, and
// a flag whose consumer vanished must fail here, not at the show.
if (conArchivo.evaluar("typeof capaVenue === 'function'", false) !== true)
  morir(new Error("capaVenue is missing: mejoras.venue3d has no consumer again"));
if (!conArchivo.pedidos.some(u => /tablero\.json$/.test(u)))
  morir(new Error("boot never asked for tablero.json: the flag is read by nobody"));
const flagReal = tableroReal.mejoras.venue3d;
if (conArchivo.salaVisible !== (flagReal === true))
  morir(new Error(`venue layer visible=${conArchivo.salaVisible} with venue3d=${flagReal}: the flag does not gate`));
if (base.salaVisible !== false)
  morir(new Error(`no board and the venue layer is visible=${base.salaVisible}`));
const conSala = await correr({
  tablero: { ...tableroReal, mejoras: { ...tableroReal.mejoras, venue3d: true } },
});
if (conSala.failed) morir(conSala.failed);
if (conSala.salaVisible !== true)
  morir(new Error("forcing venue3d=true did not enable the venue layer"));
if (conSala.evaluar("capaVenue({mejoras:{venue3d:false}})", null) !== false)
  morir(new Error("capaVenue reports on for a tablero that says off"));
console.log(`OK: venue layer gates on venue3d -- shipped ${flagReal === true ? "on" : "off"} `
  + `(visible=${conArchivo.salaVisible}), forced on creates the sala link`);

// ── 3. the patch on, with gains loud enough to be unambiguous ─────────────
// The board's own routing, only louder, plus one node forced to carry the
// break tag: campo.json has no curatorial tags yet, so desgarro would sit
// untested on real data and rot.
// The wiring comes from the BOARD, amplified; it used to be five rows typed
// out here. A hand-written copy of a table that lives somewhere else stops
// matching it the day the table grows, and it did: `luz` was added to the
// board, `solo("luz")` inherited THIS patch instead, its row was never
// compiled, the coefficient stayed at zero and the bench reported the effect
// inert. Two hours went into the effect and the fault was here. Only the gain
// is the bench's business -- what is wired to what is the artist's.
// The improvements come from the REAL board, with the patch forced on. It
// used to declare `mejoras: {patch_efectos: true}` and nothing else, which
// silently measured a regime the site does not run: with `nodo_glifo` off a
// node is drawn as a circle with a radial gradient, and with it ON -- which is
// how the site ships since #433 -- it is drawn as a glyph and that gradient
// never executes. `luz` was written against the gradient radius and this bench
// reported 4.259 dilated radii, a true number about something nobody sees.
// A bench that measures a regime the product does not use is worse than no
// bench: it produces evidence for the wrong thing.
const fuerte = {
  version: 1,
  // `nodo_glifo` OFF on purpose: the four drawing effects have signatures that
  // only separate under the circle regime -- with the node drawn as a glyph its
  // alpha depends on position, so moving a node also recolours it and
  // "curvatura displaces without recolouring" stops being true. Effects are
  // measured where their signature is distinguishable.
  mejoras: { ...(tableroReal.mejoras || {}), patch_efectos: true,
             nodo_glifo: false },
  patch: (tableroReal.patch || []).map(f => ({ ...f, ganancia: 6 })),
};
// The regime the SITE actually runs. `luz` is measured here and nowhere else:
// it dilates the glyph, and the glyph only exists with this key on. The first
// version of this effect scaled `r`, whose only consumer is the gradient in
// `if (!soloGlifo)` -- dead code once the key is on -- and this bench happily
// reported 4.259 dilated radii in a regime the site does not use.
const fuerteGlifo = { ...fuerte,
  mejoras: { ...(tableroReal.mejoras || {}), patch_efectos: true,
             nodo_glifo: true } };
if (!fuerte.patch.length)
  morir(new Error("the board carries no patch rows: the bench has nothing to amplify"));
const marcarQuiebre = "if (typeof NODOS!=='undefined') for (let i=0;i<NODOS.length;i+=7) NODOS[i].sen[3]=1;";
const encendido = await correr({ tablero: fuerte, antes: marcarQuiebre });
if (encendido.failed) morir(encendido.failed);
if (encendido.patchOn !== true) morir(new Error("the board turned the patch on and PATCH.on stayed false"));
if (encendido.emisores < 1) morir(new Error("patch on and nobody emitted: no work deformed anything"));

// Numeric comparison of two drawing traces. `movidas`/`maxSalto`/`maxDy` are
// geometry (a mark landed elsewhere), `tonos` is colour at the same index,
// `difs` is any difference at all including a different mark COUNT -- the
// only signature pulso leaves, since bending glyph time skips or adds glyphs.
function comparar(a, b) {
  let movidas = 0, maxSalto = 0, maxDy = 0, tonos = 0;
  let difs = Math.abs(a.traza.length - b.traza.length);
  const n = Math.min(a.traza.length, b.traza.length);
  for (let i = 0; i < n; i++) {
    if (a.traza[i] !== b.traza[i]) difs++;
    const pa = a.traza[i].split(","), pb = b.traza[i].split(",");
    if (pa.length < 3 || pb.length < 3) continue;
    const dx = Math.abs(+pb[0] - +pa[0]), dy = Math.abs(+pb[1] - +pa[1]);
    if (dx + dy > 0.5) { movidas++; maxSalto = Math.max(maxSalto, Math.hypot(dx, dy)); maxDy = Math.max(maxDy, dy); }
    if (pa.slice(2).join(",") !== pb.slice(2).join(",")) tonos++;
  }
  return { movidas, maxSalto, maxDy, tonos, difs, n };
}

const todo = comparar(base, encendido);
if (!todo.movidas) morir(new Error("patch on and not a single mark moved: the effects are inert"));
if (!todo.tonos) morir(new Error("patch on and no colour changed: sangrado is inert"));
console.log(`OK: patch on deforms -- ${todo.movidas}/${todo.n} marks displaced `
  + `(max ${todo.maxSalto.toFixed(1)} px), ${todo.tonos} colour changes, ${encendido.emisores} emitters`);

// ── 4. gravedad, which touches state and not the canvas ───────────────────
// Measured without walking the field, because the walk overwrites E.pos every
// frame and would hide exactly what this effect does.
// Park the reading in the WIDEST gap of the field. Anywhere else the measured
// archive is dense enough (219 works over some 5200 px) that the nearest work
// is already under the reading and there is nothing left to pull: a null
// measurement that says nothing about the effect.
const desviar = `
if (typeof E!=='undefined' && typeof NODOS!=='undefined' && NODOS.length > 1){
  const ys = NODOS.map(n => n.y).sort((a,b) => a-b);
  let corte = 1, hueco = 0;
  for (let i = 1; i < ys.length; i++){
    const h = ys[i] - ys[i-1];
    if (h > hueco){ hueco = h; corte = i; }
  }
  E.pos = (ys[corte] + ys[corte-1]) / 2;
}`;
const sinGravedad = await correr({ caminar: false, antes: desviar });
const conGravedad = await correr({ tablero: fuerte, caminar: false, antes: desviar });
if (conGravedad.failed) morir(conGravedad.failed);
const deriva = Math.abs(conGravedad.pos - sinGravedad.pos);
if (!(deriva > 1)) morir(new Error(`gravedad is inert: the reading drifted ${deriva} px with the patch on`));
console.log(`OK: gravedad pulls the reading ${deriva.toFixed(1)} px in 30 frames `
  + `(off: ${sinGravedad.pos.toFixed(1)}, on: ${conGravedad.pos.toFixed(1)})`);

// ── 5. the per-effect switches: each effect answers for what it encodes ────
// Under the master flag every effect has its own switch (`efectos` in the
// board). The doublecup rule: each switch is measured by the signature ONLY
// its effect can leave -- and a solo run doubles as proof that the other four
// switches really silence theirs, because their signatures must read zero.
// Derived from the board, NOT written by hand. It used to be a literal list,
// and a literal list stops matching reality the day an effect is added: the
// new effect would never be silenced in a solo run, so every other effect's
// signature would quietly include it. That is the same defect shape this repo
// has already paid for seven times. If the board grows an effect, this grows
// with it or the run fails loudly.
const EFECTOS_NOMBRES = Object.keys(tableroReal.efectos || {});
if (EFECTOS_NOMBRES.length < 5)
  morir(new Error(`the board declares ${EFECTOS_NOMBRES.length} effects: `
    + `the per-effect section cannot measure what is not declared`));
const solo = (efecto) => ({
  ...fuerte,
  efectos: Object.fromEntries(EFECTOS_NOMBRES.map(e => [e, e === efecto])),
});

// pulso bends glyph TIME, and glyph time is only drawn when the field folds
// into a work's form. Headless that state is unreachable through real data
// (the stroke fetch 404s in the sandbox), so the form is poked directly --
// same licence as marcarQuiebre above.
const armarForma = `
if (typeof E!=='undefined' && typeof NODOS!=='undefined' && NODOS.length){
  E.foco = {id:'__smoke__'};
  E.forma = 1;
  E.formaPts = NODOS.map((n, i) => [Math.cos(i*2.399), Math.sin(i*2.399)]);
}`;

// curvatura alone: geometry moves, colour does not.
const baseQ = await correr({ antes: marcarQuiebre });
const soloCurva = await correr({ tablero: solo("curvatura"), antes: marcarQuiebre });
if (soloCurva.failed) morir(soloCurva.failed);
const mCurva = comparar(baseQ, soloCurva);
if (!(mCurva.movidas > 0)) morir(new Error("curvatura alone displaced nothing: its switch is inert"));
if (mCurva.tonos !== 0) morir(new Error(`curvatura alone changed ${mCurva.tonos} colours: sangrado's switch leaks`));
console.log(`OK: curvatura alone displaces (${mCurva.movidas} marks, max ${mCurva.maxSalto.toFixed(1)} px) and zero colour changes`);

// sangrado alone: colour moves, geometry does not.
const soloSangre = await correr({ tablero: solo("sangrado"), antes: marcarQuiebre });
if (soloSangre.failed) morir(soloSangre.failed);
const mSangre = comparar(baseQ, soloSangre);
if (!(mSangre.tonos > 0)) morir(new Error("sangrado alone recoloured nothing: its switch is inert"));
if (mSangre.movidas !== 0) morir(new Error(`sangrado alone displaced ${mSangre.movidas} marks: a geometry effect leaks`));
console.log(`OK: sangrado alone recolours (${mSangre.tonos} marks) and zero displacement`);

// desgarro alone: tears are horizontal rows -- x moves, y never does.
const soloTira = await correr({ tablero: solo("desgarro"), antes: marcarQuiebre });
if (soloTira.failed) morir(soloTira.failed);
const mTira = comparar(baseQ, soloTira);
if (!(mTira.movidas > 0)) morir(new Error("desgarro alone displaced nothing: its switch is inert"));
if (mTira.maxDy > 0.01) morir(new Error(`desgarro alone moved a mark ${mTira.maxDy.toFixed(2)} px in y: tears are x-only, curvatura's switch leaks`));
if (mTira.tonos !== 0) morir(new Error(`desgarro alone changed ${mTira.tonos} colours: sangrado's switch leaks`));
console.log(`OK: desgarro alone tears x-only (${mTira.movidas} marks, max ${mTira.maxSalto.toFixed(1)} px, max dy ${mTira.maxDy.toFixed(2)})`);

// pulso alone: glyph time dilates, so glyphs change or vanish -- but nothing
// is pushed around and no state drifts.
const glifoBase = await correr({ antes: armarForma });
if (glifoBase.failed) morir(glifoBase.failed);
const soloPulso = await correr({ tablero: solo("pulso"), antes: armarForma });
if (soloPulso.failed) morir(soloPulso.failed);
const mPulso = comparar(glifoBase, soloPulso);
if (!(mPulso.difs > 0)) morir(new Error("pulso alone left the glyph trace identical: its switch is inert"));
console.log(`OK: pulso alone bends glyph time (${mPulso.difs} trace differences over ${glifoBase.traza.length} marks)`);

// luz alone: the neighbours DILATE. Its signature is the RADIUS, measured
// directly from the trace -- not inferred from what it leaves untouched.
// The first version of this test demanded zero displacement and zero colour
// change, and that was a guess, not a measurement: `r` feeds the gradient and
// the position jitter downstream, so growing it moves 673 marks and recolours
// 4941 as a side effect. What no other effect does is change the radius
// itself, and that is what gets asserted here.
// Reading it at all took two fixes to THIS bench, not to the effect: the
// trace kept position and colour only (`arc` dropped its radius and
// `createRadialGradient` -- how a node is really painted in the default
// regime -- dropped both of its), and `fuerte.patch` was a hand-typed copy of
// the board that never grew the new row, so `solo("luz")` compiled a
// coefficient of zero. The effect read "inert" twice while being correct.
const soloGlifoBase = await correr({ tablero: {...fuerteGlifo,
  efectos: Object.fromEntries(EFECTOS_NOMBRES.map(e => [e, false]))},
  antes: marcarQuiebre });
if (soloGlifoBase.failed) morir(soloGlifoBase.failed);
const soloLuz = await correr({ tablero: {...fuerteGlifo,
  efectos: Object.fromEntries(EFECTOS_NOMBRES.map(e => [e, e === "luz"]))},
  antes: marcarQuiebre });
if (soloLuz.failed) morir(soloLuz.failed);
const mLuz = comparar(soloGlifoBase, soloLuz);
// La firma de `luz` es el TAMANO TOTAL dibujado, no marca contra marca.
// Comparar por indice no sirve aca: la traza mezcla glifos (9,6 px) y titulos
// (11 px, los dibuja otro bloque), asi que un titulo que aparece o desaparece
// corre todo un lugar y el banco termina comparando un glifo contra un titulo.
// Medido asi decia "luz encoge 1.421 radios" con el efecto funcionando.
// La suma no depende del orden: si el efecto dilata, hay mas pixeles de tipo
// en el cuadro, y punto.
const sumaTam = (t) => t.reduce((acc, m) => {
  const r = m.split(",").find(p => p.startsWith("r"));
  return acc + (r ? parseFloat(r.slice(1)) || 0 : 0);
}, 0);
const conTam = (t) => t.filter(m => m.split(",").some(p => p.startsWith("r"))).length;
const tamBase = sumaTam(soloGlifoBase.traza), tamLuz = sumaTam(soloLuz.traza);
const nBase = conTam(soloGlifoBase.traza), nLuz = conTam(soloLuz.traza);
if (!(nBase > 0))
  morir(new Error("no hay una sola marca con tamano en el regimen glifo: "
    + "el banco no puede medir `luz` y lo dice en vez de aprobarla"));
if (!(tamLuz > tamBase))
  morir(new Error(`luz no dilata: ${tamBase.toFixed(0)} px de tipo sin ella `
    + `contra ${tamLuz.toFixed(0)} con ella (${nBase} y ${nLuz} marcas)`));
console.log(`OK: luz alone dilates the glyphs: ${tamBase.toFixed(0)} -> `
  + `${tamLuz.toFixed(0)} px of type over ${nLuz} marks `
  + `(+${(100*(tamLuz/tamBase-1)).toFixed(1)}%)`);

// gravedad alone: the reading drifts, exactly as in section 4.
const soloGrav = await correr({ tablero: solo("gravedad"), caminar: false, antes: desviar });
if (soloGrav.failed) morir(soloGrav.failed);
const derivaSolo = Math.abs(soloGrav.pos - sinGravedad.pos);
if (!(derivaSolo > 1)) morir(new Error(`gravedad alone is inert: the reading drifted ${derivaSolo} px`));
console.log(`OK: gravedad alone pulls the reading ${derivaSolo.toFixed(1)} px`);

// ── 6. master on, every switch off: the field must not feel a thing ────────
// This is what makes each switch a real gate and not a suggestion: with all
// five off the loud board has to draw mark for mark like no board at all, in
// both drawing modes, and the reading must not drift a pixel.
const mudo = solo("__ninguno__");           // every switch false
const apagadoQ = await correr({ tablero: mudo, antes: marcarQuiebre });
if (apagadoQ.failed) morir(apagadoQ.failed);
if (!igual(baseQ, apagadoQ)) morir(new Error("every switch off and the field trace still changed"));
const apagadoGlifo = await correr({ tablero: mudo, antes: armarForma });
if (apagadoGlifo.failed) morir(apagadoGlifo.failed);
if (!igual(glifoBase, apagadoGlifo)) morir(new Error("every switch off and the glyph trace still changed"));
const apagadoGrav = await correr({ tablero: mudo, caminar: false, antes: desviar });
if (apagadoGrav.failed) morir(apagadoGrav.failed);
const derivaMuda = Math.abs(apagadoGrav.pos - sinGravedad.pos);
if (derivaMuda > 1e-6) morir(new Error(`every switch off and the reading still drifted ${derivaMuda} px`));
console.log(`OK: every switch off under master on draws exactly the base `
  + `(${baseQ.traza.length} + ${glifoBase.traza.length} marks identical, drift ${derivaMuda.toFixed(1)} px)`);
