import { useState } from 'react';
import { Check, Copy, X } from 'lucide-react';

// Boton "copiar comando" compartido por CommandPanel / EventsPanel / ResolumePanel.
// navigator.clipboard solo existe en contextos seguros (https/localhost); en file://
// o http de red local cae al fallback de textarea+execCommand.
export async function copyText(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // sigue al fallback
  }
  try {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(ta);
    return ok;
  } catch {
    return false;
  }
}

export default function CommandCopy({ text }: { text: string }) {
  const [state, setState] = useState<'idle' | 'copied' | 'failed'>('idle');
  const copy = async () => {
    const ok = await copyText(text);
    setState(ok ? 'copied' : 'failed');
    setTimeout(() => setState('idle'), 1300);
  };
  return (
    <button
      onClick={copy}
      title={state === 'failed' ? 'No se pudo copiar (selecciona el texto a mano)' : 'Copiar comando'}
      className="group flex w-full items-center justify-between gap-3 rounded-lg border border-zinc-800/60 bg-black/30 px-4 py-3 text-left font-mono text-xs text-zinc-300 transition hover:border-zinc-600 hover:bg-zinc-900"
    >
      <span className="truncate">{text}</span>
      {state === 'copied' && <Check className="h-4 w-4 shrink-0 text-emerald-400" />}
      {state === 'failed' && <X className="h-4 w-4 shrink-0 text-red-400" />}
      {state === 'idle' && <Copy className="h-4 w-4 shrink-0 text-zinc-600 group-hover:text-zinc-300" />}
    </button>
  );
}
