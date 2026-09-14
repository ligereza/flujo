// Entry point of the hub (all panels). See mainPlano.tsx for the standalone
// plano bundle.
//
// Two sets of editable values are fetched from the hub BEFORE React mounts, so
// no panel ever renders a stale price:
//   - the field-service tariff, data/rd_packs.json, the same file the rider and
//     the Python quote read. Until 2026-07-26 the web carried its own hardcoded
//     copy, so editing it changed the PDF and left the app on the old figures.
//   - the quote tool's line items, data/cotizacion_servicios.json. Design and
//     printing services, which change per job (the user, 2026-07-26: "cada
//     archivo de illustrator es distinto y los valores igual").
//   - the floor-plan symbols the events manager adds, data/plano_simbolos.json,
//     so the editor draws the same ones the Python plan does.
//
// If the hub is not reachable (a static build opened from disk) the code values
// stay: they are the same numbers, only frozen at build time.
//
// Both fetches are on a hard deadline. Mounting waits for them so no panel ever
// paints a stale figure, and that is exactly why they must not be able to wait
// forever: a hub that accepts the connection and then hangs would leave a blank
// page with nothing on screen to explain it. Past the deadline the requests are
// aborted and the app mounts on the code values.
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App";
import { applyPackPriceOverrides, type PackId } from "./rdBrand";
import { loadCotizacionServicios } from "./data/cotizacionServicios";
import { loadPlanoSimbolos } from "./data/planoSimbolos";
import { loadVocabularioPiezas } from "./data/svgIndex";

/** Tiempo maximo que la app espera al hub antes de montar con los valores del codigo. */
const CONFIG_TIMEOUT_MS = 2500;

async function loadTariff(signal: AbortSignal): Promise<void> {
  try {
    const res = await fetch("/api/rd-packs", { signal });
    if (!res.ok) return;
    const data = await res.json();
    const packs = data?.packs;
    if (!packs || typeof packs !== "object") return;
    const overrides: Partial<Record<PackId, number>> = {};
    for (const [id, pack] of Object.entries(packs)) {
      const precio = (pack as { precio?: unknown })?.precio;
      if (typeof precio === "number") overrides[id as PackId] = precio;
    }
    applyPackPriceOverrides(overrides);
  } catch {
    // Hub unreachable, or the deadline aborted us: keep the code values.
  }
}

const control = new AbortController();
const deadline = setTimeout(() => control.abort(), CONFIG_TIMEOUT_MS);

Promise.all([
  loadTariff(control.signal),
  loadCotizacionServicios(control.signal),
  loadPlanoSimbolos(control.signal),
  loadVocabularioPiezas(control.signal),
]).finally(() => {
  clearTimeout(deadline);
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <App />
    </StrictMode>
  );
});
