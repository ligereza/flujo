// ─── Config.json canonical types from piezas_vectoriales ───

export interface ProjectMeta {
  name: string;
  slug: string;
  brand: string;
  website: string;
  note?: string;
}

export interface CanvasConfig {
  width: number;
  height: number;
  real_size_cm: { width: number; height: number };
  safe_margin_px: number;
}

export type Palette = Record<string, string>;

export interface BaseElement {
  type: string;
  x?: number;
  y?: number;
  fill?: string;
  stroke?: string;
  stroke_width?: number;
  opacity?: number;
  _id?: string; // runtime only
}

export interface TextElement extends BaseElement {
  type: 'text';
  content: string;
  x: number;
  y: number;
  size: number;
  fill: string;
  weight?: 'bold' | 'normal';
  max_width?: number;
}

export interface ParagraphElement extends BaseElement {
  type: 'paragraph';
  content: string;
  x: number;
  y: number;
  size: number;
  fill: string;
  max_width: number;
  line_height: number;
  autofit?: boolean;
}

export interface ListElement extends BaseElement {
  type: 'list';
  x: number;
  y: number;
  size: number;
  fill: string;
  max_width: number;
  line_height: number;
  indent: number;
  gap: number;
  items: string[];
}

export interface RectElement extends BaseElement {
  type: 'rect' | 'panel';
  x: number;
  y: number;
  w: number;
  h: number;
  radius?: number;
}

export interface CircleElement extends BaseElement {
  type: 'circle';
  cx: number;
  cy: number;
  r: number;
}

export interface LineElement extends BaseElement {
  type: 'line';
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}


export interface SvgImageElement extends BaseElement {
  type: 'svg_image';
  x: number;
  y: number;
  w: number;
  h: number;
  content: string;
}

export type ConfigElement = TextElement | ParagraphElement | ListElement | RectElement | CircleElement | LineElement | SvgImageElement;

export interface DocumentConfig {
  id: string;
  title: string;
  accent?: string;
  background?: string;
  elements: ConfigElement[];
}

export interface PieceConfig {
  project: ProjectMeta;
  canvas: CanvasConfig;
  palette: Palette;
  background: string;
  global_elements: ConfigElement[];
  documents: DocumentConfig[];
}

// ─── Helpers ───

let _nextId = 1;
export function assignIds(elements: ConfigElement[]): ConfigElement[] {
  return elements.map(el => ({ ...el, _id: el._id || `el_${_nextId++}` }));
}

export function resolveColor(key: string, palette: Palette): string {
  return palette[key] || key;
}

export function getElementBounds(el: ConfigElement): { x: number; y: number; w: number; h: number } {
  switch (el.type) {
    case 'text':
      return { x: el.x, y: el.y - el.size, w: el.max_width || el.size * el.content.length * 0.55, h: el.size * 1.2 };
    case 'paragraph':
      return { x: el.x, y: el.y - el.size, w: el.max_width, h: el.line_height * Math.ceil(el.content.length / (el.max_width / (el.size * 0.5))) };
    case 'list': {
      const lines = el.items.length;
      return { x: el.x, y: el.y - el.size, w: el.max_width, h: lines * (el.line_height + el.gap) };
    }
    case 'rect':
    case 'panel':
      return { x: el.x, y: el.y, w: el.w, h: el.h };
    case 'circle':
      return { x: el.cx - el.r, y: el.cy - el.r, w: el.r * 2, h: el.r * 2 };
    case 'line':
      return { x: Math.min(el.x1, el.x2), y: Math.min(el.y1, el.y2), w: Math.abs(el.x2 - el.x1) || 2, h: Math.abs(el.y2 - el.y1) || 2 };
    case 'svg_image':
      return { x: el.x, y: el.y, w: el.w, h: el.h };
  }
}

// ─── Demo configs ───

