import { useState } from 'react';
import { Radio, Check, Copy, Cpu, Zap } from 'lucide-react';

function CommandCopy({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    await navigator.clipboard?.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1300);
  };
  return (
    <button
      onClick={copy}
      className="group flex w-full items-center justify-between gap-3 rounded-lg border border-zinc-800/60 bg-black/30 px-4 py-3 text-left font-mono text-xs text-zinc-300 transition hover:border-zinc-600 hover:bg-zinc-900"
    >
      <span className="truncate">{text}</span>
      {copied ? <Check className="h-4 w-4 shrink-0 text-emerald-400" /> : <Copy className="h-4 w-4 shrink-0 text-zinc-600 group-hover:text-zinc-300" />}
    </button>
  );
}

export default function ResolumePanel() {
  const [jobId, setJobId] = useState('');
  const [fps, setFps] = useState('25');
  const [host, setHost] = useState('127.0.0.1');
  const [port, setPort] = useState('7000');

  const baseCmd = jobId.trim()
    ? `py -m flujo resolume automatizar jobs/${jobId.trim()}`
    : 'py -m flujo resolume automatizar jobs/<job_id>';

  const fullCmd = [
    baseCmd,
    fps !== '25' ? `--fps ${fps}` : '',
    host !== '127.0.0.1' ? `--host ${host}` : '',
    port !== '7000' ? `--port ${port}` : '',
  ].filter(Boolean).join(' ');

  return (
    <div className="space-y-5">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-black">
          <Radio className="h-6 w-6" /> Resolume / Chataigne
        </h1>
        <p className="mt-1 text-sm text-zinc-500">
          Automatizacion de shows con SMPTE/OSC. Genera XML pre-flight para Resolume Arena + Chataigne.
        </p>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_400px]">
        {/* Config */}
        <div className="space-y-4">
          <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-4 space-y-4">
            <h2 className="text-sm font-bold flex items-center gap-2">
              <Cpu className="h-4 w-4 text-violet-400" /> Configurar automatizacion
            </h2>

            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-[10px] font-bold uppercase tracking-widest text-zinc-600">Job ID</label>
                <input
                  value={jobId}
                  onChange={e => setJobId(e.target.value)}
                  placeholder="ej: evt_club_sol_2024"
                  className="w-full rounded-lg border border-zinc-800 bg-black/40 px-3 py-2 text-sm outline-none focus:border-zinc-600"
                />
              </div>
              <div>
                <label className="mb-1 block text-[10px] font-bold uppercase tracking-widest text-zinc-600">FPS</label>
                <input
                  value={fps}
                  onChange={e => setFps(e.target.value)}
                  placeholder="25"
                  className="w-full rounded-lg border border-zinc-800 bg-black/40 px-3 py-2 text-sm outline-none focus:border-zinc-600"
                />
              </div>
              <div>
                <label className="mb-1 block text-[10px] font-bold uppercase tracking-widest text-zinc-600">Host OSC</label>
                <input
                  value={host}
                  onChange={e => setHost(e.target.value)}
                  placeholder="127.0.0.1"
                  className="w-full rounded-lg border border-zinc-800 bg-black/40 px-3 py-2 text-sm outline-none focus:border-zinc-600"
                />
              </div>
              <div>
                <label className="mb-1 block text-[10px] font-bold uppercase tracking-widest text-zinc-600">Puerto OSC</label>
                <input
                  value={port}
                  onChange={e => setPort(e.target.value)}
                  placeholder="7000"
                  className="w-full rounded-lg border border-zinc-800 bg-black/40 px-3 py-2 text-sm outline-none focus:border-zinc-600"
                />
              </div>
            </div>

            <div className="space-y-2">
              <h3 className="text-[10px] font-bold uppercase tracking-widest text-zinc-600">Comando generado</h3>
              <CommandCopy text={fullCmd} />
            </div>
          </div>

          {/* Architecture */}
          <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-4 space-y-4">
            <h2 className="text-sm font-bold flex items-center gap-2">
              <Zap className="h-4 w-4 text-amber-400" /> Arquitectura SMPTE/OSC
            </h2>
            <div className="rounded-lg bg-black/30 border border-zinc-800/40 p-4">
              <div className="flex flex-col items-center gap-3 text-xs text-zinc-400">
                <div className="flex items-center gap-3 flex-wrap justify-center">
                  <div className="rounded-lg border border-violet-800/50 bg-violet-950/30 px-3 py-2 text-violet-300 font-bold text-center">
                    SMPTE TC<br />
                    <span className="text-[9px] font-normal text-violet-400">HH:MM:SS:FF</span>
                  </div>
                  <span className="text-zinc-600">&#8594;</span>
                  <div className="rounded-lg border border-amber-800/50 bg-amber-950/30 px-3 py-2 text-amber-300 font-bold text-center">
                    Chataigne<br />
                    <span className="text-[9px] font-normal text-amber-400">Module SMPTE</span>
                  </div>
                  <span className="text-zinc-600">&#8594;</span>
                  <div className="rounded-lg border border-blue-800/50 bg-blue-950/30 px-3 py-2 text-blue-300 font-bold text-center">
                    OSC Out<br />
                    <span className="text-[9px] font-normal text-blue-400">{host}:{port}</span>
                  </div>
                  <span className="text-zinc-600">&#8594;</span>
                  <div className="rounded-lg border border-emerald-800/50 bg-emerald-950/30 px-3 py-2 text-emerald-300 font-bold text-center">
                    Resolume Arena<br />
                    <span className="text-[9px] font-normal text-emerald-400">Clips/Layers</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="text-xs text-zinc-500 space-y-1">
              <p><strong className="text-zinc-400">Salida esperada:</strong> jobs/&#123;job_id&#125;/deliverables/show_automation.xml</p>
              <p><strong className="text-zinc-400">Acciones OSC:</strong> /composition/layers/&#123;layer&#125;/clips/&#123;clip&#125;/connect</p>
              <p><strong className="text-zinc-400">Spec:</strong> tools/resolume_chataigne_automator/SPEC.md</p>
            </div>
          </div>
        </div>

        {/* Reference */}
        <div className="space-y-4">
          <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-4 space-y-3">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-zinc-600">Comandos de referencia</h3>
            <CommandCopy text="py -m flujo resolume automatizar jobs/<job_id>" />
            <CommandCopy text="py -m flujo resolume automatizar jobs/<job_id> --fps 25" />
            <CommandCopy text="py -m flujo resolume automatizar jobs/<job_id> --host 127.0.0.1 --port 7000" />
          </div>

          <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-4 space-y-3">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-zinc-600">XML pre-flight configura</h3>
            <ul className="space-y-2 text-xs text-zinc-400">
              <li>&#8226; Entrada SMPTE HH:MM:SS:FF</li>
              <li>&#8226; Salida OSC a {host}:{port}</li>
              <li>&#8226; Acciones /composition/layers/&#123;layer&#125;/clips/&#123;clip&#125;/connect</li>
              <li>&#8226; Soporte futuro para .noisette nativo de Chataigne</li>
            </ul>
          </div>

          <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-4 space-y-3">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-zinc-600">Flujo de trabajo</h3>
            <ol className="space-y-2 text-xs text-zinc-400 list-decimal list-inside">
              <li>Crear job de tipo EVENTOS con show/set data</li>
              <li>Ejecutar <code className="font-mono bg-black/30 px-1 rounded">py -m flujo resolume automatizar</code></li>
              <li>XML se genera en <code className="font-mono bg-black/30 px-1 rounded">deliverables/</code></li>
              <li>Importar XML en Chataigne</li>
              <li>Conectar Chataigne a Resolume via OSC</li>
              <li>Verificar sincronizacion SMPTE antes del show</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
}
