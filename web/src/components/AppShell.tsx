import type React from 'react';
import { Activity, Boxes, ClipboardList, FileText, Home, Map, Shapes, TerminalSquare } from 'lucide-react';
import { cn } from '../utils/cn';

export type AppView = 'hub' | 'jobs' | 'intake' | 'commands' | 'plano' | 'visualizer';

const nav = [
  { id: 'hub' as const, label: 'Hub', icon: Home, hint: 'dashboard' },
  { id: 'jobs' as const, label: 'Jobs', icon: Boxes, hint: 'trabajo' },
  { id: 'intake' as const, label: 'Intake', icon: ClipboardList, hint: 'pedido' },
  { id: 'commands' as const, label: 'Comandos', icon: TerminalSquare, hint: 'CLI' },
  { id: 'plano' as const, label: 'Plano', icon: Map, hint: 'rider' },
  { id: 'visualizer' as const, label: 'SVG', icon: Shapes, hint: 'material' },
];

export function titleForView(view: AppView): string {
  const map: Record<AppView, string> = {
    hub: 'Hub operativo',
    jobs: 'Jobs reales',
    intake: 'Intake de pedidos',
    commands: 'Comandos rápidos',
    plano: 'Plano / Rider RD',
    visualizer: 'Visualizador SVG',
  };
  return map[view];
}

export default function AppShell({
  view,
  onViewChange,
  children,
}: {
  view: AppView;
  onViewChange: (view: AppView) => void;
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 font-sans">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 border-r border-zinc-800 bg-[#09090b] lg:flex lg:flex-col">
        <div className="flex items-center gap-3 border-b border-zinc-800 p-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-white text-xl font-black italic text-black">F</div>
          <div>
            <div className="text-base font-bold tracking-tight">flujo</div>
            <div className="text-[10px] uppercase tracking-[0.22em] text-zinc-500">workspace local</div>
          </div>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {nav.map(item => {
            const Icon = item.icon;
            const active = view === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onViewChange(item.id)}
                className={cn(
                  'group flex w-full items-center justify-between rounded-xl px-3 py-3 text-left transition-colors',
                  active ? 'bg-white text-black' : 'text-zinc-500 hover:bg-zinc-900 hover:text-zinc-100'
                )}
              >
                <span className="flex items-center gap-3">
                  <Icon className="h-4 w-4" />
                  <span className="text-sm font-semibold">{item.label}</span>
                </span>
                <span className={cn('text-[9px] uppercase tracking-widest', active ? 'text-black/50' : 'text-zinc-700 group-hover:text-zinc-500')}>{item.hint}</span>
              </button>
            );
          })}
        </nav>
        <div className="border-t border-zinc-800 p-4 text-[10px] font-mono uppercase tracking-widest text-zinc-600">
          <div className="flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-green-500 shadow-[0_0_10px_rgba(34,197,94,.8)]" /> local-first</div>
          <div className="mt-1">v0.41.0</div>
        </div>
      </aside>

      <header className="sticky top-0 z-30 border-b border-zinc-800 bg-[#09090b]/90 backdrop-blur-xl lg:ml-64">
        <div className="flex min-h-14 flex-wrap items-center justify-between gap-3 px-5 py-2 lg:px-7">
          <div>
            <div className="flex items-center gap-2 text-sm font-bold"><Activity className="h-4 w-4 text-emerald-400" /> {titleForView(view)}</div>
            <div className="text-[11px] text-zinc-500">Python backend + React UI · gratis/local</div>
          </div>
          <nav className="flex max-w-full gap-1 overflow-x-auto rounded-xl border border-zinc-800 bg-zinc-950/70 p-1 lg:hidden">
            {nav.map(item => {
              const Icon = item.icon;
              return <button key={item.id} onClick={() => onViewChange(item.id)} className={cn('rounded-lg px-3 py-2 text-xs', view === item.id ? 'bg-white text-black' : 'text-zinc-500')}><Icon className="h-4 w-4" /></button>;
            })}
          </nav>
          <div className="hidden items-center gap-2 text-[10px] font-mono uppercase tracking-widest text-zinc-600 sm:flex">
            <FileText className="h-3.5 w-3.5" /> context single-file
          </div>
        </div>
      </header>

      <main className="p-5 lg:ml-64 lg:p-7">
        {children}
      </main>
    </div>
  );
}
