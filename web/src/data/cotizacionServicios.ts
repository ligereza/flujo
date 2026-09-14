// Valores de la herramienta de cotizacion: items por defecto y presets.
//
// Fuente unica editable: data/cotizacion_servicios.json, que sirve el hub en
// /api/cotizacion-servicios. Los valores escritos aca son el RESPALDO para un
// build estatico sin hub que consultar.
//
// OJO, no confundir con la tarifa de packs de servicio en terreno
// (data/rd_packs.json, la que lee el rider). Estos son servicios de diseno e
// impresion y cambian por trabajo -- palabras del usuario, 2026-07-26: "cada
// archivo de illustrator es distinto y los valores igual". Son un punto de
// partida para editar en la cotizacion, nunca un precio fijo.
//
// Igual que applyPackPriceOverrides en rdBrand.ts, se mutan los arrays EN SU
// LUGAR y la carga ocurre antes de montar React (web/src/main.tsx), asi que
// QuotePanel nunca alcanza a dibujar un valor viejo.

export interface QuoteLineItem {
  label: string;
  qty: number;
  price: number;
  category: string;
}

export interface QuotePreset {
  label: string;
  items: QuoteLineItem[];
}

export const DEFAULT_ITEMS: QuoteLineItem[] = [
  { label: 'Diseño etiqueta (vector, 2 revisiones)', qty: 1, price: 65000, category: 'Diseño' },
  { label: 'Impresión etiqueta 16.5x6.5 cm (100 unidades)', qty: 1, price: 48000, category: 'Impresión' },
  { label: 'Post Instagram (3 variaciones)', qty: 1, price: 30000, category: 'Digital' },
];

export const PRESETS: QuotePreset[] = [
  {
    label: 'Etiqueta Suplementos',
    items: [
      { label: 'Diseño etiqueta vectorial (2 revisiones)', qty: 1, price: 65000, category: 'Diseño' },
      { label: 'Impresión 100 unidades', qty: 1, price: 48000, category: 'Impresión' },
      { label: 'Post Instagram', qty: 3, price: 12000, category: 'Digital' },
    ],
  },
  {
    label: 'Kit Evento BASE',
    items: [
      { label: 'Diseño flyer físico A5', qty: 1, price: 45000, category: 'Diseño' },
      { label: 'Impresión flyer A5 (200 unidades)', qty: 1, price: 35000, category: 'Impresión' },
      { label: 'Diseño plano/rider operativo', qty: 1, price: 30000, category: 'Diseño' },
      { label: 'Post Instagram evento', qty: 1, price: 15000, category: 'Digital' },
    ],
  },
  {
    label: 'Kit Evento MAINSTREAM',
    items: [
      { label: 'Diseño flyer físico A4 (2 idiomas)', qty: 1, price: 80000, category: 'Diseño' },
      { label: 'Impresión flyer A4 (500 unidades)', qty: 1, price: 75000, category: 'Impresión' },
      { label: 'Diseño pendón 80x180 cm', qty: 1, price: 55000, category: 'Diseño' },
      { label: 'Diseño cartelera digital', qty: 1, price: 35000, category: 'Digital' },
      { label: 'Plano/rider MAINSTREAM + SVG', qty: 1, price: 45000, category: 'Diseño' },
      { label: 'Pack Instagram (5 posts)', qty: 1, price: 40000, category: 'Digital' },
    ],
  },
];

/** Un item del JSON -> el que usa el panel. Devuelve null si no es usable. */
function parseItem(raw: unknown): QuoteLineItem | null {
  if (!raw || typeof raw !== 'object') return null;
  const o = raw as Record<string, unknown>;
  const label = typeof o.label === 'string' ? o.label.trim() : '';
  const precio = typeof o.precio === 'number' ? o.precio : NaN;
  if (!label || !Number.isFinite(precio) || precio < 0) return null;
  const qty = typeof o.qty === 'number' && o.qty > 0 ? Math.round(o.qty) : 1;
  const category = typeof o.categoria === 'string' && o.categoria ? o.categoria : 'Otro';
  return { label, qty, price: Math.round(precio), category };
}

/**
 * Lee data/cotizacion_servicios.json via el hub y reemplaza los valores de
 * respaldo. Si el hub no responde o el archivo esta roto, se quedan los del
 * codigo: la cotizacion nunca arranca vacia.
 */
export async function loadCotizacionServicios(signal?: AbortSignal): Promise<void> {
  try {
    const res = await fetch('/api/cotizacion-servicios', { signal });
    if (!res.ok) return;
    const data = await res.json();

    const items = Array.isArray(data?.items_por_defecto)
      ? data.items_por_defecto.map(parseItem).filter((i: QuoteLineItem | null): i is QuoteLineItem => i !== null)
      : [];
    if (items.length) DEFAULT_ITEMS.splice(0, DEFAULT_ITEMS.length, ...items);

    const presets: QuotePreset[] = Array.isArray(data?.presets)
      ? data.presets
          .map((p: unknown) => {
            const o = p as Record<string, unknown>;
            const label = typeof o?.label === 'string' ? o.label.trim() : '';
            const its = Array.isArray(o?.items)
              ? o.items.map(parseItem).filter((i: QuoteLineItem | null): i is QuoteLineItem => i !== null)
              : [];
            return label && its.length ? { label, items: its } : null;
          })
          .filter((p: QuotePreset | null): p is QuotePreset => p !== null)
      : [];
    if (presets.length) PRESETS.splice(0, PRESETS.length, ...presets);
  } catch {
    // Sin hub, o el plazo nos aborto: se usan los valores del codigo.
  }
}
