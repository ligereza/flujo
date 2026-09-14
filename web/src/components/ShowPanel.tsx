import { ExternalLink, Radio, ShieldCheck } from 'lucide-react';

/**
 * FLUJO owns the ISKVW/FOH context. The mobile runtime and its show controls
 * live in the separate XIO repository, so this panel deliberately exposes the
 * boundary instead of pretending that XIO is a local directory.
 */
export default function ShowPanel() {
  return (
    <div className="space-y-6">
      <header className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-violet-900/40 text-violet-300">
          <Radio className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-xl font-bold tracking-tight">FOH / ISKVW</h1>
          <p className="text-sm text-zinc-500">
            Contexto visual y de show de FLUJO; el runtime móvil se mantiene fuera de este repo.
          </p>
        </div>
      </header>

      <section className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5">
        <div className="flex items-center gap-2 text-sm font-bold">
          <ShieldCheck className="h-4 w-4 text-emerald-400" />
          Frontera de integración
        </div>
        <p className="mt-3 text-sm leading-relaxed text-zinc-400">
          FLUJO conserva los perfiles ISKVW, las vistas VJ y los contratos de lectura.
          XIO-FOH consume ese contexto desde su propio repositorio y maneja la superficie
          móvil/FOH. Un fallo del teléfono no convierte el contexto de FLUJO en escritura
          ni mueve el runtime de XIO aquí.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg border border-zinc-800 bg-zinc-950/50 p-3">
            <div className="text-[10px] font-bold uppercase tracking-widest text-violet-300">FLUJO</div>
            <div className="mt-1 text-sm text-zinc-300">ISKVW, VJ, portafolio y contratos</div>
            <div className="mt-1 text-[11px] text-zinc-600">lectura y proyección revisada</div>
          </div>
          <div className="rounded-lg border border-zinc-800 bg-zinc-950/50 p-3">
            <div className="text-[10px] font-bold uppercase tracking-widest text-sky-300">XIO-FOH</div>
            <div className="mt-1 text-sm text-zinc-300">campo móvil y operación del teléfono</div>
            <div className="mt-1 text-[11px] text-zinc-600">repositorio externo: ligereza/XIO</div>
          </div>
        </div>
        <a
          href="https://github.com/ligereza/XIO"
          target="_blank"
          rel="noreferrer"
          className="mt-4 inline-flex items-center gap-2 rounded-lg border border-violet-800/50 px-3 py-2 text-xs font-semibold text-violet-300 hover:border-violet-600"
        >
          Abrir repositorio XIO
          <ExternalLink className="h-3.5 w-3.5" />
        </a>
      </section>
    </div>
  );
}
