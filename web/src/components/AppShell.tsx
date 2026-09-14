import { type ReactNode, useEffect, useState } from 'react';
import { Menu, X, ChevronRight } from 'lucide-react';
import {
  type AppView, type WorkspaceMode,
  VISIBLE_PROFILES, getProfile, resolveInitialProfileId, persistProfileId, normalizeProfileId,
} from '../data/profiles';

// Re-exportados para no romper a quien importaba estos tipos desde AppShell
// (App.tsx los sigue tomando de aca; la fuente de verdad ahora es profiles.ts).
export type { AppView, WorkspaceMode };

interface Props {
  view: AppView;
  onViewChange: (v: AppView) => void;
  children: ReactNode;
}

export default function AppShell({ view, onViewChange, children }: Props) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  // La version estuvo cableada a mano y quedo desactualizada semanas (decia
  // 0.51.0 con el repo en 0.56.1). Se lee del backend; sin backend se omite en
  // vez de mostrar un numero viejo.
  const [version, setVersion] = useState<string>('');
  useEffect(() => {
    let vivo = true;
    fetch('/api/ping')
      .then(r => r.json())
      .then(d => { if (vivo && d?.version) setVersion(String(d.version)); })
      .catch(() => {});
    return () => { vivo = false; };
  }, []);
  const [mode, setMode] = useState<WorkspaceMode>(resolveInitialProfileId);

  const profile = getProfile(mode);
  const navItems = profile.nav;
  const currentLabel = navItems.find(i => i.view === view)?.label
    || VISIBLE_PROFILES.flatMap(p => p.nav).find(i => i.view === view)?.label
    || 'flujo';

  // Si el perfil activo no incluye la vista actual (cambio de perfil a mano,
  // o perfil inicial resuelto desde URL/localStorage cuyo nav no calza con la
  // vista inicial que decidio App.tsx por la ruta), cae a la primera entrada
  // del nav de ese perfil.
  useEffect(() => {
    if (!navItems.find(n => n.view === view)) {
      onViewChange(navItems[0].view);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  // ?perfil=<id> manda sobre localStorage al resolver, pero una vez que se
  // uso para entrar queda como el nuevo perfil persistido -- si no, compartir
  // un link con ?perfil= nunca "pegaria" y el efecto de mandar el link seria
  // solo por esa sesion de pestaña.
  useEffect(() => {
    try {
      const fromUrl = normalizeProfileId(new URLSearchParams(window.location.search).get('perfil'));
      if (fromUrl) persistProfileId(fromUrl);
    } catch {
      // location.search inaccesible -- no persistir nada
    }
    // Solo al montar: el perfil desde URL se resuelve una vez, al cargar.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const switchMode = (m: WorkspaceMode) => {
    setMode(m);
    persistProfileId(m);
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-zinc-950 text-zinc-100">
      {/* Sidebar overlay on mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-zinc-800/70 bg-zinc-950
          transition-transform duration-300 lg:static lg:translate-x-0
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        {/* Brand */}
        <div className="flex h-16 items-center gap-3 border-b border-zinc-800/70 px-5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600">
            <span className="text-sm font-black text-white">f</span>
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight">flujo</h1>
            <p className="text-[10px] text-zinc-500">hub operativo</p>
          </div>
          <button onClick={() => setSidebarOpen(false)} className="ml-auto rounded-lg p-1 text-zinc-500 hover:text-zinc-300 lg:hidden">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Mode Selector: solo perfiles visibles (rd-plano queda afuera). */}
        <div className="border-b border-zinc-800/70 px-3 py-3">
          <div className="text-[10px] font-bold uppercase tracking-widest text-zinc-600 mb-2 px-2">Workspace</div>
          <div className="flex gap-1.5">
            {VISIBLE_PROFILES.map(p => {
              const SelectorIcon = p.selectorIcon;
              const active = mode === p.id;
              return (
                <button
                  key={p.id}
                  onClick={() => switchMode(p.id)}
                  className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg px-2 py-2 text-[11px] font-bold transition-all ${
                    active
                      ? p.accent.selectorActive
                      : 'text-zinc-500 hover:bg-zinc-800/50 hover:text-zinc-300 border border-transparent'
                  }`}
                >
                  <SelectorIcon className="h-3.5 w-3.5" />
                  {p.label}
                </button>
              );
            })}
          </div>
          <div className="mt-2 px-2 text-[9px] text-zinc-600 leading-relaxed">
            {profile.tagline}
          </div>
        </div>

        {/* Nav: editables primero, consulta despues */}
        <nav className="flex-1 overflow-y-auto px-3 py-4">
          {[
            { title: profile.navTitle, items: navItems.filter(i => i.view === 'hub' || i.edit) },
            { title: 'Consulta / referencia', items: navItems.filter(i => i.view !== 'hub' && !i.edit) },
          ].map(section => section.items.length > 0 && (
            <div key={section.title} className="mb-4">
              <div className="mb-2 px-2 text-[10px] font-bold uppercase tracking-widest text-zinc-600">
                {section.title}
              </div>
              {section.items.map(item => {
                const Icon = item.icon;
                const active = view === item.view;
                return (
                  <button
                    key={item.view}
                    onClick={() => { onViewChange(item.view); setSidebarOpen(false); }}
                    className={`
                      group mb-0.5 flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-all
                      ${active
                        ? 'bg-zinc-800/80 text-white shadow-sm'
                        : 'text-zinc-400 hover:bg-zinc-800/40 hover:text-zinc-200'}
                    `}
                  >
                    <Icon className={`h-4 w-4 shrink-0 ${active ? profile.accent.accentText : 'text-zinc-500 group-hover:text-zinc-400'}`} />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5 text-sm font-medium">
                        {item.label}
                        {item.edit && (
                          <span className={`rounded px-1 py-px text-[8px] font-bold uppercase tracking-wider ${profile.accent.editBadge}`}>edit</span>
                        )}
                      </div>
                      <div className="truncate text-[10px] text-zinc-600">{item.desc}</div>
                    </div>
                    {active && <ChevronRight className="h-3 w-3 text-zinc-600" />}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>

        {/* Footer */}
        <div className="border-t border-zinc-800/70 px-5 py-3">
          <div className="flex items-center gap-2">
            <profile.footerIcon className={`h-3 w-3 ${profile.accent.footerIcon}`} />
            <span className="text-[10px] text-zinc-600">
              {profile.footerLabel}
            </span>
          </div>
          <div className="text-[10px] text-zinc-600 mt-1">
            {version ? `v${version} | ` : ''}gratis/local
          </div>
          <div className="text-[10px] text-zinc-700">
            py -m flujo app
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Mobile header */}
        <header className="flex h-14 items-center gap-3 border-b border-zinc-800/70 px-4 lg:hidden">
          <button onClick={() => setSidebarOpen(true)} className="rounded-lg p-1.5 text-zinc-400 hover:text-zinc-200">
            <Menu className="h-5 w-5" />
          </button>
          <div className="flex items-center gap-2">
            <span className={`rounded-md px-1.5 py-0.5 text-[9px] font-bold ${profile.accent.mobileBadge}`}>
              {profile.shortLabel}
            </span>
            <span className="text-sm font-bold">{currentLabel}</span>
          </div>
        </header>

        {/* Scrollable content */}
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-[1600px] p-4 md:p-6 lg:p-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
