import { useRef, useState } from 'react';
import { Settings2, Download, Upload, RotateCcw, Save, AlertTriangle, Building2 } from 'lucide-react';
import PlanoTool from './PlanoTool';
import { RD_PRODUCTORAS } from '../data/productoras';
import {
  type PlanoConfig, applyPlanoConfig, savePlanoConfig, downloadPlanoConfig, readPlanoConfigFile,
} from '../data/planoConfig';
import { type PackId, PACKS, PACKS_DEFAULT_PRICES, resetPackPrices, formatCLP } from '../rdBrand';

// PlanoStandalone — shell del bundle standalone (web/src/mainPlano.tsx).
// Envuelve PlanoTool (sin tocarlo) con un panel de configuracion en runtime:
// precios de packs editables + import/export de esa config como .json, mas
// la lista de productoras RD embebida como referencia.
//
// ALCANCE, al 2026-07-27: los iconos propios y los presets de layout YA estan.
// El comentario anterior decia que faltaban y que requerian puntos de extension
// en PlanoTool.tsx que no existian; se agregaron ahi mismo (exportar/importar
// preset, alta de simbolo con guardado local, trazador en el navegador). Lo que
// sigue sin estar es asociar un preset a una productora DESDE aca: eso lo hace
// el director contra la base y devuelve el archivo.

const PACK_IDS: PackId[] = ['INFO', 'TESTEO', 'COMPLETO'];
const PACK_NAMES: Record<PackId, string> = {
  INFO: 'Pack 1 · Informativo',
  TESTEO: 'Pack 2 · Testeo y Informativo',
  COMPLETO: 'Pack 3 · Servicio Completo',
};

interface Props {
  initialConfig: PlanoConfig;
  initialWarning: string | null;
}

