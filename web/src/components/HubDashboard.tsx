import type React from 'react';
import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, Boxes, CheckCircle2, ClipboardList, Map, Shapes, Signal, TerminalSquare } from 'lucide-react';
import { flujoApi, type JobsResponse, type Ping } from '../api/flujoApi';
import type { AppView } from './AppShell';

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-2xl border border-zinc-800 bg-zinc-900/45 p-5 ${className}`}>{children}</div>;
}

function Stat({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <Card>
      <div className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">{label}</div>
      <div className="mt-2 text-3xl font-black tracking-tight">{value}</div>
      {sub && <div className="mt-1 text-xs text-zinc-500">{sub}</div>}
    </Card>
  );
}

export default function HubDashboard({ onNavigate }: { onNavigate: (view: AppView) => void }) {
  const [ping, setPing] = useState<Ping | null>(null);
  const [jobs, setJobs] = useState<JobsResponse | null>(null);
  const [svgCount, setSvgCount] = useState<number | null>(null);

  useEffect(() => {
    let alive = true;
    flujoApi.ping().then(data => alive && setPing(data)).catch(error => alive && setPing({ status: 'error', note: String(error), connected: false }));
    flujoApi.jobs().then(data => alive && setJobs(data));
    if (window.location.protocol !== 'file:') {
      fetch('/api/list-svg-works')
        .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
        .then(data => alive && setSvgCount(Number(data.count || 0)))
        .catch(() => alive && setSvgCount(null));
    }
    return () => { alive = false; };
  }, []);

  const openJobs = jobs?.jobs.filter(j => !String(j.estado || '').toLowerCase().includes('entregado')).length ?? 0;
  const recent = useMemo(() => (jobs?.jobs || []).slice(0, 5), [jobs]);

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-zinc-800 bg-gradient-to-br from-zinc-900 via-black to-emerald-950/30 p-7">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-emerald-900/60 bg-emerald-950/30 px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-emerald-300">
              <Signal className="h-3 w-3" /> {ping?.connected === false ? 'modo demo' : 'backend local'}
            </div>
            <h1 className="text-3xl font-black tracking-tight">Workspace operativo flujo</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-400">Entrada diaria para convertir pedidos en jobs trazables, revisar SVGs reales, preparar planos/riders y mantener continuidad entre agentes.</p>
          </div>
          <div className="text-left text-xs text-zinc-500 lg:text-right">
            <div className="font-mono">version: {ping?.version || '0.41.0'}</div>
            <div className="mt-1 max-w-xl truncate font-mono">{ping?.root || ping?.note || 'abre con py -m flujo app para conectar APIs'}</div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        <Stat label="Jobs" value={jobs?.count ?? '—'} sub={`${openJobs} abiertos`} />
        <Stat label="SVG reales" value={svgCount ?? '—'} sub="desde /svg" />
        <Stat label="Backend" value={ping?.connected === false ? 'demo' : 'ok'} sub={ping?.mode || 'http/local'} />
        <Stat label="Siguiente" value="v0.41" sub="hub unificado" />
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.2fr_.8fr]">
        <Card>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-bold">Acciones rápidas</h2>
            <span className="text-[10px] uppercase tracking-widest text-zinc-600">operación diaria</span>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {[
              { view: 'intake' as const, icon: ClipboardList, title: 'Pegar pedido', desc: 'Parsear con backend y crear job draft' },
              { view: 'jobs' as const, icon: Boxes, title: 'Ver jobs', desc: 'Estado real de la carpeta jobs/' },
              { view: 'plano' as const, icon: Map, title: 'Plano/Rider', desc: 'Preparar layout, rider y SVG' },
              { view: 'visualizer' as const, icon: Shapes, title: 'Material SVG', desc: 'Revisar piezas reales del repo' },
              { view: 'commands' as const, icon: TerminalSquare, title: 'Comandos', desc: 'Copiar checks y build' },
            ].map(item => {
              const Icon = item.icon;
              return (
                <button key={item.title} onClick={() => onNavigate(item.view)} className="group rounded-xl border border-zinc-800 bg-black/30 p-4 text-left transition hover:border-zinc-600 hover:bg-zinc-900">
                  <div className="flex items-center justify-between">
                    <Icon className="h-5 w-5 text-zinc-400" />
                    <ArrowRight className="h-4 w-4 text-zinc-700 transition group-hover:translate-x-1 group-hover:text-zinc-300" />
                  </div>
                  <div className="mt-3 font-bold">{item.title}</div>
                  <div className="mt-1 text-xs text-zinc-500">{item.desc}</div>
                </button>
              );
            })}
          </div>
        </Card>

        <Card>
          <div className="mb-4 flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-400" /><h2 className="text-lg font-bold">Jobs recientes</h2></div>
          <div className="space-y-2">
            {recent.length ? recent.map(job => (
              <div key={job.path || job.name} className="rounded-xl border border-zinc-800 bg-black/25 p-3">
                <div className="truncate text-sm font-semibold">{job.name}</div>
                <div className="mt-1 flex flex-wrap gap-2 text-[10px] uppercase tracking-widest text-zinc-500">
                  <span>{job.estado || 'sin estado'}</span><span>{job.tipo_pieza || 'pieza'}</span>
                </div>
              </div>
            )) : <div className="rounded-xl border border-dashed border-zinc-800 p-5 text-sm text-zinc-500">Sin jobs reales todavía. Usa Intake para crear uno.</div>}
          </div>
        </Card>
      </section>
    </div>
  );
}
