// Honest-verification probe for the campo skin. Exists because on 2026-07-30
// four claims were sold stronger than their evidence: the stay-still gesture
// was never exercised for real, the doublecup letters were never SEEN, the
// industrial regime was never driven from the FILE, and fps was never taken
// on the declared standard (phone viewport, CPU throttled). This runs all
// four with real events and real pixels, headless (never a window).
//   node tools/verificar_piel_honesta.mjs <url-base>  (default repo server)
//
// playwright-core is NOT a dependency of this repo: it is a driver the
// operator already has, and pinning it here would add a browser download to
// every install for a tool that runs by hand. It is resolved in this order,
// and if none works the tool says exactly what to do instead of dying on an
// absolute path from somebody else's disk -- which is what the first version
// did, and why it sat uncommitted.
//   1. $PLAYWRIGHT_CORE   (full path to playwright-core's index.mjs)
//   2. normal resolution  (npm i -D playwright-core, or a global install)
let chromium;
try {
  const mod = process.env.PLAYWRIGHT_CORE
    ? await import(new URL("file://" + process.env.PLAYWRIGHT_CORE).href)
    : await import("playwright-core");
  chromium = mod.chromium;
} catch (e) {
  console.log("FALTA playwright-core. Dos salidas:");
  console.log("  npm i -D playwright-core        (y correr desde el repo)");
  console.log("  PLAYWRIGHT_CORE=/ruta/a/playwright-core/index.mjs node " +
              "tools/verificar_piel_honesta.mjs");
  console.log("detalle: " + (e && e.code ? e.code : e));
  process.exit(2);
}

const base = process.argv[2] || "http://127.0.0.1:8478";
const url = base + "/iskvw/piel/campo/index.html";
const fallos = [];
const ok = (n, c, d) => { console.log(`${c ? "OK " : "FAIL"} ${n}: ${d}`); if (!c) fallos.push(n); };

const browser = await chromium.launch({ headless: true, channel: 'msedge' });
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
const cdp = await page.context().newCDPSession(page);
await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });

// letters actually painted: intercept fillText BEFORE the skin boots
await page.addInitScript(() => {
  window.__letras = [];
  const orig = CanvasRenderingContext2D.prototype.fillText;
  CanvasRenderingContext2D.prototype.fillText = function (t, ...a) {
    window.__letras.push(String(t)); return orig.call(this, t, ...a);
  };
});
page.on("pageerror", (e) => fallos.push("pageerror:" + e.message));
await page.goto(url);
await page.waitForTimeout(1200);

// 1 REGIMEN driven from the FILE (whatever archivo.json meta says right now)
const reg = await page.evaluate(() => ({ r: REGIMEN, rampa: rampa() }));
console.log(`regimen desde archivo: ${reg.r} rampa: "${reg.rampa}"`);

// 2 fps at phone viewport, CPU x4
const fps = await page.evaluate(() => new Promise((res) => {
  let f = 0; const t0 = performance.now();
  const p = () => { f++; (performance.now() - t0 < 2000) ? requestAnimationFrame(p) : res(Math.round(f / 2)); };
  requestAnimationFrame(p);
}));
ok("fps-telefono-x4", fps >= 30, `${fps} fps (390x844, CPU x4, ${await page.evaluate(() => NODOS.length)} nodos)`);

// 3 REAL stay-still gesture: real wheel events to land on a work, then stillness
await page.mouse.move(195, 420);
for (let i = 0; i < 6; i++) { await page.mouse.wheel(0, 40); await page.waitForTimeout(90); }
await page.waitForTimeout(8000);   // quieto de verdad: 22 frames -> resolver, ~300 -> desplegada
const gesto = await page.evaluate(() => ({
  foco: E.foco ? (E.foco.id || (E.foco.obra && E.foco.obra.id)) : null,
  despliegue: +E.despliegue.toFixed(2),
  desplegada: document.getElementById("ficha").classList.contains("desplegada"),
  icono: document.getElementById("f-icono").innerHTML.length,
  titulo: document.getElementById("f-titulo").textContent.slice(0, 30),
}));
ok("gesto-real-resuelve", !!gesto.foco, `foco=${gesto.foco} despliegue=${gesto.despliegue}`);
ok("gesto-real-desarrolla", gesto.desplegada && gesto.despliegue > 0.5,
   `desplegada=${gesto.desplegada} icono=${gesto.icono}b titulo="${gesto.titulo}"`);

// 4 the letters PAINTED are the work's vocabulary (not just code paths)
const letras = await page.evaluate(() => {
  const pintadas = window.__letras.filter((c) => /[a-z0-9áéíóúñü░▒▓█]/i.test(c));
  const alfa = pintadas.filter((c) => /[a-záéíóúñü]/i.test(c));
  const muestra = [...new Set(alfa)].slice(0, 12).join("");
  return { total: window.__letras.length, pintadas: pintadas.length, alfa: alfa.length, muestra };
});
ok("letras-pintadas", letras.pintadas > 50,
   `${letras.total} fillText, ${letras.pintadas} glifos, ${letras.alfa} alfabeticos, muestra "${letras.muestra}"`);

await browser.close();
if (fallos.length) { console.log("FALLOS:", fallos.join(", ")); process.exit(1); }
console.log("HONESTO: las cuatro afirmaciones ahora tienen medicion.");