export default function PlanoStandalone({ initialConfig, initialWarning }: Props) {
  const [config, setConfig] = useState<PlanoConfig>(initialConfig);
  const [priceDrafts, setPriceDrafts] = useState<Record<PackId, string>>(() => {
    const drafts = {} as Record<PackId, string>;
    for (const id of PACK_IDS) drafts[id] = String(PACKS[id].precio);
    return drafts;
  });
  const [banner, setBanner] = useState<string | null>(initialWarning);
  const [status, setStatus] = useState<string | null>(null);
  const [remountKey, setRemountKey] = useState(0);
  const [panelOpen, setPanelOpen] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refreshDraftsFromLive = () => {
    setPriceDrafts(() => {
      const drafts = {} as Record<PackId, string>;
      for (const id of PACK_IDS) drafts[id] = String(PACKS[id].precio);
      return drafts;
    });
  };

  const commit = (next: PlanoConfig, message: string) => {
    applyPlanoConfig(next);
    savePlanoConfig(next);
    setConfig(next);
    refreshDraftsFromLive();
    setRemountKey(k => k + 1); // PlanoTool lee PACKS en vivo, pero fuerza un remount para que se vea al toque.
    setStatus(message);
    setBanner(null);
  };

  const savePrices = () => {
    const packPrices = { ...config.packPrices };
    let bad = false;
    for (const id of PACK_IDS) {
      const n = Number(priceDrafts[id]);
      if (!Number.isFinite(n) || n <= 0) { bad = true; continue; }
      packPrices[id] = Math.round(n);
    }
    if (bad) {
      setStatus('Algún precio no es un número válido (> 0): no se guardó nada.');
      return;
    }
    commit({ ...config, packPrices }, 'Precios guardados y aplicados.');
  };

  const resetPrices = () => {
    resetPackPrices();
    commit({ ...config, packPrices: {} }, 'Precios restablecidos al valor de fabrica.');
  };

  const exportConfig = () => {
    downloadPlanoConfig(config);
    setStatus('Configuracion exportada (revisa la carpeta de descargas).');
  };

  const importConfig = async (file: File) => {
    const result = await readPlanoConfigFile(file);
    if (!result.ok) {
      setStatus(`Import fallo: ${result.warning}`);
      return;
    }
    commit(result.config, 'Configuracion importada y aplicada.');
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800/70 px-4 py-3 sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h1 className="text-sm font-bold tracking-tight">Plano / Rider RD</h1>
            <p className="text-[10px] text-zinc-500">Herramienta compartida — sin backend, todo corre en este archivo</p>
          </div>
          <button
            onClick={() => setPanelOpen(o => !o)}
            className="flex items-center gap-1.5 rounded-lg border border-zinc-700/70 px-3 py-1.5 text-[11px] font-bold text-zinc-300 hover:bg-zinc-800/60"
          >
            <Settings2 className="h-3.5 w-3.5" />
            {panelOpen ? 'Ocultar configuración' : 'Configuración'}
          </button>
        </div>
      </header>

      {panelOpen && (
        <div className="border-b border-zinc-800/70 bg-zinc-900/40 px-4 py-4 sm:px-6">
          {banner && (
            <div className="mb-3 flex items-start gap-2 rounded-lg border border-amber-700/50 bg-amber-950/40 px-3 py-2 text-[11px] text-amber-300">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span>{banner}</span>
            </div>
          )}
          {status && (
            <div className="mb-3 rounded-lg border border-zinc-700/60 bg-zinc-800/50 px-3 py-2 text-[11px] text-zinc-300">
              {status}
            </div>
          )}

          <div className="grid gap-4 lg:grid-cols-2">
            {/* Precios de packs */}
            <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-3">
              <div className="mb-2 text-[10px] font-bold uppercase tracking-widest text-zinc-500">
                Precios de packs (editable, sin recompilar)
              </div>
              <div className="space-y-2">
                {PACK_IDS.map(id => (
                  <div key={id} className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="truncate text-xs font-medium text-zinc-200">{PACK_NAMES[id]}</div>
                      <div className="text-[9px] text-zinc-600">valor de fabrica: {formatCLP(PACKS_DEFAULT_PRICES[id])}</div>
                    </div>
                    <input
                      type="number"
                      min={1}
                      value={priceDrafts[id]}
                      onChange={e => setPriceDrafts(d => ({ ...d, [id]: e.target.value }))}
                      className="w-28 shrink-0 rounded-lg border border-zinc-700 bg-zinc-900 px-2 py-1.5 text-right text-xs text-zinc-100 focus:border-sky-600 focus:outline-none"
                    />
                  </div>
                ))}
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button onClick={savePrices} className="flex items-center gap-1.5 rounded-lg bg-sky-700/80 px-3 py-1.5 text-[11px] font-bold text-white hover:bg-sky-600">
                  <Save className="h-3.5 w-3.5" /> Guardar precios
                </button>
                <button onClick={resetPrices} className="flex items-center gap-1.5 rounded-lg border border-zinc-700 px-3 py-1.5 text-[11px] font-bold text-zinc-300 hover:bg-zinc-800/60">
                  <RotateCcw className="h-3.5 w-3.5" /> Restablecer
                </button>
              </div>
            </div>

            {/* Config import/export + productoras */}
            <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-3">
              <div className="mb-2 text-[10px] font-bold uppercase tracking-widest text-zinc-500">
                Configuracion (archivo .json)
              </div>
              <p className="mb-2 text-[10px] leading-relaxed text-zinc-500">
                Exporta este archivo para respaldar tus cambios o mandarlos de vuelta.
                Importarlo aplica sus precios de inmediato.
              </p>
              <div className="flex flex-wrap gap-2">
                <button onClick={exportConfig} className="flex items-center gap-1.5 rounded-lg border border-zinc-700 px-3 py-1.5 text-[11px] font-bold text-zinc-300 hover:bg-zinc-800/60">
                  <Download className="h-3.5 w-3.5" /> Exportar configuración
                </button>
                <button onClick={() => fileInputRef.current?.click()} className="flex items-center gap-1.5 rounded-lg border border-zinc-700 px-3 py-1.5 text-[11px] font-bold text-zinc-300 hover:bg-zinc-800/60">
                  <Upload className="h-3.5 w-3.5" /> Importar configuración
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="application/json"
                  className="hidden"
                  onChange={e => {
                    const f = e.target.files?.[0];
                    if (f) void importConfig(f);
                    e.target.value = '';
                  }}
                />
              </div>

              <div className="mt-4 border-t border-zinc-800 pt-3">
                <div className="mb-1.5 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest text-zinc-500">
                  <Building2 className="h-3 w-3" /> Productoras RD (referencia)
                </div>
                <p className="mb-1.5 text-[9px] text-zinc-600">
                  Lista embebida. Para asociar un plano a una productora: armá el
                  layout, usá <b>Guardar preset</b> y mandá ese archivo; vuelve
                  asociado y se abre con <b>Abrir preset</b>.
                </p>
                <div className="max-h-24 overflow-y-auto rounded-lg border border-zinc-800 bg-zinc-900/60 p-2 text-[10px] text-zinc-400">
                  {RD_PRODUCTORAS.map(p => p.name).join(' · ')}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="p-2 sm:p-4">
        <PlanoTool key={remountKey} />
      </div>
    </div>
  );
}
