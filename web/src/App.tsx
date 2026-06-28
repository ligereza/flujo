import { useState } from 'react';
import AppShell, { type AppView } from './components/AppShell';
import CommandPanel from './components/CommandPanel';
import HubDashboard from './components/HubDashboard';
import IntakePanel from './components/IntakePanel';
import JobsPanel from './components/JobsPanel';
import PlanoTool from './components/PlanoTool';
import SvgVisualizer from './components/SvgVisualizer';

function initialView(): AppView {
  if (typeof window === 'undefined') return 'hub';
  const path = window.location.pathname.toLowerCase();
  if (path.includes('svg')) return 'visualizer';
  if (path.includes('plano')) return 'plano';
  return 'hub';
}

export default function App() {
  const [view, setView] = useState<AppView>(initialView);

  return (
    <AppShell view={view} onViewChange={setView}>
      {view === 'hub' && <HubDashboard onNavigate={setView} />}
      {view === 'jobs' && <JobsPanel />}
      {view === 'intake' && <IntakePanel />}
      {view === 'commands' && <CommandPanel />}
      {view === 'plano' && <PlanoTool />}
      {view === 'visualizer' && <SvgVisualizer />}
    </AppShell>
  );
}
