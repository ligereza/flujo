import React, { useRef, useState, useCallback } from 'react';
import { 
  Map, Download, Plus, Trash2, Eye, EyeOff, Printer, RotateCcw,
  Scan, Users, Moon, Home, Table, Armchair, Box, Zap,
  Lightbulb, Droplet, Thermometer, User, ShieldAlert, HeartPulse, Utensils,
  ChevronRight, ChevronLeft, Settings, Copy, Layers, Grid3X3, FileText,
  Heart, AlertTriangle, Coffee, RefreshCw
} from 'lucide-react';
import { cn } from '../utils/cn';

// ── Types ────────────────────────────────────────────────────────────
type Preset = 'UNDER' | 'BASE' | 'MAINSTREAM';

interface Element {
  id: string;
  type: 'rect' | 'symbol';
  symbolType?: 'power' | 'heating' | 'rack' | 'extinguisher' | 'water';
  x: number;
  y: number;
  w: number;
  h: number;
  label: string;
  color: string;
  visible: boolean;
  symbolKey?: string;
  locked?: boolean;
}

// ── Presets ──────────────────────────────────────────────────────────
const PRESET_CONFIGS: Record<Preset, { desc: string }> = {
  UNDER: {
    desc: '2 voluntarios, 1 mesa, 2 sillas, electricidad/luz básica'
  },
  BASE: {
    desc: '4 voluntarios, 2 mesas, 4 sillas, stand + testeo'
  },
  MAINSTREAM: {
    desc: '8 voluntarios, 3 mesas, 8 sillas, alto flujo tipo Espacio Riesco'
  }
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
  water: 'Punto de Agua'
};

// ── Checklist Data (17 requirements in 4 categories) ───
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

// ── Default elements builder ─────────────────────────────────────────
function buildElements(preset: Preset): Element[] {
  const base: Element[] = [
    { id: 'entrada', type: 'rect', x: 250, y: 30, w: 100, h: 30, label: 'ENTRADA', color: '#6366f1', visible: true },
    { id: 'mesa1', type: 'rect', x: 60, y: 120, w: 120, h: 50, label: 'Mesa 1', color: '#10b981', visible: true },
    { id: 'testeo', type: 'symbol', x: 200, y: 130, w: 40, h: 40, label: 'Testeo', color: '#f59e0b', visible: true, symbolKey: 'testeo' },
    { id: 'contencion', type: 'symbol', x: 380, y: 130, w: 40, h: 40, label: 'Contención', color: '#3b82f6', visible: true, symbolKey: 'contencion' },
    { id: 'power1', type: 'symbol', x: 460, y: 220, w: 32, h: 32, label: 'Poder', color: '#f59e0b', visible: true, symbolKey: 'power' },
    { id: 'extinguisher1', type: 'symbol', x: 500, y: 320, w: 32, h: 32, label: 'Extintor', color: '#ef4444', visible: true, symbolKey: 'extinguisher' },
  ];

  if (preset === 'BASE' || preset === 'MAINSTREAM') {
    base.push(
      { id: 'mesa2', type: 'rect', x: 200, y: 120, w: 120, h: 50, label: 'Mesa 2', color: '#10b981', visible: true },
      { id: 'stand1', type: 'rect', x: 60, y: 220, w: 80, h: 60, label: 'Stand', color: '#8b5cf6', visible: true },
    );
  }

  if (preset === 'MAINSTREAM') {
    base.push(
      { id: 'mesa3', type: 'rect', x: 340, y: 120, w: 120, h: 50, label: 'Mesa 3', color: '#10b981', visible: true },
      { id: 'stand2', type: 'rect', x: 160, y: 220, w: 80, h: 60, label: 'Stand 2', color: '#8b5cf6', visible: true },
      { id: 'testeo2', type: 'symbol', x: 280, y: 240, w: 40, h: 40, label: 'Testeo 2', color: '#f59e0b', visible: true, symbolKey: 'testeo' },
      { id: 'contencion2', type: 'symbol', x: 360, y: 240, w: 40, h: 40, label: 'Contención 2', color: '#3b82f6', visible: true, symbolKey: 'contencion' },
    );
  }

  return base;
}

