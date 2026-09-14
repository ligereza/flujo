// mainPlano.tsx — entry point separado del bundle standalone de Plano/Rider.
// A diferencia de main.tsx (que monta App.tsx, con TODOS los paneles del
// hub), este archivo SOLO importa PlanoStandalone -> PlanoTool. No importa
// HubDashboard, JobsPanel, IntakePanel, QuotePanel, CulturaPanel, etc., asi
// que el tree-shaking de Vite los deja afuera del bundle.
//
// El override de precios se aplica ANTES de crear el root de React (no en un
// efecto), asi PlanoTool nunca llega a leer PACKS sin el override aplicado
// en su primer render.
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import PlanoStandalone from './components/PlanoStandalone';
import { loadPlanoConfig, applyPlanoConfig } from './data/planoConfig';
import { cargarSimbolosLocales } from './data/planoSimbolos';

const { config, warning } = loadPlanoConfig();
applyPlanoConfig(config);

// Los simbolos que la encargada creo en ESTE navegador. En el bundle suelto
// no hay hub que los sirva, asi que si no se cargan aca su trabajo anterior
// no aparece al reabrir el archivo.
cargarSimbolosLocales();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <PlanoStandalone initialConfig={config} initialWarning={warning} />
  </StrictMode>
);
