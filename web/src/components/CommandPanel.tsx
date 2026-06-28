import { useState } from 'react';
import { Check, Copy, TerminalSquare } from 'lucide-react';

const groups = [
  {
    title: 'Uso diario',
    commands: ['py -m flujo app', 'py -m flujo health', 'py -m flujo verify'],
  },
  {
    title: 'Frontend React',
    commands: ['cd web', 'npm ci --no-audit --no-fund', 'npm run typecheck', 'npm run build:context'],
  },
  {
    title: 'Airdrop seguro',
    commands: ['py scripts/validate_airdrop.py', 'py scripts/run_airdrop_checks.py "mensaje"'],
  },
  {
    title: 'Operación',
    commands: ['py -m flujo portal --repo-url https://github.com/ligereza/vibecodeine', 'py -m flujo eventos flyer-auto "<url-instagram>"', 'py -m flujo hub route where --area eventos --pieza flyer'],
  },
];

function Command({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    await navigator.clipboard?.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1300);
  };
  return (
    <button onClick={copy} className="group flex w-full items-center justify-between gap-3 rounded-xl border border-zinc-800 bg-black/35 px-4 py-3 text-left font-mono text-xs text-zinc-300 transition hover:border-zinc-600 hover:bg-zinc-900">
      <span>{text}</span>
      {copied ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4 text-zinc-600 group-hover:text-zinc-300" />}
    </button>
  );
}

export default function CommandPanel() {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-black"><TerminalSquare className="h-6 w-6" /> Comandos</h1>
        <p className="mt-1 text-sm text-zinc-500">Comandos que sostienen el flujo diario y el build React.</p>
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        {groups.map(group => (
          <section key={group.title} className="rounded-2xl border border-zinc-800 bg-zinc-900/45 p-4">
            <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-zinc-500">{group.title}</h2>
            <div className="space-y-2">
              {group.commands.map(command => <Command key={command} text={command} />)}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
