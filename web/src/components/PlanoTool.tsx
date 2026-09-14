import React, { useRef, useState, useCallback, useEffect } from 'react';
import {
  Map, Download, Plus, Trash2, Eye, EyeOff, Printer, RotateCcw,
  Scan, Users, Moon, Home, Table, Armchair, Box, Zap,
  Lightbulb, Droplet, Thermometer, User, ShieldAlert, HeartPulse, Utensils,
  ChevronRight, ChevronLeft, Settings, Copy, Layers, Grid3X3, FileText,
  Heart, AlertTriangle, Coffee, RefreshCw, Flame, Sofa, Cylinder, Save, Upload
} from 'lucide-react';
import { cn } from '../utils/cn';
import { SIMBOLOS_PROPIOS, simboloPropio, markupSimboloPropio, guardarSimbolo, trazarImagen, registrarSimbolosPropios } from '../data/planoSimbolos';
import { RD_PALETTE, RD_LOGO, calcCostos, formatCLP, proporcionMonto, ALL_PACKS, PACKS, type ExportTheme, type PackId } from '../rdBrand';

// ── Types ────────────────────────────────────────────────────────────
type TechnicalSymbolKey = string;

interface Element {
  id: string;
  type: 'rect' | 'symbol';
  symbolType?: TechnicalSymbolKey;
  x: number;
  y: number;
  w: number;
  h: number;
  label: string;
  color: string;
  visible: boolean;
  symbolKey?: string;
  locked?: boolean;
  category?: string;
}

interface VjEventRecord {
  eventKey: string;
  producerName?: string | null;
  name?: string | null;
  dateRaw?: string | null;
  dateIso?: string | null;
  venueName?: string | null;
  status?: string | null;
  lineup?: string[];
  coOrganizers?: string[];
}

const ZONE_COLORS: Record<string, string> = {
  testeo: '#2d5a4a',
  contencion: '#7c3aed',
  informativo: '#0369a1',
  descanso: '#059669',
  coordinacion: '#ca8a04',
  circulacion: '#9ca3af',
  power: '#f59e0b',
  heating: '#ef4444',
  rack: '#4b5563',
  extinguisher: '#dc2626',
  water: '#2563eb',
  scan: '#06b6d4',
  terrain: '#84cc16',
  circulation: '#9ca3af',
  sensory: '#8b5cf6',
  tent: '#2d5a4a',
  table: '#10b981',
  chairs: '#ca8a04',
  trash: '#71717a',
  light: '#fde047',
  contact: '#0ea5e9',
  security: '#f97316',
  medical: '#dc2626',
  food: '#a16207',
  sillon: '#0d9488',
  toalla: '#0891b2'
};

// Una ZONA es superficie que el recinto reserva y entrega: se marca en el piso,
// se cierra, se ilumina, tiene metros cuadrados. Un SIMBOLO es algo que tiene
// que estar ahi, en un punto.
//
// ZONE_LABELS mezclaba las dos cosas y la paleta ocultaba cinco entradas a mano,
// asi que la app ofrecia dibujar como area "Toalla Nova", "Sillas" o "Mesas", y
// tambien "Medidas Recinto" y "Terreno Estable", que no son objetos del plano
// sino preguntas de checklist. Para el productor tecnico que recibe el plano,
// una zona de 4 m2 llamada "Sillas" se lee como hecho sin criterio.
//
// Separado el 2026-07-26 por decision del usuario. NO se perdio nada: todo lo
// que salio de aca sigue disponible como simbolo, que es lo que siempre fue.
const ZONAS_REALES = [
  'testeo', 'contencion', 'informativo', 'descanso', 'coordinacion', 'circulacion',
] as const;

const ZONE_LABELS: Record<string, string> = {
  testeo: 'Zona Testeo',
  contencion: 'Contención',
  informativo: 'Stand Informativo',
  descanso: 'Zona Descanso',
  coordinacion: 'Coordinación',
  circulacion: 'Circulación Público',
  power: 'Electricidad',
  heating: 'Calefacción',
  rack: 'Rack Almacén',
  extinguisher: 'Extintor',
  water: 'Punto de Agua',
  scan: 'Medidas Recinto',
  terrain: 'Terreno Estable',
  circulation: 'Circulación Pública',
  sensory: 'Baja Estimulación',
  tent: 'Toldo / Carpa',
  table: 'Mesas',
  chairs: 'Sillas',
  trash: 'Basureros / Señalética',
  light: 'Iluminación',
  contact: 'Producción',
  security: 'Seguridad',
  medical: 'Equipo Médico',
  food: 'Alimentación Equipo',
  sillon: 'Sillón doble',
  toalla: 'Toalla Nova'
};


type SymbolSpec = { key: TechnicalSymbolKey; label: string; color: string; icon: string; x: number; y: number; w: number; h: number };

const SYMBOL_CATALOG: SymbolSpec[] = [
  { key: 'scan', label: 'Medidas', color: ZONE_COLORS.scan, icon: 'Scan', x: 180, y: 260, w: 150, h: 150 },
  { key: 'terrain', label: 'Terreno', color: ZONE_COLORS.terrain, icon: 'Map', x: 380, y: 260, w: 150, h: 150 },
  { key: 'circulation', label: 'Circulación', color: ZONE_COLORS.circulation, icon: 'Users', x: 580, y: 260, w: 170, h: 150 },
  { key: 'sensory', label: 'Baja Estim.', color: ZONE_COLORS.sensory, icon: 'Moon', x: 780, y: 260, w: 170, h: 150 },
  { key: 'tent', label: 'Toldo 3x3', color: ZONE_COLORS.tent, icon: 'Home', x: 250, y: 350, w: 190, h: 170 },
  { key: 'table', label: 'Mesas', color: ZONE_COLORS.table, icon: 'Table', x: 500, y: 700, w: 180, h: 140 },
  { key: 'chairs', label: 'Sillas', color: ZONE_COLORS.chairs, icon: 'Armchair', x: 760, y: 700, w: 180, h: 140 },
  { key: 'rack', label: 'Rack', color: ZONE_COLORS.rack, icon: 'Box', x: 150, y: 1350, w: 160, h: 160 },
  { key: 'trash', label: 'Basureros', color: ZONE_COLORS.trash, icon: 'Trash2', x: 360, y: 1350, w: 160, h: 160 },
  { key: 'power', label: 'Electricidad', color: ZONE_COLORS.power, icon: 'Zap', x: 1800, y: 700, w: 160, h: 160 },
  { key: 'light', label: 'Iluminación', color: ZONE_COLORS.light, icon: 'Lightbulb', x: 2000, y: 700, w: 160, h: 160 },
  { key: 'water', label: 'Agua', color: ZONE_COLORS.water, icon: 'Droplet', x: 1800, y: 1300, w: 160, h: 160 },
  { key: 'heating', label: 'Calefacción', color: ZONE_COLORS.heating, icon: 'Thermometer', x: 1800, y: 1000, w: 160, h: 160 },
  { key: 'contact', label: 'Producción', color: ZONE_COLORS.contact, icon: 'User', x: 2200, y: 700, w: 160, h: 160 },
  { key: 'security', label: 'Seguridad', color: ZONE_COLORS.security, icon: 'ShieldAlert', x: 2200, y: 900, w: 160, h: 160 },
  { key: 'medical', label: 'Equipo Médico', color: ZONE_COLORS.medical, icon: 'HeartPulse', x: 2200, y: 1100, w: 160, h: 160 },
  { key: 'food', label: 'Alimentación', color: ZONE_COLORS.food, icon: 'Utensils', x: 2200, y: 1300, w: 160, h: 160 },
  { key: 'testeo', label: 'Testeo', color: ZONE_COLORS.testeo, icon: 'AlertTriangle', x: 1000, y: 550, w: 200, h: 200 },
  { key: 'contencion', label: 'Contención', color: ZONE_COLORS.contencion, icon: 'Heart', x: 1900, y: 550, w: 200, h: 200 },
  { key: 'extinguisher', label: 'Extintor', color: ZONE_COLORS.extinguisher, icon: 'Flame', x: 2400, y: 900, w: 160, h: 160 },
  { key: 'sillon', label: 'Sillón doble', color: ZONE_COLORS.sillon, icon: 'Sofa', x: 970, y: 700, w: 180, h: 140 },
  { key: 'toalla', label: 'Toalla Nova', color: ZONE_COLORS.toalla, icon: 'Cylinder', x: 570, y: 1350, w: 160, h: 160 },
];

// Los simbolos propios (data/plano_simbolos.json) se suman al catalogo de
// fabrica, para que aparezcan en el selector y no solo al dibujarlos. Se
// ubican en una columna libre a la derecha; el usuario los mueve como a
// cualquier otro. Un id que coincide con uno de fabrica solo lo reetiqueta o
// recolorea, igual que en el lado Python.
const simbolosPropiosSpec = (): SymbolSpec[] =>
  SIMBOLOS_PROPIOS.filter(s => !SYMBOL_CATALOG.some(f => f.key === s.id)).map((s, i) => ({
    key: s.id as TechnicalSymbolKey,
    label: s.etiqueta,
    color: s.color,
    icon: 'Shapes',
    x: 2600,
    y: 300 + i * 200,
    w: 160,
    h: 160,
  }));

// PEREZOSO A PROPOSITO: los simbolos propios llegan por fetch (main.tsx) y este
// modulo se evalua ANTES de que ese fetch termine, asi que armar la lista aca
// arriba la dejaria siempre vacia. Se arma al usarla.
const catalogoCompleto = (): SymbolSpec[] => [...SYMBOL_CATALOG, ...simbolosPropiosSpec()];

const specDe = (key: string): SymbolSpec | undefined =>
  SYMBOL_CATALOG.find(s => s.key === key) || simbolosPropiosSpec().find(s => s.key === key);

/** spec del simbolo, con el de electricidad como ultimo recurso (era el fallback previo). */
const specOPower = (key: string): SymbolSpec =>
  specDe(key) || (SYMBOL_CATALOG.find(s => s.key === 'power') as SymbolSpec);

const PLANO_FRAME = { x: 50, y: 50, w: 2870, h: 1950 };
const GRID = 20;

// Altura real de la caja de leyenda segun cantidad de simbolos. Sin cap: con 19+
// simbolos (COMPLETO + marcar todos) el cap de 900 dejaba filas dibujadas fuera del panel.
// Filas de 100 px (iconos 80 + font 32): la simbologia debe leerse en el A4 impreso.
const legendHeightFor = (n: number) => Math.max(260, 170 + Math.ceil(n / 2) * 100);

// ZONE_COLORS esta calibrada para fondo oscuro; sobre papel blanco los tonos claros
// desaparecen. Overrides solo para el print con tema white.
const PRINT_WHITE_COLOR_FIX: Record<string, string> = {
  '#fde047': '#a16207', // light: amarillo palido -> ambar oscuro
  '#84cc16': '#4d7c0f', // terrain: lima -> verde oliva
  '#9ca3af': '#52525b', // circulacion: gris claro -> gris oscuro
};

const REQUIREMENT_SYMBOL_MAP: Record<string, TechnicalSymbolKey> = {
  'Medidas disponibles del recinto (int/ext)': 'scan',
  'Tipo de terreno (nivelado, estable)': 'terrain',
  'Circulación pública segura': 'circulation',
  'Zona con menor estimulación sensorial para descanso': 'sensory',
  'Toldo/carpa (mínimo 3×3m)': 'tent',
  'Mesas (2-3 según modalidad)': 'table',
  'Sillas (4-6 por stand)': 'chairs',
  'Rack o caja de almacenamiento': 'rack',
  'Basureros, señalética': 'trash',
  'Punto eléctrico disponible': 'power',
  'Iluminación adecuada': 'light',
  'Agua/hidratación si aplica': 'water',
  'Calefacción si exterior nocturno': 'heating',
  'Contacto directo con producción': 'contact',
  'Coordinación con seguridad privada': 'security',
  'Acceso a equipo médico del evento': 'medical',
  'Extintor operativo en el stand': 'extinguisher',
  'Alimentación si jornada > 5 horas': 'food',
};

const makeSymbolElement = (key: TechnicalSymbolKey, idPrefix = 'symbol'): Element => {
  const spec = specOPower(key);
  return {
    id: `${idPrefix}-${spec.key}`,
    type: 'symbol',
    symbolKey: spec.key,
    x: spec.x,
    y: spec.y,
    w: spec.w,
    h: spec.h,
    label: spec.label,
    color: spec.color,
    visible: true,
    // Sin category el simbolo queda fuera de la leyenda agrupada (filtra por el.category).
    category: SYMBOL_CATEGORY[spec.key] || 'Zonas de Atención',
  };
};

// ── Checklist Data (18 requirements in 4 categories) ───
const CHECKLIST_SECTIONS = [
  {
    title: 'Espacio',
    iconName: 'Grid3X3',
    items: [
      { text: 'Medidas disponibles del recinto (int/ext)', icon: 'Scan' },
      { text: 'Tipo de terreno (nivelado, estable)', icon: 'Map' },
      { text: 'Circulación pública segura', icon: 'Users' },
      { text: 'Zona con menor estimulación sensorial para descanso', icon: 'Moon' }
    ]
  },
  {
    title: 'Infraestructura',
    iconName: 'Square',
    items: [
      { text: 'Toldo/carpa (mínimo 3×3m)', icon: 'Home' },
      { text: 'Mesas (2-3 según modalidad)', icon: 'Table' },
      { text: 'Sillas (4-6 por stand)', icon: 'Armchair' },
      { text: 'Rack o caja de almacenamiento', icon: 'Box' },
      { text: 'Basureros, señalética', icon: 'Trash2' }
    ]
  },
  {
    title: 'Servicios',
    iconName: 'Zap',
    items: [
      { text: 'Punto eléctrico disponible', icon: 'Zap' },
      { text: 'Iluminación adecuada', icon: 'Lightbulb' },
      { text: 'Agua/hidratación si aplica', icon: 'Droplet' },
      { text: 'Calefacción si exterior nocturno', icon: 'Thermometer' }
    ]
  },
  {
    title: 'Coordinación',
    iconName: 'Users',
    items: [
      { text: 'Contacto directo con producción', icon: 'User' },
      { text: 'Coordinación con seguridad privada', icon: 'ShieldAlert' },
      { text: 'Acceso a equipo médico del evento', icon: 'HeartPulse' },
      { text: 'Alimentación si jornada > 5 horas', icon: 'Utensils' },
      { text: 'Extintor operativo en el stand', icon: 'Flame' }
    ]
  }
];

// Categoria de cada simbolo tecnico, derivada de las mismas 4 categorias del
// checklist (Espacio/Infraestructura/Servicios/Coordinacion) via REQUIREMENT_SYMBOL_MAP.
// Los simbolos sin item de checklist asociado (zonas de servicio: testeo, contencion)
// caen en 'Zonas de Atención'.
const ITEM_TEXT_TO_CATEGORY: Record<string, string> = {};
CHECKLIST_SECTIONS.forEach(section => {
  section.items.forEach(item => { ITEM_TEXT_TO_CATEGORY[item.text] = section.title; });
});
const SYMBOL_CATEGORY: Record<TechnicalSymbolKey, string> = {};
Object.entries(REQUIREMENT_SYMBOL_MAP).forEach(([itemText, symbolKey]) => {
  SYMBOL_CATEGORY[symbolKey] = ITEM_TEXT_TO_CATEGORY[itemText] || 'Zonas de Atención';
});

