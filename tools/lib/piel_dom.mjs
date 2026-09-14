// The DOM stubs a skin needs, in ONE place.
//
// Both `iskvw_piel_smoke.mjs` (correctness) and `iskvw_piel_medir.mjs` (frame
// cost) boot a skin's own inline script inside a node `vm`. Each carried its
// own copy of the stubs, and both copies were shaped like the `campo` skin: a
// canvas returned only for the id "c", an element with six methods, no
// namespaced createElement. That is why two of the three published skins had no
// verification and no measurement at all -- pointing either tool at them died
// on the stubs, never on the skin.
//
// Measured 2026-07-31, the moment the battery was aimed at the other two:
//     terminal   canvas.getContext is not a function   (canvas has another id)
//     venue      L.querySelectorAll is not a function  (element query missing)
// Neither was a defect of the skin. Both skins work: venue draws 503 edges,
// terminal 3.480 marks.
//
// Fixing that twice, once per tool, is the same defect class this repo spent a
// day paying for elsewhere (a provider roster written by hand in two files, so
// one went stale in silence). Hence: one module, two callers.
//
// The stub is deliberately GENEROUS -- every element can be a canvas and
// answers the surface a skin plausibly touches. That can hide a real DOM bug,
// and the trade is stated rather than hidden: the alternative was two skins
// with no verification whatsoever.

const noop = () => {};

/** Un elemento generico. `ctx2d` es el contexto que devuelve `getContext`. */
export function elementoGenerico(ctx2d) {
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
    replaceChildren: noop, remove: noop,
    setAttribute: noop, removeAttribute: noop, getAttribute: () => null,
    hasAttribute: () => false,
    querySelector: () => elementoGenerico(ctx2d),
    querySelectorAll: () => [],
    closest: () => null, contains: () => false,
    focus: noop, blur: noop, click: noop, scrollIntoView: noop,
    getBoundingClientRect: () => ({ left: 0, top: 0, right: 800, bottom: 600,
                                    width: 800, height: 600, x: 0, y: 0 }),
    toDataURL: () => "data:,",
  };
  nodo.cloneNode = () => elementoGenerico(ctx2d);
  return nodo;
}

/** `document` completo, mas el canvas del id "c" que las pieles viejas usan. */
export function documentoStub(ctx2d, canvas) {
  const elements = new Map();
  const getEl = (id) => {
    if (id === "c" && canvas) return canvas;
    if (!elements.has(id)) elements.set(id, elementoGenerico(ctx2d));
    return elements.get(id);
  };
  return {
    getElementById: getEl,
    querySelector: () => elementoGenerico(ctx2d),
    querySelectorAll: () => [],
    addEventListener: noop, removeEventListener: noop,
    body: elementoGenerico(ctx2d),
    documentElement: elementoGenerico(ctx2d),
    hidden: false,
    createElement: () => elementoGenerico(ctx2d),
    // Namespaced: una piel que arma SVG lo usa. Sin esto moria en el primer
    // gesto que tocara esa rama -- justo la que nunca se ejercitaba.
    createElementNS: () => elementoGenerico(ctx2d),
    createTextNode: () => elementoGenerico(ctx2d),
    _elements: elements,
  };
}

/**
 * Resuelve lo que una piel pide por fetch, DESDE su propio directorio.
 * Devuelve la lista de segmentos relativa a la raiz del repo, o null si el
 * pedido se sale del checkout: esto lee archivos reales y una piel no puede
 * usar la sonda para mirar afuera.
 *
 * Los `..` NO se colapsan antes de combinar. Ese fue un error real: con
 * `../../datos/archivo.json` la lista se comia a si misma y `campo` se quedaba
 * sin sustrato (NODOS=8, el respaldo de herramientas) sin decir nada.
 */
export function resolverPedido(url, piel) {
  const limpio = String(url).replace(/[?#].*$/, "");
  const abs = ["iskvw", "piel", piel];
  for (const p of limpio.split("/")) {
    if (p === "" || p === ".") continue;
    if (p === "..") { if (!abs.length) return null; abs.pop(); }
    else abs.push(p);
  }
  return abs;
}
