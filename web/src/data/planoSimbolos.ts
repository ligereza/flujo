// Simbolos propios del plano: los que la jefa de eventos agrega soltando un
// .svg en data/plano_simbolos/ y declarandolo en data/plano_simbolos.json.
//
// El hub los sirve en /api/plano-simbolos y esto los carga ANTES de montar
// React (web/src/main.tsx), asi PlanoTool ya los tiene en su primer render.
// Hasta el 2026-07-26 el editor visual tenia su propia lista fija de iconos: un
// simbolo agregado aparecia en el plano de `flujo plano` y NO en el editor,
// que es justamente donde ella trabaja.
//
// Sin hub (bundle estatico) no hay simbolos propios y el editor funciona con
// los de fabrica, igual que antes.

import { trazarEnNavegador } from './trazador';

export interface SimboloPropio {
  id: string;
  etiqueta: string;
  color: string;
  zona: string;
  cuando: string;
  /** Contenido del .svg de la disenadora. Vacio = solo reetiqueta uno de fabrica. */
  svg: string;
}

/** Se muta en su lugar: PlanoTool la lee en vivo, no copia al importar. */
export const SIMBOLOS_PROPIOS: SimboloPropio[] = [];

const POR_ID = new Map<string, SimboloPropio>();

export function simboloPropio(id: string): SimboloPropio | undefined {
  return POR_ID.get(id);
}

const RE_COMENTARIO = /<!--[\s\S]*?-->/g;
const RE_SCRIPT = /<script\b[\s\S]*?<\/script\s*>/gi;
const RE_EVENTO = /\son[a-z]+\s*=\s*("[\s\S]*?"|'[\s\S]*?')/gi;
const RE_DECL = /<\?xml[\s\S]*?\?>|<!DOCTYPE[\s\S]*?>/gi;
const RE_SVG_ABRE = /<svg\b([^>]*)>/i;
const RE_VIEWBOX = /viewBox\s*=\s*["']([^"']+)["']/i;
const RE_MEDIDA = /\b(width|height)\s*=\s*["']([\d.]+)/gi;

function medidas(atributos: string): [number, number] {
  const vb = RE_VIEWBOX.exec(atributos);
  if (vb) {
    const p = vb[1].replace(/,/g, ' ').split(/\s+/).filter(Boolean);
    if (p.length === 4) {
      const w = Number(p[2]);
      const h = Number(p[3]);
      if (w > 0 && h > 0) return [w, h];
    }
  }
  const found: Record<string, number> = {};
  let m: RegExpExecArray | null;
  RE_MEDIDA.lastIndex = 0;
  while ((m = RE_MEDIDA.exec(atributos)) !== null) found[m[1].toLowerCase()] = Number(m[2]);
  const w = found.width || 0;
  const h = found.height || 0;
  return w > 0 && h > 0 ? [w, h] : [160, 160];
}

/**
 * Encaja el .svg de la disenadora en la casilla del icono, centrado en (cx, cy).
 *
 * MISMA convencion que los iconos de fabrica y que el lado Python
 * (src/flujo/plano/iconos.py): lienzo de 160x160 escalado por `scale`. Se
 * mantiene la proporcion, se reemplaza `currentColor` por el color declarado y
 * se recorta lo que no debe viajar en un plano que se entrega (script, on*).
 * Devuelve '' si el archivo no parece un SVG, y quien llama dibuja el marcador
 * neutro de siempre.
 */
export function markupSimboloPropio(
  svg: string, color: string, cx: number, cy: number, scale: number,
): string {
  const limpio = svg
    .replace(RE_DECL, '')
    .replace(RE_COMENTARIO, '')
    .replace(RE_SCRIPT, '')
    .replace(RE_EVENTO, '');
  const apertura = RE_SVG_ABRE.exec(limpio);
  if (!apertura) return '';
  const [w, h] = medidas(apertura[1]);
  let interior = limpio.slice(apertura.index + apertura[0].length);
  const cierre = interior.toLowerCase().lastIndexOf('</svg>');
  if (cierre !== -1) interior = interior.slice(0, cierre);
  interior = interior.split('currentColor').join(color).trim();

  const k = (160 * scale) / Math.max(w, h);
  const tx = cx - (k * w) / 2;
  const ty = cy - (k * h) / 2;
  return `<g transform="translate(${tx.toFixed(2)} ${ty.toFixed(2)}) scale(${k.toFixed(4)})">${interior}</g>`;
}

/**
 * Traza una imagen (PNG/JPG) y devuelve el SVG del contorno, SIN guardarlo.
 *
 * Se muestra antes de guardar a proposito: un trazado automatico puede salir
 * sucio, y quien decide si sirve es quien lo mira. Traza siluetas, que es lo
 * que es un icono; una foto va a dar una mancha.
 */
export async function trazarImagen(archivo: File): Promise<{ ok: boolean; svg?: string; error?: string }> {
  try {
    const buf = new Uint8Array(await archivo.arrayBuffer());
    let bin = '';
    for (let i = 0; i < buf.length; i++) bin += String.fromCharCode(buf[i]);
    const res = await fetch('/api/plano-simbolos/trazar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ imagen_b64: btoa(bin) }),
    });
    const data = await res.json().catch(() => ({}));
    if (!data?.ok) return { ok: false, error: data?.error || 'No se pudo trazar la imagen.' };
    return { ok: true, svg: data.svg };
  } catch {
    // Sin servidor se traza en el navegador, con el mismo algoritmo. Antes
    // esto devolvia "abri la app con py -m flujo app", que es mandar a una
    // consola a quien recibio un archivo justamente para no tener una.
    try {
      return { ok: true, svg: await trazarEnNavegador(archivo) };
    } catch (e) {
      return { ok: false, error: (e as Error)?.message || 'No se pudo trazar la imagen.' };
    }
  }
}