export const DEMO_ETIQUETA: PieceConfig = {
  project: {
    name: 'Etiquetas RD · ejemplo base',
    slug: 'etiquetas_rd_ejemplo',
    brand: 'Reduciendo Daño',
    website: 'REDUCIENDODANO.CL',
  },
  canvas: { width: 2800, height: 2000, real_size_cm: { width: 14, height: 10 }, safe_margin_px: 120 },
  palette: {
    cream: '#F6EFE3', paper: '#FFF8ED', ink: '#161513', muted: '#675F55',
    green: '#173F2F', orange: '#EF7B2D', yellow: '#F5C54D', blue: '#315EE8',
    line: '#D9CEC0', white: '#FFFFFF',
  },
  background: 'cream',
  global_elements: [
    { type: 'circle', cx: 180, cy: 160, r: 360, fill: 'orange', opacity: 0.12 } as CircleElement,
    { type: 'circle', cx: 2650, cy: 1880, r: 460, fill: 'blue', opacity: 0.10 } as CircleElement,
    { type: 'rect', x: 80, y: 80, w: 2640, h: 1840, radius: 70, fill: 'none', stroke: 'line', stroke_width: 5 } as RectElement,
    { type: 'rect', x: 120, y: 120, w: 88, h: 88, radius: 26, fill: 'green' } as RectElement,
    { type: 'text', content: 'RD', x: 139, y: 175, size: 42, fill: 'white', weight: 'bold' } as TextElement,
    { type: 'text', content: 'Reduciendo Daño', x: 235, y: 175, size: 42, fill: 'ink', weight: 'bold' } as TextElement,
    { type: 'line', x1: 120, y1: 1745, x2: 2680, y2: 1745, stroke: 'line', stroke_width: 5 } as LineElement,
    { type: 'text', content: 'REDUCIENDODANO.CL', x: 120, y: 1810, size: 44, fill: 'green', weight: 'bold' } as TextElement,
  ],
  documents: [
    {
      id: '01_etiqueta_impulso',
      title: 'IMPULSO',
      accent: 'blue',
      elements: [
        { type: 'rect', x: 1880, y: 118, w: 780, h: 80, radius: 40, fill: 'white', stroke: 'line', stroke_width: 2, opacity: 0.75 } as RectElement,
        { type: 'text', content: 'SUPLEMENTO ALIMENTICIO EN GOMITAS', x: 1935, y: 168, size: 28, fill: 'blue', weight: 'bold' } as TextElement,
        { type: 'text', content: 'IMPULSO', x: 120, y: 500, size: 190, fill: 'ink', weight: 'bold' } as TextElement,
        { type: 'text', content: 'Cafeína + L-teanina + Vitamina B12', x: 130, y: 585, size: 62, fill: 'blue', weight: 'bold' } as TextElement,
        { type: 'panel', x: 125, y: 700, w: 1180, h: 650, radius: 48, fill: 'white', stroke: 'line', stroke_width: 3, opacity: 0.68 } as RectElement,
        { type: 'paragraph', content: 'Fórmula diseñada para momentos de alta demanda cognitiva, estudio, trabajo o jornadas prolongadas.', x: 195, y: 790, size: 48, fill: 'ink', max_width: 1040, line_height: 66 } as ParagraphElement,
        { type: 'list', x: 195, y: 1020, size: 36, fill: 'muted', max_width: 1020, line_height: 48, indent: 42, gap: 18, items: [
          'Contribuye al estado de alerta y concentración.',
          'Apoya foco sostenido sin nerviosismo excesivo.',
          'Formato práctico en gomitas.',
        ] } as ListElement,
        { type: 'panel', x: 1450, y: 700, w: 1110, h: 650, radius: 48, fill: 'green', opacity: 0.96 } as RectElement,
        { type: 'text', content: 'INFORMACIÓN', x: 1530, y: 810, size: 52, fill: 'yellow', weight: 'bold' } as TextElement,
        { type: 'paragraph', content: 'Contenido neto: 60 gomitas\nPorción sugerida: según etiqueta final\nLote / vencimiento: espacio editable', x: 1530, y: 900, size: 42, fill: 'white', max_width: 930, line_height: 62 } as ParagraphElement,
        { type: 'rect', x: 2145, y: 1510, w: 410, h: 120, radius: 28, fill: 'white', stroke: 'line', stroke_width: 2, opacity: 0.75 } as RectElement,
        { type: 'text', content: 'CÓDIGO / QR', x: 2218, y: 1580, size: 34, fill: 'muted', weight: 'bold' } as TextElement,
      ],
    },
    {
      id: '02_etiqueta_base_blanca',
      title: 'Etiqueta base blanca',
      elements: [
        { type: 'rect', x: 120, y: 300, w: 2560, h: 1250, radius: 60, fill: 'paper', stroke: 'line', stroke_width: 4 } as RectElement,
        { type: 'text', content: 'NOMBRE PRODUCTO', x: 190, y: 480, size: 128, fill: 'ink', weight: 'bold' } as TextElement,
        { type: 'paragraph', content: 'Descripción breve del producto. Cambia este texto desde el JSON y regenera los archivos.', x: 200, y: 650, size: 52, fill: 'muted', max_width: 1600, line_height: 70 } as ParagraphElement,
        { type: 'list', x: 200, y: 880, size: 40, fill: 'ink', max_width: 1500, line_height: 56, indent: 46, gap: 16, items: [
          'Ingrediente o activo 1.',
          'Ingrediente o activo 2.',
          'Ingrediente o activo 3.',
        ] } as ListElement,
        { type: 'rect', x: 2000, y: 610, w: 420, h: 420, radius: 36, fill: 'white', stroke: 'line', stroke_width: 4 } as RectElement,
        { type: 'text', content: 'QR', x: 2158, y: 850, size: 100, fill: 'muted', weight: 'bold' } as TextElement,
      ],
    },
  ],
};

