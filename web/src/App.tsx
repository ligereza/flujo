import { useState } from 'react';
import AppShell, { type AppView } from './components/AppShell';
import HubDashboard from './components/HubDashboard';
import JobsPanel from './components/JobsPanel';
import IntakePanel from './components/IntakePanel';
import QuotePanel from './components/QuotePanel';
import CommandPanel from './components/CommandPanel';
import PlanoTool from './components/PlanoTool';
import SvgVisualizer from './components/SvgVisualizer';
import EventsPanel from './components/EventsPanel';
import ResolumePanel from './components/ResolumePanel';

function initialView(): AppView {
  if (typeof window === 'undefined') return 'hub';
  const path = window.location.pathname.toLowerCase();
  if (path.includes('svg') || path.includes('visual') || path.includes('config') || path.includes('editor')) return 'visualizer';
  if (path.includes('plano')) return 'plano';
  if (path.includes('resolume') || path.includes('chataigne')) return 'resolume';
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
    </AppShell>
  );
}
