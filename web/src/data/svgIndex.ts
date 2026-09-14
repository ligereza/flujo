// Datos de respaldo con la forma real de svg_index.json.
// Con backend, el indice real llega por GET /api/list-svg-works (ver la funcion
// de fetch mas abajo y `_list_svg_works` en src/flujo/web/hub.py), que escanea
// `svg/` en vivo. Estos datos solo se usan cuando no hay backend.
// (Antes este comentario apuntaba a un generador en scripts/ que no existe;
//  se corrigio 2026-07-25 al auditar referencias muertas de la app.)

// Abiertos a proposito. Antes eran uniones cerradas y el tipo de una pieza se
// decidia con siete ternarios encadenados mas abajo, asi que sumar "pendon" o
// cualquier clase nueva obligaba a editar TypeScript y recompilar. El
// vocabulario real vive en `data/piezas_tipos.json`, lo sirve
// /api/piezas-tipos, y agregar una clase es editar ese archivo.
export type PieceType = string;
export type PieceArea = string;
export type PieceMedio = string;

export interface TipoPieza { id: string; label: string; claves?: string[] }
export interface VocabularioPiezas {
  tipos: TipoPieza[];
  areas: TipoPieza[];
  medios: TipoPieza[];
  tipo_por_defecto?: string;
  area_por_defecto?: string;
  medio_por_defecto?: string;
}

// Respaldo minimo: si el hub no responde, la app sigue clasificando con esto
// en vez de quedarse sin vocabulario. No pretende ser la lista completa.
const VOCAB_RESPALDO: VocabularioPiezas = {
  tipos: [
    { id: 'contraportada', label: 'Contraportada', claves: ['contraportada', 'reverso'] },
    { id: 'etiqueta', label: 'Etiqueta', claves: ['etiqueta'] },
    { id: 'flyer', label: 'Flyer', claves: ['flyer'] },
  ],
  areas: [
    { id: 'eventos', label: 'Eventos', claves: ['evento'] },
    { id: 'suplementos', label: 'Suplementos', claves: ['supl'] },
    { id: 'comun', label: 'Comun', claves: [] },
  ],
  medios: [
    { id: 'digital', label: 'Digital', claves: ['digital', 'ig', 'post'] },
    { id: 'impresion', label: 'Impresion', claves: ['impres'] },
  ],
  tipo_por_defecto: 'etiqueta',
  area_por_defecto: 'comun',
  medio_por_defecto: 'impresion',
};

let VOCAB: VocabularioPiezas = VOCAB_RESPALDO;

export function vocabularioPiezas(): VocabularioPiezas {
  return VOCAB;
}

/** Carga el vocabulario del hub. Se llama una vez al arrancar la app. */
export async function loadVocabularioPiezas(signal?: AbortSignal): Promise<void> {
  try {
    const res = await fetch('/api/piezas-tipos', { signal });
    if (!res.ok) return;
    const data = await res.json();
    if (Array.isArray(data?.tipos) && data.tipos.length) {
      VOCAB = { ...VOCAB_RESPALDO, ...data };
    }
  } catch {
    // Sin hub, se sigue con el respaldo. No es un error que valga interrumpir.
  }
}

/** Primer id cuyo texto de busqueda contiene alguna de sus claves. */
function clasificar(texto: string, opciones: TipoPieza[], porDefecto: string): string {
  for (const o of opciones) {
    for (const clave of o.claves || []) {
      if (clave && texto.includes(clave)) return o.id;
    }
  }
  return porDefecto;
}

export interface SvgPiece {
  id: string;
  name: string;
  type: PieceType;
  area: PieceArea;
  medio: PieceMedio;
  herramienta: string;
  product?: string;
  realSizeCm: string;
  canvasPx: string;
  colors: string[];
  lastModified: string;
  status: 'aprobado' | 'en-revision' | 'borrador';
  svgContent?: string; // inline SVG for demo
  svgUrl?: string; // repo-served URL fallback
  notes?: string;
}

