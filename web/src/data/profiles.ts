// profiles.ts — definicion declarativa de los perfiles/workspaces del hub.
// Extraido de AppShell.tsx (que tenia el modo cableado en ternarios repetidos
// por todo el componente) para poder: 1) agregar perfiles nuevos sin tocar el
// shell, 2) tener un perfil "oculto" de distribucion (rd-plano) que no
// aparece en el selector pero sigue siendo un perfil valido.
//
// Cada perfil trae ya armadas las clases de Tailwind que antes se decidian
// con `mode === 'x' ? ... : ...` en el render. Nada de logica de color queda
// en AppShell: solo lee `profile.accent.*`.

import {
  LayoutDashboard, Boxes, ClipboardList, Calculator,
  TerminalSquare, Map, Shapes, Heart, Music, Cpu, Radio, Lightbulb, Layers, Camera, Clapperboard, Workflow, Database,
  type LucideIcon,
} from 'lucide-react';

export type AppView =
  | 'hub'
  | 'jobs'
  | 'intake'
  | 'quote'
  | 'commands'
  | 'plano'
  | 'visualizer'
  | 'events'
  | 'resolume'
  | 'mapping'
  | 'show'
  | 'automatizaciones'
  | 'rd-db'
  | 'cultura'
  | 'portafolio';

// Division en 3 (2026-07-25, orden del usuario): la app espeja la topologia de ramas del
// repo -- main / rd / iskvw. `studio` y `cultura` se fundieron en `iskvw`
// (la linea de curatoria/artistico, ex-portafolio); `main` es el nucleo
// transversal, lo que no pertenece ni a la ONG ni a la obra.
// `rd-plano` sobrevive aparte: es perfil de distribucion, no un mundo.
export type WorkspaceMode = 'main' | 'rd' | 'iskvw' | 'rd-plano';

// Ids viejos que pueden seguir vivos en el localStorage de un navegador o en
// un link ?perfil= ya compartido. Se traducen en vez de caer al default, para
// que nadie pierda su workspace al actualizar.
const LEGACY_PROFILE_IDS: Record<string, WorkspaceMode> = {
  studio: 'iskvw',
  cultura: 'iskvw',
};

export interface NavItem {
  view: AppView;
  icon: LucideIcon;
  label: string;
  desc: string;
  // true = permite editar/crear contenido dentro de la app (editor, formulario
  // con salida real); false = consulta o generador de comandos copy/paste.
  edit: boolean;
}

// Clases ya armadas para no repetir ternarios de color en el shell.
export interface ProfileAccent {
  // Boton del selector de workspace cuando esta activo.
  selectorActive: string;
  // Color del icono de nav cuando el item esta activo.
  accentText: string;
  // Badge "edit" junto al label del nav item.
  editBadge: string;
  // Badge de perfil en el header mobile (solo color; el resto de clases
  // -- rounded-md/px/py/tamano de fuente -- son compartidas en AppShell).
  mobileBadge: string;
  // Color del icono en el footer del sidebar.
  footerIcon: string;
}

export interface Profile {
  id: WorkspaceMode;
  /** Label del boton selector, ej "Modo RD". */
  label: string;
  /** Badge corto para mobile, ej "RD". */
  shortLabel: string;
  /** Descripcion de 1 linea bajo el selector de workspace. */
  tagline: string;
  /** Texto del footer del sidebar, ej "Reduciendo Daño". */
  footerLabel: string;
  /** Titulo de la primera seccion de nav (los items editables), ej "Edicion RD". */
  navTitle: string;
  selectorIcon: LucideIcon;
  footerIcon: LucideIcon;
  accent: ProfileAccent;
  nav: NavItem[];
  /**
   * true = perfil de distribucion: no aparece en el selector de workspace del
   * hub normal. Se llega a el por querystring (?perfil=) o localStorage, nunca
   * cambiando de perfil a mano dentro de la app.
   */
  hidden?: boolean;
}

// Editables primero: son las herramientas que producen trabajo dentro de la app.
const RD_NAV: NavItem[] = [
  { view: 'hub', icon: LayoutDashboard, label: 'Dashboard', desc: 'Vista general RD', edit: false },
  { view: 'plano', icon: Map, label: 'Plano / Rider', desc: 'Editor de layout de evento', edit: true },
  { view: 'visualizer', icon: Shapes, label: 'SVG Studio', desc: 'Galería + editor visual', edit: true },
  { view: 'quote', icon: Calculator, label: 'Cotización', desc: 'Presupuesto editable', edit: true },
  { view: 'intake', icon: ClipboardList, label: 'Pedidos', desc: 'Pegá el correo del cliente y queda anotado', edit: true },
  { view: 'rd-db', icon: Database, label: 'Base de datos', desc: 'Productoras, venues y logos', edit: true },
  { view: 'automatizaciones', icon: Workflow, label: 'Automatizaciones', desc: 'Cola Gmail -> issue -> render', edit: false },
  { view: 'jobs', icon: Boxes, label: 'Trabajos / Suplementos', desc: 'En qué va cada trabajo', edit: false },
];

