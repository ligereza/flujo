import React, { useState, useRef, useCallback } from 'react';
import { 
  Download, ZoomIn, ZoomOut, RotateCcw, Square, Circle, 
  Trash2, Copy, Layers, Grid3X3, Eye, EyeOff, 
  ChevronLeft, ChevronRight, Printer, FileText, 
  CheckSquare, AlertTriangle, Users, Zap, 
  Shield, Heart, Coffee, RefreshCw
} from 'lucide-react';
import { cn } from '../utils/cn';

// ─── Types ───
interface PlanoElement {
  id: string;
  type: 'rect' | 'circle' | 'text' | 'zone';
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
};

const ZONE_LABELS: Record<string, string> = {
  testeo: 'Stand de Testeo',
  contencion: 'Contención',
  informativo: 'Stand Informativo',
  descanso: 'Zona Descanso',
  coordinacion: 'Coordinación',
  circulacion: 'Circulación Público',
};

// ─── Checklist Data ───
const CHECKLIST_SECTIONS = [
  {
    title: 'Espacio',
    icon: <Grid3X3 className="w-4 h-4" />,
    items: [
      'Medidas disponibles del recinto',
      'Interior / exterior definido',
      'Superficie estable y nivelada',
      'Circulación pública segura',
    ],
  },
  {
    title: 'Infraestructura',
    icon: <Square className="w-4 h-4" />,
    items: [
      'Toldo / carpa confirmado',
      'Mesas',
      'Sillas',
      'Rack / caja almacenamiento',
      'Basureros',
      'Señalética',
    ],
  },
  {
    title: 'Condiciones',
    icon: <Zap className="w-4 h-4" />,
    items: [
      'Iluminación',
      'Punto eléctrico',
      'Calefacción si aplica',
      'Agua / hidratación si aplica',
      'Zona descanso si aplica',
    ],
  },
  {
    title: 'Coordinación',
    icon: <Users className="w-4 h-4" />,
    items: [
      'Producción',
      'Seguridad',
      'Equipo médico',
      'Alimentación si jornada > 5h',
    ],
  },
];

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
  const [page, setPage] = useState<'requirements' | 'layout'>('layout');
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
    setSelectedId(id);
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

  const deleteSelected = () => {
    if (!selectedId) return;
    setElements(prev => prev.filter(e => e.id !== selectedId));
    setSelectedId(null);
  };

  const duplicateSelected = () => {
    if (!selectedElement) return;
    const dup = { ...selectedElement, id: `${selectedElement.id}-copy-${Date.now()}`, x: selectedElement.x + 20, y: selectedElement.y + 20 };
    setElements(prev => [...prev, dup]);
    setSelectedId(dup.id);
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-bold">Rider RD · Herramienta de Plano</h3>
          <p className="text-zinc-400 text-sm mt-1">
            Documento operativo para intervención en terreno — Reduciendo Daño Chile
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPage('requirements')}
            className={cn(
              "px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2",
              page === 'requirements' ? "bg-white text-black" : "bg-zinc-900 border border-zinc-800 text-zinc-300 hover:bg-zinc-800"
            )}
          >
            <FileText className="w-4 h-4" />
            Requerimientos
          </button>
          <button
            onClick={() => setPage('layout')}
            className={cn(
              "px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2",
              page === 'layout' ? "bg-white text-black" : "bg-zinc-900 border border-zinc-800 text-zinc-300 hover:bg-zinc-800"
            )}
          >
            <Layers className="w-4 h-4" />
            Plano Layout
          </button>
          <button
            onClick={() => loadFromBackend()}
            className="px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 bg-emerald-900/30 border border-emerald-800/60 text-emerald-200 hover:bg-emerald-800/40"
          >
            <RefreshCw className="w-4 h-4" />
            Motor Python
          </button>
        </div>
      </div>
      {backendStatus && (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 px-4 py-2 text-xs text-zinc-400">
          {backendStatus}
        </div>
      )}

      {/* ═══ PAGE 1: REQUIREMENTS ═══ */}
      {page === 'requirements' && (
        <div className="grid grid-cols-3 gap-6">
          {/* Left: Event Info */}
          <div className="col-span-2 space-y-6">
            {/* Event header card */}
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

            {/* Modalidades */}
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

            {/* Requerimientos detailed */}
            <div className="p-6 bg-zinc-900/50 border border-zinc-800 rounded-xl space-y-6">
              <h4 className="text-sm font-bold uppercase tracking-widest text-zinc-400">Requerimientos Operativos</h4>

              <div className="grid grid-cols-2 gap-6">
                <ReqSection icon={<Grid3X3 className="w-4 h-4" />} title="Espacio" items={[
                  'Medidas disponibles del recinto (int/ext)',
                  'Tipo de terreno (nivelado, estable)',
                  'Circulación pública segura',
                  'Zona con menor estimulación sensorial para descanso',
                ]} />
                <ReqSection icon={<Square className="w-4 h-4" />} title="Infraestructura" items={[
                  'Toldo/carpa (mínimo 3×3m)',
                  'Mesas (2-3 según modalidad)',
                  'Sillas (4-6 por stand)',
                  'Rack o caja de almacenamiento',
                  'Basureros, señalética',
                ]} />
                <ReqSection icon={<Zap className="w-4 h-4" />} title="Servicios" items={[
                  'Punto eléctrico disponible',
                  'Iluminación adecuada',
                  'Agua/hidratación si aplica',
                  'Calefacción si exterior nocturno',
                ]} />
                <ReqSection icon={<Users className="w-4 h-4" />} title="Coordinación" items={[
                  'Contacto directo con producción',
                  'Coordinación con seguridad privada',
                  'Acceso a equipo médico del evento',
                  'Alimentación si jornada > 5 horas',
                ]} />
              </div>
            </div>
          </div>

          {/* Right: Checklist */}
          <div className="space-y-4">
            <div className="p-5 bg-zinc-900/50 border border-zinc-800 rounded-xl sticky top-24">
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-sm font-bold uppercase tracking-widest text-zinc-400">Checklist Rider</h4>
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

              <div className="space-y-5">
                {CHECKLIST_SECTIONS.map(section => (
                  <div key={section.title}>
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-zinc-500">{section.icon}</span>
                      <span className="text-xs font-bold uppercase tracking-wider text-zinc-400">{section.title}</span>
                    </div>
                    <div className="space-y-1.5">
                      {section.items.map(item => (
                        <button
                          key={item}
                          onClick={() => toggleCheck(`${section.title}-${item}`)}
                          className="w-full flex items-center gap-2.5 text-left group"
                        >
                          <div className={cn(
                            "w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 transition-colors",
                            checkedItems.has(`${section.title}-${item}`)
                              ? "bg-green-600 border-green-600"
                              : "border-zinc-700 group-hover:border-zinc-500"
                          )}>
                            {checkedItems.has(`${section.title}-${item}`) && (
                              <CheckSquare className="w-3 h-3 text-white" />
                            )}
                          </div>
                          <span className={cn(
                            "text-xs transition-colors",
                            checkedItems.has(`${section.title}-${item}`)
                              ? "text-zinc-500 line-through"
                              : "text-zinc-300 group-hover:text-white"
                          )}>
                            {item}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <button
              onClick={() => setPage('layout')}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-white text-black rounded-lg text-sm font-bold hover:bg-zinc-200 transition-colors"
            >
              Ir al Plano
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* ═══ PAGE 2: LAYOUT / PLANO ═══ */}
      {page === 'layout' && (
        <div className="grid grid-cols-4 gap-6">
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
            <div className="bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden relative" style={{ height: 560 }}>
              <div className="w-full h-full overflow-auto">
                <svg
                  ref={svgRef}
                  viewBox="0 0 800 550"
                  className="w-full h-full"
                  style={{ transform: `scale(${zoom})`, transformOrigin: 'top left', minWidth: 800 * zoom, minHeight: 550 * zoom }}
                  onMouseMove={handleMouseMove}
                  onMouseUp={handleMouseUp}
                  onMouseLeave={handleMouseUp}
                  onClick={() => setSelectedId(null)}
                >
                  {/* Grid */}
                  {showGrid && (
                    <g opacity={0.15}>
                      {Array.from({ length: 81 }, (_, i) => (
                        <line key={`gv${i}`} x1={i * 10} y1={0} x2={i * 10} y2={550} stroke="#555" strokeWidth={i % 5 === 0 ? 0.5 : 0.2} />
                      ))}
                      {Array.from({ length: 56 }, (_, i) => (
                        <line key={`gh${i}`} x1={0} y1={i * 10} x2={800} y2={i * 10} stroke="#555" strokeWidth={i % 5 === 0 ? 0.5 : 0.2} />
                      ))}
                    </g>
                  )}

                  {/* Boundary frame */}
                  <rect x={20} y={20} width={760} height={510} fill="none" stroke="#333" strokeWidth={1} strokeDasharray="6 3" rx={4} />
                  <text x={30} y={16} fill="#555" fontSize={9} fontFamily="Inter, sans-serif">A4 Horizontal — 29.7 × 21 cm</text>

                  {/* Elements */}
                  {elements.filter(e => e.visible).map(el => (
                    <g
                      key={el.id}
                      onMouseDown={e => handleMouseDown(e, el.id)}
                      style={{ cursor: el.locked ? 'default' : 'move' }}
                      onClick={e => { e.stopPropagation(); setSelectedId(el.id); }}
                    >
                      <rect
                        x={el.x}
                        y={el.y}
                        width={el.width}
                        height={el.height}
                        rx={4}
                        fill={el.color + '30'}
                        stroke={selectedId === el.id ? '#fff' : el.color}
                        strokeWidth={selectedId === el.id ? 2 : 1}
                        strokeDasharray={el.zoneType === 'circulacion' ? '6 3' : undefined}
                      />
                      <text
                        x={el.x + el.width / 2}
                        y={el.y + el.height / 2}
                        textAnchor="middle"
                        dominantBaseline="central"
                        fill={el.color}
                        fontSize={11}
                        fontFamily="Inter, sans-serif"
                        fontWeight={600}
                        style={{ pointerEvents: 'none' }}
                      >
                        {el.label}
                      </text>
                      {/* Dimensions */}
                      <text
                        x={el.x + el.width / 2}
                        y={el.y + el.height / 2 + 16}
                        textAnchor="middle"
                        dominantBaseline="central"
                        fill="#666"
                        fontSize={8}
                        fontFamily="monospace"
                        style={{ pointerEvents: 'none' }}
                      >
                        {el.width}×{el.height}
                      </text>
                    </g>
                  ))}

                  {/* Legend */}
                  {showLegend && (
                    <g transform="translate(600, 35)">
                      <rect x={0} y={0} width={170} height={140} rx={4} fill="#09090bcc" stroke="#333" />
                      <text x={12} y={20} fill="#aaa" fontSize={9} fontWeight={700} fontFamily="Inter, sans-serif">LEYENDA</text>
                      {Object.entries(ZONE_COLORS).map(([key, color], i) => (
                        <g key={key} transform={`translate(12, ${35 + i * 18})`}>
                          <rect x={0} y={-5} width={10} height={10} rx={2} fill={color + '50'} stroke={color} strokeWidth={1} />
                          <text x={16} y={4} fill="#bbb" fontSize={9} fontFamily="Inter, sans-serif">{ZONE_LABELS[key]}</text>
                        </g>
                      ))}
                    </g>
                  )}

                  {/* Title block */}
                  <g transform="translate(30, 490)">
                    <text fill="#888" fontSize={10} fontWeight={700} fontFamily="Inter, sans-serif">{eventName}</text>
                    <text x={0} y={14} fill="#555" fontSize={8} fontFamily="Inter, sans-serif">{eventVenue} · {eventDate}</text>
                    <text x={700} y={0} textAnchor="end" fill="#444" fontSize={7} fontFamily="monospace">Reduciendo Daño Chile · Rider Operativo</text>
                  </g>
                </svg>
              </div>
            </div>
          </div>

          {/* Right panel */}
          <div className="space-y-4">
            {/* Add zones */}
            <div className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-xl">
              <h4 className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 mb-3">Agregar Zona</h4>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(ZONE_LABELS).map(([key, label]) => (
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
              <div className="mt-3 grid grid-cols-2 gap-2">
                <button
                  onClick={() => {
                    const id = `furniture-${Date.now()}`;
                    setElements(prev => [...prev, {
                      id, type: 'rect', x: 300, y: 250, width: 60, height: 30,
                      label: 'Mesa', color: '#888', rotation: 0, locked: false, visible: true,
                    }]);
                    setSelectedId(id);
                  }}
                  className="flex items-center gap-2 px-2.5 py-2 bg-zinc-800/50 border border-zinc-800 rounded-lg text-[10px] font-medium hover:bg-zinc-800 transition-colors"
                >
                  <Square className="w-3 h-3 text-zinc-500" /> Mesa
                </button>
                <button
                  onClick={() => {
                    const id = `furniture-${Date.now()}`;
                    setElements(prev => [...prev, {
                      id, type: 'rect', x: 300, y: 300, width: 30, height: 30,
                      label: 'Silla', color: '#666', rotation: 0, locked: false, visible: true,
                    }]);
                    setSelectedId(id);
                  }}
                  className="flex items-center gap-2 px-2.5 py-2 bg-zinc-800/50 border border-zinc-800 rounded-lg text-[10px] font-medium hover:bg-zinc-800 transition-colors"
                >
                  <Circle className="w-3 h-3 text-zinc-500" /> Silla
                </button>
              </div>
            </div>

            {/* Selected element properties */}
            {selectedElement && (
              <div className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-xl">
                <h4 className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 mb-3">Propiedades</h4>
                <div className="space-y-3">
                  <div>
                    <label className="text-[10px] text-zinc-500 block mb-1">Etiqueta</label>
                    <input
                      value={selectedElement.label}
                      onChange={e => setElements(prev => prev.map(el => el.id === selectedId ? { ...el, label: e.target.value } : el))}
                      className="w-full bg-black/30 border border-zinc-700 rounded px-2 py-1 text-xs focus:outline-none focus:border-zinc-500"
                    />
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
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-[10px] text-zinc-500 block mb-1">X</label>
                      <input
                        type="number"
                        value={selectedElement.x}
                        onChange={e => setElements(prev => prev.map(el => el.id === selectedId ? { ...el, x: Number(e.target.value) } : el))}
                        className="w-full bg-black/30 border border-zinc-700 rounded px-2 py-1 text-xs font-mono focus:outline-none focus:border-zinc-500"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-zinc-500 block mb-1">Y</label>
                      <input
                        type="number"
                        value={selectedElement.y}
                        onChange={e => setElements(prev => prev.map(el => el.id === selectedId ? { ...el, y: Number(e.target.value) } : el))}
                        className="w-full bg-black/30 border border-zinc-700 rounded px-2 py-1 text-xs font-mono focus:outline-none focus:border-zinc-500"
                      />
                    </div>
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
                {elements.map(el => (
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
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-lg text-xs font-medium hover:bg-zinc-800 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
              Volver a Requerimientos
            </button>
          </div>
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
      <h5 className="text-sm font-bold mb-1.5">{title}</h5>
      <p className="text-[11px] text-zinc-500 leading-relaxed">{description}</p>
    </div>
  );
}

function ReqSection({ icon, title, items }: { icon: React.ReactNode; title: string; items: string[] }) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <span style={{ color: RD_PALETTE.accent }}>{icon}</span>
        <span className="text-xs font-bold uppercase tracking-wider">{title}</span>
      </div>
      <ul className="space-y-1.5">
        {items.map((item, i) => (
          <li key={i} className="flex items-start gap-2 text-xs text-zinc-400">
            <span className="text-zinc-600 mt-0.5">›</span>
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
