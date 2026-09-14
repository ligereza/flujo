// planoConfig.ts — capa de configuracion en runtime para el bundle standalone
// de Plano/Rider (web/src/mainPlano.tsx). Objetivo: la persona que recibe el
// .html pueda cambiar precios sin recompilar, y exportar/importar esos
// cambios como un archivo .json para mandarlos de vuelta o respaldarlos.
//
// Persistencia: localStorage bajo PLANO_CONFIG_STORAGE_KEY. Al arrancar:
// config guardada > defaults del codigo (rdBrand.PACKS_DEFAULT_PRICES). Si
// el JSON esta corrupto o es de otra `version`, cae a defaults y devuelve un
// warning para mostrar en la UI -- nunca explota.
//
// ALCANCE HONESTO (2026-07-25): el shape ya reserva `customSymbols` y
// `presets` para la fase de iconos-custom + presets-de-layout-por-productora
// que pidio el usuario, pero esos dos campos NO estan wireados a PlanoTool.tsx
// todavia -- PlanoTool no expone props/contexto para leer su `elements` ni
// para agregar tipos de simbolo nuevos al catalogo, y esta fuera de alcance
// tocarlo en esta sesion (otro agente lo tiene tomado). Quedan en el archivo
// de config como placeholders tipados para que el formato sea compatible
// hacia adelante, pero la UI de este bundle NO ofrece botones para
// llenarlos porque no harian nada real. Ver el reporte de la sesion para la
// propuesta concreta de los puntos de extension que los desbloquearian.

import { type PackId, type PackPriceOverrides, applyPackPriceOverrides } from '../rdBrand';

export const PLANO_CONFIG_VERSION = 1;
export const PLANO_CONFIG_STORAGE_KEY = 'flujo.planoConfig';

/** Reservado -- ver ALCANCE HONESTO arriba. No wireado todavia. */
export interface CustomSymbolDef {
  id: string;
  label: string;
  color: string;
  /** Nombre de icono de lucide-react, ej "Sofa". Nunca un path SVG a mano. */
  lucideIcon: string;
}

/** Reservado -- ver ALCANCE HONESTO arriba. No wireado todavia. */
export interface PlanoPreset {
  id: string;
  nombre: string;
  productoraSlug: string | null;
  elements: unknown[];
}

export interface PlanoConfig {
  version: number;
  packPrices: PackPriceOverrides;
  customSymbols: CustomSymbolDef[];
  presets: PlanoPreset[];
}

export const DEFAULT_PLANO_CONFIG: PlanoConfig = {
  version: PLANO_CONFIG_VERSION,
  packPrices: {},
  customSymbols: [],
  presets: [],
};

const PACK_IDS: PackId[] = ['INFO', 'TESTEO', 'COMPLETO'];

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}

function sanitizePackPrices(raw: unknown): PackPriceOverrides {
  const out: PackPriceOverrides = {};
  if (!isPlainObject(raw)) return out;
  for (const id of PACK_IDS) {
    const v = raw[id];
    if (typeof v === 'number' && Number.isFinite(v) && v > 0) out[id] = v;
  }
  return out;
}

function sanitizeConfigBody(raw: Record<string, unknown>): PlanoConfig {
  return {
    version: PLANO_CONFIG_VERSION,
    packPrices: sanitizePackPrices(raw.packPrices),
    // Se preservan si vienen bien formados (para no perder datos de una
    // config futura mas nueva que se abra en un bundle viejo), aunque esta
    // version de la UI no los edite.
    customSymbols: Array.isArray(raw.customSymbols) ? (raw.customSymbols as CustomSymbolDef[]) : [],
    presets: Array.isArray(raw.presets) ? (raw.presets as PlanoPreset[]) : [],
  };
}

export interface StartupLoadResult {
  config: PlanoConfig;
  warning: string | null;
}

/** Uso al arrancar la app: SIEMPRE devuelve una config valida (cae a defaults si algo esta mal). */
export function normalizeStartupConfig(raw: unknown): StartupLoadResult {
  if (!isPlainObject(raw)) {
    return { config: { ...DEFAULT_PLANO_CONFIG }, warning: null };
  }
  if (raw.version !== PLANO_CONFIG_VERSION) {
    return {
      config: { ...DEFAULT_PLANO_CONFIG },
      warning: `Configuracion guardada con version ${String(raw.version)} (esperada ${PLANO_CONFIG_VERSION}): se uso el valor por defecto.`,
    };
  }
  return { config: sanitizeConfigBody(raw), warning: null };
}

export function loadPlanoConfig(): StartupLoadResult {
  try {
    const raw = window.localStorage.getItem(PLANO_CONFIG_STORAGE_KEY);
    if (!raw) return { config: { ...DEFAULT_PLANO_CONFIG }, warning: null };
    return normalizeStartupConfig(JSON.parse(raw));
  } catch {
    return {
      config: { ...DEFAULT_PLANO_CONFIG },
      warning: 'No se pudo leer la configuración guardada (JSON corrupto): se usó el valor por defecto.',
    };
  }
}

export function savePlanoConfig(config: PlanoConfig): void {
  try {
    window.localStorage.setItem(PLANO_CONFIG_STORAGE_KEY, JSON.stringify(config));
  } catch {
    // localStorage no disponible (modo privado, cuota, etc.) -- no bloquear la UI
  }
}

export function downloadPlanoConfig(config: PlanoConfig, filename = 'plano_rd_config.json'): void {
  const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export type ImportResult =
  | { ok: true; config: PlanoConfig }
  | { ok: false; warning: string };

/**
 * Uso al importar un archivo: a diferencia del arranque, NUNCA cae a
 * defaults en silencio -- si el archivo esta corrupto o es incompatible,
 * devuelve ok:false y el llamador no debe aplicar ningun cambio.
 */
export async function readPlanoConfigFile(file: File): Promise<ImportResult> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(await file.text());
  } catch {
    return { ok: false, warning: 'El archivo no es un JSON valido.' };
  }
  if (!isPlainObject(parsed)) {
    return { ok: false, warning: 'El archivo no tiene el formato esperado (no es un objeto JSON).' };
  }
  if (parsed.version !== PLANO_CONFIG_VERSION) {
    return { ok: false, warning: `Versión de configuración no soportada (${String(parsed.version)}, esperada ${PLANO_CONFIG_VERSION}).` };
  }
  return { ok: true, config: sanitizeConfigBody(parsed) };
}

/** Aplica la config al estado en vivo del bundle (hoy: solo precios de packs). */
export function applyPlanoConfig(config: PlanoConfig): void {
  applyPackPriceOverrides(config.packPrices);
}
