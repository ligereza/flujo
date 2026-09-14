import { useState } from 'react';
import AppShell, { type AppView } from './components/AppShell';
import { isLinkableView } from './data/profiles';
import HubDashboard from './components/HubDashboard';
import JobsPanel from './components/JobsPanel';
import IntakePanel from './components/IntakePanel';
import QuotePanel from './components/QuotePanel';
import CommandPanel from './components/CommandPanel';
import PlanoTool from './components/PlanoTool';
import SvgVisualizer from './components/SvgVisualizer';
import EventsPanel from './components/EventsPanel';
import ResolumePanel from './components/ResolumePanel';
import MappingTool from './components/MappingTool';
import CulturaPanel from './components/CulturaPanel';
import ShowPanel from './components/ShowPanel';
import AutomatizacionesPanel from './components/AutomatizacionesPanel';
import RdDbPanel from './components/RdDbPanel';
import PortafolioPanel from './components/PortafolioPanel';

function initialView(): AppView {
  if (typeof window === 'undefined') return 'hub';
  // `?vista=<id>` opens a panel directly, so a panel can be linked or
  // screenshotted without clicking through the nav. Validated against the views
  // the profiles actually declare: an unknown value falls through to the path
  // rules below instead of leaving a blank screen.
  const pedida = new URLSearchParams(window.location.search).get('vista');
  if (isLinkableView(pedida)) return pedida;
  const path = window.location.pathname.toLowerCase();
  if (path.includes('svg') || path.includes('visual') || path.includes('config') || path.includes('editor')) return 'visualizer';
  if (path.includes('plano')) return 'plano';
  if (path.includes('resolume') || path.includes('chataigne')) return 'resolume';
  if (path.includes('mapping') || path.includes('rigging')) return 'mapping';
  if (path.includes('event')) return 'events';
  return 'hub';
}

export default function App() {
  const [view, setView] = useState<AppView>(initialView);

  return (
    <AppShell view={view} onViewChange={setView}>
      {view === 'hub' && <HubDashboard onNavigate={setView} />}
      {view === 'jobs' && <JobsPanel />}
      {view === 'intake' && <IntakePanel />}
      {view === 'quote' && <QuotePanel />}
      {view === 'commands' && <CommandPanel />}
      {view === 'plano' && <PlanoTool />}
      {view === 'visualizer' && <SvgVisualizer />}
      {view === 'events' && <EventsPanel />}
      {view === 'resolume' && <ResolumePanel />}
      {view === 'mapping' && <MappingTool />}
      {view === 'show' && <ShowPanel />}
      {view === 'automatizaciones' && <AutomatizacionesPanel />}
      {view === 'rd-db' && <RdDbPanel />}
      {view === 'cultura' && <CulturaPanel />}
      {view === 'portafolio' && <PortafolioPanel />}
    </AppShell>
  );
}
