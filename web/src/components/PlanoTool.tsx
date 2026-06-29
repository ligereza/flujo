import React, { useState, useRef, useCallback } from 'react';
import { 
  Download, ZoomIn, ZoomOut, RotateCcw, 
  Trash2, Copy, Layers, Grid3X3, Eye, EyeOff, 
  ChevronLeft, ChevronRight, Printer, FileText, 
  CheckSquare, AlertTriangle, Users, Zap, 
  Shield, Heart, Coffee, RefreshCw, Settings,
  Scan, Map, Moon, Home, Table, Armchair, Box, 
  Lightbulb, Droplet, Thermometer, User, ShieldAlert, HeartPulse, Utensils
} from 'lucide-react';
import { cn } from '../utils/cn';

// ─── Types ───
interface PlanoElement {
  id: string;
  type: 'rect' | 'circle' | 'text' | 'zone' | 'symbol';
  symbolType?: 'power' | 'heating' | 'rack' | 'extinguisher' | 'water';
  x: number;
  y: number;
  width: number;
  height: number;
  label: string;
  color: string;
  rotation: number;
  locked: boolean;
  visible: boolean;
  zoneType?: 'testeo' | 'contencion' | 'informativo' | 'descanso' | 'coordinacion' | 'circulacion';
}

// ─── Paleta RD ───
const RD_PALETTE = {
  ink: '#1f2a24',
  accent: '#2d5a4a',
  paper: '#f8f1e3',
  support: '#675f55',
  alert: '#c2410f',
};

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
  water: '#2563eb'
};

const ZONE_LABELS: Record<string, string> = {
  testeo: 'Stand de Testeo',
  contencion: 'Contención',
  informativo: 'Stand Informativo',
  descanso: 'Zona Descanso',
  coordinacion: 'Coordinación',
  circulacion: 'Circulación Público',
  power: "Punto Eléctrico",
  heating: "Calefacción",
  rack: "Rack Almacén",
  extinguisher: "Extintor",
  water: "Punto de Agua"
};

// ─── Checklist Data (17 requirements in 4 categories) ───
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
      { text: 'Alimentación si jornada > 5 horas', icon: 'Utensils' }
    ]
  }
];

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
    default: return <Grid3X3 className={className} />;
  }
};

// ─── Default elements for a new plano ───
const DEFAULT_ELEMENTS: PlanoElement[] = [
  { id: 'toldo', type: 'rect', x: 150, y: 100, width: 500, height: 350, label: 'Toldo / Carpa', color: '#2d5a4a20', rotation: 0, locked: false, visible: true },
  { id: 'mesa-testeo', type: 'rect', x: 180, y: 140, width: 200, height: 80, label: 'Mesa Testeo', color: ZONE_COLORS.testeo, rotation: 0, locked: false, visible: true, zoneType: 'testeo' },
  { id: 'mesa-info', type: 'rect', x: 420, y: 140, width: 200, height: 80, label: 'Mesa Informativa', color: ZONE_COLORS.informativo, rotation: 0, locked: false, visible: true, zoneType: 'informativo' },
  { id: 'zona-contencion', type: 'rect', x: 180, y: 280, width: 180, height: 140, label: 'Contención', color: ZONE_COLORS.contencion, rotation: 0, locked: false, visible: true, zoneType: 'contencion' },
  { id: 'zona-descanso', type: 'rect', x: 420, y: 280, width: 200, height: 140, label: 'Zona Descanso', color: ZONE_COLORS.descanso, rotation: 0, locked: false, visible: true, zoneType: 'descanso' },
  { id: 'entrada', type: 'rect', x: 350, y: 470, width: 100, height: 30, label: 'Entrada Público', color: ZONE_COLORS.circulacion, rotation: 0, locked: false, visible: true, zoneType: 'circulacion' },
];

type EventPresetId = 'under' | 'base' | 'mainstream';

type EventPreset = {
  id: EventPresetId;
  label: string;
  short: string;
  volunteers: number;
  assistants: number;
  duration: number;
  tables: number;
  chairs: number;
  power: string;
  light: string;
  testing: boolean;
  massive: boolean;
};

const EVENT_PRESETS: Record<EventPresetId, EventPreset> = {
  under: {
    id: 'under', label: 'UNDER', short: 'Club chico / bajo flujo',
    volunteers: 2, assistants: 350, duration: 4, tables: 1, chairs: 2,
    power: '1 punto electrico basico', light: 'luz ambiente o 1 foco simple', testing: false, massive: false,
  },
  base: {
    id: 'base', label: 'BASE', short: 'Evento mediano / testeo',
    volunteers: 4, assistants: 1200, duration: 6, tables: 2, chairs: 4,
    power: '1 punto electrico estable', light: 'iluminacion de mesa + stand', testing: true, massive: false,
  },
  mainstream: {
    id: 'mainstream', label: 'MAINSTREAM', short: 'Espacio Riesco / festival',
    volunteers: 8, assistants: 6000, duration: 8, tables: 3, chairs: 8,
    power: '2 puntos electricos o circuito dedicado', light: 'iluminacion dedicada para stand y testeo', testing: true, massive: true,
  },
};

