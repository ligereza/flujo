import { useState } from 'react';
import { Camera, ExternalLink } from 'lucide-react';
import CommandCopy from './CommandCopy';

export default function EventsPanel() {
  const [igUrl, setIgUrl] = useState('');
  const [result, setResult] = useState<string | null>(null);

  // Armado local de comando (no ejecuta nada en backend): instantaneo, sin
  // spinner fake que simule una llamada que no existe.
  const generateCommand = () => {
    if (!igUrl.trim()) return;
    setResult(`py -m flujo eventos flyer-auto "${igUrl.trim()}"`);
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
              Pega un link de Instagram. El pipeline descarga via mirror publico, genera paleta de colores y prepara el flyer.
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
                disabled={!igUrl.trim()}
                className="flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-bold text-black hover:bg-zinc-200 disabled:opacity-60"
              >
                <ExternalLink className="h-4 w-4" />
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
                { step: '1', title: 'Descarga IG', desc: 'parth-dl baja la imagen del post (via primaria desde 2026-07-22)' },
                { step: '2', title: 'Paleta', desc: 'Extrae colores dominantes automaticamente' },
                { step: '3', title: 'Blender', desc: 'Render por nodos, sin Photoshop (opcional)' },
                { step: '4', title: 'Entrega', desc: 'PNG a OneDrive y cierre del issue' },
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
              <li>&#8226; Descarga real = <strong>parth-dl</strong> (via primaria desde 2026-07-22). Video/reel usa el thumbnail; de un carrusel baja SOLO la primera imagen.</li>
              <li>&#8226; imginn.com quedo en 403 por Cloudflare: solo fallback best-effort. instaloader NO funciona (IG exige login) y yt-dlp no se usa.</li>
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
