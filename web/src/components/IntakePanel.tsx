import { useState } from 'react';
import { ClipboardList, Loader2, PlusCircle, Wand2 } from 'lucide-react';
import { flujoApi, type CreateJobResponse, type ParsePedidoResponse } from '../api/flujoApi';

const sample = 'Suplementos - modificar etiqueta Omega 3. Necesito formato etiqueta 16.5x6.5 cm, agregar tabla nutricional y preparar post Instagram.';

export default function IntakePanel() {
  const [text, setText] = useState(sample);
  const [name, setName] = useState('');
  const [parsed, setParsed] = useState<ParsePedidoResponse | null>(null);
  const [created, setCreated] = useState<CreateJobResponse | null>(null);
  const [busy, setBusy] = useState<'parse' | 'create' | null>(null);

  const parse = async () => {
    setBusy('parse');
    setCreated(null);
    try { setParsed(await flujoApi.parsePedido(text)); }
    catch (error) { setParsed({ error: error instanceof Error ? error.message : String(error) }); }
    finally { setBusy(null); }
  };

  const create = async () => {
    setBusy('create');
    try { setCreated(await flujoApi.createJobDraft(text, name)); }
    catch (error) { setCreated({ created: false, error: error instanceof Error ? error.message : String(error) }); }
    finally { setBusy(null); }
  };

  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_420px]">
      <section className="space-y-4">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-black"><ClipboardList className="h-6 w-6" /> Intake</h1>
          <p className="mt-1 text-sm text-zinc-500">Pega un correo/pedido, parsea con la lógica real y crea un job draft.</p>
        </div>
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/45 p-4">
          <label className="mb-2 block text-[10px] font-bold uppercase tracking-widest text-zinc-500">Nombre opcional del job</label>
          <input value={name} onChange={e => setName(e.target.value)} placeholder="ej: suplementos omega 3" className="mb-4 w-full rounded-xl border border-zinc-800 bg-black/40 px-4 py-3 text-sm outline-none focus:border-zinc-600" />
          <label className="mb-2 block text-[10px] font-bold uppercase tracking-widest text-zinc-500">Pedido</label>
          <textarea value={text} onChange={e => setText(e.target.value)} rows={14} className="w-full rounded-xl border border-zinc-800 bg-black/40 px-4 py-3 text-sm leading-6 outline-none focus:border-zinc-600" />
          <div className="mt-4 flex flex-wrap gap-2">
            <button onClick={parse} disabled={busy !== null} className="flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-bold text-black hover:bg-zinc-200 disabled:opacity-60">
              {busy === 'parse' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />} Parsear
            </button>
            <button onClick={create} disabled={busy !== null} className="flex items-center gap-2 rounded-lg border border-emerald-800/60 bg-emerald-950/40 px-4 py-2 text-sm font-bold text-emerald-200 hover:bg-emerald-900/50 disabled:opacity-60">
              {busy === 'create' ? <Loader2 className="h-4 w-4 animate-spin" /> : <PlusCircle className="h-4 w-4" />} Crear job draft
            </button>
          </div>
        </div>
      </section>

      <aside className="space-y-4">
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/45 p-4">
          <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-zinc-500">Parse result</h2>
          {parsed ? (
            <div className="space-y-3">
              {parsed.error && <div className="rounded-lg border border-red-900/60 bg-red-950/30 p-3 text-xs text-red-300">{parsed.error}</div>}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <Info label="Tipo" value={parsed.tipo} />
                <Info label="Formato" value={parsed.formato} />
                <Info label="Medidas" value={parsed.medidas} />
                <Info label="Tool" value={parsed.tool} />
              </div>
              {!!parsed.warnings?.length && <div className="rounded-lg bg-black/30 p-3 text-xs text-yellow-300">{parsed.warnings.map((w, i) => <div key={i}>• {w}</div>)}</div>}
              <pre className="max-h-72 overflow-auto rounded-lg bg-black/40 p-3 text-[10px] text-zinc-500">{JSON.stringify(parsed, null, 2)}</pre>
            </div>
          ) : <p className="text-sm text-zinc-500">Aun no parseado.</p>}
        </div>

        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/45 p-4">
          <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-zinc-500">Job draft</h2>
          {created ? (
            <div className="space-y-3 text-sm">
              <div className={created.created ? 'text-emerald-300' : 'text-yellow-300'}>{created.created ? 'Job creado' : 'No creado'}</div>
              {created.name && <Info label="Nombre" value={created.name} />}
              {created.job_path && <Info label="Path" value={created.job_path} />}
              {created.next && <code className="block rounded-lg bg-black/40 p-3 text-xs text-zinc-300">{created.next}</code>}
              {created.error && <div className="rounded-lg border border-red-900/60 bg-red-950/30 p-3 text-xs text-red-300">{created.error}</div>}
            </div>
          ) : <p className="text-sm text-zinc-500">Usa Crear job draft para escribir en jobs/.</p>}
        </div>
      </aside>
    </div>
  );
}

function Info({ label, value }: { label: string; value: unknown }) {
  return <div className="rounded-lg bg-black/30 p-3"><div className="text-[9px] font-bold uppercase tracking-widest text-zinc-600">{label}</div><div className="mt-1 break-words text-xs text-zinc-300">{String(value || '—')}</div></div>;
}