export const DEMO_FLYER: PieceConfig = {
  project: { name: 'Flyer horizontal mínimo', slug: 'flyer_horizontal_minimo', brand: 'Marca', website: 'WEB.CL' },
  canvas: { width: 2800, height: 2000, real_size_cm: { width: 14, height: 10 }, safe_margin_px: 120 },
  palette: { cream: '#F6EFE3', white: '#FFFFFF', ink: '#161513', muted: '#675F55', line: '#D9CEC0', accent: '#173F2F' },
  background: 'cream',
  global_elements: [
    { type: 'rect', x: 80, y: 80, w: 2640, h: 1840, radius: 70, fill: 'none', stroke: 'line', stroke_width: 5 } as RectElement,
    { type: 'text', content: 'Marca', x: 120, y: 160, size: 44, fill: 'ink', weight: 'bold' } as TextElement,
    { type: 'text', content: 'WEB.CL', x: 120, y: 1870, size: 44, fill: 'accent', weight: 'bold' } as TextElement,
  ],
  documents: [
    {
      id: '01_flyer_base',
      title: 'Flyer base',
      elements: [
        { type: 'text', content: 'TÍTULO PRINCIPAL', x: 120, y: 400, size: 130, fill: 'ink', weight: 'bold' } as TextElement,
        { type: 'panel', x: 120, y: 560, w: 2560, h: 980, radius: 50, fill: 'white', stroke: 'line', stroke_width: 3, opacity: 0.7 } as RectElement,
        { type: 'paragraph', content: 'Aquí va la descripción principal. Cambia este texto desde el JSON.', x: 200, y: 660, size: 54, fill: 'muted', max_width: 2300, line_height: 72 } as ParagraphElement,
        { type: 'list', x: 200, y: 880, size: 42, fill: 'ink', max_width: 2200, line_height: 58, indent: 48, gap: 18, items: [
          'Punto uno',
          'Punto dos',
          'Punto tres',
        ] } as ListElement,
      ],
    },
  ],
};

export const DEMO_CONFIGS: Record<string, PieceConfig> = {
  'Etiqueta RD — IMPULSO': DEMO_ETIQUETA,
  'Flyer horizontal mínimo': DEMO_FLYER,
};