export const MOCK_SVG_INDEX: SvgPiece[] = [
  {"id": "01_linea_suplementos_rd", "name": "01_linea_suplementos_rd.svg", "type": "etiqueta", "area": "suplementos", "medio": "impresion", "herramienta": "illustrator", "product": "Linea completa", "realSizeCm": "10.0x14.0 cm", "canvasPx": "2000x2800", "colors": [], "lastModified": "2026-07-26", "status": "aprobado", "svgUrl": "/svg/suplementos_rd/09_contraportadas_dark/01_linea_suplementos_rd.svg", "notes": "Contraportada regenerable desde _master_contraportadas.json. Lo impreso salio del PDF de dos caras del disenador; el contenido es el mismo"},
  {"id": "02_impulso", "name": "02_impulso.svg", "type": "etiqueta", "area": "suplementos", "medio": "impresion", "herramienta": "illustrator", "product": "Impulso", "realSizeCm": "10.0x14.0 cm", "canvasPx": "2000x2800", "colors": [], "lastModified": "2026-07-26", "status": "aprobado", "svgUrl": "/svg/suplementos_rd/09_contraportadas_dark/02_impulso.svg", "notes": "Contraportada regenerable desde _master_contraportadas.json. Lo impreso salio del PDF de dos caras del disenador; el contenido es el mismo"},
  {"id": "03_hongos_adaptogenos", "name": "03_hongos_adaptogenos.svg", "type": "etiqueta", "area": "suplementos", "medio": "impresion", "herramienta": "illustrator", "product": "Hongos Adaptogenos", "realSizeCm": "10.0x14.0 cm", "canvasPx": "2000x2800", "colors": [], "lastModified": "2026-07-26", "status": "aprobado", "svgUrl": "/svg/suplementos_rd/09_contraportadas_dark/03_hongos_adaptogenos.svg", "notes": "Contraportada regenerable desde _master_contraportadas.json. Lo impreso salio del PDF de dos caras del disenador; el contenido es el mismo"},
  {"id": "04_pre_fiesta", "name": "04_pre_fiesta.svg", "type": "etiqueta", "area": "suplementos", "medio": "impresion", "herramienta": "illustrator", "product": "Pre Fiesta", "realSizeCm": "10.0x14.0 cm", "canvasPx": "2000x2800", "colors": [], "lastModified": "2026-07-26", "status": "aprobado", "svgUrl": "/svg/suplementos_rd/09_contraportadas_dark/04_pre_fiesta.svg", "notes": "Contraportada regenerable desde _master_contraportadas.json. Lo impreso salio del PDF de dos caras del disenador; el contenido es el mismo"},
  {"id": "05_magnesio", "name": "05_magnesio.svg", "type": "etiqueta", "area": "suplementos", "medio": "impresion", "herramienta": "illustrator", "product": "Magnesio", "realSizeCm": "10.0x14.0 cm", "canvasPx": "2000x2800", "colors": [], "lastModified": "2026-07-26", "status": "aprobado", "svgUrl": "/svg/suplementos_rd/09_contraportadas_dark/05_magnesio.svg", "notes": "Contraportada regenerable desde _master_contraportadas.json. Lo impreso salio del PDF de dos caras del disenador; el contenido es el mismo"},
  {"id": "06_creatina_monohidratada", "name": "06_creatina_monohidratada.svg", "type": "etiqueta", "area": "suplementos", "medio": "impresion", "herramienta": "illustrator", "product": "Creatina", "realSizeCm": "10.0x14.0 cm", "canvasPx": "2000x2800", "colors": [], "lastModified": "2026-07-26", "status": "aprobado", "svgUrl": "/svg/suplementos_rd/09_contraportadas_dark/06_creatina_monohidratada.svg", "notes": "Contraportada regenerable desde _master_contraportadas.json. Lo impreso salio del PDF de dos caras del disenador; el contenido es el mismo"},
  {"id": "07_proteina", "name": "07_proteina.svg", "type": "etiqueta", "area": "suplementos", "medio": "impresion", "herramienta": "illustrator", "product": "Proteina", "realSizeCm": "10.0x14.0 cm", "canvasPx": "2000x2800", "colors": [], "lastModified": "2026-07-26", "status": "aprobado", "svgUrl": "/svg/suplementos_rd/09_contraportadas_dark/07_proteina.svg", "notes": "Contraportada regenerable desde _master_contraportadas.json. Lo impreso salio del PDF de dos caras del disenador; el contenido es el mismo"},
  {"id": "08_post_fiesta", "name": "08_post_fiesta.svg", "type": "etiqueta", "area": "suplementos", "medio": "impresion", "herramienta": "illustrator", "product": "Post Fiesta", "realSizeCm": "10.0x14.0 cm", "canvasPx": "2000x2800", "colors": [], "lastModified": "2026-07-26", "status": "aprobado", "svgUrl": "/svg/suplementos_rd/09_contraportadas_dark/08_post_fiesta.svg", "notes": "Contraportada regenerable desde _master_contraportadas.json. Lo impreso salio del PDF de dos caras del disenador; el contenido es el mismo"},
  {"id": "packs_servicios_rd_dark", "name": "packs_servicios_rd_dark_editable.svg", "type": "flyer", "area": "eventos", "medio": "digital", "herramienta": "svg", "product": "Packs de servicio", "realSizeCm": "", "canvasPx": "", "colors": [], "lastModified": "2026-07-26", "status": "aprobado", "svgUrl": "/svg/eventos_rd/packs_servicios_rd_dark_editable.svg", "notes": "Los 3 packs de servicio, version oscura"},
  {"id": "packs_servicios_rd_blanco", "name": "packs_servicios_rd_blanco_editable.svg", "type": "flyer", "area": "eventos", "medio": "impresion", "herramienta": "svg", "product": "Packs de servicio", "realSizeCm": "", "canvasPx": "", "colors": [], "lastModified": "2026-07-26", "status": "aprobado", "svgUrl": "/svg/eventos_rd/packs_servicios_rd_blanco_editable.svg", "notes": "Los 3 packs de servicio, version para imprimir"},
] as const;

