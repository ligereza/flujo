// Boots the venue skin's inline JS in node with DOM stubs, and hands back its
// live scope. Shared by tools/venue3d_smoke.mjs (which asserts on it) and
// tools/venue_secuencia.mjs (which exports frames from it) so that BOTH run the
// same projection the browser runs -- an exported sequence that drew a slightly
// different room than the one on screen would only surface at the show.
import { readFileSync } from "node:fs";
import vm from "node:vm";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

export const RAIZ = join(dirname(fileURLToPath(import.meta.url)), "..");

const noop = () => {};

export async function correr(search = "", opciones = {}) {
  const { ancho = 900, alto = 600, cuadros = 10 } = opciones;
  const html = readFileSync(join(RAIZ, "iskvw", "piel", "venue", "index.html"), "utf8");
  const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
  if (!scripts.length) throw new Error("no inline <script> found in the venue skin");

  const conteo = { segmentos: 0, trazos: 0 };   // lineTo / stroke actually issued
  const ctx2d = new Proxy({}, {
    get: (t, k) => {
      if (k === "canvas") return canvas;
      if (k === "lineTo") return () => { conteo.segmentos++; };
      if (k === "stroke") return () => { conteo.trazos++; };
      if (k === "measureText") return () => ({ width: 10 });
      return noop;
    },
    set: () => true,
  });
  const canvas = {
    getContext: () => ctx2d, width: ancho, height: alto,
    clientWidth: ancho, clientHeight: alto, style: {},
    addEventListener: noop, removeEventListener: noop, setPointerCapture: noop,
    getBoundingClientRect: () => ({ left: 0, top: 0, width: ancho, height: alto }),
  };
  const el = () => ({
    classList: { add: noop, remove: noop, toggle: noop, contains: () => false },
    style: {}, dataset: {}, addEventListener: noop, removeEventListener: noop,
    textContent: "", innerHTML: "", appendChild: noop, setAttribute: noop,
    querySelectorAll: () => [],
    getBoundingClientRect: () => ({ left: 0, top: 0, width: ancho, height: alto }),
  });
  const elements = new Map();
  const getEl = id => {
    if (id === "c") return canvas;
    if (!elements.has(id)) elements.set(id, el());
    return elements.get(id);
  };

  let rafQueue = [];
  const sandbox = {
    console, Math, JSON, Date, Array, Object, Number, String, Map, Set, RegExp,
    Error, isNaN, parseInt, parseFloat, URLSearchParams,
    performance: { now: () => rafQueue.length * 16.7 },
    requestAnimationFrame: cb => { rafQueue.push(cb); return rafQueue.length; },
    cancelAnimationFrame: noop,
    setTimeout: () => 0, clearTimeout: noop, setInterval: () => 0, clearInterval: noop,
    // the REAL venue file: what the loop chews on must be what ships, not a
    // hand-made stub that can drift from the schema.
    fetch: async (url) => {
      const m = String(url).match(/venues\/([a-z0-9-]+)\.json$/);
      if (m) {
        try {
          const txt = readFileSync(join(RAIZ, "data", "venues", `${m[1]}.json`), "utf8");
          return { ok: true, json: async () => JSON.parse(txt) };
        } catch { return { ok: false, json: async () => ({}) }; }
      }
      return { ok: false, json: async () => ({}) };
    },
    addEventListener: noop, removeEventListener: noop, history: { replaceState: noop },
    location: { hash: "", search, href: "http://smoke.local/" + search },
    navigator: { maxTouchPoints: 0 },
    devicePixelRatio: 1, innerWidth: ancho, innerHeight: alto,
  };
  sandbox.window = sandbox;
  sandbox.document = {
    getElementById: getEl,
    querySelector: () => el(), querySelectorAll: () => [],
    addEventListener: noop, removeEventListener: noop,
    body: el(), documentElement: el(), hidden: false,
    createElement: () => el(),
  };

  const context = vm.createContext(sandbox);
  let falla = null;
  // arrancar() is async and fire-and-forget: its crash surfaces as an unhandled
  // rejection on the shared microtask queue, not as a sync throw.
  const onRejection = e => { falla = falla || e; };
  process.on("unhandledRejection", onRejection);
  try {
    for (const src of scripts) vm.runInContext(src, context, { timeout: 10000 });
  } catch (e) { falla = e; }
  await new Promise(r => setTimeout(r, 50));      // drain the async loader
  if (!falla) {
    try {
      for (let i = 0; i < cuadros && rafQueue.length; i++) {
        const batch = rafQueue; rafQueue = [];
        for (const cb of batch) cb(i * 16.7);
      }
    } catch (e) { falla = e; }
  }
  process.off("unhandledRejection", onRejection);
  return { falla, conteo, elements, leer: expr => vm.runInContext(expr, context) };
}
