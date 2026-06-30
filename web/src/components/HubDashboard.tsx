import { useEffect, useMemo, useState } from 'react';
import {
  LayoutDashboard, Boxes, ClipboardList, Calculator,
  TerminalSquare, Map, Shapes, Zap, Activity,
  CheckCircle2, Clock, AlertCircle, ArrowRight, Camera, Radio,
} from 'lucide-react';
import type { AppView } from './AppShell';
import { flujoApi, type Ping, type JobsResponse } from '../api/flujoApi';

interface Props {
  onNavigate: (v: AppView) => void;
}

export default function HubDashboard({ onNavigate }: Props) {
  const [ping, setPing] = useState<Ping | null>(null);
  const [jobs, setJobs] = useState<JobsResponse | null>(null);

  useEffect(() => {
    let alive = true;
    flujoApi.ping().then(d => alive && setPing(d));
    flujoApi.jobs().then(d => alive && setJobs(d));
    return () => { alive = false; };
  }, []);

  const openJobs = jobs?.jobs.filter(j => !String(j.estado || '').toLowerCase().includes('entregado')).length ?? 0;
  const recent = useMemo(() => (jobs?.jobs || []).slice(0, 5), [jobs]);

  const actions = [
    { view: 'visualizer' as const, icon: Shapes, title: 'SVG Studio', desc: 'Galería de piezas + Config Editor visual con texto, alineado y distribución', color: 'from-violet-500 to-purple-600', badge: '✨ mejorado' },
    { view: 'intake' as const, icon: ClipboardList, title: 'Pegar Pedido', desc: 'Parsear correo/texto y crear job draft', color: 'from-blue-500 to-cyan-600' },
    { view: 'jobs' as const, icon: Boxes, title: 'Ver Jobs', desc: 'Estado real de la carpeta jobs/', color: 'from-yellow-500 to-amber-600' },
    { view: 'plano' as const, icon: Map, title: 'Plano / Rider', desc: 'Preparar layout, rider y SVG de evento', color: 'from-emerald-500 to-teal-600' },
    { view: 'quote' as const, icon: Calculator, title: 'Cotización', desc: 'Base editable para productora/jefatura', color: 'from-pink-500 to-rose-600' },
    { view: 'commands' as const, icon: TerminalSquare, title: 'Comandos', desc: 'Copiar checks y build', color: 'from-zinc-400 to-zinc-600' },
    { view: 'events' as const, icon: Camera, title: 'Eventos / IG', desc: 'Descarga Instagram y pipeline flyer-auto para Studio', color: 'from-fuchsia-500 to-violet-600', badge: 'Studio' },
    { view: 'resolume' as const, icon: Radio, title: 'Resolume / Chataigne', desc: 'Generar XML pre-flight SMPTE/OSC para shows', color: 'from-indigo-500 to-blue-600', badge: 'SMPTE' },
  ];

  const statusColor = (s?: string) => {
    const v = String(s || '').toLowerCase();
    if (v.includes('entregado')) return 'text-emerald-400 bg-emerald-500/10';
    if (v.includes('revision') || v.includes('revis')) return 'text-blue-400 bg-blue-500/10';
    if (v.includes('diseno') || v.includes('dise')) return 'text-purple-400 bg-purple-500/10';
    if (v.includes('pendiente')) return 'text-yellow-400 bg-yellow-500/10';
    return 'text-zinc-400 bg-zinc-800';
  };

  return (
    <div className="space-y-8">
      {/* Hero header */}
      <div className="relative overflow-hidden rounded-2xl border border-zinc-800/70 bg-gradient-to-br from-zinc-900 via-zinc-900 to-zinc-800 p-6 md:p-8">
        <div className="absolute right-0 top-0 h-64 w-64 bg-gradient-to-bl from-emerald-500/5 to-transparent" />
        <div className="relative">
          <div className="flex items-center gap-3 mb-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 shadow-lg shadow-emerald-500/20">
              <Zap className="h-5 w-5 text-white" />
            </div>
            <div>
              <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider
                ${ping?.connected !== false ? 'border-emerald-800 bg-emerald-950/50 text-emerald-400' : 'border-zinc-700 bg-zinc-800/50 text-zinc-400'}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${ping?.connected !== false ? 'bg-emerald-400 animate-pulse' : 'bg-zinc-500'}`} />
                {ping?.connected !== false ? 'backend local' : 'modo demo'}
              </span>
            </div>
          </div>
          <h1 className="text-2xl font-black tracking-tight md:text-3xl">Workspace operativo flujo</h1>
          <p className="mt-2 max-w-xl text-sm text-zinc-400 leading-relaxed">
            Entrada diaria para convertir pedidos en jobs trazables, revisar SVGs reales, preparar planos/riders y mantener continuidad entre agentes.
          </p>
        </div>

        {/* Stats row */}
        <div className="relative mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
          {[
            { label: 'Jobs abiertos', value: openJobs, icon: Activity, color: 'text-amber-400' },
            { label: 'Total jobs', value: jobs?.count ?? 0, icon: Boxes, color: 'text-blue-400' },
            { label: 'Versión', value: ping?.version || '0.47.13', icon: LayoutDashboard, color: 'text-emerald-400' },
            { label: 'Estado', value: ping?.connected !== false ? 'Conectado' : 'Demo', icon: ping?.connected !== false ? CheckCircle2 : AlertCircle, color: ping?.connected !== false ? 'text-emerald-400' : 'text-zinc-400' },
          ].map(stat => {
            const Icon = stat.icon;
            return (
              <div key={stat.label} className="rounded-xl border border-zinc-800/60 bg-black/30 p-3">
                <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-zinc-500">
                  <Icon className={`h-3.5 w-3.5 ${stat.color}`} />
                  {stat.label}
                </div>
                <div className="mt-1 text-lg font-bold">{stat.value}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Quick actions grid */}
      <div>
        <div className="mb-4 flex items-center gap-2">
          <h2 className="text-lg font-bold">Acciones rápidas</h2>
          <span className="text-xs text-zinc-500">operación diaria</span>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {actions.map(item => {
            const Icon = item.icon;
            return (
              <button
                key={item.view}
                onClick={() => onNavigate(item.view)}
                className="group relative overflow-hidden rounded-xl border border-zinc-800/60 bg-zinc-900/50 p-5 text-left transition-all hover:border-zinc-700 hover:bg-zinc-800/50 hover:shadow-lg"
              >
                <div className={`absolute inset-0 bg-gradient-to-br ${item.color} opacity-0 transition-opacity group-hover:opacity-[0.03]`} />
                <div className="relative">
                  <div className="flex items-start justify-between">
                    <div className={`flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br ${item.color} shadow-lg`}>
                      <Icon className="h-5 w-5 text-white" />
                    </div>
                    {'badge' in item && item.badge && (
                      <span className="rounded-full bg-violet-500/20 px-2 py-0.5 text-[10px] font-bold text-violet-300">
                        {item.badge}
                      </span>
                    )}
                  </div>
                  <h3 className="mt-3 text-sm font-bold">{item.title}</h3>
                  <p className="mt-1 text-xs text-zinc-500">{item.desc}</p>
                  <div className="mt-3 flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-zinc-600 group-hover:text-zinc-400">
                    Abrir <ArrowRight className="h-3 w-3" />
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Recent jobs */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold">Jobs recientes</h2>
          <button onClick={() => onNavigate('jobs')} className="text-xs text-zinc-500 hover:text-zinc-300 flex items-center gap-1">
            Ver todos <ArrowRight className="h-3 w-3" />
          </button>
        </div>
        <div className="space-y-2">
          {recent.length ? recent.map(job => (
            <div key={job.path || job.name} className="flex items-center gap-4 rounded-xl border border-zinc-800/50 bg-zinc-900/30 p-3 transition-colors hover:bg-zinc-800/30">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-zinc-800">
                <Boxes className="h-4 w-4 text-zinc-500" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium truncate">{job.name}</div>
                <div className="text-[10px] text-zinc-600 truncate">{job.tipo_pieza || 'pieza'} · {job.proyecto || '—'}</div>
              </div>
              <span className={`shrink-0 rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider ${statusColor(job.estado)}`}>
                {job.estado || 'sin estado'}
              </span>
              <Clock className="h-3.5 w-3.5 text-zinc-700" />
            </div>
          )) : (
            <div className="rounded-xl border border-dashed border-zinc-800 p-8 text-center text-sm text-zinc-600">
              Sin jobs reales todavía. Usa <strong>Intake</strong> para crear uno.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