function elementsForPreset(preset: EventPreset): PlanoElement[] {
  const base: PlanoElement[] = [
    { id: 'toldo', type: 'rect', x: 150, y: 100, width: 500, height: 330, label: 'Toldo / Carpa', color: '#2d5a4a20', rotation: 0, locked: false, visible: true },
    { id: 'mesa-info', type: 'rect', x: 200, y: 145, width: 190, height: 75, label: 'Mesa Informativa', color: ZONE_COLORS.informativo, rotation: 0, locked: false, visible: true, zoneType: 'informativo' },
    { id: 'entrada', type: 'rect', x: 350, y: 455, width: 100, height: 30, label: 'Entrada Público', color: ZONE_COLORS.circulacion, rotation: 0, locked: false, visible: true, zoneType: 'circulacion' },
  ];
  if (preset.testing) {
    base.push({ id: 'mesa-testeo', type: 'rect', x: 425, y: 145, width: 190, height: 75, label: 'Mesa Testeo', color: ZONE_COLORS.testeo, rotation: 0, locked: false, visible: true, zoneType: 'testeo' });
  }
  if (preset.massive) {
    base.push({ id: 'zona-contencion', type: 'rect', x: 190, y: 280, width: 180, height: 120, label: 'Contención', color: ZONE_COLORS.contencion, rotation: 0, locked: false, visible: true, zoneType: 'contencion' });
    base.push({ id: 'zona-descanso', type: 'rect', x: 430, y: 280, width: 170, height: 120, label: 'Zona Descanso', color: ZONE_COLORS.descanso, rotation: 0, locked: false, visible: true, zoneType: 'descanso' });
  }
  return base;
}

