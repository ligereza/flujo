// Índice de piezas SVG para el SVG Studio Hub.
// Se carga desde svg_index.json generado por `python scripts/generate_svg_index.py`
// Fallback a MOCK_SVG_INDEX si el JSON no está disponible.

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
  filePath?: string; // ruta al archivo en el repo
  sections?: string[]; // grupos/sections dentro del SVG
  dimensions?: { width: number; height: number };
}

// ─── SVG snippets for demo pieces ───
const etiquetaSVG = `<svg viewBox="0 0 330 130" xmlns="http://www.w3.org/2000/svg">
  <rect width="330" height="130" rx="6" fill="#f8f1e3" stroke="#2d5a4a" stroke-width="1.5"/>
  <rect x="8" y="8" width="100" height="114" rx="4" fill="#2d5a4a"/>
  <text x="58" y="55" text-anchor="middle" fill="white" font-size="11" font-weight="bold" font-family="sans-serif">OMEGA 3</text>
  <text x="58" y="72" text-anchor="middle" fill="#a3d9c8" font-size="7" font-family="sans-serif">1000mg</text>
  <text x="58" y="95" text-anchor="middle" fill="white" font-size="6" font-family="sans-serif">EPA + DHA</text>
  <rect x="120" y="14" width="200" height="35" rx="3" fill="#2d5a4a15"/>
  <text x="220" y="28" text-anchor="middle" fill="#1f2a24" font-size="7" font-weight="bold" font-family="sans-serif">INFORMACIÓN NUTRICIONAL</text>
  <line x1="130" y1="38" x2="310" y2="38" stroke="#2d5a4a30" stroke-width="0.5"/>
  <text x="130" y="48" fill="#675f55" font-size="5.5" font-family="sans-serif">Porción: 1 cápsula blanda</text>
  <rect x="120" y="56" width="200" height="60" rx="3" fill="#2d5a4a08"/>
  <text x="130" y="70" fill="#675f55" font-size="5" font-family="sans-serif">Ingredientes: Aceite de pescado concentrado,</text>
  <text x="130" y="79" fill="#675f55" font-size="5" font-family="sans-serif">gelatina, glicerina, vitamina E (tocoferol).</text>
  <text x="130" y="92" fill="#675f55" font-size="5" font-family="sans-serif">Modo de uso: Tomar 1 cápsula al día.</text>
  <text x="130" y="105" fill="#c2410f" font-size="4.5" font-family="sans-serif">⚠ Mantener fuera del alcance de los niños.</text>
  <text x="275" y="123" text-anchor="middle" fill="#675f55" font-size="4" font-family="sans-serif">Contenido neto: 60 cápsulas · Lote: 2024-A</text>
</svg>`;

const etiquetaMagnesioSVG = `<svg viewBox="0 0 330 130" xmlns="http://www.w3.org/2000/svg">
  <rect width="330" height="130" rx="6" fill="#f8f1e3" stroke="#6366f1" stroke-width="1.5"/>
  <rect x="8" y="8" width="100" height="114" rx="4" fill="#4f46e5"/>
  <text x="58" y="48" text-anchor="middle" fill="white" font-size="8" font-weight="bold" font-family="sans-serif">GLICINATO</text>
  <text x="58" y="60" text-anchor="middle" fill="white" font-size="8" font-weight="bold" font-family="sans-serif">DE</text>
  <text x="58" y="72" text-anchor="middle" fill="white" font-size="8" font-weight="bold" font-family="sans-serif">MAGNESIO</text>
  <text x="58" y="90" text-anchor="middle" fill="#c7d2fe" font-size="7" font-family="sans-serif">500 mg</text>
  <rect x="120" y="14" width="200" height="35" rx="3" fill="#4f46e515"/>
  <text x="220" y="28" text-anchor="middle" fill="#1f2a24" font-size="7" font-weight="bold" font-family="sans-serif">INFORMACIÓN NUTRICIONAL</text>
  <line x1="130" y1="38" x2="310" y2="38" stroke="#4f46e530" stroke-width="0.5"/>
  <text x="130" y="48" fill="#675f55" font-size="5.5" font-family="sans-serif">Porción: 1 cápsula</text>
  <rect x="120" y="56" width="200" height="60" rx="3" fill="#4f46e508"/>
  <text x="130" y="70" fill="#675f55" font-size="5" font-family="sans-serif">Ingredientes: Glicinato de magnesio,</text>
  <text x="130" y="79" fill="#675f55" font-size="5" font-family="sans-serif">cápsula vegetal (HPMC), estearato de Mg.</text>
  <text x="130" y="92" fill="#675f55" font-size="5" font-family="sans-serif">Modo de uso: Tomar 1 cápsula diaria.</text>
  <text x="275" y="123" text-anchor="middle" fill="#675f55" font-size="4" font-family="sans-serif">Contenido neto: 90 cápsulas · Lote: 2024-B</text>
</svg>`;

