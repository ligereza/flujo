import { type ReactNode, useState } from 'react';
import {
  LayoutDashboard, Boxes, ClipboardList, Calculator,
  TerminalSquare, Map, Shapes, Menu, X, ChevronRight,
  Heart, Music, Camera, Cpu, Radio,
} from 'lucide-react';

export type AppView =
  | 'hub'
  | 'jobs'
  | 'intake'
  | 'quote'
  | 'commands'
  | 'plano'
  | 'visualizer'
  | 'events'
  | 'resolume';

export type WorkspaceMode = 'rd' | 'studio';

interface NavItem {
  view: AppView;
  icon: typeof LayoutDashboard;
  label: string;
  desc: string;
}

const RD_NAV: NavItem[] = [
  { view: 'hub', icon: LayoutDashboard, label: 'Dashboard', desc: 'Vista general RD' },
  { view: 'intake', icon: ClipboardList, label: 'Intake', desc: 'Parsear pedidos' },
  { view: 'jobs', icon: Boxes, label: 'Jobs / Suplementos', desc: 'Estado de trabajos' },
  { view: 'quote', icon: Calculator, label: 'Cotizacion', desc: 'Presupuesto RD' },
  { view: 'plano', icon: Map, label: 'Plano / Rider', desc: 'Layout de evento' },
  { view: 'visualizer', icon: Shapes, label: 'SVG Studio', desc: 'Galeria suplementos RD' },
];

const STUDIO_NAV: NavItem[] = [
  { view: 'hub', icon: LayoutDashboard, label: 'Dashboard', desc: 'Vista general Studio' },
  { view: 'commands', icon: TerminalSquare, label: 'Comandos', desc: 'CLI reference' },
  { view: 'events', icon: Camera, label: 'Eventos / IG', desc: 'Flyers Instagram' },
  { view: 'visualizer', icon: Shapes, label: 'SVG Studio', desc: 'Galeria eventos' },
  { view: 'resolume', icon: Radio, label: 'Resolume / Chataigne', desc: 'SMPTE/OSC auto' },
];

interface Props {
  view: AppView;
  onViewChange: (v: AppView) => void;
  children: ReactNode;
}