export interface NuevoSimbolo {
  etiqueta: string;
  color: string;
  zona: string;
  cuando: string;
  /** Contenido del archivo .svg que eligio la usuaria. */
  svg: string;
}

/**
 * Guarda un simbolo nuevo y recarga el catalogo.
 *
 * Devuelve el motivo cuando falla: quien lo usa no lee logs, y un fallo mudo
 * se siente como "la app no guarda". Sin hub no hay donde escribir y se dice.
 */
const CLAVE_LOCAL = 'plano_simbolos_propios';

/** Guarda el simbolo en el navegador. Es el camino del HTML suelto.
 *
 * Sin esto, el bundle que se le manda a la encargada de eventos le decia "no
 * hay conexion" justo en la accion que mas usa. Y no es un parche: ella
 * trabaja con un archivo, no con un servidor. El simbolo queda en su navegador
 * y ADEMAS viaja dentro del preset que exporta, asi que llega al otro lado.
 */
/** Etiqueta -> id, con la MISMA regla que `_slug_simbolo` del hub.
 *  Si las dos difirieran, el mismo símbolo tendría dos identidades según
 *  dónde se guardó, y un preset dejaría de encontrarlo. */
function slugSimbolo(texto: string): string {
  return texto
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 40);
}

function guardarLocal(nuevo: NuevoSimbolo): { ok: boolean; error?: string } {
  const id = slugSimbolo(String(nuevo?.etiqueta || ''));
  if (!id) return { ok: false, error: 'El símbolo necesita un nombre.' };
  const s: SimboloPropio = {
    id,
    etiqueta: String(nuevo.etiqueta || id),
    color: String(nuevo.color || '#9ca3af'),
    zona: String(nuevo.zona || ''),
    cuando: String((nuevo as { cuando?: string }).cuando || 'siempre'),
    svg: String(nuevo.svg || ''),
  };
  const previo = POR_ID.get(id);
  if (previo) Object.assign(previo, s);
  else {
    SIMBOLOS_PROPIOS.push(s);
    POR_ID.set(id, s);
  }
  try {
    localStorage.setItem(CLAVE_LOCAL, JSON.stringify(simbolosPropiosSpec()));
  } catch {
    // Sin localStorage el simbolo vive en esta pestana y viaja en el preset.
    // Vale mas que negarse a guardarlo.
  }
  return { ok: true };
}