const postFiestaSVG = `<svg viewBox="0 0 330 130" xmlns="http://www.w3.org/2000/svg">
  <rect width="330" height="130" rx="6" fill="#f8f1e3" stroke="#f59e0b" stroke-width="1.5"/>
  <rect x="8" y="8" width="100" height="114" rx="4" fill="#b45309"/>
  <text x="58" y="45" text-anchor="middle" fill="white" font-size="9" font-weight="bold" font-family="sans-serif">POST</text>
  <text x="58" y="60" text-anchor="middle" fill="white" font-size="9" font-weight="bold" font-family="sans-serif">FIESTA</text>
  <circle cx="58" cy="85" r="14" fill="#f59e0b40" stroke="#f59e0b" stroke-width="1"/>
  <text x="58" y="88" text-anchor="middle" fill="white" font-size="7" font-family="sans-serif">⚡</text>
  <rect x="120" y="14" width="200" height="100" rx="3" fill="#b4530908"/>
  <text x="220" y="35" text-anchor="middle" fill="#1f2a24" font-size="7" font-weight="bold" font-family="sans-serif">RECUPERACIÓN Y BIENESTAR</text>
  <text x="130" y="55" fill="#675f55" font-size="5" font-family="sans-serif">Complejo vitamínico con electrolitos,</text>
  <text x="130" y="64" fill="#675f55" font-size="5" font-family="sans-serif">aminoácidos y antioxidantes para una</text>
  <text x="130" y="73" fill="#675f55" font-size="5" font-family="sans-serif">recuperación más rápida y segura.</text>
  <text x="130" y="90" fill="#c2410f" font-size="4.5" font-family="sans-serif">⚠ Tabla nutricional en corrección</text>
  <text x="130" y="105" fill="#675f55" font-size="4" font-family="sans-serif">Contenido: 30 sobres · Gomitas disponibles</text>
</svg>`;

const flyerSVG = `<svg viewBox="0 0 175 248" xmlns="http://www.w3.org/2000/svg">
  <rect width="175" height="248" rx="6" fill="#1f2a24"/>
  <rect x="12" y="12" width="151" height="80" rx="4" fill="#2d5a4a"/>
  <text x="87" y="45" text-anchor="middle" fill="white" font-size="14" font-weight="bold" font-family="sans-serif">OMEGA 3</text>
  <text x="87" y="62" text-anchor="middle" fill="#a3d9c8" font-size="8" font-family="sans-serif">EPA + DHA de alta pureza</text>
  <text x="87" y="78" text-anchor="middle" fill="#f8f1e380" font-size="6" font-family="sans-serif">Salud cardiovascular · Cerebro · Articulaciones</text>
  <rect x="12" y="100" width="151" height="100" rx="4" fill="#2d5a4a20"/>
  <text x="87" y="120" text-anchor="middle" fill="#f8f1e3" font-size="7" font-weight="bold" font-family="sans-serif">¿Por qué suplementar?</text>
  <text x="24" y="138" fill="#a3d9c8" font-size="5.5" font-family="sans-serif">✓ Reduce inflamación</text>
  <text x="24" y="150" fill="#a3d9c8" font-size="5.5" font-family="sans-serif">✓ Mejora función cognitiva</text>
  <text x="24" y="162" fill="#a3d9c8" font-size="5.5" font-family="sans-serif">✓ Protege el corazón</text>
  <text x="24" y="174" fill="#a3d9c8" font-size="5.5" font-family="sans-serif">✓ Apoya salud articular</text>
  <text x="24" y="186" fill="#a3d9c8" font-size="5.5" font-family="sans-serif">✓ Fortalece sistema inmune</text>
  <rect x="12" y="208" width="151" height="28" rx="4" fill="#2d5a4a"/>
  <text x="87" y="225" text-anchor="middle" fill="white" font-size="7" font-weight="bold" font-family="sans-serif">Consulta · reducienodano.cl</text>
  <rect x="130" y="212" width="20" height="20" rx="2" fill="white"/>
  <text x="140" y="225" text-anchor="middle" fill="#1f2a24" font-size="6" font-family="sans-serif">QR</text>
</svg>`;

