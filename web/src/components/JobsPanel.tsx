import { useEffect, useMemo, useState } from 'react';
import { Boxes, RefreshCw } from 'lucide-react';
import { flujoApi, type JobItem, type JobsResponse } from '../api/flujoApi';

function statusColor(status?: string) {
  const s = String(status || '').toLowerCase();
  if (s.includes('entregado')) return 'border-green-500/20 bg-green-500/10 text-green-400';
  if (s.includes('revision') || s.includes('revis')) return 'border-blue-500/20 bg-blue-500/10 text-blue-400';
  if (s.includes('diseno') || s.includes('dise')) return 'border-purple-500/20 bg-purple-500/10 text-purple-400';
  if (s.includes('pendiente')) return 'border-yellow-500/20 bg-yellow-500/10 text-yellow-400';
  return 'border-zinc-700 bg-zinc-800/40 text-zinc-400';
}

function JobCard({ job }: { job: JobItem }) {
  const pendientes = Array.isArray(job.pendientes) ? job.pendientes : job.pendientes ? [String(job.pendientes)] : [];
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/45 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-bold">{job.name}</h3>
          <p className="mt-1 truncate font-mono text-[10px] text-zinc-600">{job.path || '(sin path)'}</p>
        </div>
        <span className={`shrink-0 rounded-full border px-2 py-1 text-[10px] font-bold uppercase tracking-widest ${statusColor(job.estado)}`}>{job.estado || 'sin estado'}</span>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2 text-xs text-zinc-500">
        <div><span className="text-zinc-700">pieza:</span> {job.tipo_pieza || '—'}</div>
        <div><span className="text-zinc-700">proyecto:</span> {job.proyecto || '—'}</div>
      </div>
      {pendientes.length > 0 && (
        <div className="mt-3 rounded-xl bg-black/25 p-3">
          <div className="mb-1 text-[10px] font-bold uppercase tracking-widest text-zinc-600">Pendientes</div>
          <ul className="space-y-1 text-xs text-zinc-400">
            {pendientes.slice(0, 4).map((p, i) => <li key={i}>• {p}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function JobsPanel() {
  const [jobs, setJobs] = useState<JobsResponse | null>(null);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);

  const load = () => {
    setLoading(true);
    flujoApi.jobs().then(setJobs).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const filtered = useMemo(() => {
    const q = query.toLowerCase().trim();
    return (jobs?.jobs || []).filter(job => !q || [job.name, job.estado, job.tipo_pieza, job.proyecto].some(v => String(v || '').toLowerCase().includes(q)));
  }, [jobs, query]);

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-black"><Boxes className="h-6 w-6" /> Jobs</h1>
          <p className="mt-1 text-sm text-zinc-500">Lista real desde `/api/list-jobs` con fallback demo.</p>
        </div>
        <button onClick={load} className="flex items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs font-bold text-zinc-300 hover:bg-zinc-800">
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> Refrescar
        </button>
      </div>
      <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Filtrar por nombre, estado, pieza..." className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm outline-none focus:border-zinc-600" />
      {jobs?.error && <div className="rounded-xl border border-yellow-900/60 bg-yellow-950/20 p-3 text-xs text-yellow-300">Fallback activo: {jobs.error}</div>}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {filtered.map(job => <JobCard key={job.path || job.name} job={job} />)}
      </div>
      {!filtered.length && <div className="rounded-2xl border border-dashed border-zinc-800 p-10 text-center text-zinc-500">No hay jobs para mostrar.</div>}
    </div>
  );
}