/** Recupera los simbolos guardados en este navegador. Los llama el arranque. */
export function cargarSimbolosLocales(): number {
  try {
    return registrarSimbolosPropios(JSON.parse(localStorage.getItem(CLAVE_LOCAL) || '[]'));
  } catch {
    return 0;
  }
}

export async function guardarSimbolo(nuevo: NuevoSimbolo): Promise<{ ok: boolean; error?: string }> {
  // Con hub, el simbolo va al repo y lo ve tambien `flujo plano`. Sin hub
  // (HTML suelto) queda en el navegador: no es lo mismo, pero es trabajo
  // guardado en vez de un mensaje de error.
  try {
    const res = await fetch('/api/plano-simbolos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(nuevo),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data?.ok) {
      return { ok: false, error: data?.error || `No se pudo guardar (${res.status}).` };
    }
    await loadPlanoSimbolos();
    return { ok: true };
  } catch {
    return guardarLocal(nuevo);
  }
}

/** Los simbolos propios tal cual, para meterlos dentro de un preset. */
export function simbolosPropiosSpec(): SimboloPropio[] {
  return SIMBOLOS_PROPIOS.map(s => ({ ...s }));
}

/** Registra simbolos que llegaron DENTRO de un preset, sin hub y sin guardar.
 *
 * Por que existe: un preset exportado por la encargada puede traer iconos que
 * ella creo. Si al abrirlo del otro lado esos iconos no estan, el plano se ve
 * con huecos justo donde ella puso lo suyo. Se suman a los que haya, sin pisar
 * uno existente con el mismo id -- lo del disco manda sobre lo que viaja.
 */
export function registrarSimbolosPropios(spec: unknown): number {
  if (!Array.isArray(spec)) return 0;
  let sumados = 0;
  for (const raw of spec) {
    const id = typeof (raw as SimboloPropio)?.id === 'string'
      ? (raw as SimboloPropio).id.trim() : '';
    if (!id || POR_ID.has(id)) continue;
    const s: SimboloPropio = {
      id,
      etiqueta: String((raw as SimboloPropio).etiqueta || id),
      color: String((raw as SimboloPropio).color || '#9ca3af'),
      zona: String((raw as SimboloPropio).zona || ''),
      cuando: String((raw as SimboloPropio).cuando || 'siempre'),
      svg: String((raw as SimboloPropio).svg || ''),
    };
    SIMBOLOS_PROPIOS.push(s);
    POR_ID.set(id, s);
    sumados++;
  }
  return sumados;
}

export async function loadPlanoSimbolos(signal?: AbortSignal): Promise<void> {
  try {
    const res = await fetch('/api/plano-simbolos', { signal });
    if (!res.ok) return;
    const data = await res.json();
    if (!Array.isArray(data?.simbolos)) return;

    const limpios: SimboloPropio[] = [];
    for (const raw of data.simbolos) {
      const id = typeof raw?.id === 'string' ? raw.id.trim() : '';
      if (!id) continue;
      limpios.push({
        id,
        etiqueta: typeof raw.etiqueta === 'string' && raw.etiqueta ? raw.etiqueta : id,
        color: typeof raw.color === 'string' && raw.color ? raw.color : '#9ca3af',
        zona: typeof raw.zona === 'string' ? raw.zona : '',
        cuando: typeof raw.cuando === 'string' ? raw.cuando : 'siempre',
        svg: typeof raw.svg === 'string' ? raw.svg : '',
      });
    }
    SIMBOLOS_PROPIOS.splice(0, SIMBOLOS_PROPIOS.length, ...limpios);
    POR_ID.clear();
    for (const s of limpios) POR_ID.set(s.id, s);
  } catch {
    // Sin hub, o el plazo nos aborto: solo los simbolos de fabrica.
  }
}
