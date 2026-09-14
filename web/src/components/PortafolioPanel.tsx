// PortafolioPanel — the public iskvw catalogue, visible from the app.
//
// iskvw is the portfolio and the ONLY site (user's decision, 2026-07-26), but
// the interface had no way to see it: the catalogue existed only as a json you
// had to open by hand, and the prototype as a loose file.
//
// READ, not edit. Editing `tools/portfolio/proyectos.json` IS administering the
// site, and that is done deliberately, not by accident from a screen. This panel
// answers "what is published, in what state, and what is missing".
//
// Visible copy stays in Spanish: this is what the user reads.

import { useEffect, useState } from 'react';
import { Layers, CircleDot, FileText, AlertTriangle } from 'lucide-react';
import {
  fetchPortfolioCatalog,
  type PortfolioCatalog,
  type PortfolioProject,
} from '../data/portfolio';

const COLOR_ESTADO: Record<string, string> = {
  activo: 'border-emerald-700 text-emerald-300',
  investigacion: 'border-amber-700 text-amber-300',
  v0: 'border-neutral-700 text-neutral-400',
  archivo: 'border-neutral-800 text-neutral-500',
};

export default function PortafolioPanel() {
  const [data, setData] = useState<PortfolioCatalog | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [linea, setLinea] = useState<string>('todas');

  useEffect(() => {
    fetchPortfolioCatalog()
      .then(setData)
      .catch(e => setError(String(e)))
      .finally(() => setCargando(false));
  }, []);

  if (cargando) return <div className="p-6 text-sm text-neutral-400">Leyendo el catálogo…</div>;

  if (error) {
    return (
      <div className="p-6">
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle className="w-5 h-5 text-amber-400" />
          <h2 className="text-lg font-semibold">No se pudo leer el catálogo</h2>
        </div>
        <pre className="text-xs text-neutral-500 whitespace-pre-wrap">{error}</pre>
      </div>
    );
  }

  const proyectos: PortfolioProject[] = data?.proyectos ?? [];
  const lineas = ['todas', ...Array.from(new Set(proyectos.map(p => p.linea)))];
  const visibles = linea === 'todas' ? proyectos : proyectos.filter(p => p.linea === linea);
  const activos = proyectos.filter(p => p.estado === 'activo').length;

  return (
    <div className="p-6 space-y-5">
      <div>
        <div className="flex items-center gap-2">
          <Layers className="w-5 h-5 text-fuchsia-400" />
          <h2 className="text-lg font-semibold">Portafolio · iskvw</h2>
        </div>
        <p className="text-sm text-neutral-400 mt-1">
          Lo que hoy publica el sitio. {proyectos.length} proyectos, {activos} activos.
          Este panel muestra el catálogo; para cambiarlo se edita{' '}
          <code className="text-neutral-300">tools/portfolio/proyectos.json</code>, que es
          la fuente que el workflow publica.
        </p>
      </div>

      <div className="rounded border border-neutral-800 p-3 text-sm">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-neutral-500" />
          <span className="text-neutral-300">Prototipo de archivo</span>
          {data?.prototipo_generado ? (
            <span className="text-xs px-2 py-0.5 rounded border border-emerald-700 text-emerald-300">
              generado
            </span>
          ) : (
            <span className="text-xs px-2 py-0.5 rounded border border-amber-700 text-amber-300">
              sin generar
            </span>
          )}
        </div>
        <p className="text-xs text-neutral-500 mt-1">
          {data?.prototipo_generado
            ? `Abrí ${data.prototipo_ruta} en el navegador. Se regenera con: py tools/gen_iskvw_prototipo.py --out ${data.prototipo_ruta}`
            : 'Generalo con: py tools/gen_iskvw_prototipo.py --out docs/iskvw/prototipo.html'}
        </p>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {lineas.map(l => (
          <button
            key={l}
            onClick={() => setLinea(l)}
            className={
              'text-xs px-2.5 py-1 rounded border transition ' +
              (linea === l
                ? 'border-fuchsia-600 text-fuchsia-300'
                : 'border-neutral-800 text-neutral-400 hover:text-neutral-200')
            }
          >
            {l}
          </button>
        ))}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {visibles.map(p => (
          <article key={p.id} className="rounded border border-neutral-800 p-3">
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-sm font-semibold text-neutral-100">{p.nombre}</h3>
              <span
                className={
                  'text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded border shrink-0 ' +
                  (COLOR_ESTADO[p.estado] ?? 'border-neutral-800 text-neutral-500')
                }
              >
                {p.estado}
              </span>
            </div>
            <div className="text-[11px] uppercase tracking-wide text-neutral-500 mt-0.5 flex items-center gap-1">
              <CircleDot className="w-3 h-3" />
              {p.linea}
            </div>
            <p className="text-xs text-neutral-400 mt-2 line-clamp-4">{p.descripcion}</p>
            <div className="flex flex-wrap gap-1 mt-2">
              {p.tags.map(t => (
                <span
                  key={t}
                  className="text-[10px] px-1.5 py-0.5 rounded-full border border-neutral-800 text-neutral-500"
                >
                  {t}
                </span>
              ))}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
