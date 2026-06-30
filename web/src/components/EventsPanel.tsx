import { useState } from 'react';
import { Camera, Check, Copy, ExternalLink, Loader2 } from 'lucide-react';

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

export default function EventsPanel() {
  const [igUrl, setIgUrl] = useState('');
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const generateCommand = () => {
    if (!igUrl.trim()) return;
    setGenerating(true);
    setTimeout(() => {
      setResult(`py -m flujo eventos flyer-auto "${igUrl.trim()}"`);
      setGenerating(false);
    }, 300);
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-black">
          <Camera className="h-6 w-6" /> Eventos / Instagram
        </h1>
        <p className="mt-1 text-sm text-zinc-500">
          Descarga de flyers desde Instagram para EVENTOS. Genera comandos para el pipeline local.
        </p>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_400px]">
        {/* Main input */}
        <div className="space-y-4">
          <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-4 space-y-4">
            <h2 className="text-sm font-bold">Generar flyer desde Instagram</h2>
            <p className="text-xs text-zinc-500">
              Pega un link de Instagram. El pipeline descarga con instaloader, genera paleta de colores y prepara el flyer.
            </p>
            <div>
              <label className="mb-1 block text-[10px] font-bold uppercase tracking-widest text-zinc-600">URL de Instagram</label>
              <input
                value={igUrl}
                onChange={e => setIgUrl(e.target.value)}
                placeholder="https://www.instagram.com/p/XXXX/"
                className="w-full rounded-lg border border-zinc-800 bg-black/40 px-4 py-3 text-sm outline-none focus:border-zinc-600"
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={generateCommand}
                disabled={!igUrl.trim() || generating}
                className="flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-bold text-black hover:bg-zinc-200 disabled:opacity-60"
              >
                {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <ExternalLink className="h-4 w-4" />}
                Generar comando
              </button>
            </div>

            {result && (
              <div className="rounded-xl border border-zinc-800/60 bg-black/30 p-4 space-y-3">
                <h3 className="text-xs font-bold text-zinc-400">Comando generado:</h3>
                <CommandCopy text={result} />
                <div className="text-[10px] text-zinc-600 space-y-1">
                  <p>Ejecuta este comando en Git Bash para descargar y procesar el flyer.</p>
                  <p>Opciones adicionales:</p>
                </div>
                <CommandCopy text={`${result} --run-droplet`} />
                <CommandCopy text={`${result} --render-blender`} />
                <CommandCopy text={`${result} --render-blender --open-blender`} />
              </div>
            )}
          </div>

          {/* Pipeline explanation */}
          <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-4 space-y-3">
            <h2 className="text-sm font-bold">Pipeline de Eventos</h2>
            <div className="grid gap-2 sm:grid-cols-2">
              {[
                { step: '1', title: 'Descarga IG', desc: 'instaloader descarga imagen/video del post' },
                { step: '2', title: 'Paleta', desc: 'Extrae colores dominantes automaticamente' },
                { step: '3', title: 'Photoshop', desc: 'Droplet PS aplica plantilla (opcional)' },
                { step: '4', title: 'Blender', desc: 'Render 3D del flyer (opcional)' },
              ].map(item => (
                <div key={item.step} className="rounded-lg bg-black/30 border border-zinc-800/40 p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-violet-900/40 text-[10px] font-bold text-violet-300">{item.step}</span>
                    <span className="text-xs font-bold">{item.title}</span>
                  </div>
                  <p className="text-[10px] text-zinc-500">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Reference commands */}
        <div className="space-y-4">
          <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-4 space-y-3">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-zinc-600">Comandos de referencia</h3>
            <CommandCopy text='py -m flujo eventos flyer-auto "<url-instagram>"' />
            <CommandCopy text='py -m flujo hub route where --area eventos --pieza flyer' />
            <CommandCopy text='py -m flujo job new "nombre evento" --email inbox/correo.txt' />
          </div>

          <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-4 space-y-3">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-zinc-600">Notas</h3>
            <ul className="space-y-2 text-xs text-zinc-400">
              <li>&#8226; Usa <strong className="text-zinc-300">instaloader</strong>. No usar yt-dlp.</li>
              <li>&#8226; Las fotos descargadas se guardan en el job correspondiente.</li>
              <li>&#8226; El pipeline infiere productora, fecha y venue del post.</li>
              <li>&#8226; Los flyers generados se sirven en SVG Studio (Modo Studio).</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
