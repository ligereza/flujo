// AutomatizacionesPanel — la cola real de las cadenas automaticas.
//
// La cadena completa es:
//   Entrada externa -> contrato revisado -> runner de FLUJO
//   -> descarga/render acotado -> salida revisada
//
// El tramo Gmail -> issue vive FUERA de este repo. Este panel cubre el hueco
// que quedaba: hasta ahora la unica forma de saber que habia pendiente era
// entrar a GitHub a mano.
//
// No dispara nada por si mismo a proposito: el runner procesa el issue
// etiquetado y el panel solo muestra la cola observable.

import { useEffect, useState } from 'react';
import { Workflow, AlertTriangle, Inbox, Ban, ExternalLink } from 'lucide-react';

interface Item {
  numero: number;
  titulo: string;
  url: string;
  creado: string;
  labels: string[];
  estado: string;
  area: string;
  accion: string;
  prioridad: string;
  origen: string;
  bloqueado: boolean;
}
interface Data {
  cola: Item[];
  disponible: boolean;
  motivo?: string;
  error?: string;
  resumen?: {
    abiertos: number;
    bloqueados: number;
    por_estado: Record<string, number>;
    por_area: Record<string, number>;
    por_accion: Record<string, number>;
  };
}

const CHIP: Record<string, string> = {
  gmail: 'bg-red-950/50 text-red-300 border-red-900/60',
  instagram: 'bg-pink-950/50 text-pink-300 border-pink-900/60',
};

export default function AutomatizacionesPanel() {
  const [data, setData] = useState<Data | null>(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    let vivo = true;
    fetch('/api/automatizaciones')
      .then(r => r.json())
      .then(d => vivo && setData(d))
      .catch(() => vivo && setData({ cola: [], disponible: false, motivo: 'sin backend (corre py -m flujo app)' }))
      .finally(() => vivo && setCargando(false));
    return () => {
      vivo = false;
    };
  }, []);

  const r = data?.resumen;
  const sinEtiquetar = (data?.cola || []).filter(i => !i.estado && !i.area && !i.accion).length;

  return (
    <div className="space-y-6">
      <header className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-sky-900/40 text-sky-300">
          <Workflow className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-xl font-bold tracking-tight">Automatizaciones</h1>
          <p className="text-sm text-zinc-500">
            Cola de pedidos que entran por Gmail y salen renderizados. Lo que antes había que ir a mirar a GitHub.
          </p>
        </div>
      </header>

      {/* La cadena, siempre visible: es el mapa mental de como funciona esto. */}
      <div className="flex flex-wrap items-center gap-2 rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 text-[12px]">
        {['Entrada externa', 'contrato revisado', 'runner FLUJO', 'descarga + render', 'salida revisada', 'cerrado'].map(
          (paso, i, arr) => (
            <span key={paso} className="flex items-center gap-2">
              <span className="rounded-md border border-zinc-800 bg-zinc-950 px-2 py-1 text-zinc-400">{paso}</span>
              {i < arr.length - 1 && <span className="text-zinc-700">→</span>}
            </span>
          ),
        )}
      </div>

      {cargando && <div className="text-sm text-zinc-600">Consultando la cola…</div>}

      {!cargando && data && !data.disponible && (
        <div className="flex items-start gap-2 rounded-xl border border-amber-800/50 bg-amber-950/30 p-4 text-sm text-amber-300">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <strong>No se pudo leer la cola.</strong>
            <div className="mt-1 text-[13px] text-amber-400/80">{data.motivo || data.error}</div>
            <div className="mt-2 text-[12px] text-amber-400/60">
              Necesita <code>gh</code> instalado y autenticado. La cola vive en GitHub, no en el repo.
            </div>
          </div>
        </div>
      )}

      {!cargando && data?.disponible && r && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { k: 'Abiertos', v: r.abiertos, i: Inbox },
              { k: 'Bloqueados', v: r.bloqueados, i: Ban },
              { k: 'Sin etiquetar', v: sinEtiquetar, i: AlertTriangle },
              { k: 'Áreas activas', v: Object.keys(r.por_area).filter(k => k !== '(sin)').length, i: Workflow },
            ].map(c => {
              const Icon = c.i;
              return (
                <div key={c.k} className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4">
                  <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest text-zinc-600">
                    <Icon className="h-3 w-3" />
                    {c.k}
                  </div>
                  <div className="mt-1 text-2xl font-black text-zinc-100">{c.v}</div>
                </div>
              );
            })}
          </div>

          {sinEtiquetar > 0 && sinEtiquetar === r.abiertos && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 text-[13px] text-zinc-400">
              El sistema de labels existe (<code className="text-zinc-300">estado/</code>,{' '}
              <code className="text-zinc-300">area/</code>, <code className="text-zinc-300">action/</code>) pero{' '}
              <strong className="text-zinc-200">ninguno de los issues abiertos lo usa</strong>. La cadena automática no
              los va a tomar: el workflow filtra por label.
            </div>
          )}

          <section className="rounded-xl border border-zinc-800 bg-zinc-900/40">
            <div className="border-b border-zinc-800 px-4 py-3 text-sm font-bold">Cola</div>
            <div className="divide-y divide-zinc-800/60">
              {data.cola.map(i => (
                <div key={i.numero} className="flex items-start gap-3 px-4 py-3">
                  <span className="mt-0.5 font-mono text-[12px] text-zinc-600">#{i.numero}</span>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm text-zinc-200">{i.titulo}</div>
                    <div className="mt-1 flex flex-wrap items-center gap-1.5">
                      {i.origen && (
                        <span className={`rounded border px-1.5 py-px text-[10px] ${CHIP[i.origen] || 'border-zinc-800 text-zinc-500'}`}>
                          {i.origen}
                        </span>
                      )}
                      {i.estado && (
                        <span className="rounded border border-sky-900/60 bg-sky-950/40 px-1.5 py-px text-[10px] text-sky-300">
                          {i.estado}
                        </span>
                      )}
                      {i.area && (
                        <span className="rounded border border-emerald-900/60 bg-emerald-950/40 px-1.5 py-px text-[10px] text-emerald-300">
                          {i.area}
                        </span>
                      )}
                      {i.accion && (
                        <span className="rounded border border-violet-900/60 bg-violet-950/40 px-1.5 py-px text-[10px] text-violet-300">
                          {i.accion}
                        </span>
                      )}
                      {i.bloqueado && (
                        <span className="rounded border border-red-900/60 bg-red-950/40 px-1.5 py-px text-[10px] text-red-300">
                          bloqueado
                        </span>
                      )}
                      <span className="text-[10px] text-zinc-700">{i.creado}</span>
                    </div>
                  </div>
                  {i.url && (
                    <a
                      href={i.url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-0.5 shrink-0 text-zinc-600 hover:text-zinc-300"
                      title="Abrir en GitHub"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  )}
                </div>
              ))}
              {data.cola.length === 0 && (
                <div className="px-4 py-6 text-center text-[13px] text-zinc-600">
                  Cola vacía. Ojo: puede ser que no haya pedidos, o que el tramo Gmail → issue se haya cortado.
                </div>
              )}
            </div>
          </section>
        </>
      )}

    </div>
  );
}