// main: nucleo transversal. Lo que sirve a las dos lineas y no es de ninguna:
// estado general, jobs, la cola de automatizaciones y la referencia de CLI.
const MAIN_NAV: NavItem[] = [
  { view: 'hub', icon: LayoutDashboard, label: 'Dashboard', desc: 'Vista general del sistema', edit: false },
  { view: 'jobs', icon: Boxes, label: 'Trabajos / Suplementos', desc: 'En qué va cada trabajo', edit: false },
  { view: 'automatizaciones', icon: Workflow, label: 'Automatizaciones', desc: 'Cola Gmail -> issue -> render', edit: false },
  { view: 'commands', icon: TerminalSquare, label: 'Comandos', desc: 'CLI reference', edit: false },
];

// iskvw: la obra. Funde el viejo Studio (VJ/club: show kit, mapping, Resolume)
// con Cultura (arte-investigacion: tapiz, tilde, psicosis, precursor). Es la
// misma persona haciendo lo mismo en dos escalas, no dos areas.
const ISKVW_NAV: NavItem[] = [
  { view: 'hub', icon: LayoutDashboard, label: 'Dashboard', desc: 'Vista general iskvw', edit: false },
  { view: 'show', icon: Clapperboard, label: 'Show kit', desc: 'Setlist, cues y registros de show', edit: true },
  { view: 'mapping', icon: Lightbulb, label: 'Mapping LED', desc: 'Rigging / pixel mapping', edit: true },
  { view: 'resolume', icon: Radio, label: 'Resolume / Chataigne', desc: 'Comando SMPTE/OSC', edit: false },
  { view: 'events', icon: Camera, label: 'Eventos / IG', desc: 'Comando flyer-auto', edit: false },
  { view: 'visualizer', icon: Shapes, label: 'SVG Studio', desc: 'Galería + editor visual', edit: true },
  { view: 'portafolio', icon: Layers, label: 'Portafolio', desc: 'Catálogo público de iskvw', edit: false },
  { view: 'cultura', icon: Layers, label: 'Cultura', desc: 'Instrumentos y lineas de obra', edit: false },
];

// rd-plano: perfil de distribucion para compartir SOLO el editor de Plano/Rider
// con una persona externa (fuera del equipo). Una sola entrada, sin dashboard,
// sin jobs, sin cotizacion. Ver web/src/mainPlano.tsx para el bundle que lo usa.
const RD_PLANO_NAV: NavItem[] = [
  { view: 'plano', icon: Map, label: 'Plano / Rider', desc: 'Editor de layout de evento', edit: true },
];