// Helper to render Lucide icons dynamically for requirements
const renderRequirementIcon = (iconName: string, className = "w-4 h-4 text-zinc-400") => {
  switch (iconName) {
    case 'Scan': return <Scan className={className} />;
    case 'Map': return <Map className={className} />;
    case 'Users': return <Users className={className} />;
    case 'Moon': return <Moon className={className} />;
    case 'Home': return <Home className={className} />;
    case 'Table': return <Table className={className} />;
    case 'Armchair': return <Armchair className={className} />;
    case 'Box': return <Box className={className} />;
    case 'Trash2': return <Trash2 className={className} />;
    case 'Zap': return <Zap className={className} />;
    case 'Lightbulb': return <Lightbulb className={className} />;
    case 'Droplet': return <Droplet className={className} />;
    case 'Thermometer': return <Thermometer className={className} />;
    case 'User': return <User className={className} />;
    case 'ShieldAlert': return <ShieldAlert className={className} />;
    case 'HeartPulse': return <HeartPulse className={className} />;
    case 'Utensils': return <Utensils className={className} />;
    case 'Flame': return <Flame className={className} />;
    case 'Sofa': return <Sofa className={className} />;
    case 'Cylinder': return <Cylinder className={className} />;
    default: return <Grid3X3 className={className} />;
  }
};

const withMedida = (label: string, m: string) => `${label} (${m})`;

// Font que quepa en el ancho del rect: con el plano a escala real un modulo de
// 3 m mide 600 px y el font fijo de 42 desbordaba los labels largos.
// ~0.62 em de ancho promedio por caracter en Arial bold uppercase.
const rectLabelFont = (label: string, w: number) =>
  Math.max(24, Math.min(42, Math.round((w - 80) / (0.62 * Math.max(label.length, 1)))));

const placedSymbol = (key: TechnicalSymbolKey, id: string, x: number, y: number, label?: string): Element => {
  const spec = specOPower(key);
  const category = SYMBOL_CATEGORY[key] || 'Zonas de Atención';
  return { id, type: 'symbol', symbolKey: spec.key, x, y, w: spec.w, h: spec.h, label: label || spec.label, color: spec.color, visible: true, category };
};

// ── Default elements builder in 2970x2100 px format, por pack ───────
// Plano tipo "compound" a proporcion real: 1 m = 200 px. El pack se dibuja como
// UN recinto contiguo (modulos 3x3 m lado a lado) con frente publico abajo y
// acceso de servicio atras, mesas a escala DENTRO de los stands, y solo los
// iconos FISICOS puestos en su lugar de uso (electricidad, agua, extintor...).
// Los requerimientos de coordinacion (medico, seguridad, produccion) NO van en
// el plano: viven en el checklist de la pagina 1, y al marcarlos ahi se agrega
// su simbolo req-* al mapa si el usuario lo quiere ubicar.
const M = 200; // px por metro
function buildElements(packId: PackId): Element[] {
  const modules = packId === 'COMPLETO' ? 3 : packId === 'TESTEO' ? 2 : 1;
  const X0 = packId === 'COMPLETO' ? 140 : packId === 'TESTEO' ? 500 : 700;
  const W = modules * 3 * M;        // frente del compound (3 m por modulo)
  const TOP = 700;                  // borde trasero de los stands
  const H = 3 * M;                  // fondo de los stands (3 m)
  const frontM = (modules * 3).toFixed(1);

  // Pack INFO es "testeo o informativo a eleccion" (1 stand, sin comprometerse a
  // cual; el detalle vive en las inclusiones del pack); TESTEO/COMPLETO incluyen
  // ambos servicios, ahi el stand 1 si es especificamente informativo.
  const stand1Label = packId === 'INFO' ? 'Stand Testeo/Info' : 'Stand Informativo';

  const base: Element[] = [
    { id: 'acceso', type: 'rect', x: X0, y: packId === 'COMPLETO' ? 240 : 560, w: W, h: 100, label: packId === 'INFO' ? 'Acceso servicio' : 'Acceso servicio / carga', color: '#9ca3af', visible: true },
    { id: 'stand1', type: 'rect', x: X0, y: TOP, w: 3 * M, h: H, label: withMedida(stand1Label, '3×3 m'), color: '#0369a1', visible: true },
    { id: 'mesa1', type: 'rect', x: X0 + (packId === 'INFO' ? 60 : 120), y: TOP + 420, w: 360, h: 120, label: withMedida('Mesa', '1.8×0.6 m'), color: '#10b981', visible: true },
    { id: 'publico', type: 'rect', x: X0, y: 1400, w: W, h: 110, label: `Frente público — ${frontM} m`, color: '#6366f1', visible: true },
  ];

  // Iconos con tamano fisico acotado (los labels ya no van en el mapa: decodifica
  // la leyenda, como en un plano tecnico real).
  const sized = (el: Element, s: number): Element => ({ ...el, w: s, h: s });

  // Reglas de equipamiento (definidas por el usuario): electricidad en CADA stand,
  // iluminacion en CADA mesa, extintor SOLO en el pack COMPLETO (evento masivo),
  // calefaccion en la zona de descanso.
  const icons: Element[] = [
    sized(placedSymbol('power', 'power1', X0 + 20, TOP + 130), 140),
    sized(placedSymbol('light', 'light1', X0 + (packId === 'INFO' ? 300 : 360), TOP + 280), 120),
    placedSymbol('trash', 'trash', X0 + W + 40, TOP + 380),
  ];

  if (packId === 'TESTEO' || packId === 'COMPLETO') {
    const S2 = X0 + 3 * M;
    base.push(
      { id: 'stand2', type: 'rect', x: S2, y: TOP, w: 3 * M, h: H, label: withMedida('Stand Testeo', '3×3 m'), color: '#2d5a4a', visible: true },
      { id: 'mesa2', type: 'rect', x: S2 + (packId === 'COMPLETO' ? 160 : 120), y: TOP + 420, w: 360, h: 120, label: withMedida('Mesa', '1.8×0.6 m'), color: '#10b981', visible: true },
    );
    icons.push(
      sized(placedSymbol('power', 'power2', S2 + 20, TOP + 130), 140),
      placedSymbol('testeo', 'testeo', S2 + 180, TOP + 170),
      sized(placedSymbol('light', 'light2', S2 + 400, TOP + 280), 120),
    );
  }

  if (packId === 'TESTEO') {
    icons.push(sized(placedSymbol('water', 'water', X0 + 3 * M + 430, TOP + 130), 140));
  }

  if (packId === 'COMPLETO') {
    const Z = X0 + 6 * M;
    base.push(
      // Back of house detras de los stands: coordinacion + almacenamiento.
      { id: 'coordinacion', type: 'rect', x: X0, y: 380, w: 900, h: 240, label: 'Coordinación Operativa (BOH)', color: '#ca8a04', visible: true },
      { id: 'descanso', type: 'rect', x: Z, y: TOP, w: 3 * M, h: H, label: withMedida('Zona Descanso', '3×3 m'), color: '#059669', visible: true },
    );
    icons.push(
      sized(placedSymbol('extinguisher', 'extinguisher', X0 + 3 * M + 20, TOP + 410), 120),
      sized(placedSymbol('rack', 'rack', X0 + 920, 420), 140),
      sized(placedSymbol('water', 'water', Z + 20, TOP + 130), 140),
      sized(placedSymbol('sensory', 'sensory', Z + 200, TOP + 130), 140),
      sized(placedSymbol('heating', 'heating', Z + 380, TOP + 130), 140),
      placedSymbol('contencion', 'contencion', Z + 200, TOP + 320),
    );
  }

  return [...base, ...icons];
}

// ── Main component ───────────────────────────────────────────────────
type Page = 'req' | 'map' | 'config';

const PLANO_CHECKED_ITEMS_KEY = 'plano_checked_items';

