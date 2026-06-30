import { useState, useMemo, useRef, useCallback, useEffect } from 'react';
import {
  Search, X, Grid3x3, List, Eye, Download, ZoomIn, ZoomOut,
  ChevronLeft, ChevronRight, Code2, Palette, Layers, Ruler,
  Upload, Clipboard, RotateCcw, Maximize2, Sun, Moon,
  FileCode, Copy, Check, ScanLine, Type, Box,
  Circle, Minus, Image, Shapes, FileJson,
  Plus, Square, Trash2, EyeOff, ChevronDown, Settings,
  MoveVertical, MoveHorizontal,
  AlignStartVertical, AlignEndVertical, AlignCenterVertical,
  AlignStartHorizontal, AlignEndHorizontal, AlignCenterHorizontal,
  AlignLeft,
} from 'lucide-react';
import {
  MOCK_SVG_INDEX, loadFromApi, TYPE_OPTIONS,
  type SvgPiece, type PieceType, type PieceArea,
} from '../data/svgIndex';
import {
  type PieceConfig, type ConfigElement, type TextElement,
  type ParagraphElement, type ListElement, type RectElement,
  type CircleElement, type LineElement, type SvgImageElement, type Palette as PaletteType,
  assignIds, resolveColor, getElementBounds, DEMO_CONFIGS,
} from '../data/configTypes';

// ═══════════════════════════════════════════════
// SVG analysis utilities
// ═══════════════════════════════════════════════

const STATUS_CFG = {
  'aprobado':    { color: 'text-emerald-400', bg: 'bg-emerald-500/15 border-emerald-500/30', dot: 'bg-emerald-400' },
  'en-revision': { color: 'text-blue-400',    bg: 'bg-blue-500/15 border-blue-500/30',    dot: 'bg-blue-400' },
  'borrador':    { color: 'text-amber-400',   bg: 'bg-amber-500/15 border-amber-500/30',  dot: 'bg-amber-400' },
} as const;

function extractColors(svg: string): string[] {
  const s = new Set<string>();
  (svg.match(/#[0-9a-fA-F]{3,8}/g) || []).forEach(c => {
    const n = c.length === 4 ? `#${c[1]}${c[1]}${c[2]}${c[2]}${c[3]}${c[3]}` : c.toLowerCase();
    if (n !== '#000000' && n !== '#ffffff' && n.length <= 7) s.add(n);
  });
  return Array.from(s).slice(0, 12);
}

function svgStructure(svg: string) {
  const t: Record<string, number> = {};
  (svg.match(/<(\w+)[\s>]/g) || []).forEach(m => {
    const tag = m.replace(/</, '').replace(/[\s>]/, '');
    if (!['svg','defs','linearGradient','radialGradient','stop','g'].includes(tag)) t[tag] = (t[tag]||0)+1;
  });
  const iconMap: Record<string,typeof Box> = { rect:Box,circle:Circle,text:Type,line:Minus,path:ScanLine,ellipse:Circle,polygon:Box,image:Image };
  return Object.entries(t).sort((a,b)=>b[1]-a[1]).map(([tag,count])=>({tag,count,icon:iconMap[tag]||Box}));
}

function svgDims(svg: string) {
  const m = svg.match(/viewBox="([^"]+)"/);
  if (m) { const p = m[1].split(/[\s,]+/).map(Number); if (p.length===4) return {width:p[2],height:p[3]}; }
  return null;
}
function svgSize(svg: string) { const b = new Blob([svg]).size; return b < 1024 ? `${b} B` : `${(b/1024).toFixed(1)} KB`; }

// ═══════════════════════════════════════════════
// Config.json → SVG renderer
// ═══════════════════════════════════════════════