export async function loadFromApi(): Promise<SvgPiece[]> {
  const resp = await fetch('/api/list-svg-works');
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const data = await resp.json();

  const readSvg = async (path?: string, inline?: string): Promise<{ svgContent?: string; svgUrl?: string }> => {
    if (inline) return { svgContent: inline };
    if (!path) return {};
    const normalized = path.replace(/^\/+/, '');
    const svgUrl = `/${normalized}`;
    try {
      const svgResp = await fetch(svgUrl);
      if (!svgResp.ok) return { svgUrl };
      const text = await svgResp.text();
      return text.trim().startsWith('<svg') || text.includes('<svg') ? { svgContent: text, svgUrl } : { svgUrl };
    } catch {
      return { svgUrl };
    }
  };

  const normalizePiece = async (item: any, groupName = 'comun'): Promise<SvgPiece> => {
    const name = String(item.name || item.id || 'pieza');
    const lower = `${name} ${item.path || ''} ${item.kind || ''}`.toLowerCase();
    const path = item.path ? String(item.path) : undefined;
    const svg = await readSvg(path, item.svgContent || item.svg);
    return {
      id: String(item.id || item.slug || path || name.replace(/\s+/g, '_').toLowerCase()),
      name,
      type: clasificar(lower, VOCAB.tipos, VOCAB.tipo_por_defecto || 'etiqueta'),
      area: clasificar(String(groupName).toLowerCase(), VOCAB.areas, VOCAB.area_por_defecto || 'comun'),
      medio: clasificar(lower, VOCAB.medios, VOCAB.medio_por_defecto || 'impresion'),
      herramienta: String(item.kind || item.herramienta || 'repo'),
      product: item.product,
      realSizeCm: String(item.realSizeCm || item.real_size_cm || '—'),
      canvasPx: String(item.canvasPx || item.canvas_px || 'SVG'),
      colors: Array.isArray(item.colors) ? item.colors : [],
      lastModified: String(item.lastModified || item.modified || 'repo'),
      status: item.status || 'borrador',
      notes: item.notes || path,
      ...svg,
    } as SvgPiece;
  };

  if (Array.isArray(data?.pieces)) return Promise.all(data.pieces.map((item: any) => normalizePiece(item, item.group || item.area || 'comun')));
  if (Array.isArray(data?.works)) return Promise.all(data.works.map((item: any) => normalizePiece(item, item.group || item.area || 'comun')));
  if (data?.groups && typeof data.groups === 'object') {
    const batches = await Promise.all(
      Object.entries(data.groups).map(async ([groupName, items]) => Promise.all((items as any[]).map(item => normalizePiece(item, groupName))))
    );
    return batches.flat();
  }
  return [];
}

/** Los tipos que ofrece el filtro. Salen del vocabulario, no de una lista fija. */
export function typeOptions(): string[] {
  return VOCAB.tipos.map(t => t.id);
}

// Compatibilidad: se conserva el nombre que ya usaba el visor, pero ahora lee
// el vocabulario cargado en vez de una constante escrita a mano.
export const TYPE_OPTIONS: PieceType[] = new Proxy([] as string[], {
  get(_t, prop) {
    const actual = typeOptions();
    const v = (actual as any)[prop];
    return typeof v === 'function' ? v.bind(actual) : v;
  },
}) as PieceType[];
