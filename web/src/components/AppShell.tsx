import { type ReactNode, useState } from 'react';
import {
  LayoutDashboard, Boxes, ClipboardList, Calculator,
  TerminalSquare, Map, Shapes, Menu, X, ChevronRight,
} from 'lucide-react';

export type AppView = 'hub' | 'jobs' | 'intake' | 'quote' | 'commands' | 'plano' | 'visualizer';

const NAV_ITEMS: { view: AppView; icon: typeof LayoutDashboard; label: string; desc: string }[] = [
  { view: 'hub', icon: LayoutDashboard, label: 'Dashboard', desc: 'Vista general' },
  { view: 'visualizer', icon: Shapes, label: 'SVG Studio', desc: 'Galería + Config Editor' },
  { view: 'jobs', icon: Boxes, label: 'Jobs', desc: 'Estado de trabajos' },
  { view: 'intake', icon: ClipboardList, label: 'Intake', desc: 'Parsear pedidos' },
  { view: 'plano', icon: Map, label: 'Plano/Rider', desc: 'Layout de evento' },
  { view: 'quote', icon: Calculator, label: 'Cotización', desc: 'Presupuesto' },
  { view: 'commands', icon: TerminalSquare, label: 'Comandos', desc: 'CLI reference' },
];

interface Props {
  view: AppView;
  onViewChange: (v: AppView) => void;
  children: ReactNode;
}

export default function AppShell({ view, onViewChange, children }: Props) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

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

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-3 py-4">
          <div className="mb-2 px-2 text-[10px] font-bold uppercase tracking-widest text-zinc-600">Herramientas</div>
          {NAV_ITEMS.map(item => {
            const Icon = item.icon;
            const active = view === item.view;
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
                <Icon className={`h-4 w-4 shrink-0 ${active ? 'text-emerald-400' : 'text-zinc-500 group-hover:text-zinc-400'}`} />
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
          <div className="text-[10px] text-zinc-600">
            v0.47.12 · gratis/local
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
          <span className="text-sm font-bold">
            {NAV_ITEMS.find(i => i.view === view)?.label || 'flujo'}
          </span>
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