const pendonSVG = `<svg viewBox="0 0 80 200" xmlns="http://www.w3.org/2000/svg">
  <rect width="80" height="200" rx="2" fill="#1f2a24"/>
  <rect x="4" y="4" width="72" height="50" rx="3" fill="#2d5a4a"/>
  <text x="40" y="25" text-anchor="middle" fill="white" font-size="6" font-weight="bold" font-family="sans-serif">REDUCIENDO</text>
  <text x="40" y="35" text-anchor="middle" fill="white" font-size="6" font-weight="bold" font-family="sans-serif">DAÑO</text>
  <text x="40" y="47" text-anchor="middle" fill="#a3d9c8" font-size="4" font-family="sans-serif">Suplementos</text>
  <circle cx="40" cy="85" r="18" fill="#2d5a4a30" stroke="#2d5a4a" stroke-width="0.5"/>
  <text x="40" y="88" text-anchor="middle" fill="#a3d9c8" font-size="8" font-family="sans-serif">💊</text>
  <text x="40" y="115" text-anchor="middle" fill="white" font-size="5" font-weight="bold" font-family="sans-serif">Cuidado</text>
  <text x="40" y="123" text-anchor="middle" fill="white" font-size="5" font-weight="bold" font-family="sans-serif">Informado</text>
  <text x="40" y="140" text-anchor="middle" fill="#675f55" font-size="3.5" font-family="sans-serif">Pre y Post Fiesta</text>
  <text x="40" y="148" text-anchor="middle" fill="#675f55" font-size="3.5" font-family="sans-serif">Omega 3 · Magnesio</text>
  <text x="40" y="156" text-anchor="middle" fill="#675f55" font-size="3.5" font-family="sans-serif">Proteína · Vitaminas</text>
  <rect x="4" y="170" width="72" height="24" rx="3" fill="#2d5a4a"/>
  <text x="40" y="185" text-anchor="middle" fill="white" font-size="4.5" font-weight="bold" font-family="sans-serif">reducienodano.cl</text>
</svg>`;

const postIgSVG = `<svg viewBox="0 0 108 135" xmlns="http://www.w3.org/2000/svg">
  <rect width="108" height="135" rx="4" fill="#1f2a24"/>
  <rect x="4" y="4" width="100" height="60" rx="3" fill="linear-gradient(#2d5a4a, #1f2a24)"/>
  <rect x="4" y="4" width="100" height="60" rx="3" fill="#2d5a4a"/>
  <text x="54" y="28" text-anchor="middle" fill="white" font-size="10" font-weight="bold" font-family="sans-serif">¿SABÍAS</text>
  <text x="54" y="42" text-anchor="middle" fill="white" font-size="10" font-weight="bold" font-family="sans-serif">QUE...?</text>
  <text x="54" y="56" text-anchor="middle" fill="#a3d9c8" font-size="5" font-family="sans-serif">Serie educativa RD</text>
  <rect x="4" y="68" width="100" height="50" rx="3" fill="#2d5a4a15"/>
  <text x="54" y="82" text-anchor="middle" fill="#f8f1e3" font-size="5" font-family="sans-serif">El Omega 3 reduce la</text>
  <text x="54" y="91" text-anchor="middle" fill="#f8f1e3" font-size="5" font-family="sans-serif">inflamación cerebral post</text>
  <text x="54" y="100" text-anchor="middle" fill="#f8f1e3" font-size="5" font-family="sans-serif">consumo de sustancias.</text>
  <text x="54" y="113" text-anchor="middle" fill="#675f55" font-size="4" font-family="sans-serif">Fuente: PubMed 2023</text>
  <rect x="4" y="122" width="100" height="9" rx="2" fill="#2d5a4a"/>
  <text x="54" y="129" text-anchor="middle" fill="white" font-size="4" font-weight="bold" font-family="sans-serif">@reducienodano · reducienodano.cl</text>
</svg>`;

const stickerSVG = `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <circle cx="50" cy="50" r="48" fill="#2d5a4a" stroke="#a3d9c8" stroke-width="1.5"/>
  <text x="50" y="35" text-anchor="middle" fill="white" font-size="8" font-weight="bold" font-family="sans-serif">CUIDA</text>
  <text x="50" y="47" text-anchor="middle" fill="white" font-size="8" font-weight="bold" font-family="sans-serif">TU</text>
  <text x="50" y="59" text-anchor="middle" fill="white" font-size="8" font-weight="bold" font-family="sans-serif">VIAJE</text>
  <text x="50" y="75" text-anchor="middle" fill="#a3d9c8" font-size="5" font-family="sans-serif">reducienodano.cl</text>
</svg>`;

