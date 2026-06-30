// Mock data based on the real svg_index.json structure from vibecodeine.
// In production this comes from `py scripts/generate_svg_index.py`.

export type PieceType = 'etiqueta' | 'flyer' | 'pendon' | 'post-ig' | 'sticker' | 'logo' | 'rider' | 'cartelera' | 'stand';
export type PieceArea = 'suplementos' | 'eventos' | 'comun';
export type PieceMedio = 'impresion' | 'digital';

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
  {"id": "01_linea_suplementos_rd_editable", "name": "01_linea_suplementos_rd_editable.svg", "type": "flyer", "area": "suplementos", "medio": "impresion", "herramienta": "svg+illustrator", "product": "Linea completa", "realSizeCm": "10.0x14.0 cm", "canvasPx": "2000x2800", "colors": [], "lastModified": "2026-06-30", "status": "aprobado", "svgUrl": "/svg/suplementos_rd/01_linea_suplementos_rd_editable.svg", "notes": "Real SVG - suplementos_rd"},
  {"id": "02_impulso_editable", "name": "02_impulso_editable.svg", "type": "flyer", "area": "suplementos", "medio": "impresion", "herramienta": "svg+illustrator", "product": "Impulso", "realSizeCm": "10.0x14.0 cm", "canvasPx": "2000x2800", "colors": [], "lastModified": "2026-06-30", "status": "aprobado", "svgUrl": "/svg/suplementos_rd/02_impulso_editable.svg", "notes": "Real SVG - suplementos_rd"},
  {"id": "03_hongos_adaptogenos_editable", "name": "03_hongos_adaptogenos_editable.svg", "type": "flyer", "area": "suplementos", "medio": "impresion", "herramienta": "svg+illustrator", "product": "Hongos Adaptogenos", "realSizeCm": "10.0x14.0 cm", "canvasPx": "2000x2800", "colors": [], "lastModified": "2026-06-30", "status": "aprobado", "svgUrl": "/svg/suplementos_rd/03_hongos_adaptogenos_editable.svg", "notes": "Real SVG - suplementos_rd"},
  {"id": "04_pre_fiesta_editable", "name": "04_pre_fiesta_editable.svg", "type": "flyer", "area": "suplementos", "medio": "impresion", "herramienta": "svg+illustrator", "product": "Pre Fiesta", "realSizeCm": "10.0x14.0 cm", "canvasPx": "2000x2800", "colors": [], "lastModified": "2026-06-30", "status": "aprobado", "svgUrl": "/svg/suplementos_rd/04_pre_fiesta_editable.svg", "notes": "Real SVG - suplementos_rd"},
  {"id": "05_magnesio_editable", "name": "05_magnesio_editable.svg", "type": "flyer", "area": "suplementos", "medio": "impresion", "herramienta": "svg+illustrator", "product": "Magnesio", "realSizeCm": "10.0x14.0 cm", "canvasPx": "2000x2800", "colors": [], "lastModified": "2026-06-30", "status": "aprobado", "svgUrl": "/svg/suplementos_rd/05_magnesio_editable.svg", "notes": "Real SVG - suplementos_rd"},
  {"id": "06_creatina_monohidratada_editable", "name": "06_creatina_monohidratada_editable.svg", "type": "flyer", "area": "suplementos", "medio": "impresion", "herramienta": "svg+illustrator", "product": "Creatina", "realSizeCm": "10.0x14.0 cm", "canvasPx": "2000x2800", "colors": [], "lastModified": "2026-06-30", "status": "aprobado", "svgUrl": "/svg/suplementos_rd/06_creatina_monohidratada_editable.svg", "notes": "Real SVG - suplementos_rd"},
  {"id": "07_proteina_editable", "name": "07_proteina_editable.svg", "type": "flyer", "area": "suplementos", "medio": "impresion", "herramienta": "svg+illustrator", "product": "Proteina", "realSizeCm": "10.0x14.0 cm", "canvasPx": "2000x2800", "colors": [], "lastModified": "2026-06-30", "status": "aprobado", "svgUrl": "/svg/suplementos_rd/07_proteina_editable.svg", "notes": "Real SVG - suplementos_rd"},
  {"id": "08_post_fiesta_editable", "name": "08_post_fiesta_editable.svg", "type": "flyer", "area": "suplementos", "medio": "impresion", "herramienta": "svg+illustrator", "product": "Post Fiesta", "realSizeCm": "10.0x14.0 cm", "canvasPx": "2000x2800", "colors": [], "lastModified": "2026-06-30", "status": "aprobado", "svgUrl": "/svg/suplementos_rd/08_post_fiesta_editable.svg", "notes": "Real SVG - suplementos_rd"},
  {"id": "01_linea_suplementos_rd_vectorizado", "name": "01_linea_suplementos_rd_vectorizado.svg", "type": "flyer", "area": "suplementos", "medio": "impresion", "herramienta": "svg", "product": "Linea completa", "realSizeCm": "10.0x14.0 cm", "canvasPx": "2000x2800", "colors": [], "lastModified": "2026-06-30", "status": "aprobado", "svgUrl": "/svg/suplementos_rd/01_linea_suplementos_rd_vectorizado.svg", "notes": "Real SVG - suplementos_rd"},
  {"id": "02_impulso_vectorizado", "name": "02_impulso_vectorizado.svg", "type": "flyer", "area": "suplementos", "medio": "impresion", "herramienta": "svg", "product": "Impulso", "realSizeCm": "10.0x14.0 cm", "canvasPx": "2000x2800", "colors": [], "lastModified": "2026-06-30", "status": "aprobado", "svgUrl": "/svg/suplementos_rd/02_impulso_vectorizado.svg", "notes": "Real SVG - suplementos_rd"},
  {"id": "03_hongos_adaptogenos_vectorizado", "name": "03_hongos_adaptogenos_vectorizado.svg", "type": "flyer", "area": "suplementos", "medio": "impresion", "herramienta": "svg", "product": "Hongos Adaptogenos", "realSizeCm": "10.0x14.0 cm", "canvasPx": "2000x2800", "colors": [], "lastModified": "2026-06-30", "status": "aprobado", "svgUrl": "/svg/suplementos_rd/03_hongos_adaptogenos_vectorizado.svg", "notes": "Real SVG - suplementos_rd"},
  {"id": "04_pre_fiesta_vectorizado", "name": "04_pre_fiesta_vectorizado.svg", "type": "flyer", "area": "suplementos", "medio": "impresion", "herramienta": "svg", "product": "Pre Fiesta", "realSizeCm": "10.0x14.0 cm", "canvasPx": "2000x2800", "colors": [], "lastModified": "2026-06-30", "status": "aprobado", "svgUrl": "/svg/suplementos_rd/04_pre_fiesta_vectorizado.svg", "notes": "Real SVG - suplementos_rd"},
  {"id": "05_magnesio_vectorizado", "name": "05_magnesio_vectorizado.svg", "type": "flyer", "area": "suplementos", "medio": "impresion", "herramienta": "svg", "product": "Magnesio", "realSizeCm": "10.0x14.0 cm", "canvasPx": "2000x2800", "colors": [], "lastModified": "2026-06-30", "status": "aprobado", "svgUrl": "/svg/suplementos_rd/05_magnesio_vectorizado.svg", "notes": "Real SVG - suplementos_rd"},
  {"id": "06_creatina_monohidratada_vectorizado", "name": "06_creatina_monohidratada_vectorizado.svg", "type": "flyer", "area": "suplementos", "medio": "impresion", "herramienta": "svg", "product": "Creatina", "realSizeCm": "10.0x14.0 cm", "canvasPx": "2000x2800", "colors": [], "lastModified": "2026-06-30", "status": "aprobado", "svgUrl": "/svg/suplementos_rd/06_creatina_monohidratada_vectorizado.svg", "notes": "Real SVG - suplementos_rd"},
  {"id": "07_proteina_vectorizado", "name": "07_proteina_vectorizado.svg", "type": "flyer", "area": "suplementos", "medio": "impresion", "herramienta": "svg", "product": "Proteina", "realSizeCm": "10.0x14.0 cm", "canvasPx": "2000x2800", "colors": [], "lastModified": "2026-06-30", "status": "aprobado", "svgUrl": "/svg/suplementos_rd/07_proteina_vectorizado.svg", "notes": "Real SVG - suplementos_rd"},
  {"id": "08_post_fiesta_vectorizado", "name": "08_post_fiesta_vectorizado.svg", "type": "flyer", "area": "suplementos", "medio": "impresion", "herramienta": "svg", "product": "Post Fiesta", "realSizeCm": "10.0x14.0 cm", "canvasPx": "2000x2800", "colors": [], "lastModified": "2026-06-30", "status": "aprobado", "svgUrl": "/svg/suplementos_rd/08_post_fiesta_vectorizado.svg", "notes": "Real SVG - suplementos_rd"},
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
      type: lower.includes('pendon') ? 'pendon' : lower.includes('sticker') ? 'sticker' : lower.includes('logo') ? 'logo' : lower.includes('rider') ? 'rider' : lower.includes('cartelera') ? 'cartelera' : lower.includes('post') ? 'post-ig' : lower.includes('flyer') ? 'flyer' : 'etiqueta',
      area: String(groupName).toLowerCase().includes('evento') ? 'eventos' : String(groupName).toLowerCase().includes('supl') ? 'suplementos' : 'comun',
      medio: lower.includes('ig') || lower.includes('digital') ? 'digital' : 'impresion',
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

export const TYPE_OPTIONS: PieceType[] = ['etiqueta', 'flyer', 'pendon', 'post-ig', 'sticker', 'logo', 'rider', 'cartelera', 'stand'];