export const PROFILES: Record<WorkspaceMode, Profile> = {
  main: {
    id: 'main',
    label: 'Main',
    shortLabel: 'MAIN',
    tagline: 'Núcleo transversal: estado del sistema, trabajos, cola de automatizaciones y referencia de comandos.',
    footerLabel: 'Main / Sistema',
    navTitle: 'Sistema',
    selectorIcon: Cpu,
    footerIcon: Cpu,
    accent: {
      selectorActive: 'bg-cyan-900/50 text-cyan-300 border border-cyan-700/50 shadow-sm shadow-cyan-900/30',
      accentText: 'text-cyan-400',
      editBadge: 'bg-cyan-900/60 text-cyan-400',
      mobileBadge: 'bg-cyan-900/50 text-cyan-300',
      footerIcon: 'text-cyan-500',
    },
    nav: MAIN_NAV,
  },
  rd: {
    id: 'rd',
    label: 'Modo RD',
    shortLabel: 'RD',
    tagline: 'ONG Reduciendo Daño: planos y riders de evento, cotizaciones, piezas de diseño y pedidos que llegan por correo.',
    footerLabel: 'Reduciendo Daño',
    navTitle: 'Edición RD',
    selectorIcon: Heart,
    footerIcon: Heart,
    accent: {
      selectorActive: 'bg-emerald-900/50 text-emerald-300 border border-emerald-700/50 shadow-sm shadow-emerald-900/30',
      accentText: 'text-emerald-400',
      editBadge: 'bg-emerald-900/60 text-emerald-400',
      mobileBadge: 'bg-emerald-900/50 text-emerald-300',
      footerIcon: 'text-emerald-500',
    },
    nav: RD_NAV,
  },
  iskvw: {
    id: 'iskvw',
    label: 'iskvw',
    shortLabel: 'ISKVW',
    tagline: 'La obra: Show kit (setlist/TC), Mapping LED, Resolume/Chataigne, Eventos/IG, SVG Studio y Cultura (tapiz, tilde, psicosis, precursor).',
    footerLabel: 'iskvw / Obra',
    navTitle: 'Edicion iskvw',
    selectorIcon: Music,
    footerIcon: Layers,
    accent: {
      selectorActive: 'bg-violet-900/50 text-violet-300 border border-violet-700/50 shadow-sm shadow-violet-900/30',
      accentText: 'text-violet-400',
      editBadge: 'bg-violet-900/60 text-violet-400',
      mobileBadge: 'bg-violet-900/50 text-violet-300',
      footerIcon: 'text-violet-500',
    },
    nav: ISKVW_NAV,
  },
  'rd-plano': {
    id: 'rd-plano',
    label: 'Plano RD',
    shortLabel: 'PLANO',
    tagline: 'Perfil de distribución: solo el editor de Plano/Rider, para compartir fuera del equipo.',
    footerLabel: 'Plano RD (compartido)',
    navTitle: 'Plano',
    selectorIcon: Map,
    footerIcon: Map,
    accent: {
      selectorActive: 'bg-sky-900/50 text-sky-300 border border-sky-700/50 shadow-sm shadow-sky-900/30',
      accentText: 'text-sky-400',
      editBadge: 'bg-sky-900/60 text-sky-400',
      mobileBadge: 'bg-sky-900/50 text-sky-300',
      footerIcon: 'text-sky-500',
    },
    nav: RD_PLANO_NAV,
    hidden: true,
  },
};

/** Perfiles visibles en el selector de workspace del hub (excluye hidden). */
export const VISIBLE_PROFILES: Profile[] = Object.values(PROFILES).filter(p => !p.hidden);

/**
 * Every view any profile can reach, derived from the profiles themselves so it
 * cannot drift: adding a panel to a profile makes it linkable automatically.
 * Used to validate `?vista=` before trusting it.
 */
export const LINKABLE_VIEWS: AppView[] = Array.from(
  new Set(Object.values(PROFILES).flatMap(p => p.nav.map(i => i.view))),
);

export function isLinkableView(value: string | null | undefined): value is AppView {
  return !!value && (LINKABLE_VIEWS as string[]).includes(value);
}

export const DEFAULT_PROFILE_ID: WorkspaceMode = 'rd';

export function isWorkspaceMode(value: string | null | undefined): value is WorkspaceMode {
  return !!value && Object.prototype.hasOwnProperty.call(PROFILES, value);
}

/**
 * Traduce un id de perfil viejo (`studio`, `cultura`) al actual. Devuelve null
 * si el valor no es ni un perfil vigente ni uno conocido del esquema anterior.
 */
export function normalizeProfileId(value: string | null | undefined): WorkspaceMode | null {
  if (isWorkspaceMode(value)) return value;
  if (value && Object.prototype.hasOwnProperty.call(LEGACY_PROFILE_IDS, value)) {
    return LEGACY_PROFILE_IDS[value];
  }
  return null;
}

export function getProfile(id: string | null | undefined): Profile {
  return PROFILES[normalizeProfileId(id) ?? DEFAULT_PROFILE_ID];
}

// ── Persistencia + seleccion por URL ────────────────────────────────────
// Orden de resolucion: ?perfil=<id> en la querystring manda sobre todo;
// si no viene, localStorage; si no hay nada (o es invalido en cualquiera de
// los dos casos), cae a DEFAULT_PROFILE_ID sin romper.
export const PROFILE_STORAGE_KEY = 'flujo.perfil';

export function resolveInitialProfileId(): WorkspaceMode {
  if (typeof window === 'undefined') return DEFAULT_PROFILE_ID;

  try {
    const fromUrl = normalizeProfileId(new URLSearchParams(window.location.search).get('perfil'));
    if (fromUrl) return fromUrl;
  } catch {
    // location.search inaccesible -- seguir con localStorage
  }

  try {
    const fromStorage = normalizeProfileId(window.localStorage.getItem(PROFILE_STORAGE_KEY));
    if (fromStorage) return fromStorage;
  } catch {
    // localStorage no disponible (modo privado, file://, cuota) -- caer a default
  }

  return DEFAULT_PROFILE_ID;
}

export function persistProfileId(id: WorkspaceMode): void {
  try {
    window.localStorage.setItem(PROFILE_STORAGE_KEY, id);
  } catch {
    // no bloquear la UI si no se puede persistir
  }
}