const logoSVG = `<svg viewBox="0 0 140 140" xmlns="http://www.w3.org/2000/svg">
  <rect width="140" height="140" rx="70" fill="#1f2a24"/>
  <circle cx="70" cy="60" r="30" fill="none" stroke="#2d5a4a" stroke-width="2"/>
  <circle cx="70" cy="60" r="20" fill="#2d5a4a40"/>
  <text x="70" y="65" text-anchor="middle" fill="white" font-size="12" font-weight="bold" font-family="sans-serif">RD</text>
  <text x="70" y="105" text-anchor="middle" fill="#a3d9c8" font-size="7" font-weight="bold" font-family="sans-serif">SUPLEMENTOS</text>
  <text x="70" y="117" text-anchor="middle" fill="#675f55" font-size="5" font-family="sans-serif">Línea de cuidado</text>
</svg>`;

const carteleraSVG = `<svg viewBox="0 0 108 192" xmlns="http://www.w3.org/2000/svg">
  <rect width="108" height="192" rx="4" fill="#111"/>
  <rect x="6" y="6" width="96" height="120" rx="3" fill="#333"/>
  <text x="54" y="55" text-anchor="middle" fill="#888" font-size="8" font-family="sans-serif">📸</text>
  <text x="54" y="70" text-anchor="middle" fill="#666" font-size="5" font-family="sans-serif">Foto IG del evento</text>
  <text x="54" y="82" text-anchor="middle" fill="#555" font-size="4" font-family="sans-serif">(descargada con instaloader)</text>
  <rect x="6" y="132" width="96" height="24" rx="3" fill="#2d5a4a"/>
  <text x="54" y="140" text-anchor="middle" fill="white" font-size="5" font-weight="bold" font-family="sans-serif">CLUB SOL</text>
  <text x="54" y="150" text-anchor="middle" fill="#a3d9c8" font-size="4" font-family="sans-serif">Viernes 21 Jun · 23:00</text>
  <rect x="6" y="162" width="96" height="24" rx="3" fill="#1f2a24"/>
  <text x="54" y="174" text-anchor="middle" fill="#675f55" font-size="4" font-family="sans-serif">Reduciendo Daño presente</text>
  <text x="54" y="183" text-anchor="middle" fill="#675f55" font-size="3.5" font-family="sans-serif">Stand informativo + testeo</text>
</svg>`;