export default function PlanoTool() {
  const [preset, setPreset] = useState<PackId>('TESTEO');
  const [exportTheme, setExportTheme] = useState<ExportTheme>('dark');
  const [page, setPage] = useState<Page>('map');
  const [elements, setElements] = useState<Element[]>(() => buildElements('TESTEO'));
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Alta de un simbolo propio desde la app. Antes habia que editar
  // data/plano_simbolos.json a mano y dejar el archivo en una carpeta, que no
  // es "puede agregar un icono" en ningun sentido util.
  const [nuevoSimboloAbierto, setNuevoSimboloAbierto] = useState(false);
  const [nuevoSimboloNombre, setNuevoSimboloNombre] = useState('');
  const [nuevoSimboloColor, setNuevoSimboloColor] = useState('#38bdf8');
  const [nuevoSimboloZona, setNuevoSimboloZona] = useState('INFRAESTRUCTURA');
  const [nuevoSimboloAviso, setNuevoSimboloAviso] = useState<string | null>(null);
  // Si sube una imagen en vez de un SVG, se traza y se le MUESTRA el resultado
  // antes de guardar: un trazado automatico puede salir sucio y quien decide si
  // sirve es ella.
  const [previewSvg, setPreviewSvg] = useState<string | null>(null);
  // SIMBOLOS_PROPIOS se muta fuera de React; esto fuerza el redibujo de la
  // paleta cuando se guarda uno nuevo.
  const [refrescoSimbolos, setRefrescoSimbolos] = useState(0);
  const [checkedItems, setCheckedItems] = useState<string[]>(() => {
    try {
      const raw = localStorage.getItem(PLANO_CHECKED_ITEMS_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  });
  const [legendPos, setLegendPos] = useState({ x: 1990, y: 120 });
  const [zoom, setZoom] = useState(1);
  const [showGrid, setShowGrid] = useState(true);
  const [showLegend, setShowLegend] = useState(true);
  const [eventName, setEventName] = useState('Evento Festival');
  const [eventDate, setEventDate] = useState('2026-06-28');
  const [eventVenue, setEventVenue] = useState('Parque Bicentenario');
  const [backendStatus, setBackendStatus] = useState('');
  const [vjEvents, setVjEvents] = useState<VjEventRecord[]>([]);
  const [selectedEventKey, setSelectedEventKey] = useState('');
  const [eventCatalogStatus, setEventCatalogStatus] = useState(
    'El catalogo aparece al abrir el plano desde el servidor del proyecto.'
  );

  const [orgTexts, setOrgTexts] = useState({
    who: 'Fundada en 2018, Reduciendo Daño es una ONG líder en implementación y formulación de políticas e insumos de reducción de daños en Chile, siendo pionera en la fabricación, distribución de implementos, reactivos y servicios de análisis de sustancias psicoactivas en el país. La Organización desarrolla proyectos de intervención en terreno orientados a fiestas, espacios de ocio y eventos donde existe consumo de sustancias psicoactivas. Nuestro objetivo es acercar herramientas de prevención, reducción de riesgos y educación preventiva, promoviendo decisiones informadas, el autocuidado y espacios más seguros.',
    goal: 'El proyecto busca informar, orientar y acompañar a personas que consuman o planeen consumir sustancias, mediante estrategias enfocadas en la seguridad, el cuidado informado y la prevención durante eventos y actividades recreativas.'
  });

  const svgRef = useRef<SVGSVGElement>(null);
  const selectedElement = elements.find(e => e.id === selectedId);
  const selectedVjEvent = vjEvents.find(event => event.eventKey === selectedEventKey);

  useEffect(() => {
    try {
      localStorage.setItem(PLANO_CHECKED_ITEMS_KEY, JSON.stringify(checkedItems));
    } catch {
      // localStorage no disponible (modo privado, cuota, etc.) — no bloquear la UI
    }
  }, [checkedItems]);

  useEffect(() => {
    if (window.location.protocol === 'file:') return;
    const controller = new AbortController();
    setEventCatalogStatus('Consultando catalogo VJ existente...');
    fetch('/api/vj/events', { signal: controller.signal })
      .then(async response => {
        if (!response.ok) throw new Error('HTTP ' + response.status);
        return response.json();
      })
      .then(data => {
        const events = Array.isArray(data?.events)
          ? data.events.filter((event: any) => typeof event?.eventKey === 'string')
          : [];
        setVjEvents(events as VjEventRecord[]);
        setEventCatalogStatus(
          data?.available === false
            ? 'El catalogo VJ todavia no esta construido.'
            : events.length
              ? String(events.length) + ' eventos existentes disponibles; no se creo otra fuente.'
              : 'Catalogo VJ disponible, pero sin eventos con datos utilizables.'
        );
      })
      .catch(error => {
        if (error?.name === 'AbortError') return;
        setVjEvents([]);
        setEventCatalogStatus(
          'Catalogo VJ no disponible en este servidor (' +
          (error instanceof Error ? error.message : String(error)) + ').'
        );
      });
    return () => controller.abort();
  }, []);

  const applyPreset = (p: PackId) => {
    setPreset(p);
    setElements(buildElements(p));
    setSelectedId(null);
    setCheckedItems([]);
    try {
      localStorage.removeItem(PLANO_CHECKED_ITEMS_KEY);
    } catch {
      // localStorage no disponible — ignorar
    }
  };

  const selectElementAndBringToFront = (id: string) => {
    // Seleccionar NO debe cambiar capas. El orden se controla con botones explícitos.
    setSelectedId(id);
  };

  const toggleVisible = (id: string) => {
    setElements(els => {
      const next = els.map(el => el.id === id ? { ...el, visible: !el.visible } : el);
      syncChecklistFromElements(next);
      return next;
    });
  };

  const removeElement = (id: string) => {
    setElements(els => {
      const next = els.filter(el => el.id !== id);
      syncChecklistFromElements(next);
      return next;
    });
    if (selectedId === id) setSelectedId(null);
  };

  const addElement = (zoneType: string) => {
    const id = `zone-${Date.now()}`;
    const newEl: Element = {
      id,
      type: 'rect',
      x: 600 + Math.random() * 500,
      y: 600 + Math.random() * 400,
      w: 600,
      h: 300,
      label: ZONE_LABELS[zoneType] || zoneType,
      color: ZONE_COLORS[zoneType] || '#555',
      visible: true
    };
    setElements(prev => {
      const next = [...prev, newEl];
      syncChecklistFromElements(next);
      return next;
    });
    setSelectedId(id);
  };

  const addSymbol = (st: TechnicalSymbolKey) => {
    const spec = specOPower(st);
    const id = `symbol-${st}-${Date.now()}`;
    const newEl: Element = {
      ...makeSymbolElement(st, `symbol-${Date.now()}`),
      id,
      x: spec.x + Math.round(Math.random() * 240),
      y: spec.y + Math.round(Math.random() * 180),
    };
    setElements(prev => {
      const next = [...prev, newEl];
      syncChecklistFromElements(next);
      return next;
    });
    setSelectedId(id);
  };

  const duplicateSelected = () => {
    if (!selectedElement) return;
    const dup: Element = { ...selectedElement, id: `${selectedElement.id}-copy-${Date.now()}`, x: selectedElement.x + 100, y: selectedElement.y + 100 };
    setElements(prev => [...prev, dup]);
    setSelectedId(dup.id);
  };

  const moveLayer = (dir: 'up' | 'down') => {
    if (!selectedId) return;
    const i = elements.findIndex(e => e.id === selectedId);
    const target = dir === 'up' ? i + 1 : i - 1;
    if (target < 0 || target >= elements.length) return;
    const next = [...elements];
    [next[i], next[target]] = [next[target], next[i]];
    setElements(next);
  };

  const layerPriority = (el: Element) => {
    // Bandas de flujo (frente publico / acceso servicio) siempre arriba.
    if (el.id === 'entrada' || el.id === 'publico' || el.id === 'acceso') return 40;
    if (el.type === 'symbol') return 30;
    if (el.type === 'rect') return 10;
    return 20;
  };

  const orderLayersByPriority = () => {
    setElements(prev => [...prev].sort((a, b) => {
      const pa = layerPriority(a);
      const pb = layerPriority(b);
      if (pa !== pb) return pa - pb;
      if (a.y !== b.y) return a.y - b.y;
      if (a.x !== b.x) return a.x - b.x;
      return a.id.localeCompare(b.id);
    }));
  };

  const alignSelected = (mode: 'left' | 'centerX' | 'right' | 'top' | 'centerY' | 'bottom') => {
    if (!selectedId) return;
    const frame = PLANO_FRAME;
    setElements(prev => prev.map(el => {
      if (el.id !== selectedId) return el;
      if (mode === 'left') return { ...el, x: frame.x };
      if (mode === 'centerX') return { ...el, x: Math.round(frame.x + (frame.w - el.w) / 2) };
      if (mode === 'right') return { ...el, x: frame.x + frame.w - el.w };
      if (mode === 'top') return { ...el, y: frame.y };
      if (mode === 'centerY') return { ...el, y: Math.round(frame.y + (frame.h - el.h) / 2) };
      if (mode === 'bottom') return { ...el, y: frame.y + frame.h - el.h };
      return el;
    }));
  };

  const snap = (value: number) => Math.round(value / GRID) * GRID;

  const autoArrangePlano = () => {
    const frame = PLANO_FRAME;
    const rectArea = { x: frame.x + 120, y: frame.y + 220, w: 1800, h: frame.h - 360 };
    const symbolArea = { x: frame.x + 2020, y: frame.y + 220, w: 740, h: frame.h - 360 };
    const rectGap = 80;
    const symbolGapX = 230;
    const symbolGapY = 185;
    let rectX = rectArea.x;
    let rectY = rectArea.y;
    let rowH = 0;
    let symbolIndex = 0;

    setElements(prev => prev.map(el => {
      if (!el.visible) return el;
      if (el.id === 'entrada') {
        return { ...el, x: snap(frame.x + (frame.w - el.w) / 2), y: frame.y + 70 };
      }
      if (el.type === 'symbol') {
        const col = symbolIndex % 3;
        const row = Math.floor(symbolIndex / 3);
        symbolIndex += 1;
        return {
          ...el,
          x: snap(symbolArea.x + col * symbolGapX),
          y: snap(Math.min(symbolArea.y + row * symbolGapY, frame.y + frame.h - el.h - 40)),
        };
      }
      if (rectX + el.w > rectArea.x + rectArea.w) {
        rectX = rectArea.x;
        rectY += rowH + rectGap;
        rowH = 0;
      }
      const next = { ...el, x: snap(rectX), y: snap(Math.min(rectY, rectArea.y + rectArea.h - el.h)) };
      rectX += el.w + rectGap;
      rowH = Math.max(rowH, el.h);
      return next;
    }).sort((a, b) => {
      const pa = layerPriority(a);
      const pb = layerPriority(b);
      if (pa !== pb) return pa - pb;
      if (a.y !== b.y) return a.y - b.y;
      if (a.x !== b.x) return a.x - b.x;
      return a.id.localeCompare(b.id);
    }));
    setLegendPos({ x: 1990, y: 120 });
  };

  const resetLegendPosition = () => setLegendPos({ x: 1990, y: 120 });

  const onMouseDown = useCallback((e: React.MouseEvent, id: string) => {
    e.preventDefault();
    const svg = svgRef.current;
    if (!svg) return;
    selectElementAndBringToFront(id);

    const pt = svg.createSVGPoint();
    pt.x = e.clientX; pt.y = e.clientY;
    const start = pt.matrixTransform(svg.getScreenCTM()!.inverse());
    const el = elements.find(x => x.id === id)!;
    const startX = el.x; const startY = el.y;

    const move = (me: MouseEvent) => {
      const mpt = svg.createSVGPoint();
      mpt.x = me.clientX; mpt.y = me.clientY;
      const mp = mpt.matrixTransform(svg.getScreenCTM()!.inverse());
      setElements(prev => prev.map(x =>
        x.id === id ? { ...x, x: Math.round((startX + (mp.x - start.x)) / GRID) * GRID, y: Math.round((startY + (mp.y - start.y)) / GRID) * GRID } : x
      ));
    };
    const up = () => {
      window.removeEventListener('mousemove', move);
      window.removeEventListener('mouseup', up);
    };
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
  }, [elements]);

  const onTouchStart = useCallback((e: React.TouchEvent, id: string) => {
    e.stopPropagation();
    const touch = e.touches[0];
    const svg = svgRef.current;
    if (!svg) return;
    selectElementAndBringToFront(id);

    const pt = svg.createSVGPoint();
    pt.x = touch.clientX; pt.y = touch.clientY;
    const start = pt.matrixTransform(svg.getScreenCTM()!.inverse());
    const el = elements.find(x => x.id === id)!;
    const startX = el.x; const startY = el.y;

    const move = (te: TouchEvent) => {
      if (te.touches.length === 0) return;
      const t = te.touches[0];
      const mpt = svg.createSVGPoint();
      mpt.x = t.clientX; mpt.y = t.clientY;
      const mp = mpt.matrixTransform(svg.getScreenCTM()!.inverse());
      setElements(prev => prev.map(x =>
        x.id === id ? { ...x, x: Math.round((startX + (mp.x - start.x)) / GRID) * GRID, y: Math.round((startY + (mp.y - start.y)) / GRID) * GRID } : x
      ));
    };
    const end = () => {
      window.removeEventListener('touchmove', move);
      window.removeEventListener('touchend', end);
    };
    window.addEventListener('touchmove', move, { passive: false });
    window.addEventListener('touchend', end);
  }, [elements]);

  // ─── Render Symbol (Procedural SVG without Emojis) ───
  // Iniciales del NOMBRE del simbolo (no de la key interna): "Carpa Hidratacion" -> "CH".
  const initialsOf = (label?: string) => {
    const words = (label || '').trim().split(/\s+/).filter(Boolean);
    const ini = words.map(w => w[0]).join('').slice(0, 2).toUpperCase();
    return ini || '?';
  };

  const renderSymbolGlyph = (key: string, fill: string, label?: string) => {
    switch (key) {
      case 'scan':
        return <><rect x="28" y="36" width="104" height="84" rx="8" fill="none" stroke={fill} strokeWidth="9" strokeDasharray="12 8"/><path d="M42 58 H118 M42 82 H92 M42 106 H108" stroke={fill} strokeWidth="7" strokeLinecap="round"/></>;
      case 'terrain':
        return <><path d="M22 112 C48 76 70 86 92 54 C110 30 126 42 140 70" fill="none" stroke={fill} strokeWidth="10" strokeLinecap="round"/><path d="M24 122 H138" stroke={fill} strokeWidth="8" strokeLinecap="round"/></>;
      case 'circulation':
        return <><path d="M34 80 H124" stroke={fill} strokeWidth="10" strokeLinecap="round"/><path d="M104 58 L128 80 L104 102" fill="none" stroke={fill} strokeWidth="10" strokeLinecap="round" strokeLinejoin="round"/><circle cx="48" cy="48" r="14" fill={fill}/><circle cx="78" cy="122" r="14" fill={fill}/></>;
      case 'sensory':
        return <><path d="M104 30 C68 38 50 66 58 96 C66 126 96 140 128 124 C82 120 66 76 104 30 Z" fill={fill}/><circle cx="42" cy="46" r="5" fill={fill}/><circle cx="132" cy="62" r="5" fill={fill}/></>;
      case 'tent':
        return <><path d="M22 122 L80 34 L138 122 Z" fill="none" stroke={fill} strokeWidth="10" strokeLinejoin="round"/><path d="M80 34 V122 M48 122 L80 78 L112 122" stroke={fill} strokeWidth="8" fill="none" strokeLinecap="round"/></>;
      case 'table':
        return <><rect x="28" y="54" width="104" height="42" rx="6" fill="none" stroke={fill} strokeWidth="10"/><path d="M46 96 V130 M114 96 V130" stroke={fill} strokeWidth="9" strokeLinecap="round"/></>;
      case 'chairs':
        return <><path d="M44 48 V112 H88 M88 112 V134" fill="none" stroke={fill} strokeWidth="10" strokeLinecap="round"/><path d="M94 48 V112 H128 M128 112 V134" fill="none" stroke={fill} strokeWidth="10" strokeLinecap="round"/></>;
      case 'rack':
        return <><rect x="24" y="24" width="112" height="112" rx="8" fill="none" stroke={fill} strokeWidth="9"/><path d="M24 62 H136 M24 98 H136 M62 24 V136 M98 24 V136" stroke={fill} strokeWidth="6" opacity="0.45"/></>;
      case 'trash':
        return <><path d="M50 52 H110 L102 134 H58 Z" fill="none" stroke={fill} strokeWidth="9" strokeLinejoin="round"/><path d="M42 52 H118 M64 38 H96 M70 72 V116 M90 72 V116" stroke={fill} strokeWidth="8" strokeLinecap="round"/></>;
      case 'power':
        return <><circle cx="80" cy="80" r="55" fill="none" stroke={fill} strokeWidth="9"/><path d="M88 28 L52 88 H82 L72 132 L112 70 H82 Z" fill={fill}/></>;
      case 'light':
        return <><circle cx="80" cy="66" r="34" fill="none" stroke={fill} strokeWidth="9"/><path d="M62 100 H98 M66 120 H94 M72 136 H88" stroke={fill} strokeWidth="8" strokeLinecap="round"/><path d="M80 14 V28 M34 34 L44 44 M126 34 L116 44" stroke={fill} strokeWidth="7" strokeLinecap="round"/></>;
      case 'water':
        return <><path d="M80 24 C116 70 126 92 110 118 C94 144 58 144 48 116 C38 88 58 66 80 24 Z" fill="none" stroke={fill} strokeWidth="10"/><path d="M62 106 C68 122 88 128 102 112" stroke={fill} strokeWidth="7" strokeLinecap="round"/></>;
      case 'heating':
        return <><rect x="42" y="30" width="76" height="104" rx="12" fill="none" stroke={fill} strokeWidth="9"/><path d="M62 54 V110 M80 54 V110 M98 54 V110" stroke={fill} strokeWidth="8" strokeLinecap="round"/></>;
      case 'contact':
        return <><circle cx="80" cy="52" r="24" fill="none" stroke={fill} strokeWidth="9"/><path d="M38 132 C44 98 116 98 122 132" fill="none" stroke={fill} strokeWidth="10" strokeLinecap="round"/></>;
      case 'security':
        return <><path d="M80 22 L124 40 V76 C124 104 106 126 80 140 C54 126 36 104 36 76 V40 Z" fill="none" stroke={fill} strokeWidth="9" strokeLinejoin="round"/><path d="M62 80 L76 94 L102 62" fill="none" stroke={fill} strokeWidth="9" strokeLinecap="round" strokeLinejoin="round"/></>;
      case 'medical':
        return <><path d="M80 136 C34 96 28 66 48 46 C62 32 78 42 80 54 C82 42 100 32 114 46 C134 66 126 98 80 136 Z" fill="none" stroke={fill} strokeWidth="9"/><path d="M80 58 V106 M56 82 H104" stroke={fill} strokeWidth="9" strokeLinecap="round"/></>;
      case 'food':
        return <><path d="M54 28 V76 M70 28 V76 M62 76 V134" stroke={fill} strokeWidth="9" strokeLinecap="round"/><path d="M104 28 C124 48 122 82 104 94 V134" fill="none" stroke={fill} strokeWidth="9" strokeLinecap="round"/></>;
      case 'extinguisher':
        return <><rect x="60" y="50" width="42" height="88" rx="9" fill="none" stroke={fill} strokeWidth="9"/><path d="M70 50 V34 H94 V50 M94 62 H120 M120 62 L134 52" stroke={fill} fill="none" strokeWidth="8" strokeLinecap="round"/><path d="M70 82 H92" stroke={fill} strokeWidth="7" strokeLinecap="round"/></>;
      case 'testeo':
        return <><circle cx="80" cy="80" r="58" fill={fill} fillOpacity="0.16" stroke={fill} strokeWidth="9"/><path d="M60 42 H100 M80 42 V82 L112 126 H48 L80 82" fill="none" stroke={fill} strokeWidth="9" strokeLinejoin="round"/></>;
      case 'contencion':
        return <><circle cx="80" cy="80" r="58" fill={fill} fillOpacity="0.16" stroke={fill} strokeWidth="9"/><path d="M80 120 C44 88 44 62 62 52 C74 46 80 56 80 64 C80 56 90 46 102 52 C120 62 116 90 80 120 Z" fill={fill}/></>;
      case 'sillon':
        return <><rect x="24" y="56" width="18" height="62" rx="7" fill="none" stroke={fill} strokeWidth="9"/><rect x="118" y="56" width="18" height="62" rx="7" fill="none" stroke={fill} strokeWidth="9"/><rect x="40" y="42" width="80" height="26" rx="8" fill="none" stroke={fill} strokeWidth="9"/><rect x="40" y="66" width="80" height="42" rx="8" fill="none" stroke={fill} strokeWidth="9"/><path d="M80 66 V108" stroke={fill} strokeWidth="9" strokeLinecap="round"/></>;
      case 'toalla':
        return <><ellipse cx="80" cy="46" rx="34" ry="14" fill="none" stroke={fill} strokeWidth="9"/><ellipse cx="80" cy="46" rx="13" ry="5" fill="none" stroke={fill} strokeWidth="9"/><path d="M46 46 V96 M114 46 V96" fill="none" stroke={fill} strokeWidth="9" strokeLinecap="round"/><path d="M46 96 C46 104 114 104 114 96" fill="none" stroke={fill} strokeWidth="9" strokeLinecap="round"/><path d="M100 98 C120 102 124 114 108 120 C94 126 98 134 114 138" fill="none" stroke={fill} strokeWidth="9" strokeLinecap="round"/></>;
      default: {
        // Simbolo del catalogo editable (data/plano_simbolos.json): se incrusta
        // su .svg. El lienzo de aqui ya es 0..160, que es la misma convencion
        // que usa markupSimboloPropio, asi que centrar en (80,80) a escala 1
        // lo deja calzado. Va sanitizado en esa funcion (sin script ni on*).
        const propio = simboloPropio(key);
        if (propio?.svg) {
          const marca = markupSimboloPropio(propio.svg, fill, 80, 80, 1);
          if (marca) return <g dangerouslySetInnerHTML={{ __html: marca }} />;
        }
        // Simbolo sin dibujo utilizable: circulo + iniciales del nombre. Mismo
        // dibujo en canvas, leyenda y print.
        return <><circle cx="80" cy="80" r="54" fill="none" stroke={fill} strokeWidth="9"/><text x="80" y="94" textAnchor="middle" fontSize="46" fill={fill} fontWeight="bold" fontFamily="monospace">{initialsOf(label)}</text></>;
      }
    }
  };

  const renderSymbol = (el: Element, isPrint = false) => {
    const isSelected = !isPrint && el.id === selectedId;
    const fill = isPrint ? '#000000' : el.color;

    return (
      <g
        key={el.id}
        transform={`translate(${el.x},${el.y})`}
        onMouseDown={isPrint ? undefined : (e) => { e.stopPropagation(); onMouseDown(e, el.id); }}
        onTouchStart={isPrint ? undefined : (e) => { e.stopPropagation(); onTouchStart(e, el.id); }}
        onClick={isPrint ? undefined : (e) => { e.stopPropagation(); selectElementAndBringToFront(el.id); }}
        className={isPrint ? undefined : "cursor-move"}
        opacity={el.visible ? 1 : 0.2}
      >
        <rect width={el.w} height={el.h} fill="transparent" stroke={isSelected ? '#fff' : 'none'} strokeWidth={5} />
        <svg x={0} y={0} width={el.w} height={el.h} viewBox="0 0 160 160" overflow="visible">
          {renderSymbolGlyph(el.symbolKey || 'unknown', fill, el.label)}
        </svg>
        {/* Sin caption junto al icono: la leyenda decodifica; al seleccionar se ve el nombre */}
        {isSelected && (
          <text x={el.w / 2} y={el.h + 34} textAnchor="middle" fontSize="30" fill={fill} fontWeight="bold" fontFamily="monospace">
            {el.label.toUpperCase()}
          </text>
        )}
        {isSelected && (
          <rect x={-10} y={-10} width={el.w + 20} height={el.h + 20} rx={12} fill="none" stroke="#10b981" strokeWidth={10} strokeDasharray="20 10" />
        )}
      </g>
    );
  };

  const clampLegendPos = (x: number, y: number) => {
    const frame = PLANO_FRAME;
    const legendWidth = 900;
    const legendHeight = legendHeightFor(visibleLegendSymbols.length);
    return {
      x: Math.min(Math.max(x, frame.x), frame.x + frame.w - legendWidth),
      y: Math.min(Math.max(y, frame.y), frame.y + frame.h - legendHeight),
    };
  };

  const onLegendMouseDown = (e: React.MouseEvent) => {
    const svg = svgRef.current;
    if (!svg) return;
    const pt = svg.createSVGPoint();
    pt.x = e.clientX; pt.y = e.clientY;
    const start = pt.matrixTransform(svg.getScreenCTM()!.inverse());
    const lx = legendPos.x; const ly = legendPos.y;

    const move = (me: MouseEvent) => {
      const mpt = svg.createSVGPoint();
      mpt.x = me.clientX; mpt.y = me.clientY;
      const mp = mpt.matrixTransform(svg.getScreenCTM()!.inverse());
      setLegendPos(clampLegendPos(lx + (mp.x - start.x), ly + (mp.y - start.y)));
    };
    const up = () => {
      window.removeEventListener('mousemove', move);
      window.removeEventListener('mouseup', up);
    };
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
    e.stopPropagation();
  };

  const onLegendTouchStart = (e: React.TouchEvent) => {
    const svg = svgRef.current;
    if (!svg) return;
    const touch = e.touches[0];
    const pt = svg.createSVGPoint();
    pt.x = touch.clientX; pt.y = touch.clientY;
    const start = pt.matrixTransform(svg.getScreenCTM()!.inverse());
    const lx = legendPos.x; const ly = legendPos.y;

    const move = (te: TouchEvent) => {
      if (te.touches.length === 0) return;
      const t = te.touches[0];
      const mpt = svg.createSVGPoint();
      mpt.x = t.clientX; mpt.y = t.clientY;
      const mp = mpt.matrixTransform(svg.getScreenCTM()!.inverse());
      setLegendPos(clampLegendPos(lx + (mp.x - start.x), ly + (mp.y - start.y)));
    };
    const end = () => {
      window.removeEventListener('touchmove', move);
      window.removeEventListener('touchend', end);
    };
    window.addEventListener('touchmove', move, { passive: false });
    window.addEventListener('touchend', end);
    e.stopPropagation();
  };

  const escapeHtml = (value: string) => value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');

  const symbolIconMarkup = (key: string, color: string, cx: number, cy: number, scale: number, label?: string) => {
    const sw = Math.max(5, 7 * scale);
    const c = color;
    const x = (n: number) => cx + (n - 80) * scale;
    const y = (n: number) => cy + (n - 80) * scale;
    switch (key) {
      case 'power':
        return `<path d="M ${x(88)} ${y(28)} L ${x(52)} ${y(88)} H ${x(82)} L ${x(72)} ${y(132)} L ${x(112)} ${y(70)} H ${x(82)} Z" fill="${c}"/>`;
      case 'scan':
        return `<rect x="${x(28)}" y="${y(36)}" width="${104*scale}" height="${84*scale}" rx="${8*scale}" fill="none" stroke="${c}" stroke-width="${sw}" stroke-dasharray="${12*scale} ${8*scale}"/><path d="M ${x(42)} ${y(58)} H ${x(118)} M ${x(42)} ${y(82)} H ${x(92)} M ${x(42)} ${y(106)} H ${x(108)}" stroke="${c}" stroke-width="${sw}" stroke-linecap="round"/>`;
      case 'terrain':
        return `<path d="M ${x(22)} ${y(112)} C ${x(48)} ${y(76)} ${x(70)} ${y(86)} ${x(92)} ${y(54)} C ${x(110)} ${y(30)} ${x(126)} ${y(42)} ${x(140)} ${y(70)}" fill="none" stroke="${c}" stroke-width="${sw}" stroke-linecap="round"/><path d="M ${x(24)} ${y(122)} H ${x(138)}" stroke="${c}" stroke-width="${sw}" stroke-linecap="round"/>`;
      case 'circulation':
        return `<path d="M ${x(34)} ${y(80)} H ${x(124)}" stroke="${c}" stroke-width="${sw}" stroke-linecap="round"/><path d="M ${x(104)} ${y(58)} L ${x(128)} ${y(80)} L ${x(104)} ${y(102)}" fill="none" stroke="${c}" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round"/><circle cx="${x(48)}" cy="${y(48)}" r="${14*scale}" fill="${c}"/><circle cx="${x(78)}" cy="${y(122)}" r="${14*scale}" fill="${c}"/>`;
      case 'sensory':
        return `<path d="M ${x(104)} ${y(30)} C ${x(68)} ${y(38)} ${x(50)} ${y(66)} ${x(58)} ${y(96)} C ${x(66)} ${y(126)} ${x(96)} ${y(140)} ${x(128)} ${y(124)} C ${x(82)} ${y(120)} ${x(66)} ${y(76)} ${x(104)} ${y(30)} Z" fill="${c}"/><circle cx="${x(42)}" cy="${y(46)}" r="${5*scale}" fill="${c}"/><circle cx="${x(132)}" cy="${y(62)}" r="${5*scale}" fill="${c}"/>`;
      case 'rack':
        return `<rect x="${x(24)}" y="${y(24)}" width="${112*scale}" height="${112*scale}" rx="${8*scale}" fill="none" stroke="${c}" stroke-width="${sw}"/><path d="M ${x(24)} ${y(62)} H ${x(136)} M ${x(24)} ${y(98)} H ${x(136)} M ${x(62)} ${y(24)} V ${y(136)} M ${x(98)} ${y(24)} V ${y(136)}" stroke="${c}" stroke-width="${sw}" opacity="0.45"/>`;
      case 'trash':
        return `<path d="M ${x(50)} ${y(52)} H ${x(110)} L ${x(102)} ${y(134)} H ${x(58)} Z" fill="none" stroke="${c}" stroke-width="${sw}" stroke-linejoin="round"/><path d="M ${x(42)} ${y(52)} H ${x(118)} M ${x(64)} ${y(38)} H ${x(96)} M ${x(70)} ${y(72)} V ${y(116)} M ${x(90)} ${y(72)} V ${y(116)}" stroke="${c}" stroke-width="${sw}" stroke-linecap="round"/>`;
      case 'light':
        return `<circle cx="${x(80)}" cy="${y(66)}" r="${34*scale}" fill="none" stroke="${c}" stroke-width="${sw}"/><path d="M ${x(62)} ${y(100)} H ${x(98)} M ${x(66)} ${y(120)} H ${x(94)} M ${x(72)} ${y(136)} H ${x(88)}" stroke="${c}" stroke-width="${sw}" stroke-linecap="round"/><path d="M ${x(80)} ${y(14)} V ${y(28)} M ${x(34)} ${y(34)} L ${x(44)} ${y(44)} M ${x(126)} ${y(34)} L ${x(116)} ${y(44)}" stroke="${c}" stroke-width="${sw}" stroke-linecap="round"/>`;
      case 'heating':
        return `<rect x="${x(42)}" y="${y(30)}" width="${76*scale}" height="${104*scale}" rx="${12*scale}" fill="none" stroke="${c}" stroke-width="${sw}"/><path d="M ${x(62)} ${y(54)} V ${y(110)} M ${x(80)} ${y(54)} V ${y(110)} M ${x(98)} ${y(54)} V ${y(110)}" stroke="${c}" stroke-width="${sw}" stroke-linecap="round"/>`;
      case 'contact':
        return `<circle cx="${x(80)}" cy="${y(52)}" r="${24*scale}" fill="none" stroke="${c}" stroke-width="${sw}"/><path d="M ${x(38)} ${y(132)} C ${x(44)} ${y(98)} ${x(116)} ${y(98)} ${x(122)} ${y(132)}" fill="none" stroke="${c}" stroke-width="${sw}" stroke-linecap="round"/>`;
      case 'food':
        return `<path d="M ${x(54)} ${y(28)} V ${y(76)} M ${x(70)} ${y(28)} V ${y(76)} M ${x(62)} ${y(76)} V ${y(134)}" stroke="${c}" stroke-width="${sw}" stroke-linecap="round"/><path d="M ${x(104)} ${y(28)} C ${x(124)} ${y(48)} ${x(122)} ${y(82)} ${x(104)} ${y(94)} V ${y(134)}" fill="none" stroke="${c}" stroke-width="${sw}" stroke-linecap="round"/>`;
      case 'water':
        return `<path d="M ${x(80)} ${y(24)} C ${x(116)} ${y(70)} ${x(126)} ${y(92)} ${x(110)} ${y(118)} C ${x(94)} ${y(144)} ${x(58)} ${y(144)} ${x(48)} ${y(116)} C ${x(38)} ${y(88)} ${x(58)} ${y(66)} ${x(80)} ${y(24)} Z" fill="none" stroke="${c}" stroke-width="${sw}"/>`;
      case 'table':
        return `<rect x="${x(28)}" y="${y(54)}" width="${104*scale}" height="${42*scale}" rx="${6*scale}" fill="none" stroke="${c}" stroke-width="${sw}"/><path d="M ${x(46)} ${y(96)} V ${y(130)} M ${x(114)} ${y(96)} V ${y(130)}" stroke="${c}" stroke-width="${sw}" stroke-linecap="round"/>`;
      case 'chairs':
        return `<path d="M ${x(44)} ${y(48)} V ${y(112)} H ${x(88)} M ${x(88)} ${y(112)} V ${y(134)} M ${x(94)} ${y(48)} V ${y(112)} H ${x(128)} M ${x(128)} ${y(112)} V ${y(134)}" fill="none" stroke="${c}" stroke-width="${sw}" stroke-linecap="round"/>`;
      case 'tent':
        return `<path d="M ${x(22)} ${y(122)} L ${x(80)} ${y(34)} L ${x(138)} ${y(122)} Z M ${x(80)} ${y(34)} V ${y(122)}" fill="none" stroke="${c}" stroke-width="${sw}" stroke-linejoin="round"/>`;
      case 'security':
        return `<path d="M ${x(80)} ${y(22)} L ${x(124)} ${y(40)} V ${y(76)} C ${x(124)} ${y(104)} ${x(106)} ${y(126)} ${x(80)} ${y(140)} C ${x(54)} ${y(126)} ${x(36)} ${y(104)} ${x(36)} ${y(76)} V ${y(40)} Z" fill="none" stroke="${c}" stroke-width="${sw}"/><path d="M ${x(62)} ${y(80)} L ${x(76)} ${y(94)} L ${x(102)} ${y(62)}" fill="none" stroke="${c}" stroke-width="${sw}" stroke-linecap="round"/>`;
      case 'medical':
        return `<path d="M ${x(80)} ${y(58)} V ${y(106)} M ${x(56)} ${y(82)} H ${x(104)}" stroke="${c}" stroke-width="${sw}" stroke-linecap="round"/><path d="M ${x(80)} ${y(136)} C ${x(34)} ${y(96)} ${x(28)} ${y(66)} ${x(48)} ${y(46)} C ${x(62)} ${y(32)} ${x(78)} ${y(42)} ${x(80)} ${y(54)} C ${x(82)} ${y(42)} ${x(100)} ${y(32)} ${x(114)} ${y(46)} C ${x(134)} ${y(66)} ${x(126)} ${y(98)} ${x(80)} ${y(136)} Z" fill="none" stroke="${c}" stroke-width="${sw}"/>`;
      case 'extinguisher':
        return `<rect x="${x(60)}" y="${y(50)}" width="${42*scale}" height="${88*scale}" rx="${9*scale}" fill="none" stroke="${c}" stroke-width="${sw}"/><path d="M ${x(70)} ${y(50)} V ${y(34)} H ${x(94)} V ${y(50)} M ${x(94)} ${y(62)} H ${x(120)} L ${x(134)} ${y(52)}" stroke="${c}" fill="none" stroke-width="${sw}" stroke-linecap="round"/>`;
      case 'testeo':
        return `<circle cx="${cx}" cy="${cy}" r="${58*scale}" fill="${c}" fill-opacity="0.12" stroke="${c}" stroke-width="${sw}"/><path d="M ${x(60)} ${y(42)} H ${x(100)} M ${x(80)} ${y(42)} V ${y(82)} L ${x(112)} ${y(126)} H ${x(48)} L ${x(80)} ${y(82)}" fill="none" stroke="${c}" stroke-width="${sw}"/>`;
      case 'contencion':
        return `<circle cx="${cx}" cy="${cy}" r="${58*scale}" fill="${c}" fill-opacity="0.12" stroke="${c}" stroke-width="${sw}"/><path d="M ${x(80)} ${y(120)} C ${x(44)} ${y(88)} ${x(44)} ${y(62)} ${x(62)} ${y(52)} C ${x(74)} ${y(46)} ${x(80)} ${y(56)} ${x(80)} ${y(64)} C ${x(80)} ${y(56)} ${x(90)} ${y(46)} ${x(102)} ${y(52)} C ${x(120)} ${y(62)} ${x(116)} ${y(90)} ${x(80)} ${y(120)} Z" fill="${c}"/>`;
      case 'sillon':
        return `<rect x="${x(24)}" y="${y(56)}" width="${18*scale}" height="${62*scale}" rx="${7*scale}" fill="none" stroke="${c}" stroke-width="${sw}"/><rect x="${x(118)}" y="${y(56)}" width="${18*scale}" height="${62*scale}" rx="${7*scale}" fill="none" stroke="${c}" stroke-width="${sw}"/><rect x="${x(40)}" y="${y(42)}" width="${80*scale}" height="${26*scale}" rx="${8*scale}" fill="none" stroke="${c}" stroke-width="${sw}"/><rect x="${x(40)}" y="${y(66)}" width="${80*scale}" height="${42*scale}" rx="${8*scale}" fill="none" stroke="${c}" stroke-width="${sw}"/><path d="M ${x(80)} ${y(66)} V ${y(108)}" stroke="${c}" stroke-width="${sw}" stroke-linecap="round"/>`;
      case 'toalla':
        return `<ellipse cx="${x(80)}" cy="${y(46)}" rx="${34*scale}" ry="${14*scale}" fill="none" stroke="${c}" stroke-width="${sw}"/><ellipse cx="${x(80)}" cy="${y(46)}" rx="${13*scale}" ry="${5*scale}" fill="none" stroke="${c}" stroke-width="${sw}"/><path d="M ${x(46)} ${y(46)} V ${y(96)} M ${x(114)} ${y(46)} V ${y(96)}" fill="none" stroke="${c}" stroke-width="${sw}" stroke-linecap="round"/><path d="M ${x(46)} ${y(96)} C ${x(46)} ${y(104)} ${x(114)} ${y(104)} ${x(114)} ${y(96)}" fill="none" stroke="${c}" stroke-width="${sw}" stroke-linecap="round"/><path d="M ${x(100)} ${y(98)} C ${x(120)} ${y(102)} ${x(124)} ${y(114)} ${x(108)} ${y(120)} C ${x(94)} ${y(126)} ${x(98)} ${y(134)} ${x(114)} ${y(138)}" fill="none" stroke="${c}" stroke-width="${sw}" stroke-linecap="round"/>`;
      default: {
        // Simbolo propio (data/plano_simbolos.json): se incrusta su .svg con la
        // misma convencion de 160x160 que los de fabrica. Si el archivo no es
        // usable, cae al marcador de iniciales de abajo en vez de desaparecer.
        const propio = simboloPropio(key);
        if (propio?.svg) {
          const marca = markupSimboloPropio(propio.svg, c, cx, cy, scale);
          if (marca) return marca;
        }
        const words = (label || key).trim().split(/\s+/).filter(Boolean);
        const ini = (words.map(w => w[0]).join('').slice(0, 2) || '?').toUpperCase();
        return `<circle cx="${cx}" cy="${cy}" r="${48*scale}" fill="none" stroke="${c}" stroke-width="${sw}"/><text x="${cx}" y="${cy + 11*scale}" text-anchor="middle" font-size="${36*scale}" font-family="Arial" font-weight="900" fill="${c}">${escapeHtml(ini)}</text>`;
      }
    }
  };

  const printColor = (c: string) =>
    exportTheme === 'white' ? (PRINT_WHITE_COLOR_FIX[c] || c) : c;

  // Sin label junto al icono: en un plano tecnico el simbolo se decodifica en la
  // leyenda, no con captions flotantes que ensucian el layout.
  const symbolPrintMarkup = (el: Element) => {
    const color = escapeHtml(printColor(el.color || '#111111'));
    const cx = el.x + el.w / 2;
    const cy = el.y + el.h / 2;
    const scale = Math.max(0.55, Math.min(el.w, el.h) / 170);
    return `
      <g>
        ${symbolIconMarkup(el.symbolKey || 'symbol', color, cx, cy, scale, el.label)}
      </g>`;
  };

  const buildPrintableMapSvg = () => {
    const pal = RD_PALETTE[exportTheme];
    const visible = elements.filter(el => el.visible);
    const mapContent = visible.map(el => {
      const label = escapeHtml(el.label.toUpperCase());
      if (el.type === 'symbol') return symbolPrintMarkup(el);
      const rectColor = escapeHtml(printColor(el.color));
      // Cajas grandes (stands/zonas) llevan el nombre arriba, como en un plano
      // real: deja el interior libre para mobiliario e iconos.
      const labelY = el.h >= 300 ? el.y + 70 : el.y + el.h / 2;
      return `
        <g>
          <rect x="${el.x}" y="${el.y}" width="${el.w}" height="${el.h}" rx="16" fill="${rectColor}" fill-opacity="0.48" stroke="${rectColor}" stroke-width="8"/>
          <text x="${el.x + el.w / 2}" y="${labelY}" text-anchor="middle" dominant-baseline="middle" font-size="${rectLabelFont(el.label, el.w)}" font-family="Arial, sans-serif" font-weight="900" fill="${pal.text}">${label}</text>
        </g>`;
    }).join('\n');

    const printCanvasWidth = 2970;
    const printCanvasHeight = 2100;
    const legendWidth = 900;
    const legendHeight = legendHeightFor(visibleLegendSymbols.length);
    // Mismo clamp que el drag en pantalla (PLANO_FRAME); antes el print clampaba al
    // canvas completo y la leyenda podia quedar fuera del marco del plano.
    const { x: legendX, y: legendY } = clampLegendPos(legendPos.x, legendPos.y);
    const legendRows = visibleLegendSymbols.map((el, i) => {
      const col = i % 2;
      const row = Math.floor(i / 2);
      const x = legendX + 48 + col * 410;
      const y = legendY + 160 + row * 100;
      const color = escapeHtml(printColor(el.color || '#111111'));
      // La leyenda describe TIPOS de simbolo: usa el nombre canonico del catalogo
      // (los elementos pueden venir numerados, ej "Testeo 1").
      const legendLabel = specDe(el.symbolKey || '')?.label || el.label;
      return `
        <g>
          ${symbolIconMarkup(el.symbolKey || 'symbol', color, x + 40, y + 40, 0.5, legendLabel)}
          <text x="${x + 104}" y="${y + 52}" font-size="32" font-family="Arial, sans-serif" font-weight="800" fill="${pal.text}">${escapeHtml(legendLabel.toUpperCase().slice(0, 16))}</text>
        </g>`;
    }).join('\n');

    return `
      <svg viewBox="0 0 ${printCanvasWidth} ${printCanvasHeight}" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">
        <rect width="${printCanvasWidth}" height="${printCanvasHeight}" fill="${pal.mapBg}"/>
        <rect x="${PLANO_FRAME.x}" y="${PLANO_FRAME.y}" width="${PLANO_FRAME.w}" height="${PLANO_FRAME.h}" fill="none" stroke="${pal.muted}" stroke-width="5" stroke-dasharray="30 20" rx="20"/>
        ${mapContent}
        <g transform="translate(0,0)">
          <rect x="${legendX}" y="${legendY}" width="${legendWidth}" height="${legendHeight}" rx="30" fill="${pal.panel}" fill-opacity="0.96" stroke="${pal.borde}" stroke-width="5"/>
          <text x="${legendX + 450}" y="${legendY + 90}" text-anchor="middle" font-size="46" font-family="Arial, sans-serif" font-weight="900" fill="${pal.accent}">SIMBOLOGÍA</text>
          ${legendRows}
        </g>
        <text x="100" y="2075" font-size="34" font-family="Arial, sans-serif" font-weight="900" fill="${pal.text}">${escapeHtml(`${eventName.toUpperCase()} · ${eventVenue.toUpperCase()} · ${eventDate}`)}</text>
        <text x="2870" y="2075" text-anchor="end" font-size="24" font-family="Arial, sans-serif" fill="${pal.muted}">Reduciendo Daño Chile · Rider Operativo</text>
      </svg>`;
  };

  const printRider = () => {
    const pal = RD_PALETTE[exportTheme];
    const checklistHtml = CHECKLIST_SECTIONS.map(section => `
      <section class="box">
        <h3>${escapeHtml(section.title)}</h3>
        <ul>
          ${section.items.map(item => `<li><span class="check">${checkedItems.includes(item.text) ? 'X' : ''}</span>${escapeHtml(item.text)}</li>`).join('')}
        </ul>
      </section>`).join('');

    // Cotizacion del pack seleccionado unicamente (precio plano, sin fan-out de presets).
    const pack = calcCostos(preset);
    const inclusionesHtml = `<ul>${pack.inclusiones.map(i => `<li>${escapeHtml(i)}</li>`).join('')}</ul>`;
    const proporcionesHtml = pack.proporciones ? `
      <table class="cot">
        <thead><tr><th>Distribución del pack</th><th class="num">%</th><th class="num">Monto</th></tr></thead>
        <tbody>
          ${pack.proporciones.map(p => `<tr><td>${escapeHtml(p.label)}</td><td class="num">${p.pct}%</td><td class="num">${formatCLP(proporcionMonto(pack, p))}</td></tr>`).join('')}
        </tbody>
      </table>` : '';
    const cotizacionHtml = `
      <table class="cot">
        <tbody>
          <tr class="tot"><td>Precio del pack</td><td class="num">${formatCLP(pack.precio)} / día</td></tr>
          <tr><td>Equipo en terreno</td><td class="num">${pack.voluntarios} voluntarios/as</td></tr>
          <tr><td>Superficie / stands</td><td class="num">${pack.m2} m² · ${pack.stands} stand(s)</td></tr>
        </tbody>
      </table>
      <h3 style="margin-top:8px">Inclusiones</h3>
      ${inclusionesHtml}
      ${proporcionesHtml}
      <p class="note">Valores referenciales en CLP; ajustables por evento. Pack: <strong>${escapeHtml(pack.label)}</strong>.</p>`;

    const html = `<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<title>Rider Plano PDF</title>
<style>
  @page { size: A4; margin: 0; }
  * { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  body { margin: 0; background: ${pal.bg}; color: ${pal.text}; font-family: Arial, Helvetica, sans-serif; font-size: 13px; }
  .page { width: 210mm; min-height: 297mm; padding: 13mm 18mm; page-break-after: always; break-after: page; overflow: hidden; background: ${pal.bg}; display: flex; flex-direction: column; gap: 12px; }
  .page-body { flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; justify-content: center; gap: 12px; }
  .page:last-child { page-break-after: auto; break-after: auto; }
  header { border-bottom: 4px solid ${pal.accent}; padding-bottom: 12px; display: flex; justify-content: space-between; align-items: end; }
  .brand { display: flex; align-items: center; gap: 12px; }
  .logo svg { height: 84px; width: auto; display: block; }
  .page-header-mini { border-bottom: 4px solid ${pal.accent}; padding-bottom: 12px; display: flex; align-items: center; gap: 12px; }
  h1 { font-size: 34px; margin: 0; font-weight: 900; font-style: italic; letter-spacing: -1px; white-space: nowrap; }
  h2 { font-size: 24px; margin: 0 0 10px; font-weight: 900; text-transform: uppercase; color: ${pal.accent}; }
  h3 { font-size: 13px; margin: 0 0 6px; font-weight: 900; text-transform: uppercase; border-bottom: 1px solid ${pal.borde}; padding-bottom: 4px; }
  p { margin: 0 0 12px; line-height: 1.65; }
  .muted { color: ${pal.muted}; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .box { border: 1px solid ${pal.borde}; padding: 16px; border-radius: 8px; break-inside: avoid; }
  ul { list-style: none; padding: 0; margin: 0; display: grid; gap: 8px; }
  li { display: flex; gap: 9px; align-items: center; }
  .check { width: 17px; height: 17px; border: 1px solid ${pal.accent}; display: inline-flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 900; flex: 0 0 auto; color: ${pal.accent}; }
  .map-frame { border: 1px solid ${pal.borde}; padding: 6mm; display: flex; justify-content: center; background: ${pal.mapBg}; }
  .map-frame svg { width: 100%; height: auto; display: block; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { border: 1px solid ${pal.borde}; padding: 12px; text-align: left; }
  th { background: ${pal.th}; font-weight: 900; }
  td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
  .cot td.cur, .cot th.cur { background: ${pal.th}; color: ${pal.accent}; font-weight: 900; }
  .cot tr.tot td { font-weight: 900; color: ${pal.total}; font-size: 13px; }
  .note { font-size: 11px; color: ${pal.muted}; margin-top: 6px; }
  /* Los textos de antecedentes son editables por el usuario; sin tope, un texto largo
     empuja el checklist fuera del A4 y overflow:hidden lo recorta en silencio. */
  .clamp { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 6; overflow: hidden; }
  /* Datos operativos del evento: lo primero que busca produccion en un rider. */
  .info-strip { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
  .info-cell { border: 1px solid ${pal.borde}; border-left: 4px solid ${pal.accent}; border-radius: 6px; padding: 10px 12px; }
  .info-cell span { display: block; font-size: 9px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.14em; color: ${pal.muted}; margin-bottom: 4px; }
  .info-cell strong { font-size: 14px; }
  /* Los estilos .contacts/.fill se retiraron junto con el bloque de contactos. */
</style>
</head>
<body>
  <main class="page">
    <header>
      <div class="brand"><span class="logo">${RD_LOGO[exportTheme]}</span><div><h1>RIDER TÉCNICO RD</h1><p class="muted">Documentación de Intervención en Terreno — ONG Reduciendo Daño</p></div></div>
      <div><strong>ORGANIZACIÓN RD</strong><br/><span class="muted">Servicio de Testeo y Reducción de Daño v2026</span></div>
    </header>
    <div class="page-body">
      <div class="info-strip">
        <div class="info-cell"><span>Evento</span><strong>${escapeHtml(eventName || '—')}</strong></div>
        <div class="info-cell"><span>Ubicación</span><strong>${escapeHtml(eventVenue || '—')}</strong></div>
        <div class="info-cell"><span>Fecha</span><strong>${escapeHtml(eventDate || '—')}</strong></div>
        <div class="info-cell"><span>Pack contratado</span><strong>${escapeHtml(pack.label)}</strong></div>
      </div>
      <section>
        <h2>1. Antecedentes</h2>
        <p class="clamp"><strong>Quiénes Somos:</strong> ${escapeHtml(orgTexts.who)}</p>
        <p class="clamp"><strong>Objetivo del Servicio:</strong> ${escapeHtml(orgTexts.goal)}</p>
      </section>
      <section>
        <h2>2. Requerimientos Operativos</h2>
        <p class="note" style="margin-bottom:10px">Los ítems marcados con <strong>X</strong> son requeridos a producción para este evento; los demás no aplican o los cubre RD.</p>
        <div class="grid">${checklistHtml}</div>
      </section>
      <!-- Sin bloque de contactos a proposito (2026-07-25, pedido del area de
           eventos RD): el rider se presenta a productoras y no debe pedir ni
           asociar nombres/telefonos de nadie. La coordinacion del dia se
           acuerda por fuera del documento. No reponer sin orden expresa. -->
    </div>
  </main>
  <main class="page">
    <div class="page-header-mini"><span class="logo">${RD_LOGO[exportTheme]}</span><h1 style="font-size:22px">RIDER TÉCNICO RD</h1></div>
    <div class="page-body">
      <h2>3. Esquema de Distribución del Stand</h2>
      <div class="map-frame">${buildPrintableMapSvg()}</div>
      <p class="note">Distribución a proporción real (1 m = 200 px de lienzo en los presets); medidas indicadas en cada elemento. Frente público abajo, acceso de servicio atrás. Superficie del pack: ${pack.m2} m² (${pack.stands} stand(s)). Ubicación sugerida en el recinto: cerca del punto médico/bienestar, fuera de la presión sonora del escenario principal, con acceso a ruta de servicio.</p>
    </div>
  </main>
  <main class="page">
    <div class="page-header-mini"><span class="logo">${RD_LOGO[exportTheme]}</span><h1 style="font-size:22px">RIDER TÉCNICO RD</h1></div>
    <div class="page-body">
      <h2>4. Cotización — ${escapeHtml(pack.label)}</h2>
      ${cotizacionHtml}
    </div>
  </main>
</body>
</html>`;

    const iframe = document.createElement('iframe');
    iframe.style.position = 'fixed';
    iframe.style.right = '0';
    iframe.style.bottom = '0';
    iframe.style.width = '0';
    iframe.style.height = '0';
    iframe.style.border = '0';
    iframe.setAttribute('title', 'Rider PDF print frame');
    document.body.appendChild(iframe);
    const doc = iframe.contentWindow?.document;
    if (!doc) return;
    doc.open();
    doc.write(html);
    doc.close();
    setTimeout(() => {
      iframe.contentWindow?.focus();
      iframe.contentWindow?.print();
      setTimeout(() => iframe.remove(), 3000);
    }, 350);
  };

  const syncElementsFromChecked = (items: string[], baseElements = elements) => {
    const wanted = items.map(item => REQUIREMENT_SYMBOL_MAP[item]).filter(Boolean);
    const requirementKeys = new Set(Object.values(REQUIREMENT_SYMBOL_MAP));
    let next = baseElements
      .filter(el => {
        if (!(el.id || '').startsWith('req-')) return true;
        return Boolean(el.symbolKey && wanted.includes(el.symbolKey));
      })
      .map(el => {
        if (!el.symbolKey || !requirementKeys.has(el.symbolKey)) return el;
        if (wanted.includes(el.symbolKey)) return { ...el, visible: true };
        return { ...el, visible: false };
      });
    wanted.forEach(key => {
      const hasVisibleSymbol = next.some(el => el.symbolKey === key && el.visible);
      if (!hasVisibleSymbol) next.push({ ...makeSymbolElement(key, 'req'), id: `req-${key}` });
    });
    return next;
  };

  const syncChecklistFromElements = (nextElements: Element[]) => {
    const visibleRequirementKeys = new Set(
      nextElements
        .filter(el => el.visible && el.symbolKey && (el.type === 'symbol' || (el.id || '').startsWith('req-')))
        .map(el => el.symbolKey as string)
    );
    const mapEntries = Object.entries(REQUIREMENT_SYMBOL_MAP);
    setCheckedItems(prev => {
      const manual = prev.filter(item => !REQUIREMENT_SYMBOL_MAP[item]);
      const fromMap = mapEntries
        .filter(([, key]) => visibleRequirementKeys.has(key))
        .map(([item]) => item);
      return Array.from(new Set([...manual, ...fromMap]));
    });
  };

  const toggleCheck = (item: string) => {
    const nextChecked = checkedItems.includes(item)
      ? checkedItems.filter(x => x !== item)
      : [...checkedItems, item];
    setCheckedItems(nextChecked);
    setElements(prev => syncElementsFromChecked(nextChecked, prev));
  };

  const handleGoToPlano = () => {
    setElements(prev => syncElementsFromChecked(checkedItems, prev));
    setPage('map');
  };

  const checkAll = () => {
    const all = CHECKLIST_SECTIONS.flatMap(s => s.items).map(i => i.text);
    const nextChecked = checkedItems.length === all.length ? [] : all;
    setCheckedItems(nextChecked);
    setElements(prev => syncElementsFromChecked(nextChecked, prev));
  };

  // ─── Export Checklist as Markdown ───
  const exportChecklistMarkdown = () => {
    let md = `# RIDER TÉCNICO RD - CHECKLIST\n\n`;
    md += `**Evento:** ${eventName}\n`;
    md += `**Fecha:** ${eventDate}\n`;
    md += `**Lugar:** ${eventVenue}\n`;
    md += `**Pack Comercial:** ${PACKS[preset].label} (${formatCLP(PACKS[preset].precio)})\n\n`;
    md += `## 1. Antecedentes de la Organización\n\n`;
    md += `**Quiénes somos:** ${orgTexts.who}\n\n`;
    md += `**Objetivo del servicio:** ${orgTexts.goal}\n\n`;
    md += `## 2. Requerimientos Operativos\n\n`;
    CHECKLIST_SECTIONS.forEach(sec => {
      md += `### ${sec.title}\n`;
      sec.items.forEach(item => {
        const isChecked = checkedItems.includes(item.text) ? '[x]' : '[ ]';
        md += `- ${isChecked} ${item.text}\n`;
      });
      md += `\n`;
    });
    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `checklist_rider_${eventName.replace(/\s+/g, '_').toLowerCase()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // ─── Export SVG ───
  const exportSVG = () => {
    // Mismo SVG tematizado del PDF; antes serializaba el DOM de pantalla (siempre
    // dark, con cursores y colores de UI) ignorando el tema dark/white elegido.
    const svgData = buildPrintableMapSvg().trim();
    const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `plano_${eventName.replace(/\s+/g, '_').toLowerCase()}.svg`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // ── el layout como archivo, para que viaje ──
  // La encargada de eventos arma el plano, exporta el SVG y el rider en PDF,
  // pero su TRABAJO -- donde puso cada cosa -- se perdia al cerrar la pestana.
  // Con esto lo manda como archivo, el director lo asocia a la base de datos y
  // se lo devuelve. Es el unico formato que viaja en las dos direcciones.
  const PRESET_FORMATO = 1;

  const exportarPreset = () => {
    const preset_layout = {
      formato: PRESET_FORMATO,
      guardado: new Date().toISOString(),
      evento: {
        nombre: eventName,
        fecha: eventDate,
        lugar: eventVenue,
        eventKey: selectedEventKey || null,
      },
      pack: preset,
      tema: exportTheme,
      leyenda: { visible: showLegend, x: legendPos.x, y: legendPos.y },
      grilla: showGrid,
      // Los simbolos propios viajan con el layout: sin ellos, el plano que
      // abre el otro lado tendria huecos donde ella puso sus iconos.
      simbolos_propios: simbolosPropiosSpec(),
      elementos: elements,
    };
    const blob = new Blob([JSON.stringify(preset_layout, null, 2)],
      { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `preset_${(eventName || 'plano').replace(/\s+/g, '_').toLowerCase()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const importarPreset = async (file: File) => {
    try {
      const d = JSON.parse(await file.text());
      if (!Array.isArray(d?.elementos)) {
        setBackendStatus('Ese archivo no es un preset de plano.');
        return;
      }
      if (d.formato !== PRESET_FORMATO) {
        // Se carga igual: negarse por un numero de version dejaria a la
        // encargada sin poder abrir su propio trabajo. Se avisa y se sigue.
        setBackendStatus(`Preset de otra version (${d.formato ?? '?'}); se cargo igual.`);
      }
      if (Array.isArray(d.simbolos_propios) && d.simbolos_propios.length) {
        registrarSimbolosPropios(d.simbolos_propios);
        setRefrescoSimbolos(n => n + 1);
      }
      setElements(d.elementos as Element[]);
      if (d.evento?.nombre) setEventName(d.evento.nombre);
      if (d.evento?.fecha) setEventDate(d.evento.fecha);
      if (d.evento?.lugar) setEventVenue(d.evento.lugar);
      if (typeof d.evento?.eventKey === 'string') setSelectedEventKey(d.evento.eventKey);
      if (d.pack) setPreset(d.pack as PackId);
      if (d.tema) setExportTheme(d.tema as ExportTheme);
      if (d.leyenda) {
        setShowLegend(!!d.leyenda.visible);
        if (typeof d.leyenda.x === 'number') setLegendPos({ x: d.leyenda.x, y: d.leyenda.y });
      }
      if (typeof d.grilla === 'boolean') setShowGrid(d.grilla);
      setSelectedId(null);
      setBackendStatus(`Preset cargado: ${d.elementos.length} elementos.`);
    } catch {
      setBackendStatus('No se pudo leer el preset (archivo dañado o incompleto).');
    }
  };

  const selectVjEvent = (eventKey: string) => {
    setSelectedEventKey(eventKey);
    if (!eventKey) {
      setBackendStatus('Edicion manual del evento; no se desvinculo ningun dato del catalogo.');
      return;
    }
    const event = vjEvents.find(candidate => candidate.eventKey === eventKey);
    if (!event) return;
    if (event.name) setEventName(event.name);
    if (event.dateIso) setEventDate(event.dateIso);
    if (event.venueName) setEventVenue(event.venueName);
    const lineup = event.lineup?.length ? event.lineup.join(', ') : 'sin lineup registrado';
    setBackendStatus(
      'Contexto VJ cargado: ' + (event.producerName || 'productora no indicada') +
      ' - DJs: ' + lineup + '. Pack, duracion y asistentes siguen sin inferirse.'
    );
  };

  const loadFromBackend = async (presetId: PackId = preset) => {
    if (window.location.protocol === 'file:') {
      applyPreset(presetId);
      setBackendStatus(`Modo demo con pack ${presetId}. Abre via py -m flujo app para usar APIs.`);
      return;
    }
    setBackendStatus('Consultando motor Python...');
    try {
      const response = await fetch('/api/plano/render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          evento: {
            nombre: eventName || 'Evento',
            fecha: eventDate,
            pack: presetId,
            ubicacion: eventVenue || 'Por definir',
            eventKey: selectedEventKey || undefined
          },
        }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      const zones = Array.isArray(data?.layout?.zones) ? data.layout.zones : [];
      // || pisaba coordenadas 0 legitimas (0 es falsy): 0 -> 300. Solo caer al
      // default cuando el valor no es numerico; ancho/alto 0 tampoco sirven.
      const numOr = (v: unknown, fallback: number) => (Number.isFinite(Number(v)) ? Number(v) * 4 : fallback);
      const mapped: Element[] = zones.map((zone: any, index: number) => {
        const zoneType = zone.type === 'stand' ? 'informativo' : zone.type === 'descanso' ? 'descanso' : zone.type === 'testeo' ? 'testeo' : zone.type === 'mesa' ? 'informativo' : 'circulacion';
        return {
          id: `api-${index}-${zoneType}`,
          type: 'rect',
          x: numOr(zone.x, 300),
          y: numOr(zone.y, 300),
          w: numOr(zone.w, 560) || 560,
          h: numOr(zone.h, 300) || 300,
          label: String(zone.label || ZONE_LABELS[zoneType] || zoneType),
          color: ZONE_COLORS[zoneType] || '#555',
          visible: true,
        };
      });
      if (mapped.length) {
        setElements(mapped);
        setSelectedId(mapped[0].id);
      }
      setBackendStatus(`Motor Python OK con pack ${presetId}: ${mapped.length} elementos cargados.`);
    } catch (error) {
      setBackendStatus(`No se pudo usar /api/plano/render: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  const totalChecks = CHECKLIST_SECTIONS.flatMap(s => s.items).length;
  const completedChecks = checkedItems.length;
  const visibleLegendSymbols = elements
    .filter(el => el.visible && el.type === 'symbol' && el.symbolKey)
    .reduce<Element[]>((acc, el) => {
      if (!acc.some(item => item.symbolKey === el.symbolKey)) acc.push(el);
      return acc;
    }, []);

  const NAV_TABS: { key: Page; label: string }[] = [
    { key: 'req', label: '☑ Checklist' },
    { key: 'map', label: '🗺 Mapa' },
    { key: 'config', label: '⚙ Config' },
  ];

  return (
    <div className="space-y-6">
      {/* Screen View (Interactive App Tool) */}
      <div className="flex items-center justify-between print:hidden">
        <div>
          <h3 className="text-2xl font-bold flex items-center gap-2">
            Rider RD · Herramienta de Plano
            {/* Antes habia un badge "v0.51.0" cableado a mano: quedo desactualizado
                y ademas este componente se distribuye standalone (sin backend que
                informe la version real). Un numero que nadie actualiza miente. */}
          </h3>
          <p className="text-zinc-400 text-sm mt-1">
            Documento operativo para intervención en terreno — Reduciendo Daño Chile
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setPage('req')}
            className={cn(
              "px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 border",
              page === 'req' ? "bg-white text-black border-white" : "bg-zinc-900 border-zinc-800 text-zinc-300 hover:bg-zinc-800"
            )}
          >
            <FileText className="w-4 h-4" />
            1. Requerimientos
          </button>
          <button
            onClick={() => setPage('map')}
            className={cn(
              "px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 border",
              page === 'map' ? "bg-white text-black border-white" : "bg-zinc-900 border-zinc-800 text-zinc-300 hover:bg-zinc-800"
            )}
          >
            <Layers className="w-4 h-4" />
            2. Distribución
          </button>
          <button
            onClick={() => setPage('config')}
            className={cn(
              "px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 border",
              page === 'config' ? "bg-white text-black border-white" : "bg-zinc-900 border-zinc-800 text-zinc-300 hover:bg-zinc-800"
            )}
          >
            <Settings className="w-4 h-4" />
            Ajustes ONG
          </button>
          <button
            onClick={() => loadFromBackend()}
            className="px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 bg-emerald-950/40 border border-emerald-800/70 text-emerald-200 hover:bg-emerald-900/50"
          >
            <RefreshCw className="h-4 w-4" />
            Motor Python
          </button>
          <button
            onClick={() => setExportTheme(t => t === 'dark' ? 'white' : 'dark')}
            title="Tema del PDF exportado (RD dark / white)"
            className="flex items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-xs font-bold text-zinc-300 hover:bg-zinc-800 transition-colors"
          >
            <Moon className="h-4 w-4" /> Tema: {exportTheme === 'dark' ? 'Dark' : 'White'}
          </button>
          <button
            onClick={printRider}
            className="flex items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-900 px-4 py-2 text-xs font-bold text-zinc-300 hover:bg-zinc-800 transition-colors"
          >
            <Printer className="h-4 w-4" /> Imprimir Rider
          </button>
        </div>
      </div>
      {backendStatus && (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 px-4 py-2 text-xs text-zinc-400 print:hidden">
          {backendStatus}
        </div>
      )}

      {/* Pack selector */}
      <div className="flex gap-2 flex-wrap bg-zinc-900/20 border border-zinc-800/80 p-3 rounded-xl items-center print:hidden">
        <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 mr-2">Packs de Servicio:</span>
        {ALL_PACKS.map(p => (
          <button
            key={p}
            onClick={() => applyPreset(p)}
            className={cn(
              'rounded-lg border px-4 py-2 text-xs font-bold uppercase tracking-widest transition-colors text-left',
              preset === p
                ? 'border-emerald-500 bg-emerald-950/60 text-emerald-300'
                : 'border-zinc-700 bg-zinc-900 text-zinc-400 hover:border-zinc-600 hover:text-zinc-200'
            )}
          >
            <span className="block">{PACKS[p].label}</span>
            <span className="block text-[9px] font-normal normal-case tracking-normal opacity-70">{formatCLP(PACKS[p].precio)} · {PACKS[p].desc}</span>
          </button>
        ))}
        <button
          onClick={() => applyPreset(preset)}
          className="ml-auto flex items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          <RotateCcw className="h-3.5 w-3.5" /> Reset
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-zinc-800 pb-0 print:hidden">
        {NAV_TABS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setPage(key)}
            className={cn(
              'px-4 py-2 text-sm font-medium rounded-t-lg transition-colors -mb-px border-b-2 flex items-center gap-2',
              page === key
                ? 'border-emerald-500 text-emerald-400 bg-zinc-900/50'
                : 'border-transparent text-zinc-500 hover:text-zinc-300'
            )}
          >
            {key === 'req' && <FileText className="w-4 h-4" />}
            {key === 'map' && <Layers className="w-4 h-4" />}
            {key === 'config' && <Settings className="w-4 h-4" />}
            {label}
          </button>
        ))}
      </div>

      {/* ── Checklist tab (17 items) ── */}
      {page === 'req' && (
        <div className="space-y-4 print:hidden">
          {/* Antecedentes Card */}
          <div className="p-6 rounded-xl border border-zinc-800 bg-zinc-900/30">
            <h3 className="text-sm font-black uppercase text-zinc-400 tracking-wider mb-4">Antecedentes del Evento</h3>
            <div className="mb-4 rounded-lg border border-zinc-800 bg-black/20 p-3">
              <label className="text-[10px] uppercase tracking-widest text-zinc-500 block mb-1 font-bold">
                Evento existente en el catalogo VJ
              </label>
              <select
                value={selectedEventKey}
                onChange={e => selectVjEvent(e.target.value)}
                disabled={!vjEvents.length}
                className="w-full bg-black/40 border border-zinc-800 rounded px-3 py-2 text-sm focus:outline-none focus:border-zinc-600 disabled:opacity-60"
              >
                <option value="">Edicion manual (sin vincular)</option>
                {vjEvents.map(event => (
                  <option key={event.eventKey} value={event.eventKey}>
                    {(event.dateIso || event.dateRaw || 'sin fecha') + ' - ' + (event.name || event.eventKey)}
                  </option>
                ))}
              </select>
              <p className="text-[11px] text-zinc-500 mt-2">{eventCatalogStatus}</p>
              {selectedVjEvent && (
                <p className="text-[11px] text-emerald-300/80 mt-1">
                  Productora: {selectedVjEvent.producerName || 'no indicada'} - DJs:{' '}
                  {selectedVjEvent.lineup?.length ? selectedVjEvent.lineup.join(', ') : 'sin lineup registrado'}
                  {selectedVjEvent.venueName ? ' - Venue: ' + selectedVjEvent.venueName : ''}
                </p>
              )}
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="text-[10px] uppercase tracking-widest text-zinc-500 block mb-1 font-bold">Nombre del Evento</label>
                <input
                  value={eventName}
                  onChange={e => setEventName(e.target.value)}
                  className="w-full bg-black/40 border border-zinc-800 rounded px-3 py-2 text-sm focus:outline-none focus:border-zinc-600"
                />
              </div>
              <div>
                <label className="text-[10px] uppercase tracking-widest text-zinc-500 block mb-1 font-bold">Fecha del Evento</label>
                <input
                  type="date"
                  value={eventDate}
                  onChange={e => setEventDate(e.target.value)}
                  className="w-full bg-black/40 border border-zinc-800 rounded px-3 py-2 text-sm focus:outline-none focus:border-zinc-600"
                />
              </div>
              <div>
                <label className="text-[10px] uppercase tracking-widest text-zinc-500 block mb-1 font-bold">Ubicación / Local</label>
                <input
                  value={eventVenue}
                  onChange={e => setEventVenue(e.target.value)}
                  className="w-full bg-black/40 border border-zinc-800 rounded px-3 py-2 text-sm focus:outline-none focus:border-zinc-600"
                />
              </div>
            </div>
          </div>

          {/* Modalidades Cards */}
          <div className="grid grid-cols-3 gap-4">
            <ModalidadCard
              icon={<Heart className="w-5 h-5 text-emerald-400" />}
              title="Stand Informativo"
              description="Personas capacitadas para orientar y entregar consejos preventivos. Material educativo, protectores auditivos, suplementos pre/post."
              color={ZONE_COLORS.informativo}
            />
            <ModalidadCard
              icon={<AlertTriangle className="w-5 h-5 text-yellow-500" />}
              title="Stand de Testeo"
              description="Análisis colorimétricos de sustancias gratuito. Equipo liderado por analistas químicos y químicos farmacéuticos."
              color={ZONE_COLORS.testeo}
            />
            <ModalidadCard
              icon={<Coffee className="w-5 h-5 text-purple-400" />}
              title="Contención"
              description="Rondas preventivas en terreno. Contención psicológica y atención en situaciones de crisis o desregulación emocional."
              color={ZONE_COLORS.contencion}
            />
          </div>

          <div className="flex items-center justify-between">
            <h2 className="font-bold text-sm text-zinc-400 uppercase tracking-widest">Requerimientos Operativos (17 items)</h2>
            <button
              onClick={checkAll}
              className="text-xs text-zinc-500 hover:text-zinc-200 transition-colors"
            >
              {checkedItems.length === CHECKLIST_SECTIONS.flatMap(s => s.items).length ? 'Desmarcar todo' : 'Marcar todo'}
            </button>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            {CHECKLIST_SECTIONS.map(s => (
              <div key={s.title} className="rounded-2xl border border-zinc-800 bg-zinc-900/45 p-5 group hover:border-emerald-500/20 transition-all">
                <div className="flex items-center gap-2 mb-4 border-b border-zinc-800/80 pb-1">
                  <span className="text-emerald-500">{renderRequirementIcon(s.iconName, "w-4 h-4")}</span>
                  <h3 className="text-xs font-bold uppercase tracking-widest text-zinc-400">{s.title}</h3>
                </div>
                <ul className="space-y-2">
                  {s.items.map(item => (
                    <li key={item.text}>
                      <label className="flex items-center gap-3 cursor-pointer group/item">
                        <input
                          type="checkbox"
                          checked={checkedItems.includes(item.text)}
                          onChange={() => toggleCheck(item.text)}
                          className="hidden"
                        />
                        <span
                          className={cn(
                            'h-4 w-4 shrink-0 rounded border-2 flex items-center justify-center transition-colors',
                            checkedItems.includes(item.text)
                              ? 'border-emerald-500 bg-emerald-500'
                              : 'border-zinc-600 group-hover/item:border-zinc-400'
                          )}
                        >
                          {checkedItems.includes(item.text) && (
                            <svg className="h-2.5 w-2.5 text-black" viewBox="0 0 10 10" fill="none">
                              <path d="M2 5l3 3 3-5" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                          )}
                        </span>
                        <div className="flex items-center gap-2 overflow-hidden flex-1">
                          {renderRequirementIcon(item.icon, "w-3.5 h-3.5 text-zinc-500 group-hover/item:text-zinc-300")}
                          <span className={cn('text-xs transition-colors truncate', checkedItems.includes(item.text) ? 'text-zinc-500 line-through' : 'text-zinc-300')}>
                            {item.text}
                          </span>
                        </div>
                      </label>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between rounded-xl border border-zinc-800/60 bg-zinc-900/20 px-6 py-4">
            <span className="text-xs text-zinc-500 uppercase tracking-widest font-mono">
              {completedChecks} / {totalChecks} Requerimientos completados
            </span>
            <button
              onClick={exportChecklistMarkdown}
              className="flex items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-900 px-3.5 py-2 text-xs font-bold text-zinc-300 hover:bg-zinc-800 transition-all active:scale-[0.98]"
            >
              <Download className="w-3.5 h-3.5" /> Exportar Checklist (.md)
            </button>
          </div>

          <button
            onClick={handleGoToPlano}
            className="w-full py-5 bg-emerald-500 hover:bg-emerald-400 text-black font-black rounded-3xl shadow-xl shadow-emerald-500/10 transition-transform active:scale-[0.98] flex items-center justify-center gap-3 text-base"
          >
            Ir al Plano de Distribución (Sincronizar Selección)
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* ── Map tab ── */}
      {page === 'map' && (
        <div className="grid grid-cols-4 gap-6 print:hidden">
          {/* SVG Canvas and Controls */}
          <div className="col-span-3 space-y-4">
            <div className="flex items-center justify-between px-1">
              <div className="flex items-center gap-1.5">
                <button onClick={() => setZoom(z => Math.min(z + 0.15, 2.5))} className="p-2 bg-zinc-900 border border-zinc-800 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-white" title="Zoom +"><Plus className="w-3.5 h-3.5"/></button>
                <button onClick={() => setZoom(z => Math.max(z - 0.15, 0.4))} className="p-2 bg-zinc-900 border border-zinc-800 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-white" title="Zoom -"><Trash2 className="w-3.5 h-3.5"/></button>
                <button onClick={() => setZoom(1)} className="p-2 bg-zinc-900 border border-zinc-800 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-white" title="Reset Zoom"><RotateCcw className="w-3.5 h-3.5"/></button>
                <div className="w-px h-5 bg-zinc-800 mx-1" />
                <button onClick={() => setShowGrid(!showGrid)} className={cn("p-2 border rounded-lg transition-colors text-xs font-bold", showGrid ? "bg-zinc-800 border-zinc-700 text-white" : "bg-zinc-900 border-zinc-800 text-zinc-500")}>Grilla</button>
                <button onClick={() => setShowLegend(!showLegend)} className={cn("p-2 border rounded-lg transition-colors text-xs font-bold", showLegend ? "bg-zinc-800 border-zinc-700 text-white" : "bg-zinc-900 border-zinc-800 text-zinc-500")}>Leyenda</button>
                <button onClick={autoArrangePlano} className="p-2 border border-emerald-700/60 bg-emerald-950/40 rounded-lg transition-colors text-xs font-bold text-emerald-300 hover:bg-emerald-900/50">Auto ordenar</button>
                <button onClick={orderLayersByPriority} className="p-2 border border-sky-700/60 bg-sky-950/40 rounded-lg transition-colors text-xs font-bold text-sky-300 hover:bg-sky-900/50">Orden capas</button>
                <button onClick={resetLegendPosition} className="p-2 border border-zinc-800 bg-zinc-900 rounded-lg transition-colors text-xs font-bold text-zinc-500 hover:text-zinc-300">Reset leyenda</button>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono text-zinc-600 mr-2">{Math.round(zoom * 100)}%</span>
                <button onClick={exportSVG} className="flex items-center gap-1.5 p-2 bg-zinc-900 border border-zinc-800 rounded-lg text-xs font-bold hover:bg-zinc-800 text-zinc-400 hover:text-white"><Download className="w-3.5 h-3.5"/> SVG</button>
                {/* El layout como archivo: el SVG y el PDF son el resultado,
                    esto es el TRABAJO, y es lo unico que se puede volver a
                    abrir y seguir editando. */}
                <button onClick={exportarPreset} title="Guardar este plano como archivo, para mandarlo o seguirlo despues"
                  className="flex items-center gap-1.5 p-2 bg-zinc-900 border border-zinc-800 rounded-lg text-xs font-bold hover:bg-zinc-800 text-zinc-400 hover:text-white"><Save className="w-3.5 h-3.5"/> Guardar preset</button>
                <label title="Abrir un plano guardado"
                  className="flex items-center gap-1.5 p-2 bg-zinc-900 border border-zinc-800 rounded-lg text-xs font-bold hover:bg-zinc-800 text-zinc-400 hover:text-white cursor-pointer">
                  <Upload className="w-3.5 h-3.5"/> Abrir preset
                  <input type="file" accept=".json,application/json" className="hidden"
                    onChange={e => { const f = e.target.files?.[0]; if (f) importarPreset(f); e.target.value = ''; }} />
                </label>
              </div>
            </div>

            {/* SVG Canvas wrapper */}
            <div className="rounded-2xl border border-zinc-800 bg-zinc-950 overflow-hidden relative" style={{ height: "650px" }}>
              <div className="w-full h-full overflow-auto flex items-center justify-center p-4">
                <div className="relative bg-[#09090b] border border-zinc-800 shadow-2xl transition-all" style={{ width: 800, height: 565, transform: `scale(${zoom})`, transformOrigin: "center" }}>
                  <svg
                    ref={svgRef}
                    viewBox="0 0 2970 2100"
                    className="w-full h-full"
                    onClick={() => setSelectedId(null)}
                  >
                    {/* Grid pattern */}
                    {showGrid && (
                      <g opacity={0.08}>
                        {Array.from({ length: 150 }, (_, i) => (
                          <line key={`gv${i}`} x1={i * 20} y1={0} x2={i * 20} y2={2100} stroke="#555" strokeWidth={i % 5 === 0 ? 3 : 1} />
                        ))}
                        {Array.from({ length: 110 }, (_, i) => (
                          <line key={`gh${i}`} x1={0} y1={i * 20} x2={2970} y2={i * 20} stroke="#555" strokeWidth={i % 5 === 0 ? 3 : 1} />
                        ))}
                      </g>
                    )}

                    {/* Boundary frame */}
                    <rect x={PLANO_FRAME.x} y={PLANO_FRAME.y} width={PLANO_FRAME.w} height={PLANO_FRAME.h} fill="none" stroke="#3f3f46" strokeWidth={5} strokeDasharray="30 20" rx={20} />

                    {/* Elements */}
                    {elements.filter(el => el.visible).map(el => {
                      if (el.type === 'symbol') {
                        return renderSymbol(el);
                      }
                      return (
                        <g
                          key={el.id}
                          transform={`translate(${el.x},${el.y})`}
                          onMouseDown={(e) => { e.stopPropagation(); onMouseDown(e, el.id); }}
                          onTouchStart={(e) => { e.stopPropagation(); onTouchStart(e, el.id); }}
                          onClick={(e) => { e.stopPropagation(); selectElementAndBringToFront(el.id); }}
                          className="cursor-move"
                        >
                          <rect
                            width={el.w}
                            height={el.h}
                            rx={16}
                            fill={el.color}
                            fillOpacity={0.48}
                            style={{ mixBlendMode: 'screen' }}
                            stroke={el.id === selectedId ? '#ffffff' : el.color}
                            strokeWidth={el.id === selectedId ? 10 : 5}
                          />
                          <text x={el.w / 2} y={el.h >= 300 ? 70 : el.h / 2} textAnchor="middle" dominantBaseline="central" fontSize={rectLabelFont(el.label, el.w)} fill="white" fontWeight="bold">
                            {el.label.toUpperCase()}
                          </text>
                          {/* Medidas en metros (1 m = 200 px), no en px: el operador piensa en metros */}
                          <text x={el.w / 2} y={el.h >= 300 ? 120 : el.h / 2 + 44} textAnchor="middle" dominantBaseline="central" fontSize={24} fill="#ffffff80" fontWeight="bold" fontFamily="monospace">
                            {(el.w / 200).toFixed(1)}×{(el.h / 200).toFixed(1)} m
                          </text>
                          {el.id === selectedId && (
                            <rect x={-5} y={-10} width={el.w + 10} height={el.h + 20} rx={16} fill="none" stroke="#10b981" strokeWidth={5} strokeDasharray="15 10" />
                          )}
                        </g>
                      );
                    })}

                    {/* Draggable Legend */}
                    {showLegend && (
                      <g
                        transform={`translate(${legendPos.x},${legendPos.y})`}
                        onMouseDown={onLegendMouseDown}
                        onTouchStart={onLegendTouchStart}
                        className="cursor-grab"
                      >
                        <rect width={900} height={legendHeightFor(visibleLegendSymbols.length)} rx={30} fill="#18181bcc" stroke="#3f3f46" strokeWidth={5} />
                        <text x={450} y={90} textAnchor="middle" fontSize={46} fill="#a1a1aa" fontWeight="black" fontFamily="monospace" style={{ letterSpacing: '0.08em' }}>
                          SIMBOLOGÍA
                        </text>
                        {visibleLegendSymbols.map((el, i) => {
                          const fill = el.color;
                          const col = i % 2;
                          const row = Math.floor(i / 2);
                          return (
                            <g key={`legend-${el.id}`} transform={`translate(${48 + col * 410},${160 + row * 100})`}>
                              <svg x={0} y={0} width={80} height={80} viewBox="0 0 160 160">
                                {renderSymbolGlyph(el.symbolKey || 'unknown', fill, el.label)}
                              </svg>
                              <text x={104} y={52} fontSize={32} fill="#d4d4d8" fontWeight="bold" fontFamily="sans-serif">{(specDe(el.symbolKey || '')?.label || el.label).toUpperCase().slice(0, 16)}</text>
                            </g>
                          );
                        })}
                      </g>
                    )}

                    {/* Title block */}
                    <g transform="translate(100, 2020)">
                      <text fill="#888" fontSize={36} fontWeight={900} fontFamily="Inter, sans-serif">{eventName.toUpperCase()}</text>
                      <text x={0} y={50} fill="#555" fontSize={28} fontFamily="Inter, sans-serif">{`${eventVenue.toUpperCase()} · ${eventDate}`}</text>
                      <text x={2770} y={0} textAnchor="end" fill="#aaa" fontSize={24} fontFamily="monospace">Reduciendo Daño Chile · Rider Operativo</text>
                    </g>
                  </svg>
                </div>
              </div>
            </div>
          </div>

          {/* Sidebar Controls */}
          <aside className="space-y-4">
              {/* Elements List */}
              <div className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-xl space-y-3">
                <h4 className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">Zonas de Montaje</h4>
                <div className="grid grid-cols-2 gap-2">
                  {ZONAS_REALES.map(key => [key, ZONE_LABELS[key]] as const).map(([key, label]) => (
                    <button
                      key={key}
                      onClick={() => addElement(key)}
                      className="flex items-center gap-2 px-2.5 py-2 bg-zinc-800/50 border border-zinc-800 rounded-lg text-[10px] font-medium hover:bg-zinc-800 transition-colors text-left"
                    >
                      <div className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ background: ZONE_COLORS[key] }} />
                      <span className="truncate">{label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Add Symbols */}
              <div className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-xl">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">Símbolos Técnicos</h4>
                  <button
                    onClick={() => { setNuevoSimboloAbierto(v => !v); setNuevoSimboloAviso(null); }}
                    className="text-[10px] font-bold text-emerald-400 hover:text-emerald-300"
                  >
                    {nuevoSimboloAbierto ? 'Cancelar' : '+ Agregar'}
                  </button>
                </div>
                {nuevoSimboloAbierto && (
                  <div className="mb-3 space-y-2 rounded-lg border border-zinc-800 bg-zinc-900/60 p-3">
                    <input
                      type="text"
                      value={nuevoSimboloNombre}
                      onChange={e => setNuevoSimboloNombre(e.target.value)}
                      placeholder="Nombre (ej: Punto de hidratación)"
                      className="w-full rounded bg-zinc-950 border border-zinc-800 px-2 py-1.5 text-[11px] text-zinc-200"
                    />
                    <div className="flex items-center gap-2">
                      <input
                        type="color"
                        value={nuevoSimboloColor}
                        onChange={e => setNuevoSimboloColor(e.target.value)}
                        className="h-7 w-10 rounded bg-transparent"
                        title="Color del símbolo"
                      />
                      <select
                        value={nuevoSimboloZona}
                        onChange={e => setNuevoSimboloZona(e.target.value)}
                        className="flex-1 rounded bg-zinc-950 border border-zinc-800 px-2 py-1.5 text-[11px] text-zinc-200"
                      >
                        <option value="SERVICIOS">Servicios</option>
                        <option value="INFRAESTRUCTURA">Infraestructura</option>
                        <option value="SEGURIDAD">Seguridad</option>
                        <option value="COORDINACION">Coordinación</option>
                      </select>
                    </div>
                    <input
                      type="file"
                      accept=".svg,image/svg+xml,image/png,image/jpeg,image/webp"
                      onChange={async e => {
                        const archivo = e.target.files?.[0];
                        e.target.value = '';
                        if (!archivo) return;
                        if (!nuevoSimboloNombre.trim()) {
                          setNuevoSimboloAviso('Ponele un nombre antes de elegir el archivo.');
                          return;
                        }
                        const esSvg = /\.svg$/i.test(archivo.name) || archivo.type.includes('svg');
                        if (!esSvg) {
                          // Imagen: se traza y se muestra para que ella apruebe.
                          setNuevoSimboloAviso('Trazando la imagen…');
                          const t = await trazarImagen(archivo);
                          if (!t.ok || !t.svg) {
                            setPreviewSvg(null);
                            setNuevoSimboloAviso(t.error || 'No se pudo trazar.');
                            return;
                          }
                          setPreviewSvg(t.svg);
                          setNuevoSimboloAviso(null);
                          return;
                        }
                        setNuevoSimboloAviso('Guardando…');
                        const r = await guardarSimbolo({
                          etiqueta: nuevoSimboloNombre.trim(),
                          color: nuevoSimboloColor,
                          zona: nuevoSimboloZona,
                          cuando: 'siempre',
                          svg: await archivo.text(),
                        });
                        if (r.ok) {
                          setNuevoSimboloAviso(null);
                          setNuevoSimboloNombre('');
                          setNuevoSimboloAbierto(false);
                          setRefrescoSimbolos(n => n + 1);
                        } else {
                          setNuevoSimboloAviso(r.error || 'No se pudo guardar.');
                        }
                      }}
                      className="w-full text-[10px] text-zinc-400 file:mr-2 file:rounded file:border-0 file:bg-zinc-800 file:px-2 file:py-1 file:text-[10px] file:text-zinc-200"
                    />
                    {previewSvg && (
                      <div className="space-y-2 rounded-lg border border-zinc-800 bg-zinc-950 p-3">
                        <p className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">
                          Así quedaría
                        </p>
                        <div
                          className="mx-auto h-16 w-16"
                          style={{ color: nuevoSimboloColor }}
                          dangerouslySetInnerHTML={{ __html: previewSvg }}
                        />
                        <p className="text-[9px] leading-snug text-zinc-500">
                          Se dibuja el contorno de la imagen. Si salió sucio, probá con una
                          imagen más simple y de más contraste, o exportá el ícono como SVG.
                        </p>
                        <div className="flex gap-2">
                          <button
                            onClick={async () => {
                              setNuevoSimboloAviso('Guardando…');
                              const r = await guardarSimbolo({
                                etiqueta: nuevoSimboloNombre.trim(),
                                color: nuevoSimboloColor,
                                zona: nuevoSimboloZona,
                                cuando: 'siempre',
                                svg: previewSvg,
                              });
                              if (r.ok) {
                                setPreviewSvg(null);
                                setNuevoSimboloAviso(null);
                                setNuevoSimboloNombre('');
                                setNuevoSimboloAbierto(false);
                                setRefrescoSimbolos(n => n + 1);
                              } else {
                                setNuevoSimboloAviso(r.error || 'No se pudo guardar.');
                              }
                            }}
                            className="flex-1 rounded bg-emerald-600 px-2 py-1.5 text-[10px] font-bold text-white hover:bg-emerald-500"
                          >
                            Usar este
                          </button>
                          <button
                            onClick={() => { setPreviewSvg(null); setNuevoSimboloAviso(null); }}
                            className="flex-1 rounded border border-zinc-700 px-2 py-1.5 text-[10px] font-bold text-zinc-300 hover:bg-zinc-800"
                          >
                            Descartar
                          </button>
                        </div>
                      </div>
                    )}
                    <p className="text-[9px] leading-snug text-zinc-500">
                      Lo mejor es un archivo SVG. Si sólo tenés una imagen (PNG o JPG),
                      se traza su contorno y te lo muestro antes de guardarlo.
                      Si en el diseño usás el color <code>currentColor</code>, el ícono
                      toma el color que elijas acá y se ve bien en el plano oscuro y en el blanco.
                    </p>
                    {nuevoSimboloAviso && (
                      <p className="text-[10px] font-semibold text-amber-400">{nuevoSimboloAviso}</p>
                    )}
                  </div>
                )}
                <div key={refrescoSimbolos} className="grid grid-cols-4 gap-2 max-h-80 overflow-y-auto pr-1">
                  {catalogoCompleto().map(spec => (
                    <button
                      key={spec.key}
                      onClick={() => addSymbol(spec.key)}
                      title={spec.label}
                      className="flex flex-col items-center p-2 bg-zinc-800/30 border border-zinc-800 rounded-xl hover:bg-zinc-800 group transition-all"
                    >
                      {/* Los simbolos propios se muestran con SU dibujo, no con
                          un icono generico: si la jefa de eventos agrega varios,
                          con un icono comodin no podria distinguirlos aca. */}
                      {simboloPropio(spec.key)?.svg ? (
                        <svg viewBox="0 0 160 160" className="w-4 h-4" overflow="visible">
                          {renderSymbolGlyph(spec.key, spec.color, spec.label)}
                        </svg>
                      ) : (
                        renderRequirementIcon(spec.icon, "w-4 h-4 text-zinc-300")
                      )}
                      <span className="mt-1.5 text-[7px] uppercase font-black opacity-50 group-hover:opacity-100 truncate max-w-[58px]">{spec.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Property Editor with Color Picker */}
              {selectedElement && (
                <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-xl space-y-4 shadow-2xl">
                  <h4 className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">Propiedades</h4>
                  <div className="space-y-3">
                    <div>
                      <label className="text-[10px] text-zinc-500 block mb-1">Nombre / Texto Interno</label>
                      <input
                        value={selectedElement.label}
                        onChange={e => setElements(prev => prev.map(el => el.id === selectedId ? { ...el, label: e.target.value } : el))}
                        className="w-full bg-black/40 border border-zinc-800 rounded px-2.5 py-1.5 text-xs focus:outline-none focus:border-zinc-600"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-[10px] text-zinc-500 block mb-1">Ancho (px)</label>
                        <input
                          type="number"
                          value={selectedElement.w}
                          onChange={e => {
                            const val = parseInt(e.target.value) || 0;
                            setElements(prev => prev.map(el => el.id === selectedId ? { ...el, w: val } : el));
                          }}
                          className="w-full bg-black/40 border border-zinc-800 rounded px-2.5 py-1.5 text-xs focus:outline-none focus:border-zinc-600"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-zinc-500 block mb-1">Alto (px)</label>
                        <input
                          type="number"
                          value={selectedElement.h}
                          onChange={e => {
                            const val = parseInt(e.target.value) || 0;
                            setElements(prev => prev.map(el => el.id === selectedId ? { ...el, h: val } : el));
                          }}
                          className="w-full bg-black/40 border border-zinc-800 rounded px-2.5 py-1.5 text-xs focus:outline-none focus:border-zinc-600"
                        />
                      </div>
                    </div>

                    {/* Color Picker */}
                    <div>
                      <label className="text-[10px] text-zinc-500 block mb-1.5">Color del Elemento</label>
                      <div className="flex gap-1.5 flex-wrap">
                        {Object.entries({ ...ZONE_COLORS, black: '#111827', white: '#f8fafc', pink: '#ec4899', cyan: '#06b6d4' }).map(([key, val]) => (
                          <button
                            key={key}
                            onClick={() => setElements(prev => prev.map(el => el.id === selectedId ? { ...el, color: val } : el))}
                            title={ZONE_LABELS[key] || key}
                            className={cn(
                              "w-5 h-5 rounded-full border-2 transition-all",
                              selectedElement.color === val ? "border-white scale-125" : "border-transparent hover:scale-110"
                            )}
                            style={{ background: val }}
                          />
                        ))}
                      </div>
                    </div>

                    {/* Alignment buttons */}
                    <div className="space-y-2 border-t border-zinc-800/80 pt-3">
                      <label className="text-[10px] text-zinc-500 block">Alinear al marco / ordenar</label>
                      <div className="grid grid-cols-3 gap-2">
                        <button onClick={() => alignSelected('left')} className="py-1.5 bg-zinc-800 border border-zinc-700 rounded text-[9px] font-black uppercase hover:bg-zinc-700">Izq</button>
                        <button onClick={() => alignSelected('centerX')} className="py-1.5 bg-zinc-800 border border-zinc-700 rounded text-[9px] font-black uppercase hover:bg-zinc-700">Centro</button>
                        <button onClick={() => alignSelected('right')} className="py-1.5 bg-zinc-800 border border-zinc-700 rounded text-[9px] font-black uppercase hover:bg-zinc-700">Der</button>
                        <button onClick={() => alignSelected('top')} className="py-1.5 bg-zinc-800 border border-zinc-700 rounded text-[9px] font-black uppercase hover:bg-zinc-700">Arriba</button>
                        <button onClick={() => alignSelected('centerY')} className="py-1.5 bg-zinc-800 border border-zinc-700 rounded text-[9px] font-black uppercase hover:bg-zinc-700">Medio</button>
                        <button onClick={() => alignSelected('bottom')} className="py-1.5 bg-zinc-800 border border-zinc-700 rounded text-[9px] font-black uppercase hover:bg-zinc-700">Abajo</button>
                      </div>
                      <button onClick={autoArrangePlano} className="w-full py-1.5 bg-emerald-950/50 border border-emerald-800 rounded text-[9px] font-black uppercase text-emerald-300 hover:bg-emerald-900/50">Auto ordenar plano</button>
                      <button onClick={orderLayersByPriority} className="w-full py-1.5 bg-sky-950/50 border border-sky-800 rounded text-[9px] font-black uppercase text-sky-300 hover:bg-sky-900/50">Ordenar capas base</button>
                    </div>

                    {/* Layer Reordering buttons */}
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        onClick={() => moveLayer('up')}
                        className="flex items-center justify-center gap-1 py-1.5 bg-zinc-800 border border-zinc-700 rounded text-[9px] font-black uppercase hover:bg-zinc-700"
                      >
                        <Layers className="w-3 h-3" /> Subir Capa
                      </button>
                      <button
                        onClick={() => moveLayer('down')}
                        className="flex items-center justify-center gap-1 py-1.5 bg-zinc-800 border border-zinc-700 rounded text-[9px] font-black uppercase hover:bg-zinc-700"
                      >
                        <Layers className="w-3 h-3" /> Bajar Capa
                      </button>
                    </div>

                    <div className="flex items-center gap-2 pt-2 border-t border-zinc-800/80">
                      <button onClick={duplicateSelected} className="flex-1 flex items-center justify-center gap-1.5 py-1.5 bg-zinc-800 border border-zinc-700 rounded text-[10px] font-medium hover:bg-zinc-700 transition-colors">
                        <Copy className="w-3 h-3" /> Duplicar
                      </button>
                      <button onClick={() => selectedId && removeElement(selectedId)} className="flex-1 flex items-center justify-center gap-1.5 py-1.5 bg-red-900/20 text-red-400 border border-red-900/30 rounded text-[10px] font-medium hover:bg-red-900/30 transition-colors">
                        <Trash2 className="w-3 h-3" /> Eliminar
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Layers List */}
              <div className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-xl space-y-3">
                <h4 className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">Capas ({elements.length})</h4>
                <div className="space-y-1 max-h-48 overflow-y-auto">
                  {[...elements].reverse().map(el => (
                    <div
                      key={el.id}
                      onClick={() => selectElementAndBringToFront(el.id)}
                      className={cn(
                        "w-full flex items-center gap-2 px-2 py-1.5 rounded text-left text-[10px] transition-colors cursor-pointer",
                        selectedId === el.id ? "bg-zinc-800 text-white" : "text-zinc-400 hover:bg-zinc-800/30"
                      )}
                    >
                      <div className="w-2 h-2 rounded-sm flex-shrink-0" style={{ background: el.color }} />
                      <span className="truncate flex-1">{el.label}</span>
                      <button
                        onClick={e => {
                          e.stopPropagation();
                          toggleVisible(el.id);
                        }}
                        className="p-0.5 hover:text-white"
                      >
                        {el.visible ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Navigation button back */}
              <button
                onClick={() => setPage('req')}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-lg text-xs font-medium hover:bg-zinc-800 transition-all"
              >
                <ChevronLeft className="w-4 h-4" />
                Volver a Requerimientos
              </button>
            </aside>
          </div>
        )}

        {/* ── Config tab ── */}
        {page === 'config' && (
          <div className="space-y-4">
            <h2 className="font-bold text-sm text-zinc-400 uppercase tracking-widest">Configuración de la ONG</h2>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-2xl border border-zinc-800 bg-zinc-900/45 p-5 space-y-4">
                <h3 className="text-sm font-bold uppercase tracking-widest text-emerald-500">Personalización de Textos</h3>
                <div className="space-y-3">
                  <div>
                    <label className="text-[10px] uppercase tracking-widest text-zinc-500 block mb-1 font-bold">Quiénes Somos</label>
                    <textarea value={orgTexts.who} onChange={e => setOrgTexts({...orgTexts, who: e.target.value})} className="w-full bg-black/40 border border-zinc-800 p-4 rounded-xl text-xs leading-relaxed outline-none focus:border-zinc-600 min-h-[100px]" />
                  </div>
                  <div>
                    <label className="text-[10px] uppercase tracking-widest text-zinc-500 block mb-1 font-bold">Objetivo del Servicio</label>
                    <textarea value={orgTexts.goal} onChange={e => setOrgTexts({...orgTexts, goal: e.target.value})} className="w-full bg-black/40 border border-zinc-800 p-4 rounded-xl text-xs leading-relaxed outline-none focus:border-zinc-600 min-h-[100px]" />
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border border-zinc-800 bg-zinc-900/45 p-5 space-y-3">
                <h3 className="text-sm font-bold uppercase tracking-widest text-zinc-500">Integración CLI</h3>
                <div className="space-y-2">
                  {[
                    'py -m flujo app',
                    'py -m flujo health',
                  ].map(cmd => (
                    <code key={cmd} className="block rounded-lg bg-black/40 px-3 py-2 text-[10px] text-zinc-400 break-all">
                      {cmd}
                    </code>
                  ))}
                </div>
                <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-3">
                  <p className="text-[10px] font-bold uppercase tracking-widest text-zinc-600 mb-1">Notas</p>
                  <p className="text-xs text-zinc-500 leading-relaxed">
                    El plano se genera en el de forma local. Para una versión dinámica con datos reales de jobs,
                    conecta el backend levantando la aplicación con <code className="text-zinc-400">py -m flujo app</code>.
                  </p>
                </div>
                <button
                  onClick={() => setPage('req')}
                  className="w-full py-4 bg-zinc-800 rounded-xl text-xs font-black uppercase tracking-widest hover:bg-zinc-700 transition-all"
                >
                  Guardar y Volver
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

// ─── Sub-components ───

function ModalidadCard({ icon, title, description, color }: { icon: React.ReactNode; title: string; description: string; color: string }) {
  return (
    <div className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-xl hover:border-zinc-700 transition-colors group">
      <div className="w-9 h-9 rounded-lg flex items-center justify-center mb-3" style={{ background: color + '25', color }}>
        {icon}
      </div>
      <h4 className="text-sm font-bold text-white mb-2">{title}</h4>
      <p className="text-xs text-zinc-400 leading-relaxed">{description}</p>
    </div>
  );
}