// ── Main component ───────────────────────────────────────────────────
type Page = 'req' | 'map' | 'config';

export default function PlanoTool() {
  const [preset, setPreset] = useState<Preset>('BASE');
  const [page, setPage] = useState<Page>('map');
  const [elements, setElements] = useState<Element[]>(() => buildElements('BASE'));
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [checkedItems, setCheckedItems] = useState<string[]>([]);
  const [legendPos, setLegendPos] = useState({ x: 420, y: 350 });
  const [zoom, setZoom] = useState(1);
  const [showGrid, setShowGrid] = useState(true);
  const [showLegend, setShowLegend] = useState(true);
  const [eventName, setEventName] = useState('Evento Festival');
  const [eventDate, setEventDate] = useState('2026-06-28');
  const [eventVenue, setEventVenue] = useState('Parque Bicentenario');
  const [backendStatus, setBackendStatus] = useState('');

  const [orgTexts, setOrgTexts] = useState({
    who: 'Reduciendo Daño es una ONG chilena dedicada a la reduccion de riesgos y danos asociados al consumo de sustancias en contextos de ocio y alta exigencia.',
    goal: 'Proveer un espacio de analisis quimico gratuito, orientacion objetiva, hidratacion y contencion psicologica para cuidar a los asistentes.'
  });

  const svgRef = useRef<SVGSVGElement>(null);
  const selectedElement = elements.find(e => e.id === selectedId);
  const proposal = PRESET_CONFIGS[preset];

  const applyPreset = (p: Preset) => {
    setPreset(p);
    setElements(buildElements(p));
    setSelectedId(null);
    setCheckedItems([]);
  };

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

  const toggleVisible = (id: string) =>
    setElements(els => els.map(el => el.id === id ? { ...el, visible: !el.visible } : el));

  const removeElement = (id: string) => {
    setElements(els => els.filter(el => el.id !== id));
    if (selectedId === id) setSelectedId(null);
  };

  const addElement = (zoneType: string) => {
    const id = `zone-${Date.now()}`;
    const newEl: Element = {
      id,
      type: 'rect',
      x: 150 + Math.random() * 100,
      y: 150 + Math.random() * 100,
      w: 160,
      h: 100,
      label: ZONE_LABELS[zoneType] || zoneType,
      color: ZONE_COLORS[zoneType] || '#555',
      visible: true
    };
    setElements(prev => [...prev, newEl]);
    setSelectedId(id);
  };

  const addSymbol = (st: 'power' | 'heating' | 'rack' | 'extinguisher' | 'water') => {
    const id = `symbol-${Date.now()}`;
    const newEl: Element = {
      id,
      type: 'symbol',
      symbolKey: st,
      x: 200 + Math.random() * 100,
      y: 200 + Math.random() * 100,
      w: 40,
      h: 40,
      label: ZONE_LABELS[st] || st,
      color: ZONE_COLORS[st] || '#555',
      visible: true
    };
    setElements(prev => [...prev, newEl]);
    setSelectedId(id);
  };

  const duplicateSelected = () => {
    if (!selectedElement) return;
    const dup: Element = { ...selectedElement, id: `${selectedElement.id}-copy-${Date.now()}`, x: selectedElement.x + 20, y: selectedElement.y + 20 };
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
        x.id === id ? { ...x, x: Math.round((startX + (mp.x - start.x)) / 10) * 10, y: Math.round((startY + (mp.y - start.y)) / 10) * 10 } : x
      ));
    };
    const up = () => {
      window.removeEventListener('mousemove', move);
      window.removeEventListener('mouseup', up);
    };
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
  }, [elements]);

  // ─── Render Symbol (Procedural SVG without Emojis) ───
  const renderSymbol = (el: Element, isPrint = false) => {
    const isSelected = el.id === selectedId;
    const zoneColors: Record<string, string> = {
      testeo: '#f59e0b',
      contencion: '#7c3aed',
      power: '#f59e0b',
      heating: '#ef4444',
      rack: '#4b5563',
      extinguisher: '#dc2626',
      water: '#2563eb'
    };
    const fill = isPrint ? '#000000' : (el.symbolKey ? (zoneColors[el.symbolKey] || el.color) : el.color);

    return (
      <g
        key={el.id}
        transform={`translate(${el.x},${el.y})`}
        onMouseDown={(e) => onMouseDown(e, el.id)}
        className="cursor-move"
        opacity={el.visible ? 1 : 0.2}
      >
        <rect width={el.w} height={el.h} fill="transparent" stroke={isSelected ? '#fff' : 'none'} strokeWidth={2} />
        {el.symbolKey === 'power' && (
          <g stroke={fill} strokeWidth="2" fill="none">
            <circle cx="20" cy="20" r="12" />
            <path d="M20 10 L16 20 H24 L20 30" stroke={fill} strokeWidth="2.5" />
          </g>
        )}
        {el.symbolKey === 'heating' && (
          <g stroke={fill} strokeWidth="2" fill="none">
             <rect x="8" y="10" width="24" height="20" rx="2" />
             <path d="M14 14 V26 M20 14 V26 M26 14 V26" />
          </g>
        )}
        {el.symbolKey === 'rack' && (
           <g stroke={fill} strokeWidth="2" fill="none">
              <rect x="5" y="5" width="30" height="30" />
              <path d="M5 15 H35 M5 25 H35 M15 5 V35 M25 5 V35" strokeOpacity="0.3" />
           </g>
        )}
        {el.symbolKey === 'extinguisher' && (
           <g fill={fill}>
              <rect x="15" y="12" width="10" height="25" rx="2" />
              <path d="M17 12 V8 H23 V12 M23 15 H28" stroke={fill} fill="none" strokeWidth="2" />
           </g>
        )}
        {el.symbolKey === 'water' && (
           <g stroke={fill} strokeWidth="2" fill="none">
              <circle cx="20" cy="20" r="12" />
              <path d="M20 15 Q25 25 20 30 Q15 25 20 15" fill={fill} />
           </g>
        )}
        {['testeo', 'contencion'].includes(el.symbolKey || '') && (
          <g>
            <circle cx={el.w / 2} cy={el.h / 2} r={el.w / 2} fill={fill} fillOpacity={0.7} stroke={fill} strokeWidth={2} />
          </g>
        )}
        <text x="20" y="52" textAnchor="middle" fontSize="7" fill={fill} fontWeight="bold" fontFamily="monospace">{el.label.toUpperCase()}</text>
        {isSelected && (
          <rect x={-2} y={-2} width={el.w + 4} height={el.h + 4} rx={6} fill="none" stroke="#10b981" strokeWidth={2} strokeDasharray="4 2" />
        )}
      </g>
    );
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
      setLegendPos({ x: lx + (mp.x - start.x), y: ly + (mp.y - start.y) });
    };
    const up = () => {
      window.removeEventListener('mousemove', move);
      window.removeEventListener('mouseup', up);
    };
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
    e.stopPropagation();
  };

  const printRider = () => window.print();

  const toggleCheck = (item: string) => {
    setCheckedItems(prev =>
      prev.includes(item) ? prev.filter(x => x !== item) : [...prev, item]
    );
  };

  const checkAll = () => {
    const all = CHECKLIST_SECTIONS.flatMap(s => s.items).map(i => i.text);
    setCheckedItems(prev => prev.length === all.length ? [] : all);
  };

  // ─── Export Checklist as Markdown ───
  const exportChecklistMarkdown = () => {
    let md = `# RIDER TÉCNICO RD - CHECKLIST\n\n`;
    md += `**Evento:** ${eventName}\n`;
    md += `**Fecha:** ${eventDate}\n`;
    md += `**Lugar:** ${eventVenue}\n`;
    md += `**Preset Comercial:** ${preset}\n\n`;
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

  const loadFromBackend = async (presetId: Preset = preset) => {
    if (window.location.protocol === 'file:') {
      setBackendStatus(`Modo de emulacion local con preset ${presetId}. Abre via py -m flujo app para usar APIs.`);
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
            preset: presetId.toLowerCase(),
            ubicacion: eventVenue || 'Por definir'
          },
        }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      const zones = Array.isArray(data?.layout?.zones) ? data.layout.zones : [];
      const mapped: Element[] = zones.map((zone: any, index: number) => {
        const isSymbol = ['testeo', 'contencion', 'power', 'heating', 'extinguisher', 'water'].includes(zone.type);
        return {
          id: `api-${index}-${zone.type}`,
          type: isSymbol ? 'symbol' : 'rect',
          symbolKey: isSymbol ? zone.type : undefined,
          x: Number(zone.x) || 80,
          y: Number(zone.y) || 80,
          w: Number(zone.w) || 140,
          h: Number(zone.h) || 80,
          label: String(zone.label || ZONE_LABELS[zone.type] || zone.type),
          color: ZONE_COLORS[zone.type] || '#555',
          visible: true,
        };
      });
      if (mapped.length) {
        setElements(mapped);
        setSelectedId(mapped[0].id);
      }
      setBackendStatus(`Motor Python OK con preset ${presetId}: ${mapped.length} elementos cargados.`);
    } catch (error) {
      setBackendStatus(`No se pudo usar /api/plano/render: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  const totalChecks = CHECKLIST_SECTIONS.flatMap(s => s.items).length;
  const completedChecks = checkedItems.length;

  const NAV_TABS: { key: Page; label: string }[] = [
    { key: 'req', label: '☑ Checklist' },
    { key: 'map', label: '🗺 Mapa' },
    { key: 'config', label: '⚙ Config' },
  ];

  return (
    <div className="space-y-5 selection:bg-emerald-500/30">
      {/* ── Print-only rider (Designed for paper and PDF) ── */}
      <div className="hidden print:block text-black bg-white p-8 font-sans text-xs">
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
                    const isChecked = checkedItems.includes(item.text);
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
            <svg viewBox="0 0 800 550" className="w-full max-w-[650px] aspect-[1.45/1]">
              <rect width="100%" height="100%" fill="#fafafa" stroke="#ccc" />
              <rect x={20} y={20} width={760} height={510} fill="none" stroke="#666" strokeWidth={1} strokeDasharray="4 2" />
              {elements.filter(e => e.visible).map(el => {
                if (el.type === 'symbol') return renderSymbol(el, true);
                return (
                  <g key={el.id}>
                    <rect x={el.x} y={el.y} width={el.w} height={el.h} rx={4} fill="none" stroke="#000" strokeWidth={1.5} />
                    <text x={el.x + el.w/2} y={el.y + el.h/2} textAnchor="middle" dominantBaseline="central" fontSize={9} fontWeight="bold">{el.label.toUpperCase()}</text>
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

      {/* ── Screen UI (Dark and Techno-Elegant) ── */}
      <div className="print:hidden space-y-4">
        {/* Header */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="flex items-center gap-2 text-2xl font-black">
              <Map className="h-6 w-6" /> Plano / Rider
              <span className="text-xs bg-emerald-500/20 text-emerald-400 font-black px-2.5 py-0.5 rounded-full uppercase tracking-wider">v0.43.3</span>
            </h1>
            <p className="mt-1 text-sm text-zinc-500">
              Preset operativo NGO RD — {proposal.desc}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => loadFromBackend()}
              className="flex items-center gap-2 rounded-lg border border-emerald-800 bg-emerald-950/40 px-4 py-2 text-xs font-bold text-emerald-300 hover:bg-emerald-900/40 transition-colors"
            >
              <RefreshCw className="h-4 w-4" /> Motor Python
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
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 px-4 py-2 text-xs text-zinc-400">
            {backendStatus}
          </div>
        )}

        {/* Preset selector */}
        <div className="flex gap-2 flex-wrap bg-zinc-900/20 border border-zinc-800/80 p-3 rounded-xl items-center">
          <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 mr-2">Presets de Carga:</span>
          {(['UNDER', 'BASE', 'MAINSTREAM'] as Preset[]).map(p => (
            <button
              key={p}
              onClick={() => applyPreset(p)}
              className={cn(
                'rounded-lg border px-4 py-2 text-xs font-bold uppercase tracking-widest transition-colors',
                preset === p
                  ? 'border-emerald-500 bg-emerald-950/60 text-emerald-300'
                  : 'border-zinc-700 bg-zinc-900 text-zinc-400 hover:border-zinc-600 hover:text-zinc-200'
              )}
            >
              {p}
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
        <div className="flex gap-1 border-b border-zinc-800 pb-0">
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
          <div className="space-y-4">
            {/* Antecedentes Card */}
            <div className="p-6 rounded-xl border border-zinc-800 bg-zinc-900/30">
              <h3 className="text-sm font-black uppercase text-zinc-400 tracking-wider mb-4">Antecedentes del Evento</h3>
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
              onClick={() => setPage('map')}
              className="w-full py-5 bg-emerald-500 hover:bg-emerald-400 text-black font-black rounded-3xl shadow-xl shadow-emerald-500/10 transition-transform active:scale-[0.98] flex items-center justify-center gap-3 text-base"
            >
              Ir al Plano de Distribución
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        )}

        {/* ── Map tab ── */}
        {page === 'map' && (
          <div className="grid grid-cols-4 gap-6">
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
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono text-zinc-600 mr-2">{Math.round(zoom * 100)}%</span>
                  <button onClick={exportSVG} className="flex items-center gap-1.5 p-2 bg-zinc-900 border border-zinc-800 rounded-lg text-xs font-bold hover:bg-zinc-800 text-zinc-400 hover:text-white"><Download className="w-3.5 h-3.5"/> SVG</button>
                </div>
              </div>

              {/* SVG Canvas wrapper */}
              <div className="rounded-2xl border border-zinc-800 bg-zinc-950 overflow-hidden relative" style={{ height: "560px" }}>
                <div className="w-full h-full overflow-auto flex items-center justify-center p-4">
                  <div className="relative bg-white shadow-2xl transition-all" style={{ width: 800, height: 550, transform: `scale(${zoom})`, transformOrigin: "center" }}>
                    <svg
                      ref={svgRef}
                      viewBox="0 0 800 550"
                      className="w-full h-full"
                      onClick={() => setSelectedId(null)}
                    >
                      {/* Grid pattern */}
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
                      <rect x="20" y="20" width="760" height="510" fill="none" stroke="#3f3f46" strokeWidth={1} strokeDasharray="6 4" rx={4} />

                      {/* Elements */}
                      {elements.filter(el => el.visible).map(el => {
                        if (el.type === 'symbol') return renderSymbol(el);
                        const isSelected = el.id === selectedId;
                        const common = { 
                          onMouseDown: (e: any) => onMouseDown(e, el.id), 
                          className: cn("cursor-move transition-all", isSelected && "stroke-white stroke-2") 
                        };
                        return (
                          <g key={el.id} onClick={(e) => { e.stopPropagation(); selectElementAndBringToFront(el.id); }}>
                            <rect
                              x={el.x}
                              y={el.y}
                              width={el.w}
                              height={el.h}
                              rx={12}
                              fill={el.color}
                              fillOpacity={0.7}
                              stroke={isSelected ? '#ffffff' : el.color}
                              strokeWidth={isSelected ? 2.5 : 1.5}
                              {...common}
                            />
                            <text
                              x={el.x + el.w / 2}
                              y={el.y + el.h / 2}
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
                              x={el.x + el.w / 2}
                              y={el.y + el.h / 2 + 16}
                              textAnchor="middle"
                              dominantBaseline="central"
                              fill="#ffffff80"
                              fontSize={8}
                              fontFamily="monospace"
                              style={{ pointerEvents: 'none' }}
                            >
                              {el.w}×{el.h}
                            </text>
                          </g>
                        );
                      })}

                      {/* Draggable Legend */}
                      {showLegend && (
                        <g
                          transform={`translate(${legendPos.x},${legendPos.y})`}
                          onMouseDown={onLegendMouseDown}
                          className="cursor-grab"
                        >
                          <rect width={150} height={140} rx={12} fill="#18181bcc" stroke="#3f3f46" strokeWidth={1} />
                          <text x={75} y={20} textAnchor="middle" fontSize={9} fill="#a1a1aa" fontWeight="bold">
                            LEYENDA TÉCNICA
                          </text>
                          {['testeo', 'contencion', 'power', 'extinguisher'].map((k, i) => {
                            const colors: Record<string, string> = { testeo: '#2d5a4a', contencion: '#7c3aed', power: '#f59e0b', extinguisher: '#dc2626' };
                            const fill = colors[k] || '#6366f1';
                            return (
                              <g key={k} transform={`translate(12,${35 + i * 22})`}>
                                {['power', 'extinguisher'].includes(k) ? (
                                  <rect width={12} height={12} rx={2.5} fill={fill} fillOpacity={0.6} stroke={fill} strokeWidth={1} />
                                ) : (
                                  <circle cx={6} cy={6} r={6} fill={fill} fillOpacity={0.6} stroke={fill} strokeWidth={1} />
                                )}
                                <text x={20} y={9} fontSize={8.5} fill="#a1a1aa" fontWeight="bold" fontFamily="sans-serif">{ZONE_LABELS[k]}</text>
                              </g>
                            );
                          })}
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

            {/* Sidebar Controls */}
            <aside className="space-y-4">
              {/* Elements List */}
              <div className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-xl space-y-3">
                <h4 className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">Zonas de Montaje</h4>
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
                <h4 className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 mb-3">Símbolos Técnicos</h4>
                <div className="grid grid-cols-3 gap-2">
                  {(['power','heating','rack','extinguisher','water'] as const).map(s => (
                    <button
                      key={s}
                      onClick={() => addSymbol(s)}
                      className="flex flex-col items-center p-3 bg-zinc-800/30 border border-zinc-800 rounded-xl hover:bg-zinc-800 group transition-all"
                    >
                      {s === 'power' && <Zap className="w-4 h-4 text-yellow-500" />}
                      {s === 'heating' && <RotateCcw className="w-4 h-4 text-red-500" />}
                      {s === 'rack' && <Box className="w-4 h-4 text-zinc-400" />}
                      {s === 'extinguisher' && <ShieldAlert className="w-4 h-4 text-red-600" />}
                      {s === 'water' && <Droplet className="w-4 h-4 text-blue-500" />}
                      <span className="mt-2 text-[7px] uppercase font-black opacity-40 group-hover:opacity-100">{s}</span>
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
                      <label className="text-[10px] text-zinc-500 block mb-1">Nombre</label>
                      <input
                        value={selectedElement.label}
                        onChange={e => setElements(prev => prev.map(el => el.id === selectedId ? { ...el, label: e.target.value } : el))}
                        className="w-full bg-black/40 border border-zinc-800 rounded px-2.5 py-1.5 text-xs focus:outline-none focus:border-zinc-600"
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
                    <button
                      key={el.id}
                      onClick={() => selectElementAndBringToFront(el.id)}
                      className={cn(
                        "w-full flex items-center gap-2 px-2 py-1.5 rounded text-left text-[10px] transition-colors",
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
                    </button>
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
                    `py -m flujo portal --repo-url https://github.com/ligereza/vibecodeine`,
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