export default function PlanoTool() {
  const [page, setPage] = useState<'requirements' | 'layout' | 'config'>('layout');
  const [elements, setElements] = useState<PlanoElement[]>(DEFAULT_ELEMENTS);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [showGrid, setShowGrid] = useState(true);
  const [dragging, setDragging] = useState<{ id: string; offsetX: number; offsetY: number } | null>(null);
  const [checkedItems, setCheckedItems] = useState<Set<string>>(new Set());
  const [eventName, setEventName] = useState('Evento Festival');
  const [eventDate, setEventDate] = useState('2026-06-28');
  const [eventVenue, setEventVenue] = useState('Parque Bicentenario');
  const [showLegend, setShowLegend] = useState(true);
  const [backendStatus, setBackendStatus] = useState('');
  const [eventPreset, setEventPreset] = useState<EventPresetId>('base');

  const [orgTexts, setOrgTexts] = useState({
    who: 'Reduciendo Daño es una ONG chilena dedicada a la reduccion de riesgos y danos asociados al consumo de sustancias en contextos de ocio y alta exigencia.',
    goal: 'Proveer un espacio de analisis quimico gratuito, orientacion objetiva, hidratacion y contencion psicologica para cuidar a los asistentes.'
  });

  const svgRef = useRef<SVGSVGElement>(null);

  const applyPresetLocal = (presetId: EventPresetId) => {
    const preset = EVENT_PRESETS[presetId];
    setEventPreset(presetId);
    const next = elementsForPreset(preset);
    setElements(next);
    setSelectedId(next[0]?.id ?? null);
    setBackendStatus(`Preset ${preset.label}: ${preset.volunteers} voluntarios, ${preset.tables} mesa(s), ${preset.chairs} sillas. Puedes ajustar si tu jefe pide cambios.`);
  };

  const selectedElement = elements.find(e => e.id === selectedId);

  // ─── Select Element and Bring to Front ───
  const selectElementAndBringToFront = (id: string) => {
    setSelectedId(id);
    setElements(prev => {
      const idx = prev.findIndex(e => e.id === id);
      if (idx === -1) return prev;
      const target = prev[idx];
      const next = prev.filter(e => e.id !== id);
      next.push(target);
      return next;
    });
  };

  // ─── Drag handlers ───
  const handleMouseDown = useCallback((e: React.MouseEvent, id: string) => {
    const el = elements.find(el => el.id === id);
    if (!el || el.locked) return;
    const svg = svgRef.current;
    if (!svg) return;
    const pt = svg.createSVGPoint();
    pt.x = e.clientX;
    pt.y = e.clientY;
    const svgP = pt.matrixTransform(svg.getScreenCTM()?.inverse());
    setDragging({ id, offsetX: svgP.x - el.x, offsetY: svgP.y - el.y });
    selectElementAndBringToFront(id);
    e.stopPropagation();
  }, [elements]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!dragging) return;
    const svg = svgRef.current;
    if (!svg) return;
    const pt = svg.createSVGPoint();
    pt.x = e.clientX;
    pt.y = e.clientY;
    const svgP = pt.matrixTransform(svg.getScreenCTM()?.inverse());
    setElements(prev => prev.map(el =>
      el.id === dragging.id
        ? { ...el, x: Math.round((svgP.x - dragging.offsetX) / 10) * 10, y: Math.round((svgP.y - dragging.offsetY) / 10) * 10 }
        : el
    ));
  }, [dragging]);

  const handleMouseUp = useCallback(() => {
    setDragging(null);
  }, []);

  // ─── Element actions ───
  const addElement = (zoneType: string) => {
    const id = `zone-${Date.now()}`;
    const newEl: PlanoElement = {
      id,
      type: 'rect',
      x: 200 + Math.random() * 200,
      y: 200 + Math.random() * 100,
      width: 160,
      height: 100,
      label: ZONE_LABELS[zoneType] || zoneType,
      color: ZONE_COLORS[zoneType] || '#555',
      rotation: 0,
      locked: false,
      visible: true,
      zoneType: zoneType as PlanoElement['zoneType'],
    };
    setElements(prev => [...prev, newEl]);
    setSelectedId(id);
  };

  const addSymbol = (st: 'power' | 'heating' | 'rack' | 'extinguisher' | 'water') => {
    const id = `symbol-${Date.now()}`;
    const newEl: PlanoElement = {
      id,
      type: 'symbol',
      symbolType: st,
      x: 300 + Math.random() * 100,
      y: 200 + Math.random() * 100,
      width: 40,
      height: 40,
      label: ZONE_LABELS[st] || st,
      color: ZONE_COLORS[st] || '#555',
      rotation: 0,
      locked: false,
      visible: true
    };
    setElements(prev => [...prev, newEl]);
    setSelectedId(id);
  };

  const deleteSelected = () => {
    if (!selectedId) return;
    setElements(prev => prev.filter(e => e.id !== selectedId));
    setSelectedId(null);
  };

  const duplicateSelected = () => {
    if (!selectedElement) return;
    const dup: PlanoElement = { ...selectedElement, id: `${selectedElement.id}-copy-${Date.now()}`, x: selectedElement.x + 20, y: selectedElement.y + 20 };
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

  const loadFromBackend = async (presetId: EventPresetId = eventPreset) => {
    const preset = EVENT_PRESETS[presetId];
    setEventPreset(presetId);
    if (window.location.protocol === 'file:') {
      applyPresetLocal(presetId);
      setBackendStatus(`Modo demo con preset ${preset.label}: abre con py -m flujo app para usar /api/plano/render.`);
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
            preset: preset.id,
            duracion_horas: preset.duration,
            voluntarios: preset.volunteers,
            asistentes_estimados: preset.assistants,
            incluye_testeo: preset.testing,
            masivo: preset.massive,
            ubicacion: eventVenue || 'Por definir',
            layout_mode: 'manual',
            notas: `Base generada desde preset ${preset.label}: ${preset.power}; ${preset.light}`,
          },
        }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      const zones = Array.isArray(data?.layout?.zones) ? data.layout.zones : [];
      const mapped: PlanoElement[] = zones.map((zone: any, index: number) => {
        const zoneType = zone.type === 'stand' ? 'informativo' : zone.type === 'descanso' ? 'descanso' : zone.type === 'testeo' ? 'testeo' : zone.type === 'mesa' ? 'informativo' : 'circulacion';
        return {
          id: `api-${index}-${zoneType}`,
          type: 'rect',
          x: Number(zone.x) || 80,
          y: Number(zone.y) || 80,
          width: Number(zone.w) || 140,
          height: Number(zone.h) || 80,
          label: String(zone.label || ZONE_LABELS[zoneType] || zoneType),
          color: ZONE_COLORS[zoneType] || '#555',
          rotation: 0,
          locked: false,
          visible: true,
          zoneType: zoneType as PlanoElement['zoneType'],
        };
      });
      if (mapped.length) {
        setElements(mapped);
        setSelectedId(mapped[0].id);
      }
      setBackendStatus(`Motor Python OK con preset ${preset.label}: ${mapped.length} zonas cargadas.`);
    } catch (error) {
      setBackendStatus(`No se pudo usar /api/plano/render: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  const toggleCheck = (item: string) => {
    setCheckedItems(prev => {
      const next = new Set(prev);
      next.has(item) ? next.delete(item) : next.add(item);
      return next;
    });
  };

  const totalChecks = CHECKLIST_SECTIONS.reduce((sum, s) => sum + s.items.length, 0);
  const completedChecks = checkedItems.size;

  // ─── Export SVG ───
  const exportSVG = () => {
    if (!svgRef.current) return;
    const svgData = new XMLSerializer().serializeToString(svgRef.current);
    const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `plano_${eventName.replace(/\s+/g, '_').toLowerCase()}.svg`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // ─── Export Checklist as Markdown ───
  const exportChecklistMarkdown = () => {
    let md = `# RIDER TÉCNICO RD - CHECKLIST\n\n`;
    md += `**Evento:** ${eventName}\n`;
    md += `**Fecha:** ${eventDate}\n`;
    md += `**Lugar:** ${eventVenue}\n`;
    md += `**Preset Comercial:** ${eventPreset.toUpperCase()}\n\n`;
    md += `## 1. Antecedentes de la Organización\n\n`;
    md += `**Quiénes somos:** ${orgTexts.who}\n\n`;
    md += `**Objetivo del servicio:** ${orgTexts.goal}\n\n`;
    md += `## 2. Requerimientos Operativos\n\n`;
    CHECKLIST_SECTIONS.forEach(sec => {
      md += `### ${sec.title}\n`;
      sec.items.forEach(item => {
        const isChecked = checkedItems.has(`${sec.title}-${item.text}`) ? '[x]' : '[ ]';
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

  // ─── Render Symbol (Procedural SVG without Emojis) ───
  const renderSymbol = (el: PlanoElement, isPrint = false) => {
    const color = isPrint ? '#000' : el.color;
    return (
      <g key={el.id} transform={`translate(${el.x},${el.y})`} onMouseDown={(e) => handleMouseDown(e, el.id)} className="cursor-move">
        <rect width={el.width} height={el.height} fill="transparent" stroke={el.id === selectedId ? '#fff' : 'none'} strokeWidth={2} />
        {el.symbolType === 'power' && (
          <g stroke={color} strokeWidth="2" fill="none">
            <circle cx="20" cy="20" r="12" />
            <path d="M20 10 L16 20 H24 L20 30" stroke={color} strokeWidth="2.5" />
          </g>
        )}
        {el.symbolType === 'heating' && (
          <g stroke={color} strokeWidth="2" fill="none">
             <rect x="8" y="10" width="24" height="20" rx="2" />
             <path d="M14 14 V26 M20 14 V26 M26 14 V26" />
          </g>
        )}
        {el.symbolType === 'rack' && (
           <g stroke={color} strokeWidth="2" fill="none">
              <rect x="5" y="5" width="30" height="30" />
              <path d="M5 15 H35 M5 25 H35 M15 5 V35 M25 5 V35" strokeOpacity="0.3" />
           </g>
        )}
        {el.symbolType === 'extinguisher' && (
           <g fill={color}>
              <rect x="15" y="12" width="10" height="25" rx="2" />
              <path d="M17 12 V8 H23 V12 M23 15 H28" stroke={color} fill="none" strokeWidth="2" />
           </g>
        )}
        {el.symbolType === 'water' && (
           <g stroke={color} strokeWidth="2" fill="none">
              <circle cx="20" cy="20" r="12" />
              <path d="M20 15 Q25 25 20 30 Q15 25 20 15" fill={color} />
           </g>
        )}
        <text x="20" y="52" textAnchor="middle" fontSize="7" fill={color} fontWeight="bold" fontFamily="monospace">{el.label.toUpperCase()}</text>
      </g>
    );
  };

  return (
    <div className="space-y-6" onMouseMove={handleMouseMove} onMouseUp={handleMouseUp}>
      {/* Printable Area (Styled strictly for high contrast and paper output) */}
      <div className="hidden print:block p-8 text-black bg-white font-sans text-xs">
        <header className="border-b-4 border-black pb-4 mb-8 flex justify-between items-end">
          <div>
            <h1 className="text-3xl font-black italic tracking-tighter uppercase">RIDER TÉCNICO RD</h1>
            <p className="text-[9px] uppercase tracking-[0.2em] font-bold mt-1">Documentación de Intervención en Terreno — ONG Reduciendo Daño</p>
          </div>
          <div className="text-right">
            <p className="text-base font-bold">ORGANIZACIÓN RD</p>
            <p className="text-[9px] opacity-60">Servicio de Testeo y Reducción de Daño v2026</p>
          </div>
        </header>

        <section className="mb-6">
          <h2 className="text-lg font-black uppercase tracking-tight mb-2">1. Antecedentes</h2>
          <div className="grid grid-cols-1 gap-3 leading-relaxed">
            <p><strong>Quiénes Somos:</strong> {orgTexts.who}</p>
            <p><strong>Objetivo del Servicio:</strong> {orgTexts.goal}</p>
            <p><strong>Evento:</strong> {eventName} · <strong>Ubicación:</strong> {eventVenue} · <strong>Fecha:</strong> {eventDate}</p>
          </div>
        </section>

        <section className="mb-6">
          <h2 className="text-lg font-black uppercase tracking-tight mb-2">2. Requerimientos Operativos</h2>
          <div className="grid grid-cols-2 gap-4">
            {CHECKLIST_SECTIONS.map(section => (
              <div key={section.title} className="border border-zinc-300 p-3 rounded">
                <h3 className="font-bold text-[10px] uppercase mb-2 border-b border-zinc-200 pb-1 flex items-center gap-1">
                  {section.title}
                </h3>
                <ul className="space-y-1">
                  {section.items.map(item => {
                    const isChecked = checkedItems.has(`${section.title}-${item.text}`);
                    return (
                      <li key={item.text} className="flex items-center gap-2">
                        <div className="w-3.5 h-3.5 border border-black flex items-center justify-center font-bold font-mono text-[9px]">
                          {isChecked ? 'X' : ' '}
                        </div>
                        <span className={cn(isChecked ? "line-through opacity-50" : "")}>{item.text}</span>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
          </div>
        </section>

        <div className="break-before-page" style={{ height: '20px' }} />

        <section className="h-full flex flex-col">
          <h2 className="text-lg font-black uppercase tracking-tight mb-2">3. Esquema de Distribución del Stand</h2>
          <div className="border border-black p-4 bg-zinc-50 relative flex justify-center items-center">
            {/* Embedded SVG rendered safely inside print document stream */}
            <svg viewBox="0 0 800 550" className="w-full max-w-[650px] aspect-[1.45/1]">
              <rect width="100%" height="100%" fill="#fafafa" stroke="#ccc" />
              <rect x={20} y={20} width={760} height={510} fill="none" stroke="#666" strokeWidth={1} strokeDasharray="4 2" />
              {elements.filter(e => e.visible).map(el => {
                if (el.type === 'symbol') return renderSymbol(el, true);
                return (
                  <g key={el.id}>
                    <rect x={el.x} y={el.y} width={el.width} height={el.height} fill="none" stroke="#000" strokeWidth={1.5} />
                    <text x={el.x + el.width/2} y={el.y + el.height/2} textAnchor="middle" dominantBaseline="central" fontSize={9} fontWeight="bold">{el.label.toUpperCase()}</text>
                  </g>
                );
              })}
              <g transform="translate(40, 500)">
                <text fontSize={9} fill="#444">{eventName} · {eventVenue} · {eventDate}</text>
              </g>
            </svg>
          </div>
        </section>
      </div>

      {/* Screen View (Interactive App Tool) */}
      <div className="flex items-center justify-between print:hidden">
        <div>
          <h3 className="text-2xl font-bold flex items-center gap-2">
            Rider RD · Herramienta de Plano
            <span className="text-xs bg-emerald-500/20 text-emerald-400 font-black px-2 py-0.5 rounded-full uppercase tracking-wider">v0.43.3</span>
          </h3>
          <p className="text-zinc-400 text-sm mt-1">
            Documento operativo para intervención en terreno — Reduciendo Daño Chile
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPage('requirements')}
            className={cn(
              "px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 border",
              page === 'requirements' ? "bg-white text-black border-white" : "bg-zinc-900 border-zinc-800 text-zinc-300 hover:bg-zinc-800"
            )}
          >
            <FileText className="w-4 h-4" />
            1. Requerimientos
          </button>
          <button
            onClick={() => setPage('layout')}
            className={cn(
              "px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 border",
              page === 'layout' ? "bg-white text-black border-white" : "bg-zinc-900 border-zinc-800 text-zinc-300 hover:bg-zinc-800"
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
            <RefreshCw className="w-4 h-4 animate-spin-hover" />
            Motor Python
          </button>
        </div>
      </div>
      {backendStatus && (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 px-4 py-2 text-xs text-zinc-400 print:hidden">
          {backendStatus}
        </div>
      )}

      {/* ═══ PAGE 1: REQUIREMENTS (17 items) ═══ */}
      {page === 'requirements' && (
        <div className="grid grid-cols-3 gap-6 print:hidden">
          {/* Left: Info card and modality blocks */}
          <div className="col-span-2 space-y-6">
            <div className="p-6 rounded-xl border border-zinc-800" style={{ background: 'linear-gradient(135deg, #1f2a24 0%, #09090b 100%)' }}>
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: RD_PALETTE.accent }}>
                  <Shield className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h4 className="text-lg font-bold text-white">Reduciendo Daño Chile</h4>
                  <p className="text-xs text-zinc-400">Propuesta de Servicio · Intervención en Terreno</p>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="text-[10px] uppercase tracking-widest text-zinc-500 block mb-1">Evento</label>
                  <input
                    value={eventName}
                    onChange={e => setEventName(e.target.value)}
                    className="w-full bg-black/30 border border-zinc-700 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-zinc-500"
                  />
                </div>
                <div>
                  <label className="text-[10px] uppercase tracking-widest text-zinc-500 block mb-1">Fecha</label>
                  <input
                    type="date"
                    value={eventDate}
                    onChange={e => setEventDate(e.target.value)}
                    className="w-full bg-black/30 border border-zinc-700 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-zinc-500"
                  />
                </div>
                <div>
                  <label className="text-[10px] uppercase tracking-widest text-zinc-500 block mb-1">Lugar</label>
                  <input
                    value={eventVenue}
                    onChange={e => setEventVenue(e.target.value)}
                    className="w-full bg-black/30 border border-zinc-700 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-zinc-500"
                  />
                </div>
              </div>
            </div>

            {/* Presets card selectors */}
            <div className="bg-zinc-900/40 border border-zinc-800 p-6 rounded-2xl">
              <h4 className="text-xs font-black uppercase text-zinc-400 tracking-wider mb-4">Presets de Carga de Eventos</h4>
              <div className="grid grid-cols-3 gap-4">
                {(['under', 'base', 'mainstream'] as const).map(p => (
                  <button
                    key={p}
                    onClick={() => applyPresetLocal(p)}
                    className={cn(
                      "p-4 rounded-xl border text-left transition-all",
                      eventPreset === p 
                        ? "bg-emerald-950/40 border-emerald-500/80 text-emerald-300"
                        : "bg-black/20 border-zinc-800/80 text-zinc-400 hover:border-zinc-700"
                    )}
                  >
                    <div className="font-black uppercase text-xs">{p}</div>
                    <div className="text-[10px] mt-1 opacity-70 font-semibold">{EVENT_PRESETS[p].short}</div>
                    <div className="text-[9px] mt-2 font-mono text-zinc-500">Voluntarios: {EVENT_PRESETS[p].volunteers} | Mesas: {EVENT_PRESETS[p].tables}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <ModalidadCard
                icon={<Heart className="w-5 h-5" />}
                title="Stand Informativo"
                description="Personas capacitadas para orientar y entregar consejos preventivos. Material educativo, protectores auditivos, suplementos pre/post."
                color={ZONE_COLORS.informativo}
              />
              <ModalidadCard
                icon={<AlertTriangle className="w-5 h-5" />}
                title="Stand de Testeo"
                description="Análisis colorimétricos de sustancias gratuito. Equipo liderado por analistas químicos y químicos farmacéuticos."
                color={ZONE_COLORS.testeo}
              />
              <ModalidadCard
                icon={<Coffee className="w-5 h-5" />}
                title="Contención"
                description="Rondas preventivas en terreno. Contención psicológica y atención en situaciones de crisis o desregulación emocional."
                color={ZONE_COLORS.contencion}
              />
            </div>
          </div>

          {/* Right: Requirements interactive checklist */}
          <div className="space-y-4">
            <div className="p-5 bg-zinc-900/50 border border-zinc-800 rounded-2xl sticky top-24">
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-sm font-bold uppercase tracking-widest text-zinc-400">Requerimientos (17)</h4>
                <span className={cn(
                  "text-xs font-bold px-2 py-0.5 rounded",
                  completedChecks === totalChecks 
                    ? "bg-green-500/20 text-green-400" 
                    : "bg-zinc-800 text-zinc-500"
                )}>
                  {completedChecks}/{totalChecks}
                </span>
              </div>

              {/* Progress bar */}
              <div className="w-full h-1.5 bg-zinc-800 rounded-full mb-6 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${(completedChecks / totalChecks) * 100}%`,
                    background: completedChecks === totalChecks ? '#22c55e' : RD_PALETTE.accent,
                  }}
                />
              </div>

              <div className="space-y-4 max-h-[380px] overflow-y-auto pr-1">
                {CHECKLIST_SECTIONS.map(section => (
                  <div key={section.title} className="space-y-2">
                    <div className="flex items-center gap-2 border-b border-zinc-800/80 pb-1 mt-2">
                      <span className="text-emerald-500">{renderRequirementIcon(section.iconName, "w-3.5 h-3.5")}</span>
                      <span className="text-[10px] font-black uppercase tracking-wider text-zinc-400">{section.title}</span>
                    </div>
                    <div className="space-y-1.5">
                      {section.items.map(item => {
                        const itemKey = `${section.title}-${item.text}`;
                        const isChecked = checkedItems.has(itemKey);
                        return (
                          <button
                            key={item.text}
                            onClick={() => toggleCheck(itemKey)}
                            className="w-full flex items-center gap-2.5 text-left group"
                          >
                            <div className={cn(
                              "w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 transition-all",
                              isChecked
                                ? "bg-green-600 border-green-600"
                                : "border-zinc-700 group-hover:border-zinc-500"
                            )}>
                              {isChecked && (
                                <CheckSquare className="w-3 h-3 text-white" />
                              )}
                            </div>
                            <div className="flex items-center gap-2 overflow-hidden flex-1">
                              {renderRequirementIcon(item.icon, "w-3 h-3 text-zinc-500 group-hover:text-zinc-300")}
                              <span className={cn(
                                "text-[11px] transition-colors truncate",
                                isChecked
                                  ? "text-zinc-500 line-through"
                                  : "text-zinc-300 group-hover:text-white"
                              )}>
                                {item.text}
                              </span>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>

              <div className="pt-4 mt-4 border-t border-zinc-800/80 space-y-2">
                <button
                  onClick={exportChecklistMarkdown}
                  className="w-full flex items-center justify-center gap-2 py-2.5 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg text-xs font-semibold transition-colors"
                >
                  <Download className="w-3.5 h-3.5" /> Exportar Checklist (.md)
                </button>
              </div>
            </div>

            <button
              onClick={() => setPage('layout')}
              className="w-full py-5 bg-emerald-500 hover:bg-emerald-400 text-black font-black rounded-3xl shadow-xl shadow-emerald-500/10 transition-transform active:scale-[0.98] flex items-center justify-center gap-3 text-base"
            >
              Ir al Plano de Distribución
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}

      {/* ═══ PAGE 2: LAYOUT / PLANO ═══ */}
      {page === 'layout' && (
        <div className="grid grid-cols-4 gap-6 print:hidden">
          {/* Canvas area */}
          <div className="col-span-3">
            {/* Toolbar */}
            <div className="flex items-center justify-between mb-3 px-1">
              <div className="flex items-center gap-1">
                <ToolBtn icon={<ZoomIn className="w-3.5 h-3.5" />} onClick={() => setZoom(z => Math.min(z + 0.15, 2.5))} tooltip="Zoom +" />
                <ToolBtn icon={<ZoomOut className="w-3.5 h-3.5" />} onClick={() => setZoom(z => Math.max(z - 0.15, 0.4))} tooltip="Zoom -" />
                <ToolBtn icon={<RotateCcw className="w-3.5 h-3.5" />} onClick={() => setZoom(1)} tooltip="Reset zoom" />
                <div className="w-px h-5 bg-zinc-800 mx-1" />
                <ToolBtn icon={<Grid3X3 className="w-3.5 h-3.5" />} onClick={() => setShowGrid(!showGrid)} active={showGrid} tooltip="Grilla" />
                <ToolBtn icon={showLegend ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />} onClick={() => setShowLegend(!showLegend)} active={showLegend} tooltip="Leyenda" />
              </div>
              <div className="flex items-center gap-1">
                <span className="text-[10px] font-mono text-zinc-600 mr-2">{Math.round(zoom * 100)}%</span>
                <ToolBtn icon={<Download className="w-3.5 h-3.5" />} onClick={exportSVG} tooltip="Exportar SVG" />
                <ToolBtn icon={<Printer className="w-3.5 h-3.5" />} onClick={() => window.print()} tooltip="Imprimir" />
              </div>
            </div>

            {/* SVG Canvas */}
            <div className="bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden relative" style={{ height: "650px" }}>
              <div className="w-full h-full overflow-auto flex items-center justify-center p-4">
                <div className="relative bg-white shadow-2xl transition-all" style={{ width: 800, height: 600, transform: `scale(${zoom})`, transformOrigin: "center" }}>
                  <svg
                    ref={svgRef}
                    viewBox="0 0 800 550"
                    className="w-full h-full"
                    onClick={() => setSelectedId(null)}
                  >
                    {/* Grid */}
                    {showGrid && (
                      <g opacity={0.08}>
                        {Array.from({ length: 81 }, (_, i) => (
                          <line key={`gv${i}`} x1={i * 10} y1={0} x2={i * 10} y2={550} stroke="#111" strokeWidth={i % 5 === 0 ? 0.6 : 0.3} />
                        ))}
                        {Array.from({ length: 56 }, (_, i) => (
                          <line key={`gh${i}`} x1={0} y1={i * 10} x2={800} y2={i * 10} stroke="#111" strokeWidth={i % 5 === 0 ? 0.6 : 0.3} />
                        ))}
                      </g>
                    )}

                    {/* Boundary frame */}
                    <rect x={20} y={20} width={760} height={510} fill="none" stroke="#666" strokeWidth={1} strokeDasharray="6 3" rx={4} />
                    <text x={30} y={16} fill="#777" fontSize={9} fontFamily="Inter, sans-serif">A4 Horizontal — 29.7 × 21 cm</text>

                    {/* Elements */}
                    {elements.filter(e => e.visible).map(el => {
                      if (el.type === 'symbol') {
                        return renderSymbol(el);
                      }
                      const isSelected = el.id === selectedId;
                      const common = { 
                        onMouseDown: (e: any) => handleMouseDown(e, el.id), 
                        className: cn("cursor-move transition-all", isSelected && "stroke-white stroke-2") 
                      };
                      if (el.type === 'rect') {
                        return (
                          <g key={el.id} onClick={(e) => { e.stopPropagation(); selectElementAndBringToFront(el.id); }}>
                            <rect
                              x={el.x}
                              y={el.y}
                              width={el.width}
                              height={el.height}
                              rx={12}
                              fill={el.color}
                              fillOpacity={0.7}
                              stroke={isSelected ? '#ffffff' : el.color}
                              strokeWidth={isSelected ? 2.5 : 1}
                              strokeDasharray={el.zoneType === 'circulacion' ? '6 3' : undefined}
                              {...common}
                            />
                            <text
                              x={el.x + el.width / 2}
                              y={el.y + el.height / 2}
                              textAnchor="middle"
                              dominantBaseline="central"
                              fill="#ffffff"
                              fontSize={11}
                              fontFamily="Inter, sans-serif"
                              fontWeight={700}
                              style={{ pointerEvents: 'none' }}
                            >
                              {el.label.toUpperCase()}
                            </text>
                            <text
                              x={el.x + el.width / 2}
                              y={el.y + el.height / 2 + 16}
                              textAnchor="middle"
                              dominantBaseline="central"
                              fill="#ffffff80"
                              fontSize={8}
                              fontFamily="monospace"
                              style={{ pointerEvents: 'none' }}
                            >
                              {el.width}×{el.height}
                            </text>
                          </g>
                        );
                      }
                      return null;
                    })}

                    {/* Legend */}
                    {showLegend && (
                      <g transform="translate(600, 35)">
                        <rect x={0} y={0} width={170} height={140} rx={12} fill="#09090bcc" stroke="#333" strokeWidth={1} />
                        <text x={12} y={20} fill="#aaa" fontSize={9} fontWeight={900} fontFamily="Inter, sans-serif">LEYENDA</text>
                        {Object.entries(ZONE_COLORS).filter(([k]) => ['testeo','contencion','informativo','descanso','coordinacion','circulacion'].includes(k)).map(([key, color], i) => (
                          <g key={key} transform={`translate(12, ${35 + i * 16})`}>
                            <rect x={0} y={-5} width={10} height={10} rx={2.5} fill={color + 'aa'} stroke={color} strokeWidth={1} />
                            <text x={16} y={4} fill="#bbb" fontSize={9} fontFamily="Inter, sans-serif">{ZONE_LABELS[key]}</text>
                          </g>
                        ))}
                      </g>
                    )}

                    {/* Title block */}
                    <g transform="translate(30, 490)">
                      <text fill="#222" fontSize={11} fontWeight={900} fontFamily="Inter, sans-serif">{eventName.toUpperCase()}</text>
                      <text x={0} y={14} fill="#666" fontSize={8} fontFamily="Inter, sans-serif">{eventVenue.toUpperCase()} · {eventDate}</text>
                      <text x={700} y={0} textAnchor="end" fill="#aaa" fontSize={7} fontFamily="monospace">Reduciendo Daño Chile · Rider Operativo</text>
                    </g>
                  </svg>
                </div>
              </div>
            </div>
          </div>

          {/* Right panel */}
          <div className="space-y-4">
            {/* Add zones */}
            <div className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-xl">
              <h4 className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 mb-3">Zonas de Montaje</h4>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(ZONE_LABELS).filter(([k]) => !['power','heating','rack','extinguisher','water'].includes(k)).map(([key, label]) => (
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
              <h4 className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 mb-3">Símbolos Técnicos (Sin Emoji)</h4>
              <div className="grid grid-cols-3 gap-2">
                {(['power','heating','rack','extinguisher','water'] as const).map(s => (
                  <button
                    key={s}
                    onClick={() => addSymbol(s)}
                    className="flex flex-col items-center p-3.5 bg-zinc-800/30 border border-zinc-800 rounded-xl hover:bg-zinc-800 group transition-all"
                  >
                    {s === 'power' && <Zap className="w-4 h-4 text-yellow-500" />}
                    {s === 'heating' && <RefreshCw className="w-4 h-4 text-red-500" />}
                    {s === 'rack' && <Box className="w-4 h-4 text-zinc-400" />}
                    {s === 'extinguisher' && <ShieldAlert className="w-4 h-4 text-red-600" />}
                    {s === 'water' && <Droplet className="w-4 h-4 text-blue-500" />}
                    <span className="mt-2 text-[7px] uppercase font-black opacity-40 group-hover:opacity-100">{s}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Selected element properties and Color Picker */}
            {selectedElement && (
              <div className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-xl space-y-4">
                <h4 className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">Propiedades</h4>
                <div className="space-y-3">
                  <div>
                    <label className="text-[10px] text-zinc-500 block mb-1">Nombre</label>
                    <input
                      value={selectedElement.label}
                      onChange={e => setElements(prev => prev.map(el => el.id === selectedId ? { ...el, label: e.target.value } : el))}
                      className="w-full bg-black/30 border border-zinc-700 rounded px-2 py-1 text-xs focus:outline-none focus:border-zinc-500"
                    />
                  </div>

                  {/* Color Picker */}
                  <div>
                    <label className="text-[10px] text-zinc-500 block mb-1.5">Color del Elemento</label>
                    <div className="flex gap-1.5 flex-wrap">
                      {Object.entries(ZONE_COLORS).map(([key, val]) => (
                        <button
                          key={key}
                          onClick={() => setElements(prev => prev.map(el => el.id === selectedId ? { ...el, color: val } : el))}
                          title={ZONE_LABELS[key]}
                          className={cn(
                            "w-5 h-5 rounded-full border-2 transition-all",
                            selectedElement.color === val ? "border-white scale-110" : "border-transparent hover:scale-105"
                          )}
                          style={{ background: val }}
                        />
                      ))}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-[10px] text-zinc-500 block mb-1">Ancho</label>
                      <input
                        type="number"
                        value={selectedElement.width}
                        onChange={e => setElements(prev => prev.map(el => el.id === selectedId ? { ...el, width: Number(e.target.value) } : el))}
                        className="w-full bg-black/30 border border-zinc-700 rounded px-2 py-1 text-xs font-mono focus:outline-none focus:border-zinc-500"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-zinc-500 block mb-1">Alto</label>
                      <input
                        type="number"
                        value={selectedElement.height}
                        onChange={e => setElements(prev => prev.map(el => el.id === selectedId ? { ...el, height: Number(e.target.value) } : el))}
                        className="w-full bg-black/30 border border-zinc-700 rounded px-2 py-1 text-xs font-mono focus:outline-none focus:border-zinc-500"
                      />
                    </div>
                  </div>

                  {/* Z-Index Controls */}
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

                  <div className="flex items-center gap-2 pt-2">
                    <button onClick={duplicateSelected} className="flex-1 flex items-center justify-center gap-1.5 py-1.5 bg-zinc-800 border border-zinc-700 rounded text-[10px] font-medium hover:bg-zinc-700 transition-colors">
                      <Copy className="w-3 h-3" /> Duplicar
                    </button>
                    <button onClick={deleteSelected} className="flex-1 flex items-center justify-center gap-1.5 py-1.5 bg-red-900/30 border border-red-900/50 rounded text-[10px] font-medium text-red-400 hover:bg-red-900/50 transition-colors">
                      <Trash2 className="w-3 h-3" /> Eliminar
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Elements list */}
            <div className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-xl">
              <h4 className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 mb-3">Capas ({elements.length})</h4>
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {[...elements].reverse().map(el => (
                  <button
                    key={el.id}
                    onClick={() => setSelectedId(el.id)}
                    className={cn(
                      "w-full flex items-center gap-2 px-2 py-1.5 rounded text-left text-[10px] transition-colors",
                      selectedId === el.id ? "bg-zinc-800 text-white" : "text-zinc-400 hover:bg-zinc-800/50"
                    )}
                  >
                    <div className="w-2 h-2 rounded-sm flex-shrink-0" style={{ background: el.color }} />
                    <span className="truncate flex-1">{el.label}</span>
                    <button
                      onClick={e => {
                        e.stopPropagation();
                        setElements(prev => prev.map(item => item.id === el.id ? { ...item, visible: !item.visible } : item));
                      }}
                      className="p-0.5 hover:text-white"
                    >
                      {el.visible ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
                    </button>
                  </button>
                ))}
              </div>
            </div>

            {/* Navigation */}
            <button
              onClick={() => setPage('requirements')}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-lg text-xs font-medium hover:bg-zinc-800 transition-all"
            >
              <ChevronLeft className="w-4 h-4" />
              Volver a Requerimientos
            </button>
          </div>
        </div>
      )}

      {/* ═══ PAGE 3: CONFIGURATION ═══ */}
      {page === 'config' && (
        <div className="max-w-3xl mx-auto space-y-12 bg-black/40 p-12 rounded-3xl border border-zinc-800 print:hidden">
          <header>
            <h2 className="text-4xl font-black tracking-tighter">Configuración de Mensajes</h2>
            <p className="text-zinc-500 text-xs mt-2 uppercase tracking-widest font-mono">Personalización de Textos de la ONG para Impresión</p>
          </header>
          
          <section className="space-y-8">
            <div className="space-y-4">
              <label className="text-[10px] font-black uppercase text-emerald-500 tracking-[0.2em]">Quiénes Somos</label>
              <textarea value={orgTexts.who} onChange={e => setOrgTexts({...orgTexts, who: e.target.value})} className="w-full bg-zinc-900 border border-zinc-800 p-6 rounded-3xl text-sm min-h-[120px] outline-none focus:border-emerald-500 transition-colors leading-relaxed shadow-inner" />
            </div>
            <div className="space-y-4">
              <label className="text-[10px] font-black uppercase text-emerald-500 tracking-[0.2em]">Objetivo del Servicio</label>
              <textarea value={orgTexts.goal} onChange={e => setOrgTexts({...orgTexts, goal: e.target.value})} className="w-full bg-zinc-900 border border-zinc-800 p-6 rounded-3xl text-sm min-h-[120px] outline-none focus:border-emerald-500 transition-colors leading-relaxed shadow-inner" />
            </div>
          </section>

          <div className="p-10 bg-zinc-900/50 border border-dashed border-zinc-800 rounded-[3rem] text-center">
            <p className="text-zinc-400 text-xs italic leading-relaxed">Los cambios en esta sección se reflejan en tiempo real en la vista de impresión del Rider Técnico.</p>
          </div>
          
          <button onClick={() => setPage('requirements')} className="w-full py-5 bg-zinc-800 rounded-3xl font-black text-xs uppercase tracking-widest hover:bg-zinc-700 transition-all active:scale-[0.99]">Guardar Ajustes y Volver</button>
        </div>
      )}
    </div>
  );
}

// ─── Sub-components ───

function ToolBtn({ icon, onClick, tooltip, active }: { icon: React.ReactNode; onClick: () => void; tooltip: string; active?: boolean }) {
  return (
    <button
      onClick={onClick}
      title={tooltip}
      className={cn(
        "p-2 rounded-md transition-colors",
        active ? "bg-zinc-700 text-white" : "bg-zinc-900 text-zinc-500 hover:text-white hover:bg-zinc-800 border border-zinc-800"
      )}
    >
      {" "}
      {icon}
    </button>
  );
}

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