export const MOCK_SVG_INDEX: SvgPiece[] = [
  {
    id: 'sup_etiqueta_omega3',
    name: 'Etiqueta Omega 3',
    type: 'etiqueta',
    area: 'suplementos',
    medio: 'impresion',
    herramienta: 'SVG+Illustrator',
    product: 'Omega 3 1000mg',
    realSizeCm: '16.5 × 6.5 cm',
    canvasPx: '3300 × 1300',
    colors: ['#2d5a4a', '#f8f1e3', '#a3d9c8'],
    lastModified: '2024-05-14',
    status: 'en-revision',
    svgContent: etiquetaSVG,
    notes: 'Revisando colores según brief.',
  },
  {
    id: 'sup_etiqueta_magnesio',
    name: 'Etiqueta Glicinato de Magnesio',
    type: 'etiqueta',
    area: 'suplementos',
    medio: 'impresion',
    herramienta: 'SVG+Illustrator',
    product: 'Glicinato de Magnesio 500mg',
    realSizeCm: '16.5 × 6.5 cm',
    canvasPx: '3300 × 1300',
    colors: ['#4f46e5', '#f8f1e3', '#c7d2fe'],
    lastModified: '2024-05-12',
    status: 'borrador',
    svgContent: etiquetaMagnesioSVG,
    notes: 'Siguiendo línea de magnesio previamente planificada.',
  },
  {
    id: 'sup_etiqueta_postfiesta',
    name: 'Etiqueta Post Fiesta',
    type: 'etiqueta',
    area: 'suplementos',
    medio: 'impresion',
    herramienta: 'SVG+Illustrator',
    product: 'Post Fiesta Recovery',
    realSizeCm: '16.5 × 6.5 cm',
    canvasPx: '3300 × 1300',
    colors: ['#b45309', '#f59e0b', '#f8f1e3'],
    lastModified: '2024-05-16',
    status: 'en-revision',
    svgContent: postFiestaSVG,
    notes: 'Corregir tabla nutricional. Agregar ingredientes de gomitas.',
  },
  {
    id: 'sup_flyer_omega3',
    name: 'Flyer Omega 3',
    type: 'flyer',
    area: 'suplementos',
    medio: 'impresion',
    herramienta: 'SVG+Illustrator',
    product: 'Omega 3',
    realSizeCm: '14.8 × 21 cm (A5)',
    canvasPx: '1748 × 2480',
    colors: ['#1f2a24', '#2d5a4a', '#a3d9c8'],
    lastModified: '2024-05-10',
    status: 'aprobado',
    svgContent: flyerSVG,
    notes: 'Revisar espacio junto al QR. Decidir WhatsApp texto o QR.',
  },
  {
    id: 'sup_pendon_rd',
    name: 'Pendón Suplementos RD',
    type: 'pendon',
    area: 'suplementos',
    medio: 'impresion',
    herramienta: 'Illustrator',
    product: 'Línea Suplementos RD',
    realSizeCm: '80 × 200 cm (paramétrico)',
    canvasPx: 'paramétrico — 150 dpi',
    colors: ['#1f2a24', '#2d5a4a', '#a3d9c8'],
    lastModified: '2024-05-08',
    status: 'borrador',
    svgContent: pendonSVG,
    notes: 'Pendiente: nuevos servicios RD en revisión. Falta frase principal.',
  },
  {
    id: 'sup_post_ig_sabias',
    name: 'Post IG — ¿Sabías que...?',
    type: 'post-ig',
    area: 'suplementos',
    medio: 'digital',
    herramienta: 'Photoshop',
    product: 'Serie Educativa',
    realSizeCm: 'digital (4:5)',
    canvasPx: '1080 × 1350',
    colors: ['#1f2a24', '#2d5a4a', '#f8f1e3'],
    lastModified: '2024-05-15',
    status: 'aprobado',
    svgContent: postIgSVG,
    notes: 'Parte del paquete mensual de imágenes para IG.',
  },
  {
    id: 'sup_sticker_cuida',
    name: 'Sticker — Cuida tu Viaje',
    type: 'sticker',
    area: 'suplementos',
    medio: 'impresion',
    herramienta: 'SVG+Illustrator',
    product: 'Stickers eventos (1/5)',
    realSizeCm: '7 × 7 cm circular',
    canvasPx: '1400 × 1400',
    colors: ['#2d5a4a', '#a3d9c8'],
    lastModified: '2024-05-11',
    status: 'borrador',
    svgContent: stickerSVG,
    notes: 'Sticker #1 de 5 inspirados en suplementos.',
  },
  {
    id: 'sup_logo_linea',
    name: 'Logo Línea Suplementos',
    type: 'logo',
    area: 'suplementos',
    medio: 'impresion',
    herramienta: 'SVG+Illustrator',
    product: 'Línea Suplementos RD',
    realSizeCm: 'variable',
    canvasPx: '1400 × 1400',
    colors: ['#1f2a24', '#2d5a4a', '#a3d9c8'],
    lastModified: '2024-05-06',
    status: 'borrador',
    svgContent: logoSVG,
    notes: 'Falta cerrar: nombre de línea, estilo visual, si es logo/sello/isotipo.',
  },
  {
    id: 'evt_cartelera_individual',
    name: 'Cartelera Individual — Club Sol',
    type: 'cartelera',
    area: 'eventos',
    medio: 'digital',
    herramienta: 'Photoshop+Blender',
    product: 'Evento Club Sol',
    realSizeCm: 'digital (9:16)',
    canvasPx: '1080 × 1920',
    colors: ['#111', '#2d5a4a'],
    lastModified: '2024-05-16',
    status: 'aprobado',
    svgContent: carteleraSVG,
    notes: 'Foto IG enmarcada en Blender + droplet PS. Infiere productora/fecha/venue.',
  },
];

// Cargar índice desde JSON generado (fallback a MOCK_SVG_INDEX)
export async function loadSvgIndex(): Promise<SvgPiece[]> {
  try {
    const resp = await fetch('/src/data/svg_index.json');
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return await resp.json() as SvgPiece[];
  } catch (err) {
    console.warn('⚠ No se pudo cargar svg_index.json, usando MOCK_SVG_INDEX:', err);
    return MOCK_SVG_INDEX;
  }
}

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
      filePath: item.filePath || path,
      sections: item.sections || [],
      dimensions: item.dimensions,
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
