// mainRd.tsx — entry del bundle de HERRAMIENTAS RD, para entregar sin servidor.
//
// Es el hermano de mainPlano.tsx: el plano viaja en su propio archivo porque es
// lo que la encargada de eventos usa a diario, y el resto de las herramientas
// viaja en este. Dos archivos y no uno para que abrir el plano no cargue lo que
// no se va a usar.
//
// A diferencia de main.tsx, NO importa App.tsx: ahi viven tambien los paneles
// que no son de RD (cultura, MAK, portafolio, show), y el tree-shaking de Vite
// los dejaria adentro. Aca se nombra lo que entra. Incluir por nombre en vez de
// borrar lo que sobra es lo unico que garantiza que no se filtre nada: borrando
// siempre se olvida algo.
import { StrictMode, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Database, Calculator, CalendarDays, Inbox } from 'lucide-react';
import './index.css';
import RdDbPanel from './components/RdDbPanel';
import QuotePanel from './components/QuotePanel';
import EventsPanel from './components/EventsPanel';
import IntakePanel from './components/IntakePanel';
import { loadPlanoConfig, applyPlanoConfig } from './data/planoConfig';

// Los precios de los packs, con el mismo archivo de configuracion que el
// bundle del plano: una tarifa cambiada tiene que valer en los dos.
const { config } = loadPlanoConfig();
applyPlanoConfig(config);

type Vista = 'base' | 'cotizacion' | 'eventos' | 'pedidos';

const VISTAS: Array<{ id: Vista; nombre: string; icono: typeof Database; que: string }> = [
  { id: 'base', nombre: 'Base de datos', icono: Database,
    que: 'Productoras y venues, con el estado de cada logo.' },
  { id: 'cotizacion', nombre: 'Cotización', icono: Calculator,
    que: 'Arma el presupuesto de una intervención en terreno.' },
  { id: 'eventos', nombre: 'Eventos', icono: CalendarDays,
    que: 'Los flyers y su automatización.' },
  { id: 'pedidos', nombre: 'Pedidos', icono: Inbox,
    que: 'Lee un pedido escrito y lo ordena en campos.' },
];

function Herramientas() {
  const [vista, setVista] = useState<Vista>('base');
  const actual = VISTAS.find(v => v.id === vista)!;

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-200">
      <header className="border-b border-zinc-900 bg-zinc-950/95 sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-5 py-3 flex items-center gap-5 flex-wrap">
          <div>
            <h1 className="text-sm font-bold tracking-wide text-emerald-400">
              Herramientas RD
            </h1>
            <p className="text-[11px] text-zinc-600">Reduciendo Daño · funciona sin conexión</p>
          </div>
          <nav className="flex gap-1.5 flex-wrap">
            {VISTAS.map(v => {
              const Icono = v.icono;
              return (
                <button key={v.id} onClick={() => setVista(v.id)} title={v.que}
                  className={
                    'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold border transition-colors '
                    + (vista === v.id
                      ? 'bg-emerald-950/50 border-emerald-800 text-emerald-300'
                      : 'bg-zinc-900 border-zinc-800 text-zinc-500 hover:text-zinc-300')
                  }>
                  <Icono className="w-3.5 h-3.5" /> {v.nombre}
                </button>
              );
            })}
          </nav>
        </div>
      </header>

      {/* Que hace la vista abierta, dicho en una linea: quien recibe este
          archivo no vio nunca la aplicacion completa. */}
      <p className="max-w-6xl mx-auto px-5 pt-4 text-xs text-zinc-500">{actual.que}</p>

      <main className="max-w-6xl mx-auto px-5 py-4">
        {vista === 'base' && <RdDbPanel />}
        {vista === 'cotizacion' && <QuotePanel />}
        {vista === 'eventos' && <EventsPanel />}
        {vista === 'pedidos' && <IntakePanel />}
      </main>

      <footer className="max-w-6xl mx-auto px-5 py-6 text-[11px] text-zinc-700">
        El plano y el rider viajan en su propio archivo, <code>plano_rd.html</code>.
      </footer>
    </div>
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Herramientas />
  </StrictMode>
);