function renderCfgEl(el: ConfigElement, pal: PaletteType, isSel: boolean, onSelect: () => void) {
  const rc = (k?: string) => k ? resolveColor(k, pal) : 'none';
  const ss = isSel ? '#3b82f6' : undefined;
  const sw = isSel ? 3 : undefined;

  switch (el.type) {
    case 'rect': case 'panel': {
      const e = el as RectElement;
      return (
        <g key={e._id} onClick={ev => { ev.stopPropagation(); onSelect(); }} className="cursor-pointer">
          <rect x={e.x} y={e.y} width={e.w} height={e.h} rx={e.radius||0}
            fill={e.fill==='none'?'none':rc(e.fill)} stroke={ss||(e.stroke?rc(e.stroke):'none')}
            strokeWidth={sw||e.stroke_width||0} opacity={e.opacity??1} />
          {isSel && <rect x={e.x-2} y={e.y-2} width={e.w+4} height={e.h+4} rx={(e.radius||0)+2}
            fill="none" stroke="#3b82f6" strokeWidth={2} strokeDasharray="8 4" />}
        </g>
      );
    }
    case 'circle': {
      const e = el as CircleElement;
      return <g key={e._id} onClick={ev=>{ev.stopPropagation();onSelect();}} className="cursor-pointer">
        <circle cx={e.cx} cy={e.cy} r={e.r} fill={rc(e.fill)} opacity={e.opacity??1}
          stroke={ss||(e.stroke?rc(e.stroke):'none')} strokeWidth={sw||e.stroke_width||0} />
      </g>;
    }
    case 'line': {
      const e = el as LineElement;
      return <g key={e._id} onClick={ev=>{ev.stopPropagation();onSelect();}} className="cursor-pointer">
        <line x1={e.x1} y1={e.y1} x2={e.x2} y2={e.y2} stroke={ss||rc(e.stroke)} strokeWidth={sw||e.stroke_width||1} />
      </g>;
    }
    case 'svg_image': {
      const e = el as SvgImageElement;
      const href = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(e.content)}`;
      return <g key={e._id} onClick={ev=>{ev.stopPropagation();onSelect();}} className="cursor-pointer">
        <image href={href} x={e.x} y={e.y} width={e.w} height={e.h} preserveAspectRatio="xMidYMid meet" />
        {isSel && <rect x={e.x-4} y={e.y-4} width={e.w+8} height={e.h+8} fill="none" stroke="#3b82f6" strokeWidth={2} strokeDasharray="8 4"/>}
      </g>;
    }
    case 'text': {
      const e = el as TextElement;
      return <g key={e._id} onClick={ev=>{ev.stopPropagation();onSelect();}} className="cursor-pointer">
        <text x={e.x} y={e.y} fontSize={e.size} fontWeight={e.weight||'normal'}
          fill={rc(e.fill)} fontFamily="Inter, system-ui, sans-serif">{e.content}</text>
        {isSel && (()=>{const b=getElementBounds(e);return<rect x={b.x-4} y={b.y-4} width={b.w+8} height={b.h+8}
          fill="none" stroke="#3b82f6" strokeWidth={2} strokeDasharray="6 3"/>;})()}
      </g>;
    }
    case 'paragraph': {
      const e = el as ParagraphElement;
      const wrapped: string[] = [];
      for (const ln of e.content.split('\n')) {
        let cur = '';
        const cw = e.size*0.52, mc = Math.floor(e.max_width/cw);
        for (const w of ln.split(' ')) {
          if ((cur+' '+w).trim().length > mc && cur) { wrapped.push(cur); cur = w; }
          else cur = cur ? cur+' '+w : w;
        }
        if (cur) wrapped.push(cur);
      }
      return <g key={e._id} onClick={ev=>{ev.stopPropagation();onSelect();}} className="cursor-pointer">
        {wrapped.map((l,i)=><text key={i} x={e.x} y={e.y+i*e.line_height}
          fontSize={e.size} fill={rc(e.fill)} fontFamily="Inter, system-ui, sans-serif">{l}</text>)}
        {isSel && <rect x={e.x-4} y={e.y-e.size-4} width={e.max_width+8}
          height={wrapped.length*e.line_height+8} fill="none" stroke="#3b82f6" strokeWidth={2} strokeDasharray="6 3"/>}
      </g>;
    }
    case 'list': {
      const e = el as ListElement;
      return <g key={e._id} onClick={ev=>{ev.stopPropagation();onSelect();}} className="cursor-pointer">
        {e.items.map((item,i)=><g key={i}>
          <text x={e.x} y={e.y+i*(e.line_height+e.gap)} fontSize={e.size} fill={rc(e.fill)} fontFamily="Inter, system-ui, sans-serif">•</text>
          <text x={e.x+e.indent} y={e.y+i*(e.line_height+e.gap)} fontSize={e.size} fill={rc(e.fill)} fontFamily="Inter, system-ui, sans-serif">{item}</text>
        </g>)}
        {isSel && <rect x={e.x-4} y={e.y-e.size-4} width={e.max_width+8}
          height={e.items.length*(e.line_height+e.gap)+8} fill="none" stroke="#3b82f6" strokeWidth={2} strokeDasharray="6 3"/>}
      </g>;
    }
  }
}

// ═══════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════

type TopTab = 'gallery' | 'editor';

export default function SvgVisualizer() {
  const [topTab, setTopTab] = useState<TopTab>('gallery');
  const [pieceForEditor, setPieceForEditor] = useState<SvgPiece | null>(null);

  const configurePiece = useCallback((piece: SvgPiece) => {
    setPieceForEditor(piece);
    setTopTab('editor');
  }, []);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 shadow-lg shadow-violet-500/20">
            <Shapes className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tight">SVG Studio</h1>
            <p className="text-xs text-zinc-500">Galería de piezas + editor de config.json</p>
          </div>
        </div>
        {/* Top tab toggle */}
        <div className="flex rounded-lg border border-zinc-800 bg-zinc-900/60 p-0.5">
          <button onClick={() => setTopTab('gallery')}
            className={`flex items-center gap-1.5 rounded-md px-4 py-2 text-xs font-bold transition-colors ${topTab==='gallery' ? 'bg-zinc-700 text-white' : 'text-zinc-500 hover:text-zinc-300'}`}>
            <Shapes className="h-3.5 w-3.5" /> Galería SVG
          </button>
          <button onClick={() => setTopTab('editor')}
            className={`flex items-center gap-1.5 rounded-md px-4 py-2 text-xs font-bold transition-colors ${topTab==='editor' ? 'bg-zinc-700 text-white' : 'text-zinc-500 hover:text-zinc-300'}`}>
            <FileJson className="h-3.5 w-3.5" /> Config Editor
          </button>
        </div>
      </div>

      {topTab === 'gallery' && <GalleryView onConfigure={configurePiece} />}
      {topTab === 'editor' && <EditorView pieceToLoad={pieceForEditor} />}
    </div>
  );
}

// ═══════════════════════════════════════════════
// GALLERY VIEW
// ═══════════════════════════════════════════════

function GalleryView({ onConfigure }: { onConfigure: (piece: SvgPiece) => void }) {
  const [pieces, setPieces] = useState<SvgPiece[]>(MOCK_SVG_INDEX);
  const [sourceStatus, setSourceStatus] = useState('Demo local');
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState<PieceType|'all'>('all');
  const [filterArea, setFilterArea] = useState<PieceArea|'all'>('all');
  const [filterStatus, setFilterStatus] = useState<SvgPiece['status']|'all'>('all');
  const [viewMode, setViewMode] = useState<'grid'|'list'>('grid');
  const [selectedPiece, setSelectedPiece] = useState<SvgPiece|null>(null);
  const [modalZoom, setModalZoom] = useState(1);
  const [modalTab, setModalTab] = useState<'preview'|'code'|'inspect'|'colors'>('preview');
  const [previewBg, setPreviewBg] = useState<'dark'|'light'|'checker'>('dark');
  const [codeCopied, setCodeCopied] = useState(false);
  const [showCustom, setShowCustom] = useState(false);
  const [customSvg, setCustomSvg] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);
  const folderRef = useRef<HTMLInputElement>(null);

  const refreshRepoSvgs = useCallback(async () => {
    if (typeof window !== 'undefined' && window.location.protocol === 'file:') {
      setPieces(MOCK_SVG_INDEX);
      setSourceStatus('Demo local: abre con py -m flujo app para escanear svg/');
      return;
    }
    setSourceStatus('Actualizando svg/…');
    try {
      const d = await loadFromApi();
      setPieces(d.length ? d : MOCK_SVG_INDEX);
      setSourceStatus(d.length ? `${d.length} SVGs desde repo` : 'Fallback demo');
    } catch (error) {
      setPieces(MOCK_SVG_INDEX);
      setSourceStatus(`Fallback demo (${error instanceof Error ? error.message : 'sin API'})`);
    }
  }, []);

  const loadLocalSvgFiles = useCallback(async (files: FileList | null) => {
    const list = Array.from(files || []).filter(file => file.name.toLowerCase().endsWith('.svg'));
    if (!list.length) return;
    const loaded = await Promise.all(list.map(async (file) => {
      const svgContent = await file.text();
      const dims = svgDims(svgContent);
      const relativePath = (file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name;
      return {
        id: `local_${relativePath.replace(/[^a-z0-9]+/gi, '_').toLowerCase()}`,
        name: file.name,
        type: relativePath.toLowerCase().includes('pendon') ? 'pendon' : relativePath.toLowerCase().includes('sticker') ? 'sticker' : relativePath.toLowerCase().includes('logo') ? 'logo' : relativePath.toLowerCase().includes('post') ? 'post-ig' : relativePath.toLowerCase().includes('flyer') ? 'flyer' : 'etiqueta',
        area: relativePath.toLowerCase().includes('evento') ? 'eventos' : relativePath.toLowerCase().includes('supl') ? 'suplementos' : 'comun',
        medio: 'impresion',
        herramienta: 'carpeta local',
        realSizeCm: 'local',
        canvasPx: dims ? `${dims.width}×${dims.height}` : 'SVG',
        colors: extractColors(svgContent),
        lastModified: new Date(file.lastModified || Date.now()).toISOString().slice(0, 10),
        status: 'borrador',
        svgContent,
        notes: relativePath,
      } as SvgPiece;
    }));
    setPieces(loaded);
    setSourceStatus(`${loaded.length} SVGs desde carpeta local`);
  }, []);

  useEffect(() => { refreshRepoSvgs(); }, [refreshRepoSvgs]);

  const filtered = useMemo(() => pieces.filter(p => {
    const q = search.toLowerCase();
    return (!q || p.name.toLowerCase().includes(q) || p.product?.toLowerCase().includes(q) || p.type.includes(q))
      && (filterType==='all' || p.type===filterType)
      && (filterArea==='all' || p.area===filterArea)
      && (filterStatus==='all' || p.status===filterStatus);
  }), [pieces, search, filterType, filterArea, filterStatus]);

  const stats = useMemo(() => ({
    aprobado: pieces.filter(p=>p.status==='aprobado').length,
    revision: pieces.filter(p=>p.status==='en-revision').length,
    borrador: pieces.filter(p=>p.status==='borrador').length,
  }), [pieces]);

  const currentIdx = selectedPiece ? filtered.findIndex(p=>p.id===selectedPiece.id) : -1;
  const activeFilters = [filterType!=='all',filterArea!=='all',filterStatus!=='all',search!==''].filter(Boolean).length;

  const downloadSVG = (p: SvgPiece) => {
    if (!p.svgContent) return;
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([p.svgContent],{type:'image/svg+xml'}));
    a.download = `${p.id}.svg`; a.click();
  };
  const exportPng = useCallback((p: SvgPiece, sc=2) => {
    if (!p.svgContent) return;
    const d=svgDims(p.svgContent); const w=(d?.width||400)*sc; const h=(d?.height||300)*sc;
    const c=document.createElement('canvas'); c.width=w; c.height=h;
    const ctx=c.getContext('2d'); if(!ctx) return;
    const img=new window.Image();
    const u=URL.createObjectURL(new Blob([p.svgContent],{type:'image/svg+xml;charset=utf-8'}));
    img.onload=()=>{ctx.drawImage(img,0,0,w,h);URL.revokeObjectURL(u);
      const a=document.createElement('a');a.href=c.toDataURL('image/png');a.download=`${p.id}.png`;a.click();};
    img.src=u;
  },[]);
  const copySvg = (s: string) => { navigator.clipboard?.writeText(s); setCodeCopied(true); setTimeout(()=>setCodeCopied(false),1500); };
  const configurePiece = (piece: SvgPiece) => {
    if (!piece.svgContent) return;
    onConfigure(piece);
    setSelectedPiece(null);
  };
  const goTo = (d: -1|1) => { const n=currentIdx+d; if (n>=0&&n<filtered.length){setSelectedPiece(filtered[n]);setModalZoom(1);} };
  const handleCustomPreview = () => {
    if (!customSvg.trim()) return;
    const d=svgDims(customSvg);
    setSelectedPiece({id:`custom_${Date.now()}`,name:'SVG personalizado',type:'etiqueta',area:'comun',medio:'digital',
      herramienta:'Custom',realSizeCm:d?`${d.width}×${d.height}`:'—',canvasPx:d?`${d.width}×${d.height}`:'—',
      colors:extractColors(customSvg),lastModified:new Date().toISOString().split('T')[0],status:'borrador',
      svgContent:customSvg,notes:'SVG pegado manualmente'});
    setModalTab('preview'); setModalZoom(1); setShowCustom(false);
  };

  const bgCls = previewBg==='dark'?'bg-zinc-950':previewBg==='light'?'bg-white'
    :'bg-[length:20px_20px] bg-[image:linear-gradient(45deg,#27272a_25%,transparent_25%,transparent_75%,#27272a_75%),linear-gradient(45deg,#27272a_25%,transparent_25%,transparent_75%,#27272a_75%)] bg-[position:0_0,10px_10px] bg-zinc-900';

  return (
    <div className="space-y-4">
      {/* Status pills */}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="text-zinc-600">{sourceStatus}</span>
        <span className="ml-auto" />
        <span className="flex items-center gap-1.5 rounded-md border border-emerald-800/40 bg-emerald-950/20 px-2 py-0.5 text-emerald-400">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"/>{stats.aprobado} aprobados
        </span>
        <span className="flex items-center gap-1.5 rounded-md border border-blue-800/40 bg-blue-950/20 px-2 py-0.5 text-blue-400">
          <span className="h-1.5 w-1.5 rounded-full bg-blue-400"/>{stats.revision} revisión
        </span>
        <span className="flex items-center gap-1.5 rounded-md border border-amber-800/40 bg-amber-950/20 px-2 py-0.5 text-amber-400">
          <span className="h-1.5 w-1.5 rounded-full bg-amber-400"/>{stats.borrador} borradores
        </span>
      </div>

      {/* Toolbar */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500"/>
          <input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Buscar..."
            className="w-full rounded-lg border border-zinc-800 bg-zinc-900/50 py-2 pl-9 pr-9 text-sm outline-none focus:border-zinc-600"/>
          {search && <button onClick={()=>setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"><X className="h-4 w-4"/></button>}
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-md border border-zinc-800 bg-zinc-900/50 p-0.5">
            <button onClick={()=>setViewMode('grid')} className={`rounded px-2 py-1.5 ${viewMode==='grid'?'bg-zinc-700 text-white':'text-zinc-500 hover:text-zinc-300'}`}><Grid3x3 className="h-4 w-4"/></button>
            <button onClick={()=>setViewMode('list')} className={`rounded px-2 py-1.5 ${viewMode==='list'?'bg-zinc-700 text-white':'text-zinc-500 hover:text-zinc-300'}`}><List className="h-4 w-4"/></button>
          </div>
          <button onClick={refreshRepoSvgs} className="flex items-center gap-1.5 rounded-lg border border-emerald-800/60 bg-emerald-950/25 px-3 py-2 text-xs font-medium text-emerald-300 hover:bg-emerald-900/40">
            <RotateCcw className="h-3.5 w-3.5"/> Actualizar repo
          </button>
          <button onClick={()=>folderRef.current?.click()} className="flex items-center gap-1.5 rounded-lg border border-zinc-800 px-3 py-2 text-xs font-medium text-zinc-400 hover:text-zinc-200">
            <FileCode className="h-3.5 w-3.5"/> Carpeta local
          </button>
          <input ref={folderRef} type="file" accept=".svg,image/svg+xml" multiple className="hidden" onChange={e=>loadLocalSvgFiles(e.target.files)} {...({ webkitdirectory: 'true', directory: 'true' } as any)} />
          <button onClick={()=>setShowCustom(!showCustom)} className={`flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-medium ${showCustom?'border-violet-600 bg-violet-950/50 text-violet-300':'border-zinc-800 text-zinc-400 hover:text-zinc-200'}`}>
            <Upload className="h-3.5 w-3.5"/> Pegar SVG
          </button>
        </div>
      </div>

      {/* Custom SVG input */}
      {showCustom && (
        <div className="rounded-lg border border-violet-800/40 bg-violet-950/15 p-3 space-y-2">
          <textarea value={customSvg} onChange={e=>setCustomSvg(e.target.value)} placeholder="<svg ...>...</svg>" rows={5}
            className="w-full rounded-md border border-zinc-800 bg-black/40 px-3 py-2 font-mono text-xs outline-none focus:border-zinc-600"/>
          <div className="flex gap-2">
            <button onClick={handleCustomPreview} disabled={!customSvg.trim()} className="rounded-md bg-violet-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-violet-500 disabled:opacity-40">
              <Eye className="inline h-3 w-3 mr-1"/>Vista previa</button>
            <button onClick={()=>fileRef.current?.click()} className="rounded-md border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-xs text-zinc-300 hover:bg-zinc-700">
              <Upload className="inline h-3 w-3 mr-1"/>Archivo</button>
            <input ref={fileRef} type="file" accept=".svg" className="hidden" onChange={e=>{const f=e.target.files?.[0];if(f){const r=new FileReader();r.onload=()=>setCustomSvg(r.result as string);r.readAsText(f);}}}/>
            <button onClick={async()=>{const t=await navigator.clipboard?.readText();if(t)setCustomSvg(t);}} className="rounded-md border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-xs text-zinc-300 hover:bg-zinc-700">
              <Clipboard className="inline h-3 w-3 mr-1"/>Clipboard</button>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px]">
        {(['all',...TYPE_OPTIONS] as const).map(t=>(
          <button key={t} onClick={()=>setFilterType(t as PieceType|'all')}
            className={`rounded-full px-2 py-0.5 ${filterType===t?'bg-zinc-700 text-white':'text-zinc-500 hover:text-zinc-300'}`}>
            {t==='all'?'Todos':t}</button>
        ))}
        <span className="text-zinc-800">·</span>
        {(['all','suplementos','eventos','comun'] as const).map(a=>(
          <button key={a} onClick={()=>setFilterArea(a as PieceArea|'all')}
            className={`rounded-full px-2 py-0.5 ${filterArea===a?'bg-zinc-700 text-white':'text-zinc-500 hover:text-zinc-300'}`}>
            {a==='all'?'Áreas':a}</button>
        ))}
        <span className="text-zinc-800">·</span>
        {(['all','aprobado','en-revision','borrador'] as const).map(s=>(
          <button key={s} onClick={()=>setFilterStatus(s as SvgPiece['status']|'all')}
            className={`rounded-full px-2 py-0.5 ${filterStatus===s?'bg-zinc-700 text-white':'text-zinc-500 hover:text-zinc-300'}`}>
            {s==='all'?'Estados':s}</button>
        ))}
        {activeFilters>0 && <button onClick={()=>{setFilterType('all');setFilterArea('all');setFilterStatus('all');setSearch('');}}
          className="ml-1 flex items-center gap-1 rounded-full bg-zinc-800 px-2 py-0.5 text-zinc-400 hover:text-zinc-200">
          <RotateCcw className="h-3 w-3"/>limpiar</button>}
        <span className="ml-auto font-bold text-zinc-300">{filtered.length}</span>
        <span className="text-zinc-500">{filtered.length===1?'pieza':'piezas'}</span>
      </div>

      {/* ─── Grid ─── */}
      {viewMode==='grid' && (
        <div className="grid gap-3 grid-cols-2 md:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
          {filtered.map(piece => {
            const st = STATUS_CFG[piece.status];
            return (
              <button key={piece.id} onClick={()=>{setSelectedPiece(piece);setModalZoom(1);setModalTab('preview');}}
                className="group text-left overflow-hidden rounded-xl border border-zinc-800/50 bg-zinc-900/30 transition-all hover:border-zinc-600 hover:bg-zinc-800/40 focus:outline-none focus:ring-1 focus:ring-violet-500/50">
                {/* Preview — contained */}
                <div className="relative bg-zinc-950/80 overflow-hidden" style={{aspectRatio:'5/3.5'}}>
                  {piece.svgContent ? (
                    <div className="absolute inset-3 flex items-center justify-center svg-contain"
                      dangerouslySetInnerHTML={{__html:piece.svgContent}}/>
                  ) : piece.svgUrl ? (
                    <img src={piece.svgUrl} alt={piece.name} className="absolute inset-3 h-[calc(100%-1.5rem)] w-[calc(100%-1.5rem)] object-contain" />
                  ) : <div className="absolute inset-0 flex items-center justify-center text-2xl text-zinc-700">📄</div>}
                  {/* status */}
                  <span className={`absolute right-1.5 top-1.5 flex items-center gap-1 rounded-full border px-1.5 py-px text-[9px] font-bold backdrop-blur-sm ${st.bg} ${st.color}`}>
                    <span className={`h-1 w-1 rounded-full ${st.dot}`}/>{piece.status}
                  </span>
                </div>
                {/* Info */}
                <div className="px-2.5 py-2 space-y-1">
                  <h3 className="truncate text-xs font-bold leading-tight">{piece.name}</h3>
                  <div className="flex items-center justify-between gap-1">
                    <span className="truncate rounded bg-zinc-800/70 px-1.5 py-px text-[9px] text-zinc-400">{piece.type}</span>
                    <div className="flex shrink-0 gap-0.5">
                      {piece.colors.slice(0,3).map((c,i)=><span key={i} className="h-2.5 w-2.5 rounded-full border border-zinc-700/60" style={{backgroundColor:c}}/>)}
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-[9px] text-zinc-600">
                    <span className="truncate">{piece.realSizeCm}</span>
                    {piece.svgContent && <span>{svgSize(piece.svgContent)}</span>}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      )}

      {/* ─── List ─── */}
      {viewMode==='list' && (
        <div className="overflow-hidden rounded-lg border border-zinc-800/50">
          <table className="w-full text-xs">
            <thead><tr className="border-b border-zinc-800/50 bg-zinc-900/50 text-[9px] font-bold uppercase tracking-widest text-zinc-500">
              <th className="px-3 py-2 text-left w-16">Preview</th>
              <th className="px-3 py-2 text-left">Nombre</th>
              <th className="px-3 py-2 text-left hidden md:table-cell">Tipo</th>
              <th className="px-3 py-2 text-left hidden lg:table-cell">Área</th>
              <th className="px-3 py-2 text-left hidden md:table-cell">Medida</th>
              <th className="px-3 py-2 text-left">Estado</th>
            </tr></thead>
            <tbody className="divide-y divide-zinc-800/30">
              {filtered.map(piece=>{
                const st=STATUS_CFG[piece.status];
                return <tr key={piece.id} onClick={()=>{setSelectedPiece(piece);setModalZoom(1);setModalTab('preview');}}
                  className="cursor-pointer hover:bg-zinc-800/20">
                  <td className="px-3 py-2"><div className="h-8 w-12 rounded bg-zinc-900 overflow-hidden svg-contain"
                    dangerouslySetInnerHTML={{__html:piece.svgContent||''}}/></td>
                  <td className="px-3 py-2"><div className="font-medium">{piece.name}</div>
                    {piece.product&&<div className="text-[10px] text-zinc-600">{piece.product}</div>}</td>
                  <td className="px-3 py-2 hidden md:table-cell text-zinc-400">{piece.type}</td>
                  <td className="px-3 py-2 hidden lg:table-cell text-zinc-400">{piece.area}</td>
                  <td className="px-3 py-2 hidden md:table-cell text-zinc-500">{piece.realSizeCm}</td>
                  <td className="px-3 py-2">
                    <span className={`inline-flex items-center gap-1 rounded-full border px-1.5 py-px text-[9px] font-bold ${st.bg} ${st.color}`}>
                      <span className={`h-1 w-1 rounded-full ${st.dot}`}/>{piece.status}</span></td>
                </tr>;
              })}
            </tbody>
          </table>
        </div>
      )}

      {!filtered.length && <div className="rounded-lg border border-dashed border-zinc-800 p-10 text-center text-sm text-zinc-600">Sin piezas que coincidan.</div>}

      {/* ═══ DETAIL MODAL ═══ */}
      {selectedPiece && (
        <div className="fixed inset-0 z-[100] flex items-start justify-center overflow-y-auto bg-black/80 backdrop-blur-sm p-3 md:p-6" onClick={()=>setSelectedPiece(null)}>
          <div className="relative w-full max-w-5xl rounded-2xl border border-zinc-800/70 bg-zinc-950 shadow-2xl my-2" onClick={e=>e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between border-b border-zinc-800/60 px-5 py-3">
              <div className="min-w-0 flex-1">
                <h2 className="truncate text-base font-bold">{selectedPiece.name}</h2>
                <div className="flex items-center gap-2 mt-0.5 text-[10px] text-zinc-500">
                  <span>{selectedPiece.product||selectedPiece.type}</span><span className="text-zinc-700">·</span><span>{selectedPiece.area}</span>
                  <span className={`ml-1 inline-flex items-center gap-1 rounded-full border px-1.5 py-px font-bold ${STATUS_CFG[selectedPiece.status].bg} ${STATUS_CFG[selectedPiece.status].color}`}>
                    <span className={`h-1 w-1 rounded-full ${STATUS_CFG[selectedPiece.status].dot}`}/>{selectedPiece.status}</span>
                </div>
              </div>
              <div className="flex items-center gap-1.5 ml-3">
                <div className="flex items-center gap-0.5 rounded-md border border-zinc-800 bg-zinc-900 px-1.5 py-0.5">
                  <button onClick={()=>setModalZoom(z=>Math.max(.25,z-.25))} className="text-zinc-400 hover:text-white p-0.5"><ZoomOut className="h-3 w-3"/></button>
                  <span className="w-8 text-center text-[9px] font-bold text-zinc-400">{Math.round(modalZoom*100)}%</span>
                  <button onClick={()=>setModalZoom(z=>Math.min(4,z+.25))} className="text-zinc-400 hover:text-white p-0.5"><ZoomIn className="h-3 w-3"/></button>
                  <button onClick={()=>setModalZoom(1)} className="text-zinc-500 hover:text-white p-0.5"><RotateCcw className="h-2.5 w-2.5"/></button>
                </div>
                <button onClick={()=>setSelectedPiece(null)} className="rounded-md p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-white"><X className="h-4 w-4"/></button>
              </div>
            </div>
            {/* Tabs */}
            <div className="flex items-center border-b border-zinc-800/60 px-5">
              {([{k:'preview' as const,i:Eye,l:'Preview'},{k:'code' as const,i:Code2,l:'Código'},{k:'inspect' as const,i:Layers,l:'Inspector'},{k:'colors' as const,i:Palette,l:'Colores'}]).map(t=>(
                <button key={t.k} onClick={()=>setModalTab(t.k)}
                  className={`flex items-center gap-1 border-b-2 px-3 py-2.5 text-[11px] font-medium ${modalTab===t.k?'border-violet-500 text-white':'border-transparent text-zinc-500 hover:text-zinc-300'}`}>
                  <t.i className="h-3 w-3"/>{t.l}</button>
              ))}
            </div>
            {/* Body */}
            <div className="flex flex-col lg:flex-row" style={{minHeight:'440px'}}>
              <div className="flex-1 min-w-0">
                {/* Preview */}
                {modalTab==='preview' && (
                  <div className="relative h-full">
                    <div className="absolute right-3 top-3 z-10 flex gap-0.5 rounded-md border border-zinc-800 bg-zinc-900/90 p-0.5 backdrop-blur-sm">
                      {([['dark',Moon],['light',Sun],['checker',Grid3x3]] as const).map(([k,I])=>(
                        <button key={k} onClick={()=>setPreviewBg(k)} className={`rounded p-1 ${previewBg===k?'bg-zinc-700 text-white':'text-zinc-500 hover:text-zinc-300'}`}>
                          <I className="h-3 w-3"/></button>
                      ))}
                    </div>
                    {currentIdx>0 && <button onClick={()=>goTo(-1)} className="absolute left-3 top-1/2 z-10 -translate-y-1/2 rounded-full bg-black/50 p-1.5 text-zinc-300 backdrop-blur-sm hover:bg-black/70"><ChevronLeft className="h-4 w-4"/></button>}
                    {currentIdx>=0 && currentIdx<filtered.length-1 && <button onClick={()=>goTo(1)} className="absolute right-3 top-1/2 z-10 -translate-y-1/2 rounded-full bg-black/50 p-1.5 text-zinc-300 backdrop-blur-sm hover:bg-black/70"><ChevronRight className="h-4 w-4"/></button>}
                    <div className={`flex items-center justify-center overflow-auto p-6 ${bgCls}`} style={{minHeight:'440px'}}>
                      {selectedPiece.svgContent ? <div className="svg-modal-preview transition-transform" style={{transform:`scale(${modalZoom})`,transformOrigin:'center'}}
                        dangerouslySetInnerHTML={{__html:selectedPiece.svgContent}}/> : selectedPiece.svgUrl ? <img src={selectedPiece.svgUrl} alt={selectedPiece.name} className="max-h-[420px] max-w-full object-contain" style={{transform:`scale(${modalZoom})`,transformOrigin:'center'}}/> : null}
                    </div>
                    {currentIdx>=0 && <div className="absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full bg-black/50 px-2.5 py-0.5 text-[9px] font-bold text-zinc-400 backdrop-blur-sm">{currentIdx+1}/{filtered.length}</div>}
                  </div>
                )}
                {/* Code */}
                {modalTab==='code' && (
                  <div className="relative">
                    <button onClick={()=>selectedPiece.svgContent&&copySvg(selectedPiece.svgContent)}
                      className="absolute right-3 top-3 z-10 flex items-center gap-1 rounded-md bg-zinc-800 px-2.5 py-1 text-[10px] font-bold text-zinc-300 hover:bg-zinc-700">
                      {codeCopied?<Check className="h-3 w-3 text-emerald-400"/>:<Copy className="h-3 w-3"/>}{codeCopied?'Copiado':'Copiar'}</button>
                    <pre className="max-h-[440px] overflow-auto bg-zinc-950 p-5 font-mono text-[11px] leading-5 text-zinc-300">
                      {selectedPiece.svgContent?.replace(/></g,'>\n<').split('\n').map((l,i)=>
                        <div key={i} className="flex"><span className="mr-3 w-7 text-right text-zinc-700 select-none">{i+1}</span><span className="flex-1">{l}</span></div>
                      )}
                    </pre>
                  </div>
                )}
                {/* Inspector */}
                {modalTab==='inspect' && selectedPiece.svgContent && (()=>{
                  const dims=svgDims(selectedPiece.svgContent!);
                  return <div className="p-5 space-y-5">
                    <div><h3 className="flex items-center gap-2 text-xs font-bold mb-2"><Ruler className="h-3.5 w-3.5 text-violet-400"/>Dimensiones</h3>
                      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">{[['ViewBox W',dims?`${dims.width}`:'—'],['ViewBox H',dims?`${dims.height}`:'—'],['Real',selectedPiece.realSizeCm],['Canvas',selectedPiece.canvasPx]].map(([l,v])=>(
                        <div key={l} className="rounded-md border border-zinc-800/50 bg-zinc-900/30 p-2"><div className="text-[8px] font-bold uppercase text-zinc-600">{l}</div><div className="text-xs font-bold">{v}</div></div>
                      ))}</div></div>
                    <div><h3 className="flex items-center gap-2 text-xs font-bold mb-2"><Layers className="h-3.5 w-3.5 text-blue-400"/>Estructura</h3>
                      <div className="grid grid-cols-2 gap-1.5 md:grid-cols-3">{svgStructure(selectedPiece.svgContent!).map(el=>{const I=el.icon;return(
                        <div key={el.tag} className="flex items-center gap-2 rounded-md border border-zinc-800/50 bg-zinc-900/30 px-2 py-1.5"><I className="h-3.5 w-3.5 text-zinc-500"/>
                          <div><div className="text-[10px] font-bold font-mono">&lt;{el.tag}&gt;</div><div className="text-[9px] text-zinc-500">{el.count}</div></div></div>
                      );})}</div></div>
                    <div><h3 className="flex items-center gap-2 text-xs font-bold mb-2"><FileCode className="h-3.5 w-3.5 text-emerald-400"/>Stats</h3>
                      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">{[['Tamaño',svgSize(selectedPiece.svgContent!)],['Líneas',String(selectedPiece.svgContent!.split('\n').length)],['Chars',String(selectedPiece.svgContent!.length)],['Tool',selectedPiece.herramienta]].map(([l,v])=>(
                        <div key={l} className="rounded-md border border-zinc-800/50 bg-zinc-900/30 p-2"><div className="text-[8px] font-bold uppercase text-zinc-600">{l}</div><div className="text-xs font-bold">{v}</div></div>
                      ))}</div></div>
                    {dims && (()=>{const r=dims.width/dims.height,mx=180,dw=r>=1?mx:mx*r,dh=r>=1?mx/r:mx;return(
                      <div><h3 className="flex items-center gap-2 text-xs font-bold mb-2"><Maximize2 className="h-3.5 w-3.5 text-amber-400"/>Proporción</h3>
                        <div className="flex items-center gap-3"><div className="rounded border border-dashed border-zinc-600 bg-zinc-800/30 flex items-center justify-center text-[9px] text-zinc-500" style={{width:dw,height:dh}}>{dims.width}×{dims.height}</div>
                          <div className="text-[10px] text-zinc-500"><div>{r.toFixed(2)}:1</div><div>{r>1.7?'Panorámico':r>1.3?'Landscape':r>.8?'Cuadrado':r>.5?'Portrait':'Vertical'}</div></div></div></div>
                    );})()}
                  </div>;
                })()}
                {/* Colors */}
                {modalTab==='colors' && selectedPiece.svgContent && (
                  <div className="p-5 space-y-5">
                    <div><h3 className="flex items-center gap-2 text-xs font-bold mb-3"><Palette className="h-3.5 w-3.5 text-violet-400"/>Paleta extraída</h3>
                      <div className="grid grid-cols-4 gap-2 md:grid-cols-6">{extractColors(selectedPiece.svgContent!).map((c,i)=>(
                        <button key={i} onClick={()=>navigator.clipboard?.writeText(c)} className="group flex flex-col items-center gap-1.5 rounded-lg border border-zinc-800/50 bg-zinc-900/30 p-2 hover:border-zinc-700">
                          <div className="h-10 w-10 rounded-lg border border-zinc-700 group-hover:scale-110 transition-transform" style={{backgroundColor:c}}/>
                          <span className="font-mono text-[9px] text-zinc-500 group-hover:text-zinc-300">{c}</span></button>
                      ))}</div></div>
                    <div><h3 className="text-xs font-bold mb-2">Gradiente</h3>
                      <div className="h-8 w-full rounded-lg border border-zinc-800" style={{background:`linear-gradient(90deg,${extractColors(selectedPiece.svgContent!).join(',')})`}}/></div>
                  </div>
                )}
              </div>
              {/* Sidebar */}
              <div className="w-full border-t border-zinc-800/60 lg:w-72 lg:border-l lg:border-t-0">
                <div className="p-4 space-y-3">
                  <h3 className="text-[9px] font-bold uppercase tracking-widest text-zinc-600">Metadata</h3>
                  {[['Tipo',selectedPiece.type],['Área',`${selectedPiece.area} · ${selectedPiece.medio}`],['Medida',selectedPiece.realSizeCm],['Canvas',selectedPiece.canvasPx],['Tool',selectedPiece.herramienta],['Producto',selectedPiece.product],['Fecha',selectedPiece.lastModified]].filter(x=>x[1]).map(([l,v])=>(
                    <div key={l} className="rounded-md bg-zinc-900/50 p-2"><div className="text-[8px] font-bold uppercase text-zinc-600">{l}</div><div className="mt-0.5 text-[11px] text-zinc-300">{v}</div></div>
                  ))}
                  <div className="rounded-md bg-zinc-900/50 p-2"><div className="text-[8px] font-bold uppercase text-zinc-600 mb-1">Colores</div>
                    <div className="flex flex-wrap gap-1">{selectedPiece.colors.map((c,i)=><div key={i} className="flex items-center gap-1 rounded bg-black/30 px-1.5 py-0.5"><span className="h-2.5 w-2.5 rounded-sm border border-zinc-700" style={{backgroundColor:c}}/><span className="font-mono text-[8px] text-zinc-500">{c}</span></div>)}</div></div>
                  {selectedPiece.notes && <div className="rounded-md bg-zinc-900/50 p-2"><div className="text-[8px] font-bold uppercase text-zinc-600">Notas</div><p className="mt-0.5 text-[10px] text-zinc-400 leading-relaxed">{selectedPiece.notes}</p></div>}
                  <div className="rounded-md bg-zinc-900/50 p-2"><div className="text-[8px] font-bold uppercase text-zinc-600 mb-1">CLI</div>
                    <code className="block rounded bg-black/40 p-1.5 font-mono text-[9px] text-zinc-500 leading-4">py -m flujo render run<br/>projects/piezas_vectoriales/<br/>{selectedPiece.id}/config.json</code></div>
                  <div className="space-y-1.5 pt-1">
                    {selectedPiece.svgContent && <>
                      <button onClick={()=>configurePiece(selectedPiece)} className="flex w-full items-center justify-center gap-1.5 rounded-md border border-emerald-700/50 bg-emerald-950/40 px-3 py-2 text-[11px] font-bold text-emerald-300 hover:bg-emerald-900/50"><Settings className="h-3.5 w-3.5"/>Configurar este SVG</button>
                      <button onClick={()=>downloadSVG(selectedPiece)} className="flex w-full items-center justify-center gap-1.5 rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 text-[11px] font-bold text-zinc-200 hover:bg-zinc-700"><Download className="h-3.5 w-3.5"/>SVG</button>
                      <button onClick={()=>exportPng(selectedPiece)} className="flex w-full items-center justify-center gap-1.5 rounded-md border border-violet-700/40 bg-violet-950/30 px-3 py-2 text-[11px] font-bold text-violet-300 hover:bg-violet-900/40"><Image className="h-3.5 w-3.5"/>PNG 2×</button>
                    </>}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════
// EDITOR VIEW (config.json)
// ═══════════════════════════════════════════════

function EditorView({ pieceToLoad }: { pieceToLoad: SvgPiece | null }) {
  const [config, setConfig] = useState<PieceConfig|null>(null);
  const [activeDocIndex, setActiveDocIndex] = useState(0);
  const [selectedId, setSelectedId] = useState<string|null>(null);
  const [zoom, setZoom] = useState(0.35);
  const [showGrid, setShowGrid] = useState(true);
  const [showGlobals, setShowGlobals] = useState(true);
  const [jsonInput, setJsonInput] = useState('');
  const [showJsonInput, setShowJsonInput] = useState(false);
  const [copied, setCopied] = useState(false);
  const [multi, setMulti] = useState<string[]>([]);
  const [showPal, setShowPal] = useState(false);
  const [dragging, setDragging] = useState<{id:string;sx:number;sy:number;ox:number;oy:number}|null>(null);
  const [repoPieces, setRepoPieces] = useState<SvgPiece[]>([]);
  const [repoStatus, setRepoStatus] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);
  const svgFileRef = useRef<HTMLInputElement>(null);

  useEffect(() => { loadCfg(DEMO_CONFIGS['Etiqueta RD — IMPULSO']); }, []);

  const loadCfg = (c: PieceConfig) => {
    setConfig({...c, global_elements:assignIds(c.global_elements), documents:c.documents.map(d=>({...d,elements:assignIds(d.elements)}))});
    setActiveDocIndex(0); setSelectedId(null); setMulti([]);
  };

  const loadSvgPiece = useCallback(async (piece: SvgPiece) => {
    let svgContent = piece.svgContent;
    // Si no hay contenido inline pero hay URL, cargar desde el repo
    if (!svgContent && piece.svgUrl) {
      try {
        const resp = await fetch(piece.svgUrl);
        if (resp.ok) {
          const text = await resp.text();
          if (text.trim().startsWith('<svg') || text.includes('<svg')) {
            svgContent = text;
          }
        }
      } catch (e) {
        console.warn('No se pudo cargar SVG desde', piece.svgUrl, e);
      }
    }
    if (!svgContent) {
      console.warn('loadSvgPiece: pieza sin contenido SVG ni URL valida:', piece.name, piece.svgUrl);
      return;
    }
    const dims = svgDims(svgContent) || { width: 2000, height: 2800 };
    const cfg: PieceConfig = {
      project: { name: piece.name, slug: piece.id.replace(/[^a-z0-9]+/gi, '_').toLowerCase(), brand: piece.product || piece.area, website: 'REDUCIENDODANO.CL' },
      canvas: { width: Math.max(800, Math.round(dims.width)), height: Math.max(600, Math.round(dims.height)), real_size_cm: { width: 0, height: 0 }, safe_margin_px: 40 },
      palette: { paper: '#ffffff', ink: '#111111', line: '#d4d4d8', accent: '#10b981' },
      background: 'paper',
      global_elements: [],
      documents: [{
        id: '01_svg_importado',
        title: piece.name,
        elements: [{ type: 'svg_image', x: 0, y: 0, w: Math.max(800, Math.round(dims.width)), h: Math.max(600, Math.round(dims.height)), content: svgContent } as SvgImageElement],
      }],
    };
    loadCfg(cfg);
    setZoom(dims.width > 1800 ? 0.35 : 0.65);
  }, []);



  const refreshEditorSvgs = useCallback(async () => {
    setRepoStatus('Actualizando SVGs…');
    try {
      const list = typeof window !== 'undefined' && window.location.protocol === 'file:' ? MOCK_SVG_INDEX : await loadFromApi();
      setRepoPieces(list.filter(piece => Boolean(piece.svgContent) || Boolean(piece.svgUrl)));
      setRepoStatus(`${list.length} SVGs (${list.filter(p => Boolean(p.svgContent)).length} con preview)`);
    } catch (error) {
      setRepoPieces(MOCK_SVG_INDEX);
      setRepoStatus(`Demo (${error instanceof Error ? error.message : 'sin API'})`);
    }
  }, []);

  const loadLocalSvgForEditor = useCallback(async (files: FileList | null) => {
    const file = Array.from(files || []).find(item => item.name.toLowerCase().endsWith('.svg'));
    if (!file) return;
    const svgContent = await file.text();
    const dims = svgDims(svgContent);
    loadSvgPiece({
      id: `local_${file.name.replace(/[^a-z0-9]+/gi, '_').toLowerCase()}`,
      name: file.name,
      type: 'etiqueta',
      area: 'comun',
      medio: 'impresion',
      herramienta: 'archivo local',
      realSizeCm: 'local',
      canvasPx: dims ? `${dims.width}×${dims.height}` : 'SVG',
      colors: extractColors(svgContent),
      lastModified: new Date(file.lastModified || Date.now()).toISOString().slice(0, 10),
      status: 'borrador',
      svgContent,
      notes: file.name,
    });
  }, [loadSvgPiece]);

  useEffect(() => { refreshEditorSvgs(); }, [refreshEditorSvgs]);
  useEffect(() => { if (pieceToLoad?.svgContent) loadSvgPiece(pieceToLoad); }, [pieceToLoad, loadSvgPiece]);

  const doc = config?.documents[activeDocIndex];
  const allEls = useMemo(()=>{
    if(!config) return [];
    return [...(showGlobals?config.global_elements:[]),...(doc?.elements||[])];
  },[config,doc,showGlobals]);

  const selEl = useMemo(()=>allEls.find(e=>e._id===selectedId)||null,[allEls,selectedId]);
  const isGlobal = useMemo(()=>config?.global_elements.some(e=>e._id===selectedId)||false,[config,selectedId]);

  const updEl = useCallback((id:string,upd:Partial<ConfigElement>)=>{
    setConfig(p=>{if(!p)return p;
      const u=(l:ConfigElement[])=>l.map(e=>e._id===id?{...e,...upd} as ConfigElement:e);
      return {...p,global_elements:u(p.global_elements),documents:p.documents.map(d=>({...d,elements:u(d.elements)}))};
    });
  },[]);

  const delEl = useCallback((id:string)=>{
    setConfig(p=>{if(!p)return p;return{...p,global_elements:p.global_elements.filter(e=>e._id!==id),documents:p.documents.map(d=>({...d,elements:d.elements.filter(e=>e._id!==id)}))};});
    setSelectedId(null);
  },[]);

  function moveEl(el:ConfigElement,dx:number,dy:number) {
    switch(el.type){
      case 'text':case 'paragraph':case 'list':
        updEl(el._id!,{x:Math.round((el as TextElement).x+dx),y:Math.round((el as TextElement).y+dy)} as Partial<TextElement>);break;
      case 'rect':case 'panel':
        updEl(el._id!,{x:Math.round((el as RectElement).x+dx),y:Math.round((el as RectElement).y+dy)} as Partial<RectElement>);break;
      case 'svg_image':
        updEl(el._id!,{x:Math.round((el as SvgImageElement).x+dx),y:Math.round((el as SvgImageElement).y+dy)} as Partial<SvgImageElement>);break;
      case 'circle':
        updEl(el._id!,{cx:Math.round((el as CircleElement).cx+dx),cy:Math.round((el as CircleElement).cy+dy)} as Partial<CircleElement>);break;
      case 'line':{const e=el as LineElement;
        updEl(el._id!,{x1:Math.round(e.x1+dx),y1:Math.round(e.y1+dy),x2:Math.round(e.x2+dx),y2:Math.round(e.y2+dy)} as Partial<LineElement>);break;}
    }
  }

  const getMultiEls = useCallback(()=>{
    const ids=multi.length>1?multi:(selectedId?[selectedId]:[]);
    return allEls.filter(e=>ids.includes(e._id!));
  },[allEls,multi,selectedId]);

  const align = useCallback((mode:'left'|'center-h'|'right'|'top'|'center-v'|'bottom')=>{
    const els=getMultiEls(); if(els.length<2) return;
    const bs=els.map(e=>({id:e._id!,...getElementBounds(e)}));
    if(mode==='left'){const t=Math.min(...bs.map(b=>b.x));bs.forEach(b=>{moveEl(els.find(e=>e._id===b.id)!,t-b.x,0);});}
    if(mode==='right'){const t=Math.max(...bs.map(b=>b.x+b.w));bs.forEach(b=>{moveEl(els.find(e=>e._id===b.id)!,t-(b.x+b.w),0);});}
    if(mode==='center-h'){const mn=Math.min(...bs.map(b=>b.x)),mx=Math.max(...bs.map(b=>b.x+b.w)),c=(mn+mx)/2;bs.forEach(b=>{moveEl(els.find(e=>e._id===b.id)!,c-(b.x+b.w/2),0);});}
    if(mode==='top'){const t=Math.min(...bs.map(b=>b.y));bs.forEach(b=>{moveEl(els.find(e=>e._id===b.id)!,0,t-b.y);});}
    if(mode==='bottom'){const t=Math.max(...bs.map(b=>b.y+b.h));bs.forEach(b=>{moveEl(els.find(e=>e._id===b.id)!,0,t-(b.y+b.h));});}
    if(mode==='center-v'){const mn=Math.min(...bs.map(b=>b.y)),mx=Math.max(...bs.map(b=>b.y+b.h)),c=(mn+mx)/2;bs.forEach(b=>{moveEl(els.find(e=>e._id===b.id)!,0,c-(b.y+b.h/2));});}
  },[getMultiEls]);

  const distrib = useCallback((axis:'h'|'v')=>{
    const els=getMultiEls(); if(els.length<3) return;
    const items=els.map(e=>({id:e._id!,...getElementBounds(e)}));
    if(axis==='h'){items.sort((a,b)=>a.x-b.x);const span=items[items.length-1].x+items[items.length-1].w-items[0].x,tw=items.reduce((s,i)=>s+i.w,0),g=(span-tw)/(items.length-1);
      let cx=items[0].x;items.forEach((it,i)=>{if(i===0){cx+=it.w+g;return;}moveEl(els.find(e=>e._id===it.id)!,cx-it.x,0);cx+=it.w+g;});}
    else{items.sort((a,b)=>a.y-b.y);const span=items[items.length-1].y+items[items.length-1].h-items[0].y,th=items.reduce((s,i)=>s+i.h,0),g=(span-th)/(items.length-1);
      let cy=items[0].y;items.forEach((it,i)=>{if(i===0){cy+=it.h+g;return;}moveEl(els.find(e=>e._id===it.id)!,0,cy-it.y);cy+=it.h+g;});}
  },[getMultiEls]);

  const handleSel = useCallback((id:string,e?:React.MouseEvent)=>{
    if(e?.shiftKey){setMulti(p=>p.includes(id)?p.filter(x=>x!==id):[...p,id]);}
    else{setSelectedId(id);setMulti([id]);}
  },[]);

  const onMD = useCallback((e:React.MouseEvent,id:string)=>{
    e.stopPropagation(); const el=allEls.find(e=>e._id===id); if(!el) return;
    const b=getElementBounds(el); setDragging({id,sx:e.clientX,sy:e.clientY,ox:b.x,oy:b.y}); handleSel(id,e);
  },[allEls,handleSel]);
  const onMM = useCallback((e:React.MouseEvent)=>{
    if(!dragging) return; const el=allEls.find(e=>e._id===dragging.id); if(!el) return;
    const dx=(e.clientX-dragging.sx)/zoom, dy=(e.clientY-dragging.sy)/zoom;
    const b=getElementBounds(el); moveEl(el,dragging.ox+dx-b.x,dragging.oy+dy-b.y);
  },[dragging,allEls,zoom]);
  const onMU = useCallback(()=>setDragging(null),[]);

  const expJson = useCallback(()=>{
    if(!config) return '';
    const c=JSON.parse(JSON.stringify(config));
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const strip=(l:any[])=>l.map((e:any)=>{const{_id,...r}=e;return r;});
    c.global_elements=strip(c.global_elements);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    c.documents=c.documents.map((d:any)=>({...d,elements:strip(d.elements)}));
    return JSON.stringify(c,null,2);
  },[config]);

  const copyJ = ()=>{navigator.clipboard?.writeText(expJson());setCopied(true);setTimeout(()=>setCopied(false),1500);};
  const dlJ = ()=>{const j=expJson();const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([j],{type:'application/json'}));a.download=`${config?.project.slug||'config'}.json`;a.click();};

  const addEl = (type:ConfigElement['type'])=>{
    if(!config||!doc) return;
    const _id=`el_${Date.now()}`, cx=config.canvas.width/2, cy=config.canvas.height/2;
    let n:ConfigElement;
    switch(type){
      case 'text':n={_id,type:'text',content:'Nuevo texto',x:cx-200,y:cy,size:48,fill:'ink',weight:'bold'} as TextElement;break;
      case 'paragraph':n={_id,type:'paragraph',content:'Párrafo nuevo.',x:cx-400,y:cy,size:42,fill:'muted',max_width:800,line_height:58} as ParagraphElement;break;
      case 'list':n={_id,type:'list',x:cx-400,y:cy,size:36,fill:'ink',max_width:800,line_height:48,indent:42,gap:16,items:['Item 1','Item 2']} as ListElement;break;
      case 'rect':case 'panel':n={_id,type,x:cx-200,y:cy-100,w:400,h:200,radius:20,fill:'white',stroke:'line',stroke_width:2} as RectElement;break;
      case 'circle':n={_id,type:'circle',cx,cy,r:100,fill:'accent',opacity:.2} as CircleElement;break;
      case 'line':n={_id,type:'line',x1:cx-200,y1:cy,x2:cx+200,y2:cy,stroke:'line',stroke_width:3} as LineElement;break;
      default:return;
    }
    setConfig(p=>{if(!p) return p;return{...p,documents:p.documents.map((d,i)=>i===activeDocIndex?{...d,elements:[...d.elements,n]}:d)};});
    setSelectedId(_id); setMulti([_id]);
  };

  if(!config) return null;
  const pal=config.palette;

  return (
    <div className="space-y-3">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative group">
          <button className="flex items-center gap-1 rounded-md border border-zinc-800 bg-zinc-900/50 px-2.5 py-1.5 text-[11px] text-zinc-400 hover:text-zinc-200">
            <FileJson className="h-3 w-3"/> Demos <ChevronDown className="h-3 w-3"/></button>
          <div className="invisible group-hover:visible absolute left-0 top-full z-20 mt-1 w-52 rounded-md border border-zinc-800 bg-zinc-900 py-0.5 shadow-xl">
            {Object.keys(DEMO_CONFIGS).map(n=><button key={n} onClick={()=>loadCfg(DEMO_CONFIGS[n])} className="w-full px-3 py-1.5 text-left text-[11px] text-zinc-400 hover:bg-zinc-800 hover:text-white">{n}</button>)}
          </div>
        </div>
        <div className="relative group">
          <button className="flex items-center gap-1 rounded-md border border-emerald-800/50 bg-emerald-950/25 px-2.5 py-1.5 text-[11px] text-emerald-300 hover:bg-emerald-900/40">
            <Shapes className="h-3 w-3"/> SVGs repo <ChevronDown className="h-3 w-3"/></button>
          <div className="invisible group-hover:visible absolute left-0 top-full z-20 mt-1 max-h-72 w-72 overflow-y-auto rounded-md border border-zinc-800 bg-zinc-900 py-0.5 shadow-xl">
            <button onClick={refreshEditorSvgs} className="w-full px-3 py-1.5 text-left text-[11px] font-bold text-emerald-300 hover:bg-zinc-800">Actualizar lista · {repoStatus || 'repo'}</button>
            {repoPieces.map(piece=><button key={piece.id} onClick={()=>loadSvgPiece(piece)} className="w-full px-3 py-1.5 text-left text-[11px] text-zinc-400 hover:bg-zinc-800 hover:text-white">{piece.name}</button>)}
          </div>
        </div>
        <button onClick={()=>svgFileRef.current?.click()} className="flex items-center gap-1 rounded-md border border-zinc-800 bg-zinc-900/50 px-2.5 py-1.5 text-[11px] text-zinc-400 hover:text-zinc-200"><FileCode className="h-3 w-3"/>SVG local</button>
        <input ref={svgFileRef} type="file" accept=".svg,image/svg+xml" className="hidden" onChange={e=>loadLocalSvgForEditor(e.target.files)}/>
        <button onClick={()=>setShowJsonInput(!showJsonInput)} className="flex items-center gap-1 rounded-md border border-zinc-800 bg-zinc-900/50 px-2.5 py-1.5 text-[11px] text-zinc-400 hover:text-zinc-200"><Upload className="h-3 w-3"/>JSON</button>
        <button onClick={()=>fileRef.current?.click()} className="flex items-center gap-1 rounded-md border border-zinc-800 bg-zinc-900/50 px-2.5 py-1.5 text-[11px] text-zinc-400 hover:text-zinc-200"><Upload className="h-3 w-3"/>Archivo</button>
        <input ref={fileRef} type="file" accept=".json" className="hidden" onChange={e=>{const f=e.target.files?.[0];if(f){const r=new FileReader();r.onload=()=>{try{loadCfg(JSON.parse(r.result as string));}catch{}};r.readAsText(f);}}}/>
        <span className="flex-1"/>
        <span className="hidden sm:inline rounded-md bg-zinc-800 px-2 py-1 text-[10px] font-bold text-zinc-400">{config.project.name}</span>
        <span className="hidden sm:inline text-[10px] text-zinc-600">{config.canvas.width}×{config.canvas.height}</span>
        <button onClick={copyJ} className="flex items-center gap-1 rounded-md border border-zinc-800 bg-zinc-900/50 px-2.5 py-1.5 text-[11px] text-zinc-400 hover:text-zinc-200">
          {copied?<Check className="h-3 w-3 text-emerald-400"/>:<Copy className="h-3 w-3"/>}{copied?'Copiado':'Copiar'}</button>
        <button onClick={dlJ} className="flex items-center gap-1 rounded-md bg-white px-2.5 py-1.5 text-[11px] font-bold text-black hover:bg-zinc-200"><Download className="h-3 w-3"/>JSON</button>
      </div>

      {showJsonInput && <div className="rounded-lg border border-amber-800/40 bg-amber-950/15 p-3 space-y-2">
        <textarea value={jsonInput} onChange={e=>setJsonInput(e.target.value)} placeholder="Pega config.json..." rows={6}
          className="w-full rounded-md border border-zinc-800 bg-black/40 px-3 py-2 font-mono text-xs outline-none focus:border-zinc-600"/>
        <button onClick={()=>{try{loadCfg(JSON.parse(jsonInput));setShowJsonInput(false);setJsonInput('');}catch{alert('JSON inválido');}}} className="rounded-md bg-amber-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-amber-500">Cargar</button>
      </div>}

      {/* Main */}
      <div className="flex flex-col gap-3 xl:flex-row">
        {/* Canvas */}
        <div className="flex-1 min-w-0 overflow-hidden rounded-xl border border-zinc-800/50 bg-zinc-950">
          {/* Doc tabs + zoom */}
          <div className="flex flex-wrap items-center justify-between gap-1 border-b border-zinc-800/50 px-2 py-1.5">
            <div className="flex items-center gap-1">
              {config.documents.map((d,i)=><button key={d.id} onClick={()=>{setActiveDocIndex(i);setSelectedId(null);}}
                className={`rounded px-2 py-1 text-[10px] font-bold ${activeDocIndex===i?'bg-zinc-700 text-white':'text-zinc-500 hover:text-zinc-300'}`}>{d.title}</button>)}
              <button onClick={()=>setShowGlobals(g=>!g)} className={`flex items-center gap-1 rounded px-1.5 py-1 text-[10px] font-bold ${showGlobals?'text-emerald-400':'text-zinc-600'}`}>
                {showGlobals?<Eye className="h-3 w-3"/>:<EyeOff className="h-3 w-3"/>}Global</button>
            </div>
            <div className="flex items-center gap-0.5">
              <button onClick={()=>setShowGrid(g=>!g)} className={`rounded p-1 ${showGrid?'text-emerald-400':'text-zinc-600'}`}><Grid3x3 className="h-3 w-3"/></button>
              <button onClick={()=>setZoom(z=>Math.max(.1,z-.05))} className="rounded p-1 text-zinc-500 hover:text-zinc-300"><ZoomOut className="h-3 w-3"/></button>
              <span className="w-8 text-center text-[9px] font-bold text-zinc-500">{Math.round(zoom*100)}%</span>
              <button onClick={()=>setZoom(z=>Math.min(1,z+.05))} className="rounded p-1 text-zinc-500 hover:text-zinc-300"><ZoomIn className="h-3 w-3"/></button>
              <button onClick={()=>setZoom(.35)} className="rounded p-1 text-zinc-500 hover:text-zinc-300"><RotateCcw className="h-2.5 w-2.5"/></button>
            </div>
          </div>
          {/* Align/distrib/add bar */}
          <div className="flex flex-wrap items-center gap-0.5 border-b border-zinc-800/50 px-2 py-1">
            <span className="text-[8px] font-bold uppercase tracking-widest text-zinc-600 mr-0.5">Alinear:</span>
            {([['left',AlignStartVertical],['center-h',AlignCenterVertical],['right',AlignEndVertical],['top',AlignStartHorizontal],['center-v',AlignCenterHorizontal],['bottom',AlignEndHorizontal]] as const).map(([m,I])=>
              <button key={m} onClick={()=>align(m as any)} disabled={multi.length<2} className="rounded p-1 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300 disabled:opacity-30"><I className="h-3 w-3"/></button>)}
            <span className="mx-0.5 text-zinc-800">|</span>
            <span className="text-[8px] font-bold uppercase tracking-widest text-zinc-600 mr-0.5">Dist:</span>
            <button onClick={()=>distrib('h')} disabled={multi.length<3} className="rounded p-1 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300 disabled:opacity-30"><MoveHorizontal className="h-3 w-3"/></button>
            <button onClick={()=>distrib('v')} disabled={multi.length<3} className="rounded p-1 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300 disabled:opacity-30"><MoveVertical className="h-3 w-3"/></button>
            <span className="mx-0.5 text-zinc-800">|</span>
            <span className="text-[8px] font-bold uppercase tracking-widest text-zinc-600 mr-0.5">Add:</span>
            {([['text',Type],['paragraph',AlignLeft],['list',List],['rect',Square],['panel',Layers],['circle',Circle],['line',Minus]] as const).map(([t,I])=>
              <button key={t} onClick={()=>addEl(t as any)} title={t} className="rounded p-1 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300"><I className="h-3 w-3"/></button>)}
          </div>
          {/* Canvas SVG */}
          <div className="overflow-auto" style={{maxHeight:'560px'}} onMouseMove={onMM} onMouseUp={onMU} onMouseLeave={onMU}>
            <svg viewBox={`0 0 ${config.canvas.width} ${config.canvas.height}`}
              style={{width:config.canvas.width*zoom,height:config.canvas.height*zoom,minWidth:config.canvas.width*zoom,minHeight:config.canvas.height*zoom}}
              onClick={()=>{setSelectedId(null);setMulti([]);}}>
              <rect width={config.canvas.width} height={config.canvas.height} fill={resolveColor(config.background,pal)}/>
              {showGrid && <g opacity={.12}>{Array.from({length:Math.ceil(config.canvas.width/100)+1},(_,i)=><line key={`v${i}`} x1={i*100} y1={0} x2={i*100} y2={config.canvas.height} stroke="#999" strokeWidth={1}/>)}
                {Array.from({length:Math.ceil(config.canvas.height/100)+1},(_,i)=><line key={`h${i}`} x1={0} y1={i*100} x2={config.canvas.width} y2={i*100} stroke="#999" strokeWidth={1}/>)}</g>}
              <rect x={config.canvas.safe_margin_px} y={config.canvas.safe_margin_px} width={config.canvas.width-config.canvas.safe_margin_px*2} height={config.canvas.height-config.canvas.safe_margin_px*2} fill="none" stroke="#ccc" strokeWidth={1} strokeDasharray="12 8" opacity={.25}/>
              {allEls.filter(e=>['rect','panel','circle','line','svg_image'].includes(e.type)).map(e=><g key={e._id} onMouseDown={ev=>onMD(ev,e._id!)} className="cursor-move">{renderCfgEl(e,pal,multi.includes(e._id!),()=>{})}</g>)}
              {allEls.filter(e=>['text','paragraph','list'].includes(e.type)).map(e=><g key={e._id} onMouseDown={ev=>onMD(ev,e._id!)} className="cursor-move">{renderCfgEl(e,pal,multi.includes(e._id!),()=>{})}</g>)}
            </svg>
          </div>
        </div>

        {/* Props panel */}
        <div className="w-full xl:w-72 space-y-2 overflow-y-auto" style={{maxHeight:'680px'}}>
          {/* Palette */}
          <div className="rounded-lg border border-zinc-800/50 bg-zinc-900/30 p-2.5">
            <button onClick={()=>setShowPal(p=>!p)} className="flex items-center gap-1.5 w-full text-left text-[9px] font-bold uppercase tracking-widest text-zinc-600">
              <Palette className="h-3 w-3 text-amber-400"/>Paleta<ChevronDown className={`h-2.5 w-2.5 ml-auto transition-transform ${showPal?'rotate-180':''}`}/></button>
            {showPal && <div className="mt-2 grid grid-cols-5 gap-1">{Object.entries(pal).map(([n,h])=>
              <button key={n} onClick={()=>navigator.clipboard?.writeText(n)} className="group flex flex-col items-center gap-0.5 rounded p-0.5 hover:bg-zinc-800" title={`${n}: ${h}`}>
                <span className="h-5 w-5 rounded border border-zinc-700" style={{backgroundColor:h}}/><span className="text-[7px] text-zinc-600 truncate max-w-full">{n}</span></button>
            )}</div>}
          </div>
          {/* Elements list */}
          <div className="rounded-lg border border-zinc-800/50 bg-zinc-900/30 p-2.5">
            <div className="flex items-center gap-1.5 mb-1.5 text-[9px] font-bold uppercase tracking-widest text-zinc-600"><Layers className="h-3 w-3 text-blue-400"/>Elementos ({allEls.length})</div>
            <div className="space-y-px max-h-40 overflow-y-auto">
              {allEls.map(el=>{
                const act=multi.includes(el._id!);
                const lbl=el.type==='text'?(el as TextElement).content.slice(0,20):el.type==='paragraph'?(el as ParagraphElement).content.slice(0,20):el.type==='list'?`Lista(${(el as ListElement).items.length})`:el.type;
                const isG=config.global_elements.some(g=>g._id===el._id);
                return <button key={el._id} onClick={e=>handleSel(el._id!,e)} className={`flex w-full items-center gap-1.5 rounded px-1.5 py-1 text-left text-[10px] border ${act?'bg-blue-500/10 text-blue-300 border-blue-500/30':'text-zinc-400 hover:bg-zinc-800/50 border-transparent'}`}>
                  <span className="w-10 shrink-0 rounded bg-zinc-800 px-1 py-px text-center text-[8px] font-bold text-zinc-500 uppercase">{el.type.slice(0,4)}</span>
                  <span className="truncate flex-1">{lbl}</span>{isG&&<span className="text-[7px] text-zinc-600">G</span>}
                </button>;
              })}
            </div>
            <div className="mt-1 text-[8px] text-zinc-600">Shift+click = multi · drag en canvas</div>
          </div>
          {/* Selected props */}
          {selEl ? (
            <div className="rounded-lg border border-blue-800/30 bg-blue-950/15 p-2.5 space-y-2">
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1 text-[9px] font-bold uppercase tracking-widest text-blue-400"><Settings className="h-3 w-3"/>{selEl.type} {isGlobal?'(G)':''}</span>
                <button onClick={()=>delEl(selectedId!)} className="text-zinc-600 hover:text-red-400"><Trash2 className="h-3 w-3"/></button>
              </div>
              <PropEditor el={selEl} pal={pal} updEl={updEl}/>
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-zinc-800 p-3 text-center text-[10px] text-zinc-600">
              Click un elemento para editar.<br/><strong>Shift+click</strong> = multi → alinear/distribuir.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════
// Property editor sub-component
// ═══════════════════════════════════════════════

function PropEditor({el,pal,updEl}:{el:ConfigElement;pal:PaletteType;updEl:(id:string,u:Partial<ConfigElement>)=>void}) {
  const palKeys = Object.keys(pal);
  const F = ({l,children}:{l:string;children:React.ReactNode}) => <div><label className="block text-[8px] font-bold uppercase text-zinc-600 mb-px">{l}</label>{children}</div>;
  const inp = "w-full rounded border border-zinc-700 bg-black/40 px-2 py-1 text-[11px] outline-none focus:border-blue-600 font-mono";
  const sel = "w-full rounded border border-zinc-700 bg-black/40 px-2 py-1 text-[11px] outline-none focus:border-blue-600";

  if (el.type==='text') { const e=el as TextElement; return <>
    <F l="Contenido"><input value={e.content} onChange={v=>updEl(e._id!,{content:v.target.value} as any)} className={inp}/></F>
    <div className="grid grid-cols-2 gap-1.5">
      <F l="Tamaño"><input type="number" value={e.size} onChange={v=>updEl(e._id!,{size:+v.target.value} as any)} className={inp}/></F>
      <F l="Peso"><select value={e.weight||'normal'} onChange={v=>updEl(e._id!,{weight:v.target.value} as any)} className={sel}><option value="normal">Normal</option><option value="bold">Bold</option></select></F>
    </div>
    <div className="grid grid-cols-2 gap-1.5"><F l="X"><input type="number" value={e.x} onChange={v=>updEl(e._id!,{x:+v.target.value} as any)} className={inp}/></F><F l="Y"><input type="number" value={e.y} onChange={v=>updEl(e._id!,{y:+v.target.value} as any)} className={inp}/></F></div>
    <F l="Color"><div className="flex items-center gap-1.5"><span className="h-4 w-4 rounded border border-zinc-700" style={{backgroundColor:resolveColor(e.fill,pal)}}/><select value={e.fill} onChange={v=>updEl(e._id!,{fill:v.target.value} as any)} className={sel}>{palKeys.map(k=><option key={k} value={k}>{k}</option>)}</select></div></F>
  </>;}

  if (el.type==='paragraph') { const e=el as ParagraphElement; return <>
    <F l="Contenido"><textarea value={e.content} onChange={v=>updEl(e._id!,{content:v.target.value} as any)} rows={3} className={inp+' resize-y'}/></F>
    <div className="grid grid-cols-3 gap-1.5">
      <F l="Tamaño"><input type="number" value={e.size} onChange={v=>updEl(e._id!,{size:+v.target.value} as any)} className={inp}/></F>
      <F l="Interlin"><input type="number" value={e.line_height} onChange={v=>updEl(e._id!,{line_height:+v.target.value} as any)} className={inp}/></F>
      <F l="Ancho"><input type="number" value={e.max_width} onChange={v=>updEl(e._id!,{max_width:+v.target.value} as any)} className={inp}/></F>
    </div>
    <div className="grid grid-cols-2 gap-1.5"><F l="X"><input type="number" value={e.x} onChange={v=>updEl(e._id!,{x:+v.target.value} as any)} className={inp}/></F><F l="Y"><input type="number" value={e.y} onChange={v=>updEl(e._id!,{y:+v.target.value} as any)} className={inp}/></F></div>
    <F l="Color"><div className="flex items-center gap-1.5"><span className="h-4 w-4 rounded border border-zinc-700" style={{backgroundColor:resolveColor(e.fill,pal)}}/><select value={e.fill} onChange={v=>updEl(e._id!,{fill:v.target.value} as any)} className={sel}>{palKeys.map(k=><option key={k} value={k}>{k}</option>)}</select></div></F>
  </>;}

  if (el.type==='list') { const e=el as ListElement; return <>
    <F l="Items">
      {e.items.map((it,i)=><div key={i} className="flex items-center gap-1 mb-0.5">
        <span className="text-[9px] text-zinc-600 w-3 text-right">{i+1}</span>
        <input value={it} onChange={v=>{const n=[...e.items];n[i]=v.target.value;updEl(e._id!,{items:n} as any);}} className={inp+' flex-1'}/>
        <button onClick={()=>updEl(e._id!,{items:e.items.filter((_,j)=>j!==i)} as any)} className="text-zinc-600 hover:text-red-400"><Trash2 className="h-2.5 w-2.5"/></button>
      </div>)}
      <button onClick={()=>updEl(e._id!,{items:[...e.items,'Nuevo']} as any)} className="flex items-center gap-0.5 text-[9px] text-zinc-500 hover:text-zinc-300 mt-0.5"><Plus className="h-2.5 w-2.5"/>item</button>
    </F>
    <div className="grid grid-cols-3 gap-1.5">
      <F l="Tamaño"><input type="number" value={e.size} onChange={v=>updEl(e._id!,{size:+v.target.value} as any)} className={inp}/></F>
      <F l="Interlin"><input type="number" value={e.line_height} onChange={v=>updEl(e._id!,{line_height:+v.target.value} as any)} className={inp}/></F>
      <F l="Indent"><input type="number" value={e.indent} onChange={v=>updEl(e._id!,{indent:+v.target.value} as any)} className={inp}/></F>
    </div>
    <div className="grid grid-cols-3 gap-1.5">
      <F l="X"><input type="number" value={e.x} onChange={v=>updEl(e._id!,{x:+v.target.value} as any)} className={inp}/></F>
      <F l="Y"><input type="number" value={e.y} onChange={v=>updEl(e._id!,{y:+v.target.value} as any)} className={inp}/></F>
      <F l="Gap"><input type="number" value={e.gap} onChange={v=>updEl(e._id!,{gap:+v.target.value} as any)} className={inp}/></F>
    </div>
    <F l="Color"><div className="flex items-center gap-1.5"><span className="h-4 w-4 rounded border border-zinc-700" style={{backgroundColor:resolveColor(e.fill,pal)}}/><select value={e.fill} onChange={v=>updEl(e._id!,{fill:v.target.value} as any)} className={sel}>{palKeys.map(k=><option key={k} value={k}>{k}</option>)}</select></div></F>
  </>;}

  if (el.type==='rect'||el.type==='panel') { const e=el as RectElement; return <>
    <div className="grid grid-cols-2 gap-1.5"><F l="X"><input type="number" value={e.x} onChange={v=>updEl(e._id!,{x:+v.target.value} as any)} className={inp}/></F><F l="Y"><input type="number" value={e.y} onChange={v=>updEl(e._id!,{y:+v.target.value} as any)} className={inp}/></F></div>
    <div className="grid grid-cols-3 gap-1.5"><F l="W"><input type="number" value={e.w} onChange={v=>updEl(e._id!,{w:+v.target.value} as any)} className={inp}/></F><F l="H"><input type="number" value={e.h} onChange={v=>updEl(e._id!,{h:+v.target.value} as any)} className={inp}/></F><F l="R"><input type="number" value={e.radius||0} onChange={v=>updEl(e._id!,{radius:+v.target.value} as any)} className={inp}/></F></div>
    <F l="Fill"><div className="flex items-center gap-1.5"><span className="h-4 w-4 rounded border border-zinc-700" style={{backgroundColor:e.fill==='none'?'transparent':resolveColor(e.fill||'',pal)}}/><select value={e.fill||'none'} onChange={v=>updEl(e._id!,{fill:v.target.value} as any)} className={sel}><option value="none">none</option>{palKeys.map(k=><option key={k} value={k}>{k}</option>)}</select></div></F>
    <F l="Stroke"><div className="flex items-center gap-1.5"><select value={e.stroke||''} onChange={v=>updEl(e._id!,{stroke:v.target.value||undefined} as any)} className={sel+' flex-1'}><option value="">none</option>{palKeys.map(k=><option key={k} value={k}>{k}</option>)}</select><input type="number" value={e.stroke_width||0} onChange={v=>updEl(e._id!,{stroke_width:+v.target.value} as any)} className={inp+' !w-14'} placeholder="w"/></div></F>
    <F l="Opacidad"><div className="flex items-center gap-1.5"><input type="range" min={0} max={1} step={.05} value={e.opacity??1} onChange={v=>updEl(e._id!,{opacity:+v.target.value} as any)} className="flex-1"/><span className="text-[9px] text-zinc-500 w-8">{Math.round((e.opacity??1)*100)}%</span></div></F>
  </>;}

  if (el.type==='circle') { const e=el as CircleElement; return <>
    <div className="grid grid-cols-3 gap-1.5"><F l="CX"><input type="number" value={e.cx} onChange={v=>updEl(e._id!,{cx:+v.target.value} as any)} className={inp}/></F><F l="CY"><input type="number" value={e.cy} onChange={v=>updEl(e._id!,{cy:+v.target.value} as any)} className={inp}/></F><F l="R"><input type="number" value={e.r} onChange={v=>updEl(e._id!,{r:+v.target.value} as any)} className={inp}/></F></div>
    <F l="Fill"><div className="flex items-center gap-1.5"><span className="h-4 w-4 rounded-full border border-zinc-700" style={{backgroundColor:resolveColor(e.fill||'',pal)}}/><select value={e.fill||''} onChange={v=>updEl(e._id!,{fill:v.target.value} as any)} className={sel}>{palKeys.map(k=><option key={k} value={k}>{k}</option>)}</select></div></F>
    <F l="Opacidad"><div className="flex items-center gap-1.5"><input type="range" min={0} max={1} step={.05} value={e.opacity??1} onChange={v=>updEl(e._id!,{opacity:+v.target.value} as any)} className="flex-1"/><span className="text-[9px] text-zinc-500 w-8">{Math.round((e.opacity??1)*100)}%</span></div></F>
  </>;}

  if (el.type==='line') { const e=el as LineElement; return <>
    <div className="grid grid-cols-2 gap-1.5"><F l="X1"><input type="number" value={e.x1} onChange={v=>updEl(e._id!,{x1:+v.target.value} as any)} className={inp}/></F><F l="Y1"><input type="number" value={e.y1} onChange={v=>updEl(e._id!,{y1:+v.target.value} as any)} className={inp}/></F><F l="X2"><input type="number" value={e.x2} onChange={v=>updEl(e._id!,{x2:+v.target.value} as any)} className={inp}/></F><F l="Y2"><input type="number" value={e.y2} onChange={v=>updEl(e._id!,{y2:+v.target.value} as any)} className={inp}/></F></div>
    <F l="Stroke"><div className="flex items-center gap-1.5"><select value={e.stroke||''} onChange={v=>updEl(e._id!,{stroke:v.target.value} as any)} className={sel+' flex-1'}>{palKeys.map(k=><option key={k} value={k}>{k}</option>)}</select><input type="number" value={e.stroke_width||1} onChange={v=>updEl(e._id!,{stroke_width:+v.target.value} as any)} className={inp+' !w-14'}/></div></F>
  </>;}

  return null;
}