export default function AppShell({ view, onViewChange, children }: Props) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [mode, setMode] = useState<WorkspaceMode>('rd');

  const navItems = mode === 'rd' ? RD_NAV : STUDIO_NAV;
  const currentLabel = navItems.find(i => i.view === view)?.label
    || RD_NAV.find(i => i.view === view)?.label
    || STUDIO_NAV.find(i => i.view === view)?.label
    || 'flujo';

  const switchMode = (m: WorkspaceMode) => {
    setMode(m);
    // If current view doesn't exist in the new mode, go to hub
    const targetNav = m === 'rd' ? RD_NAV : STUDIO_NAV;
    if (!targetNav.find(n => n.view === view)) {
      onViewChange('hub');
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-zinc-950 text-zinc-100">
      {/* Sidebar overlay on mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-zinc-800/70 bg-zinc-950
          transition-transform duration-300 lg:static lg:translate-x-0
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        {/* Brand */}
        <div className="flex h-16 items-center gap-3 border-b border-zinc-800/70 px-5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600">
            <span className="text-sm font-black text-white">f</span>
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight">flujo</h1>
            <p className="text-[10px] text-zinc-500">hub operativo</p>
          </div>
          <button onClick={() => setSidebarOpen(false)} className="ml-auto rounded-lg p-1 text-zinc-500 hover:text-zinc-300 lg:hidden">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Mode Selector */}
        <div className="border-b border-zinc-800/70 px-3 py-3">
          <div className="text-[10px] font-bold uppercase tracking-widest text-zinc-600 mb-2 px-2">Workspace</div>
          <div className="flex gap-1.5">
            <button
              onClick={() => switchMode('rd')}
              className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg px-2 py-2 text-[11px] font-bold transition-all ${
                mode === 'rd'
                  ? 'bg-emerald-900/50 text-emerald-300 border border-emerald-700/50 shadow-sm shadow-emerald-900/30'
                  : 'text-zinc-500 hover:bg-zinc-800/50 hover:text-zinc-300 border border-transparent'
              }`}
            >
              <Heart className="h-3.5 w-3.5" />
              Modo RD
            </button>
            <button
              onClick={() => switchMode('studio')}
              className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg px-2 py-2 text-[11px] font-bold transition-all ${
                mode === 'studio'
                  ? 'bg-violet-900/50 text-violet-300 border border-violet-700/50 shadow-sm shadow-violet-900/30'
                  : 'text-zinc-500 hover:bg-zinc-800/50 hover:text-zinc-300 border border-transparent'
              }`}
            >
              <Music className="h-3.5 w-3.5" />
              Studio
            </button>
          </div>
          <div className="mt-2 px-2 text-[9px] text-zinc-600 leading-relaxed">
            {mode === 'rd'
              ? 'ONG Reduciendo Dano: Suplementos, Cotizaciones, Plano/Rider, SVG Studio.'
              : 'VJ & Club: Comandos, Eventos/IG, SVG Studio eventos, Resolume/Chataigne.'}
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-3 py-4">
          <div className="mb-2 px-2 text-[10px] font-bold uppercase tracking-widest text-zinc-600">
            {mode === 'rd' ? 'Herramientas RD' : 'Herramientas Studio'}
          </div>
          {navItems.map(item => {
            const Icon = item.icon;
            const active = view === item.view;
            const accentColor = mode === 'rd' ? 'text-emerald-400' : 'text-violet-400';
            return (
              <button
                key={item.view}
                onClick={() => { onViewChange(item.view); setSidebarOpen(false); }}
                className={`
                  group mb-0.5 flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-all
                  ${active
                    ? 'bg-zinc-800/80 text-white shadow-sm'
                    : 'text-zinc-400 hover:bg-zinc-800/40 hover:text-zinc-200'}
                `}
              >
                <Icon className={`h-4 w-4 shrink-0 ${active ? accentColor : 'text-zinc-500 group-hover:text-zinc-400'}`} />
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium">{item.label}</div>
                  <div className="truncate text-[10px] text-zinc-600">{item.desc}</div>
                </div>
                {active && <ChevronRight className="h-3 w-3 text-zinc-600" />}
              </button>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="border-t border-zinc-800/70 px-5 py-3">
          <div className="flex items-center gap-2">
            {mode === 'rd'
              ? <Heart className="h-3 w-3 text-emerald-500" />
              : <Cpu className="h-3 w-3 text-violet-500" />
            }
            <span className="text-[10px] text-zinc-600">
              {mode === 'rd' ? 'Reduciendo Dano' : 'Studio / Personal'}
            </span>
          </div>
          <div className="text-[10px] text-zinc-600 mt-1">
            v0.47.13 | gratis/local
          </div>
          <div className="text-[10px] text-zinc-700">
            py -m flujo app
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Mobile header */}
        <header className="flex h-14 items-center gap-3 border-b border-zinc-800/70 px-4 lg:hidden">
          <button onClick={() => setSidebarOpen(true)} className="rounded-lg p-1.5 text-zinc-400 hover:text-zinc-200">
            <Menu className="h-5 w-5" />
          </button>
          <div className="flex items-center gap-2">
            {mode === 'rd'
              ? <span className="rounded-md bg-emerald-900/50 px-1.5 py-0.5 text-[9px] font-bold text-emerald-300">RD</span>
              : <span className="rounded-md bg-violet-900/50 px-1.5 py-0.5 text-[9px] font-bold text-violet-300">STUDIO</span>
            }
            <span className="text-sm font-bold">{currentLabel}</span>
          </div>
        </header>

        {/* Scrollable content */}
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-[1600px] p-4 md:p-6 lg:p-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
