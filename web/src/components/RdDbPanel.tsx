// RdDbPanel — la base de datos RD (productoras y venues) dentro del hub.
//
// Hasta ahora la DB solo se consultaba por CLI (`flujo rd-db ...`). Este panel
// la muestra y permite lo unico que hoy se hace a mano y a destiempo:
// reemplazar el logo de una productora.
//
// Politica de datos (2026-07-25, pedido del area de eventos RD): el endpoint
// que alimenta este panel arma cada registro con allowlist explicita y NO
// entrega contactos ni handles. Si algo de eso aparece aca, es un bug.
//
// Politica de logos (2026-07-23): el logo oficial se busca en la web de la
// productora y se guarda junto a su URL de origen. NUNCA se recorta de un
// flyer: un recorte es un derivado de baja calidad y sin fuente.

import type { CSSProperties } from 'react';
import { useEffect, useRef, useState } from 'react';
import { Database, Upload, CheckCircle2, CircleDashed, MapPin, AlertTriangle, BarChart3, ChevronRight, History, Layout, Radio, FlaskConical } from 'lucide-react';
import EnsayosSection, { type Ensayos } from './EnsayosSection';

interface Venue {
  nombre: string;
  venue_id?: string | null;
  estado: string;
  preferido: boolean;
}
interface Evento {
  event_key?: string;
  nombre: string;
  fecha?: string;
  fecha_iso?: string | null;
  venue?: string;
  estado?: string;
  fuente?: string;
  lineup?: string[];
  fuentes_primarias?: string[];
  sin_fuente_primaria?: boolean;
  pack?: string;
  duracion_horas?: number;
  asistentes_estimados?: number;
  rider_ref?: string;
  layout_ref?: string;
  venue_link?: { id?: string | null; name?: string; status?: string };
  venue_source_link?: { name?: string; venue_id?: string | null; estado?: string; status?: string; reason?: string };
  flyer_link?: { ref?: string; status?: string; generated_key?: string };
  rider_link?: { ref?: string; status?: string; generated_key?: string };
  layout_link?: { ref?: string; status?: string; generated_key?: string };
  database_link?: { id?: number; status?: string; reason?: string; table?: string; venue?: { id?: number; venue_id?: string | null; status?: string; reason?: string } };
  triangulacion?: {
    status?: string;
    event_key?: string;
    identidad_completa?: boolean;
    venue_db?: { id?: number; venue_id?: string | null; status?: string; reason?: string };
    venue_canonico?: { id?: string | null; name?: string; status?: string };
  };
}
interface Distribucion {
  valor: string;
  conteo: number;
  porcentaje: number;
}
interface Procedencia {
  filas_brutas: number;
  primera_aparicion: number;
  repetidas_en_hoja: number;
  copiadas_de_otra_jornada: number;
  sin_clasificar: number;
  origenes: Record<string, number>;
}
interface Evidencia {
  productora_candidata?: string | null;
  match_candidata?: 'exacto' | 'aproximado' | 'abreviatura' | 'sin_identificar';
  event_id: string;
  hoja: string;
  indice_hoja: number;
  nombre: string;
  periodo: string;
  fecha_iso?: string | null;
  estado_fecha?: string;
  estado_duplicado?: string;
  tamano_grupo_duplicado?: number;
  venue_fuente?: string | null;
  productora_fuente?: string | null;
  estado_enlace?: string;
  filas: number;
  muestra_declarada: { campo: string; total: number; distribucion: Distribucion[] };
  resultados_colorimetricos: { campos: string[]; total: number; distribucion: Distribucion[] };
  procedencia?: Procedencia;
}
interface Productora {
  slug: string;
  nombre: string;
  aliases: string[];
  tipos: string[];
  venues: Venue[];
  logo: { estado: string; vector: boolean; archivo?: boolean };
  confirmada: boolean;
  confirmacion: string;
  fuente: string;
  eventos?: Evento[];
  /** SVG del logo horneado en el bundle sin servidor. Ausente con hub. */
  logo_svg?: string;
}
interface VenueCat {
  id: string;
  nombre: string;
  tipo: string;
  escala: string;
  capacidad: string;
}
// `__SIN_SERVIDOR__` lo define vite en los builds standalone; en el hub no
// existe, y ahi vale false.
const SIN_SERVIDOR = typeof __SIN_SERVIDOR__ !== 'undefined' && __SIN_SERVIDOR__;

/** Lectura colorimetrica de toda la evidencia: sustancia x reactivo x color. */
interface Concordancia {
  sustancia: string; reactivo: string; total: number; evaluadas: number;
  coincide: number; sin_reaccion: number; discrepa: number;
  esperado: string[]; reaccion_texto: string; alerta: string[];
  top_discrepancias: Record<string, number>;
}

interface Colorimetria {
  matriz: Record<string, Record<string, Record<string, number>>>;
  esperado: Record<string, Record<string, { colores: string[]; notas: { familia: string; reaccion: string; hex: string }[]; alerta: unknown[] }>>;
  concordancia: Concordancia[];
  por_evento: Record<string, Record<string, number>>;
  por_periodo: Record<string, Record<string, number>>;
  muestras_por_periodo: Record<string, number>;
  jornadas_por_periodo: Record<string, number>;
  procedencia_por_periodo?: Record<string, Record<string, number>>;
  por_color: Record<string, number>;
  por_reactivo: Record<string, number>;
  por_sustancia: Record<string, number>;
  variantes: Record<string, Record<string, number>>;
  estados: Record<string, number>;
  pendientes: { crudo: string; estado: string; sin_reconocer: string[]; identidades: string[] }[];
  pendientes_total: number;
  muestras: number;
  observaciones: number;
  etiquetas: Record<string, string>;
  etiquetas_reactivo: Record<string, string>;
  hex: Record<string, string>;
  paleta_rd: Record<string, { familia: string; reaccion: string; hex: string }[]>;
  limitacion: string;
}

interface Data {
  /** true = los datos vienen dentro del archivo, no de un servidor. */
  horneado?: boolean;
  colorimetria?: Colorimetria;
  productoras: Productora[];
  venues: VenueCat[];
  evidencia_periodos?: Record<string, Evidencia[]>;
  ensayos?: Ensayos;
  evidencia_2025?: Evidencia[];
  resumen?: {
    productoras: number;
    con_vector: number;
    confirmadas: number;
    venues: number;
    eventos?: number;
    eventos_triangulables?: number;
    eventos_sin_fuente_primaria?: number;
    eventos_sin_fecha_iso?: number;
    eventos_sin_lineup?: number;
    eventos_db_exactos?: number;
    eventos_db_pendientes?: number;
    eventos_venue_db_exactos?: number;
    eventos_venue_canonicos?: number;
    eventos_triangulacion_completa?: number;
  };
  excluido_a_proposito?: string[];
  error?: string;
}

interface RdHostProducer {
  productora_slug?: string;
  logo_loaded?: boolean;
  logo_status?: string;
}
interface RdHostVenue {
  venue_nombre?: string;
}
interface RdHostEvent {
  event_id: string;
  event_label_candidate?: string;
  link_status?: string;
  link_review_status?: string;
  productoras?: RdHostProducer[];
  venues?: RdHostVenue[];
  mesas?: Array<{ etiqueta?: string }>;
}
interface RdHostBootstrap {
  schema?: string;
  events?: RdHostEvent[];
  xioEvents?: Array<{ client_event_id?: string; event_name?: string }>;
}
interface RdHostTest {
  reagent?: string;
  resultColor?: string;
  family?: string;
  matchesDeclared?: boolean | null;
  limitation?: string;
}
interface RdHostSample {
  sampleId: number;
  date?: string;
  eventRef?: string;
  sampleCode?: string;
  substanceDeclared?: string;
  sampleType?: string;
  color?: string;
  texture?: string;
  photoRef?: string;
  captures?: Array<{ kind?: string; silhouettePreviewRef?: string; reliefRef?: string }>;
  tests?: RdHostTest[];
}
interface RdHostSamples {
  eventRef?: string;
  sampleCount?: number;
  samples?: RdHostSample[];
}

// Los estados del logo llegan como llaves del dato ("sin_ficha",
// "no_encontrado"). Mostrados tal cual parecen un error del sistema; acá se
// dicen como se los diría una persona.
const ESTADO_LOGO: Record<string, string> = {
  sin_ficha: 'sin ficha',
  no_encontrado: 'sin logo',
  raster: 'logo sin vectorizar',
  vector: 'logo vectorial',
};

type VistaId = 'colorimetria' | 'jornadas' | 'productoras' | 'campo';

const VISTAS: {
  id: VistaId; nombre: string; icono: typeof Database;
  cuenta?: (d: Data, r: NonNullable<Data['resumen']>) => number;
}[] = [
  { id: 'colorimetria', nombre: 'Ensayos', icono: FlaskConical,
    cuenta: d => d.ensayos?.obs.length ?? Object.keys(d.colorimetria?.matriz ?? {}).length },
  { id: 'jornadas', nombre: 'Jornadas', icono: History,
    cuenta: d => (Object.values(d.evidencia_periodos ?? {}).reduce((n, e) => n + e.length, 0)
      || (d.evidencia_2025?.length ?? 0)) },
  { id: 'productoras', nombre: 'Productoras', icono: Database,
    cuenta: (_d, r) => r.productoras },
  { id: 'campo', nombre: 'Campo', icono: Radio,
    cuenta: (_d, r) => r.venues },
];

/**
 * Resumen en una franja, no en doce tarjetas.
 *
 * El panel abria con doce cajas grandes de metrica, cada una con titulo,
 * numero y linea de ayuda. En un telefono eso son seis filas antes del primer
 * dato util. Aca quedan las cuatro cifras que se miran de reojo; el resto vive
 * dentro de la vista a la que pertenecen, que es donde significan algo.
 */
function ResumenCompacto({ r, c, evidencia }: {
  r: NonNullable<Data['resumen']>;
  c?: Colorimetria;
  evidencia?: Record<string, Evidencia[]>;
}) {
  const jornadas = Object.values(evidencia ?? {}).reduce((n, e) => n + e.length, 0);
  // `muestras propias` y no `muestras`: el total bruto incluye las filas
  // repetidas dentro de su hoja y las copiadas de otra jornada, y ponerlo
  // aqui arriba contradecia el conteo de la vista de Ensayos, que solo cuenta
  // las propias. Dos cifras distintas del mismo dato en la misma pantalla son
  // una cifra menos, no una mas.
  const propias = Object.values(evidencia ?? {}).reduce(
    (n, e) => n + e.reduce((m, x) => m + (x.procedencia?.primera_aparicion ?? x.filas), 0), 0);
  const celdas = [
    { k: 'muestras propias', v: propias || (c?.muestras ?? 0) },
    { k: 'filas fuente', v: Object.values(evidencia ?? {}).reduce(
        (n, e) => n + e.reduce((m, x) => m + x.filas, 0), 0) },
    { k: 'jornadas', v: jornadas },
    { k: 'prod.', v: r.productoras },
  ];
  return (
    <div className="flex divide-x divide-zinc-800 overflow-x-auto rounded-xl border border-zinc-800 bg-zinc-900/40">
      {celdas.map(x => (
        <div key={x.k} className="min-w-0 flex-1 px-3 py-2.5">
          <div className="text-lg font-bold leading-none tabular-nums text-zinc-100">{x.v.toLocaleString('es-CL')}</div>
          <div className="mt-1 text-[10px] uppercase tracking-wider text-zinc-600">{x.k}</div>
        </div>
      ))}
    </div>
  );
}

function PeriodosResumen({ evidencia }: {
  evidencia: Record<string, Evidencia[]>;
}) {
  const periodos = Object.keys(evidencia).sort();
  if (!periodos.length) return null;
  return (
    <div className="mt-3 flex flex-wrap items-center gap-1.5 text-[10px]">
      <span className="mr-1 uppercase tracking-wider text-zinc-600">Períodos</span>
      {periodos.map(periodo => (
        <span key={periodo} className="rounded border border-zinc-800 bg-zinc-900/50 px-2 py-1 text-zinc-400">
          {periodo} · {evidencia[periodo].length} jornadas · {evidencia[periodo].reduce((n, e) => n + e.filas, 0)} filas · {evidencia[periodo].reduce((n, e) => n + (e.procedencia?.primera_aparicion ?? e.filas), 0)} propias
        </span>
      ))}
    </div>
  );
}

export default function RdDbPanel() {
  const [vista, setVista] = useState<VistaId>('colorimetria');
  const [periodoActivo, setPeriodoActivo] = useState('todos');
  const [data, setData] = useState<Data | null>(null);
  const [estado, setEstado] = useState<'cargando' | 'ok' | 'error'>('cargando');
  const [subiendo, setSubiendo] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string>('');
  const [productoraActiva, setProductoraActiva] = useState<string | null>(null);
  const [evidenciaActiva, setEvidenciaActiva] = useState<string | null>(null);
  const [hostBootstrap, setHostBootstrap] = useState<RdHostBootstrap | null>(null);
  const [hostEventRef, setHostEventRef] = useState('');
  const [hostSamples, setHostSamples] = useState<RdHostSamples | null>(null);
  const [hostError, setHostError] = useState('');
  const [planoEstado, setPlanoEstado] = useState<{ key: string; status: 'cargando' | 'ready' | 'pending_review' | 'error'; missing?: string[]; error?: string; generated?: boolean } | null>(null);
  const [planoDraftKey, setPlanoDraftKey] = useState<string | null>(null);
  const [planoDraftPack, setPlanoDraftPack] = useState('');
  const [planoDraftDuration, setPlanoDraftDuration] = useState('');
  const [planoDraftAttendees, setPlanoDraftAttendees] = useState('');
  // Cache-buster: tras reemplazar un logo hay que forzar que el <img> lo relea.
  const [rev, setRev] = useState(0);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const objetivo = useRef<string>('');

  // Sin hub se usa la copia horneada en el bundle. Antes esto mostraba "error"
  // en el archivo que se entrega sin servidor, que es justo donde no hay a
  // quien pedirle. La copia sale de la MISMA funcion que sirve el hub
  // (flujo.rd.panel), horneada por tools/gen_rd_standalone.py.
  // En el bundle suelto se va derecho al respaldo: probar el servidor primero
  // dejaba un 404 en la consola de quien abre el archivo.
  const cargarHorneada = async () => {
    try {
      const d = (await import('../data/rdDbEmbebida.json')).default as unknown as Data;
      setData(d);
      setEstado('ok');
    } catch {
      setEstado('error');
    }
  };

  const cargar = () =>
    SIN_SERVIDOR ? cargarHorneada() : fetch('/api/rd-db')
      .then(r => r.json())
      .then(d => {
        setData(d);
        setEstado(d?.error ? 'error' : 'ok');
      })
      .catch(cargarHorneada);

  useEffect(() => {
    cargar();
  }, []);

  // The same RD bundle is also served by XIO at /rd_field/view. Only there do
  // we ask the host for its live DB projection; a file:// standalone build
  // stays autonomous and does not produce failing 404 requests.
  useEffect(() => {
    const servedByXio = typeof window !== 'undefined'
      && window.location.pathname.includes('/api/plugins/rd_field');
    if (!SIN_SERVIDOR || !servedByXio) return;
    let active = true;
    fetch('/api/plugins/rd_field/bootstrap', { cache: 'no-store' })
      .then(response => response.ok ? response.json() : Promise.reject(new Error(`HTTP ${response.status}`)))
      .then((next: RdHostBootstrap) => {
        if (!active) return;
        setHostBootstrap(next);
        setHostEventRef(current => current || next.events?.[0]?.event_id || '');
        setHostError('');
      })
      .catch(error => {
        if (active) setHostError(`No se pudo leer la DB del host XIO (${String(error?.message || error)}).`);
      });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!hostEventRef) return;
    let active = true;
    fetch(`/api/plugins/rd_field/samples?eventRef=${encodeURIComponent(hostEventRef)}`, { cache: 'no-store' })
      .then(response => response.ok ? response.json() : Promise.reject(new Error(`HTTP ${response.status}`)))
      .then((next: RdHostSamples) => { if (active) setHostSamples(next); })
      .catch(error => {
        if (active) setHostError(`No se pudieron leer las muestras de ${hostEventRef} (${String(error?.message || error)}).`);
      });
    return () => { active = false; };
  }, [hostEventRef]);

  const pedirArchivo = (slug: string) => {
    objetivo.current = slug;
    inputRef.current?.click();
  };

  const alElegir = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = ''; // permite volver a elegir el mismo archivo
    if (!file) return;
    const slug = objetivo.current;
    setSubiendo(slug);
    setAviso('');
    try {
      const b64: string = await new Promise((ok, err) => {
        const fr = new FileReader();
        fr.onload = () => ok(String(fr.result));
        fr.onerror = () => err(fr.error);
        fr.readAsDataURL(file);
      });
      const fuente = window.prompt(
        `URL de origen del logo de "${slug}" (opcional, pero conviene: queda guardada junto al archivo)`,
        '',
      );
      const r = await fetch('/api/rd-db/logo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slug, filename: file.name, data: b64, fuente: fuente || '' }),
      }).then(x => x.json());
      if (r.ok) {
        setAviso(`${slug}: logo reemplazado (${r.archivo}, ${r.kb} KB)${r.fuente_guardada ? ' + fuente' : ''}`);
        setRev(v => v + 1);
        cargar();
      } else {
        setAviso(`${slug}: ${r.error}`);
      }
    } catch (err) {
      setAviso(`${slug}: fallo al subir (${err})`);
    } finally {
      setSubiendo(null);
    }
  };

  const r = data?.resumen;
  const activa = data?.productoras.find(p => p.slug === productoraActiva) ?? null;
  const evidenciaPeriodos = data?.evidencia_periodos
    ?? (data?.evidencia_2025 ? { '2025': data.evidencia_2025 } : {});
  const periodos = Object.keys(evidenciaPeriodos).sort();
  const evidenciaVisible = periodoActivo === 'todos'
    ? periodos.flatMap(periodo => evidenciaPeriodos[periodo] ?? [])
    : (evidenciaPeriodos[periodoActivo] ?? []);
  const evidencia = evidenciaVisible.find(e => e.event_id === evidenciaActiva) ?? null;
  const hostEvent = hostBootstrap?.events?.find(event => event.event_id === hostEventRef) ?? null;
  const hostTests = (hostSamples?.samples || []).flatMap(sample => sample.tests || []);
  const hostColors = hostTests.reduce<Record<string, number>>((counts, test) => {
    const value = String(test.resultColor || '').trim() || 'sin resultado';
    counts[value] = (counts[value] || 0) + 1;
    return counts;
  }, {});
  const hostColorRows = Object.entries(hostColors)
    .sort(([, left], [, right]) => right - left)
    .slice(0, 8);
  const enlacePendiente = (ev: Evento) => [ev.flyer_link?.status !== 'explicit', ev.rider_link?.status !== 'explicit', ev.layout_link?.status !== 'explicit'].filter(Boolean).length;
  const venueResumen = activa?.eventos?.reduce<Record<string, number>>((counts, ev) => {
    const venue = ev.venue_link?.name || ev.venue;
    if (venue) counts[venue] = (counts[venue] || 0) + 1;
    return counts;
  }, {}) ?? {};
  const venueMasRepetido = Object.entries(venueResumen).sort(([, left], [, right]) => right - left)[0];

  const abrirPlanoRider = async (eventKey: string, overrides?: { pack: string; duracion_horas: number; asistentes_estimados: number }) => {
    setPlanoEstado({ key: eventKey, status: 'cargando' });
    try {
      const response = await fetch('/api/rd-db/event-link', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event_key: eventKey, ...(overrides ? { overrides } : {}) }),
      });
      const result = await response.json();
      if (!response.ok || result.status === 'error' || result.status === 'not_found') {
        throw new Error(result.error || `HTTP ${response.status}`);
      }
      setPlanoEstado({ key: eventKey, status: result.status, missing: result.missing, generated: result.links?.rider?.status === 'generated' || result.links?.layout?.status === 'generated' });
    } catch (error) {
      setPlanoEstado({ key: eventKey, status: 'error', error: String(error instanceof Error ? error.message : error) });
    }
  };

  const prepararPlanoRider = (ev: Evento) => {
    if (!ev.event_key) return;
    if (ev.pack && ev.duracion_horas && ev.asistentes_estimados) {
      abrirPlanoRider(ev.event_key, {
        pack: ev.pack,
        duracion_horas: ev.duracion_horas,
        asistentes_estimados: ev.asistentes_estimados,
      });
      return;
    }
    setPlanoDraftKey(ev.event_key);
    setPlanoDraftPack(ev.pack || '');
    setPlanoDraftDuration(ev.duracion_horas ? String(ev.duracion_horas) : '');
    setPlanoDraftAttendees(ev.asistentes_estimados ? String(ev.asistentes_estimados) : '');
    setPlanoEstado(null);
  };

  const generarPlanoRider = (eventKey: string) => {
    const duration = Number(planoDraftDuration);
    const attendees = Number(planoDraftAttendees);
    if (!planoDraftPack || !(duration > 0) || !(attendees > 0)) {
      setPlanoEstado({ key: eventKey, status: 'error', error: 'Completa pack, duración y asistentes con valores mayores que cero.' });
      return;
    }
    setPlanoDraftKey(null);
    abrirPlanoRider(eventKey, {
      pack: planoDraftPack,
      duracion_horas: duration,
      asistentes_estimados: attendees,
    });
  };

  return (
    <div className="space-y-6">
      <input ref={inputRef} type="file" accept=".png,.jpg,.jpeg,.webp,.svg" onChange={alElegir} className="hidden" />

      <header className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-900/40 text-emerald-300">
          <Database className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-xl font-bold tracking-tight">Base de datos RD</h1>
          <p className="text-sm text-zinc-500">
            {data?.horneado
              ? 'Testeos, jornadas y productoras, con los datos dentro de este archivo. Para editarlos hace falta la aplicación completa.'
              : 'Los testeos históricos, las jornadas que los produjeron y las productoras detrás.'}
          </p>
        </div>
      </header>

      {estado === 'error' && (
        <div className="flex items-start gap-2 rounded-xl border border-amber-800/50 bg-amber-950/30 p-4 text-sm text-amber-300">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            Sin backend. Este panel lee la DB del repo, así que necesita <code>py -m flujo app</code> corriendo.
          </div>
        </div>
      )}

      {aviso && (
        <div className="rounded-xl border border-zinc-700 bg-zinc-900/60 px-4 py-2 text-[13px] text-zinc-300">{aviso}</div>
      )}

      {estado === 'ok' && r && (
        <>
          <ResumenCompacto r={r} c={data!.colorimetria} evidencia={evidenciaPeriodos} />
          <PeriodosResumen evidencia={evidenciaPeriodos} />

          {/* Una vista a la vez. Antes el panel apilaba doce tarjetas de
              metricas y siete secciones a ancho completo: en un telefono eso
              son varias pantallas de scroll antes de ver un dato. */}
          <nav className="grid grid-cols-2 gap-1 rounded-xl border border-zinc-800 bg-zinc-900/40 p-1 sm:flex">
            {VISTAS.map(v => (
              <button
                key={v.id}
                type="button"
                onClick={() => setVista(v.id)}
                className={`flex min-w-0 items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium ${
                  vista === v.id ? 'bg-zinc-800 text-zinc-100' : 'text-zinc-500 hover:text-zinc-300'}`}
              >
                <v.icono className="h-3.5 w-3.5 shrink-0" />
                <span className="truncate">{v.nombre}</span>
                {v.cuenta !== undefined && <span className="ml-auto shrink-0 text-[10px] tabular-nums text-zinc-600">{v.cuenta(data!, r)}</span>}
              </button>
            ))}
          </nav>

          {vista === 'campo' && hostBootstrap && (
            <section className="rounded-xl border border-sky-900/60 bg-sky-950/10 p-4 sm:p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-sky-300">
                    <Radio className="h-3.5 w-3.5" /> Host XIO · registros de terreno
                  </div>
                  <h2 className="mt-1 text-lg font-bold text-zinc-100">DB offline del dispositivo que corre el server</h2>
                  <p className="mt-1 max-w-3xl text-xs leading-relaxed text-zinc-500">
                    Lectura en vivo del mismo host que recibe la APK. Se conserva el <code>event_id</code> exacto; esta vista no crea ni enlaza eventos por nombre.
                  </p>
                </div>
                <span className="rounded-lg border border-sky-900/60 px-2 py-1 text-[10px] text-sky-300">{hostBootstrap.schema || 'xio-flujo-rd'}</span>
              </div>

              <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)]">
                <label className="block rounded-xl border border-zinc-800 bg-zinc-950/40 p-4">
                  <span className="block text-[10px] font-bold uppercase tracking-wider text-zinc-600">Evento exacto del host</span>
                  <select value={hostEventRef} onChange={event => setHostEventRef(event.target.value)} className="mt-2 min-h-10 w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 text-sm text-zinc-200">
                    {(hostBootstrap.events || []).map(event => {
                      const producer = event.productoras?.map(item => item.productora_slug).filter(Boolean).join(' · ');
                      const venue = event.venues?.map(item => item.venue_nombre).filter(Boolean).join(' · ');
                      return <option key={event.event_id} value={event.event_id}>{event.event_label_candidate || event.event_id}{producer ? ` · ${producer}` : ''}{venue ? ` · ${venue}` : ''}</option>;
                    })}
                  </select>
                  {hostEvent && <p className="mt-2 text-[11px] text-zinc-500"><code>{hostEvent.event_id}</code> · {hostEvent.link_status || 'estado de enlace pendiente'} · {hostEvent.productoras?.some(item => item.logo_loaded) ? 'logo cargado en el catálogo' : 'sin logo cargado'}</p>}
                </label>

                <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-600">Resultados colorimétricos registrados</span>
                    <span className="text-xs text-zinc-400">{hostSamples?.sampleCount ?? 0} muestras · {hostTests.length} pruebas</span>
                  </div>
                  <div className="mt-3 space-y-2">
                    {hostColorRows.map(([value, count]) => {
                      const percentage = hostTests.length ? (count / hostTests.length) * 100 : 0;
                      return <div key={value}><div className="flex items-center justify-between gap-3 text-[11px]"><span className="min-w-0 truncate text-zinc-400" title={value}>{value}</span><span className="shrink-0 text-zinc-500">{count} · {percentage.toFixed(1).replace('.0', '')}%</span></div><div className="mt-1 h-1.5 overflow-hidden rounded-full bg-zinc-800"><div className="h-full rounded-full bg-sky-400" style={{ width: `${Math.min(percentage, 100)}%` }} /></div></div>;
                    })}
                    {!hostColorRows.length && <p className="text-[11px] text-zinc-600">Aún no hay resultados para este evento.</p>}
                  </div>
                </div>
              </div>

              {hostSamples?.samples?.length ? (
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  {hostSamples.samples.map(sample => (
                    <article key={sample.sampleId} className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
                      <div className="flex items-start justify-between gap-3"><div><h3 className="font-bold text-zinc-100">{sample.sampleCode || `Muestra ${sample.sampleId}`}</h3><p className="mt-1 text-[11px] text-zinc-500">{sample.date || 'sin fecha'} · {sample.sampleType || 'tipo no indicado'}</p></div><span className="rounded border border-sky-900/60 px-2 py-1 text-[10px] text-sky-300">{sample.substanceDeclared || 'sustancia no declarada'}</span></div>
                      <div className="mt-3 grid grid-cols-2 gap-2 text-[11px]"><div className="rounded-lg border border-zinc-800 p-2"><span className="block text-zinc-600">Color declarado</span><span className="text-zinc-300">{sample.color || 'sin registro'}</span></div><div className="rounded-lg border border-zinc-800 p-2"><span className="block text-zinc-600">Textura</span><span className="text-zinc-300">{sample.texture || 'sin registro'}</span></div></div>
                      <div className="mt-3 space-y-1 text-[11px] text-zinc-500">{(sample.tests || []).map(test => <div key={`${sample.sampleId}-${test.reagent}-${test.resultColor}`} className="flex justify-between gap-3 border-t border-zinc-800/70 pt-1"><span>{test.reagent || 'reactivo pendiente'}</span><span className="text-zinc-300">{test.resultColor || 'sin resultado'}</span></div>)}{!sample.tests?.length && <p>Sin pruebas registradas.</p>}</div>
                      <p className="mt-3 text-[10px] text-zinc-600">Capturas: {sample.captures?.length || 0} · foto/máscara/relieve se conservan como referencias del host.</p>
                    </article>
                  ))}
                </div>
              ) : (
                <p className="mt-4 rounded-lg border border-dashed border-zinc-800 px-3 py-3 text-xs text-zinc-600">Este <code>event_id</code> existe en el catálogo, pero todavía no tiene muestras guardadas en el host.</p>
              )}
              {hostError && <p className="mt-3 text-xs text-amber-400">{hostError}</p>}
              <p className="mt-4 flex items-start gap-2 text-[11px] leading-relaxed text-zinc-600"><Radio className="mt-0.5 h-3.5 w-3.5 shrink-0" /> Los porcentajes describen valores guardados; no interpretan identidad, pureza, dosis ni seguridad.</p>
            </section>
          )}

          {vista === 'productoras' && (
          <section className="rounded-xl border border-zinc-800 bg-zinc-900/40">
            <div className="flex flex-wrap items-center gap-2 border-b border-zinc-800 px-4 py-3">
              <h2 className="text-sm font-bold">Productoras</h2>
              <span className="text-[11px] text-zinc-600">
                {data?.horneado ? '' : 'clic en el recuadro del logo para reemplazarlo'}
              </span>
            </div>
            <div className="divide-y divide-zinc-800/60">
              {data!.productoras.map(p => (
                <div key={p.slug} className={`flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:gap-4 ${productoraActiva === p.slug ? 'bg-emerald-950/15' : ''}`}>
                  <button
                    onClick={() => pedirArchivo(p.slug)}
                    disabled={subiendo === p.slug || !!data?.horneado}
                    title={data?.horneado
                      ? "Para cambiar el logo hace falta la aplicación completa"
                      : "Reemplazar logo"}
                    className="group relative flex h-14 w-20 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-zinc-800 bg-zinc-950 hover:border-emerald-700"
                  >
                    {/* Solo se pide el logo si el backend dice que hay uno. Antes
                        se pedia para las 20 y las 14 sin logo devolvian 404: la
                        consola quedaba con 18 errores rojos que se leen como una
                        falla de la app, y no lo son. */}
                    {/* Con el logo horneado se dibuja directo: pedirlo al
                        backend daba 404 en el archivo suelto y dejaba el
                        recuadro roto justo en las productoras que SI lo
                        tienen, al reves de lo que se quiere mostrar. */}
                    {p.logo_svg ? (
                      <span
                        className="max-h-full max-w-full p-1 [&>svg]:h-full [&>svg]:w-full [&>svg]:object-contain"
                        dangerouslySetInnerHTML={{ __html: p.logo_svg }}
                      />
                    ) : (!SIN_SERVIDOR && p.logo.archivo !== false) && (
                      <img
                        src={`/api/rd-db/logo?slug=${p.slug}&v=${rev}`}
                        alt=""
                        className="max-h-full max-w-full object-contain p-1"
                        onError={e => ((e.target as HTMLImageElement).style.visibility = 'hidden')}
                      />
                    )}
                    {p.logo.archivo === false && (
                      <span className="text-[9px] uppercase tracking-widest text-zinc-700">sin logo</span>
                    )}
                    <span className="absolute inset-0 flex items-center justify-center bg-black/70 opacity-0 transition-opacity group-hover:opacity-100">
                      <Upload className="h-4 w-4 text-emerald-300" />
                    </span>
                    {subiendo === p.slug && (
                      <span className="absolute inset-0 flex items-center justify-center bg-black/80 text-[10px] text-emerald-300">
                        subiendo…
                      </span>
                    )}
                  </button>

                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => { setProductoraActiva(p.slug); setEvidenciaActiva(null); }}
                        className="flex min-h-8 items-center gap-1 text-left font-medium text-zinc-100 hover:text-emerald-300"
                        aria-pressed={productoraActiva === p.slug}
                      >
                        {p.nombre}<ChevronRight className="h-3.5 w-3.5 text-zinc-600" />
                      </button>
                      <code className="text-[10px] text-zinc-600">{p.slug}</code>
                      {p.confirmada ? (
                        <span title={p.confirmacion} className="flex items-center gap-1 text-[10px] text-emerald-400">
                          <CheckCircle2 className="h-3 w-3" /> confirmada
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-[10px] text-zinc-600">
                          <CircleDashed className="h-3 w-3" /> sin confirmar
                        </span>
                      )}
                      {(p.eventos?.length ?? 0) > 0 && (
                        <span className={`rounded px-1.5 py-px text-[10px] ${
                          p.eventos!.some(e => e.sin_fuente_primaria)
                            ? 'bg-amber-950/50 text-amber-300'
                            : 'bg-emerald-950/50 text-emerald-300'
                        }`}>
                          {p.eventos!.filter(e => e.sin_fuente_primaria).length
                            ? `${p.eventos!.filter(e => e.sin_fuente_primaria).length} sin fuente primaria`
                            : 'fuentes primarias OK'}
                        </span>
                      )}
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-1.5">
                      {p.tipos.map(t => (
                        <span key={t} className="rounded border border-zinc-800 px-1.5 py-px text-[10px] text-zinc-500">
                          {t}
                        </span>
                      ))}
                      {p.venues.map(v => (
                        <span
                          key={v.nombre}
                          className="flex items-center gap-1 rounded border border-sky-900/50 bg-sky-950/30 px-1.5 py-px text-[10px] text-sky-300"
                        >
                          <MapPin className="h-2.5 w-2.5" />
                          {v.nombre}
                        </span>
                      ))}
                    </div>
                  </div>

                  <span
                    className={`shrink-0 rounded px-2 py-0.5 text-[10px] font-bold ${
                      p.logo.vector
                        ? 'bg-emerald-900/50 text-emerald-300'
                        : 'bg-zinc-800 text-zinc-500'
                    }`}
                  >
                    {/* El estado venia crudo del dato: "sin_ficha",
                        "no_encontrado". Son llaves, no palabras, y se leian
                        como si algo estuviera roto. */}
                    {p.logo.vector ? 'logo vectorial' : ESTADO_LOGO[p.logo.estado] || 'sin logo'}
                  </span>
                </div>
              ))}
            </div>
          </section>

          )}

          {vista === 'productoras' && activa && (
            <section className="rounded-xl border border-emerald-900/60 bg-emerald-950/10 p-4 sm:p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-emerald-400">
                    <Layout className="h-3.5 w-3.5" /> Ficha de productora
                  </div>
                  <h2 className="mt-1 text-lg font-bold text-zinc-100">{activa.nombre}</h2>
                  <p className="mt-1 max-w-2xl text-xs leading-relaxed text-zinc-500">
                    Aquí se unen los eventos declarados por la productora con el venue conocido. El rider/plano queda como referencia pendiente hasta que exista un enlace explícito; no se adivina.
                  </p>
                </div>
                <button type="button" onClick={() => setProductoraActiva(null)} className="min-h-8 rounded-lg border border-zinc-800 px-3 text-xs text-zinc-500 hover:text-zinc-200">
                  cerrar
                </button>
              </div>
              {activa.eventos?.length ? (
                <>
                {(activa.venues.length > 0 || venueMasRepetido) && <div className="mt-4 flex flex-wrap items-center gap-1.5 text-[10px]">
                  {venueMasRepetido && <span className="rounded border border-sky-900/50 bg-sky-950/20 px-2 py-1 text-sky-300">venue más usado: {venueMasRepetido[0]} · {venueMasRepetido[1]} evento{venueMasRepetido[1] === 1 ? '' : 's'}</span>}
                  {activa.venues.map(v => <span key={v.nombre} className="rounded border border-zinc-800 px-2 py-1 text-zinc-500">ficha venue: {v.nombre}</span>)}
                </div>}
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  {activa.eventos.map((ev, index) => (
                    <article key={`${ev.nombre}-${index}`} className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <h3 className="font-semibold text-zinc-100">{ev.nombre}</h3>
                          <p className="mt-1 text-xs text-zinc-500">{ev.fecha || 'Fecha pendiente'}</p>
                        </div>
                        <div className="flex shrink-0 items-center gap-1.5">
                          <span className="rounded bg-zinc-800 px-2 py-1 text-[10px] text-zinc-400">{ev.estado || 'sin estado'}</span>
                          {!SIN_SERVIDOR && ev.event_key && <button type="button" onClick={() => prepararPlanoRider(ev)} className="rounded border border-emerald-900/60 px-2 py-1 text-[10px] text-emerald-300 hover:bg-emerald-950/40">Plano / rider</button>}
                        </div>
                      </div>
                      <div className="mt-3 flex flex-wrap items-center gap-1.5 text-[10px]">
                        {(ev.venue_link?.name || ev.venue) && <span className="rounded border border-sky-900/50 bg-sky-950/20 px-2 py-1 text-sky-300">⌖ {ev.venue_link?.name || ev.venue}</span>}
                        {ev.venue_link?.status === 'exact' && <span className="rounded border border-emerald-900/50 bg-emerald-950/20 px-2 py-1 text-emerald-300">venue exacto</span>}
                        {ev.triangulacion?.venue_db?.status === 'exact' && <span className="rounded border border-sky-900/50 bg-sky-950/20 px-2 py-1 text-sky-300" title="Coincidencia con la declaración de venue de la productora en SQLite">venue en DB</span>}
                        {ev.flyer_link?.status === 'explicit' && <span className="rounded border border-zinc-800 px-2 py-1 text-zinc-500">Flyer: {ev.flyer_link.ref}</span>}
                        {ev.rider_link?.status === 'explicit' && <span className="rounded border border-zinc-800 px-2 py-1 text-zinc-500">Rider: {ev.rider_link.ref}</span>}
                        {ev.layout_link?.status === 'explicit' && <span className="rounded border border-zinc-800 px-2 py-1 text-zinc-500">Layout: {ev.layout_link.ref}</span>}
                        {ev.triangulacion?.status === 'exact' && <span className="rounded border border-emerald-900/50 bg-emerald-950/20 px-2 py-1 text-emerald-300" title="Coincidencia de clave estable con data/rd.db">DB exacta{ev.database_link?.id ? ` · fila ${ev.database_link.id}` : ''}</span>}
                        {ev.triangulacion?.status && ev.triangulacion.status !== 'exact' && <span className="rounded border border-amber-900/50 bg-amber-950/20 px-2 py-1 text-amber-300" title={ev.database_link?.reason || 'La proyección SQLite requiere revisión'}>DB {ev.triangulacion.status === 'missing' ? 'sin fila' : 'revisar'}</span>}
                        {ev.fuentes_primarias?.length ? <span className="rounded border border-zinc-800 px-2 py-1 text-zinc-500">fuente primaria</span> : null}
                        {enlacePendiente(ev) > 0 && <span className="rounded border border-amber-900/50 bg-amber-950/20 px-2 py-1 text-amber-300">{enlacePendiente(ev)} enlace{enlacePendiente(ev) > 1 ? 's' : ''} pendiente{enlacePendiente(ev) > 1 ? 's' : ''}</span>}
                        {ev.event_key && <code className="max-w-full truncate px-1 text-[9px] text-zinc-700" title={ev.event_key}>{ev.event_key}</code>}
                      </div>
                      {planoDraftKey === ev.event_key && (
                        <div className="mt-3 rounded-lg border border-emerald-900/50 bg-emerald-950/10 p-3">
                          <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">Generar desde este evento</div>
                          <div className="mt-2 grid gap-2 sm:grid-cols-3">
                            <select value={planoDraftPack} onChange={e => setPlanoDraftPack(e.target.value)} className="min-h-8 rounded border border-zinc-700 bg-zinc-900 px-2 text-[11px] text-zinc-200">
                              <option value="">Pack…</option>
                              <option value="INFO">INFO · Informativo</option>
                              <option value="TESTEO">TESTEO · Testeo e informativo</option>
                              <option value="COMPLETO">COMPLETO · Servicio completo</option>
                            </select>
                            <input type="number" min="0.5" step="0.5" placeholder="Duración (h)" value={planoDraftDuration} onChange={e => setPlanoDraftDuration(e.target.value)} className="min-h-8 rounded border border-zinc-700 bg-zinc-900 px-2 text-[11px] text-zinc-200 placeholder:text-zinc-600" />
                            <input type="number" min="1" step="1" placeholder="Asistentes" value={planoDraftAttendees} onChange={e => setPlanoDraftAttendees(e.target.value)} className="min-h-8 rounded border border-zinc-700 bg-zinc-900 px-2 text-[11px] text-zinc-200 placeholder:text-zinc-600" />
                          </div>
                          <div className="mt-2 flex items-center gap-2">
                            <button type="button" onClick={() => generarPlanoRider(ev.event_key!)} className="rounded border border-emerald-800 bg-emerald-950/40 px-2 py-1 text-[10px] text-emerald-300">Generar</button>
                            <button type="button" onClick={() => setPlanoDraftKey(null)} className="rounded border border-zinc-800 px-2 py-1 text-[10px] text-zinc-500">Cancelar</button>
                            <span className="text-[10px] text-zinc-600">No modifica la base; usa el motor existente.</span>
                          </div>
                        </div>
                      )}
                      {(() => {
                        const estadoEvento = planoEstado?.key === ev.event_key ? planoEstado : null;
                        return estadoEvento && estadoEvento.status !== 'cargando' && <p className={`mt-2 text-[10px] ${estadoEvento.status === 'error' ? 'text-red-300' : estadoEvento.status === 'ready' ? 'text-emerald-300' : 'text-amber-300'}`}>
                          {estadoEvento.status === 'ready' ? (estadoEvento.generated ? 'Plano y rider generados por el motor para este evento.' : 'Motor Plano-Rider listo para este evento.') : estadoEvento.status === 'pending_review' ? `Pendiente: faltan ${(estadoEvento.missing || []).join(', ')}.` : `No se pudo abrir: ${estadoEvento.error}`}
                        </p>;
                      })()}
                    </article>
                  ))}
                </div>
                </>
              ) : (
                <div className="mt-4 rounded-lg border border-dashed border-zinc-800 px-4 py-3 text-xs text-zinc-500">No hay eventos declarados para esta productora.</div>
              )}
            </section>
          )}

          {vista === 'colorimetria' && (data!.ensayos
            ? <EnsayosSection e={data!.ensayos} />
            : data!.colorimetria && <ColorimetriaSection c={data!.colorimetria} />)}

          {vista === 'jornadas' && evidenciaVisible.length > 0 && (
            <section className="rounded-xl border border-violet-900/50 bg-violet-950/10">
              <div className="flex flex-wrap items-start justify-between gap-3 border-b border-violet-900/40 px-4 py-4">
                <div>
                  <h2 className="flex items-center gap-2 text-sm font-bold text-zinc-100"><History className="h-4 w-4 text-violet-300" /> Historial de evidencia</h2>
                  <p className="mt-1 max-w-3xl text-xs leading-relaxed text-zinc-500">Fuente histórica importada por período. Las hojas aún no tienen enlace humano confirmado a productora o venue; se muestran por su <code>event_id</code> exacto y no se asignan automáticamente.</p>
                </div>
                <span className="rounded bg-violet-950/60 px-2 py-1 text-[10px] text-violet-300">{evidenciaVisible.length} hojas/eventos fuente</span>
              </div>
              <div className="flex flex-wrap gap-1.5 border-b border-violet-900/40 px-4 py-3">
                <button type="button" onClick={() => { setPeriodoActivo('todos'); setEvidenciaActiva(null); }}
                  className={periodoActivo === 'todos' ? 'rounded border border-violet-500 px-2.5 py-1 text-[10px] text-violet-200' : 'rounded border border-zinc-800 px-2.5 py-1 text-[10px] text-zinc-500'}>
                  Todos · {periodos.reduce((n, p) => n + (evidenciaPeriodos[p]?.length ?? 0), 0)}
                </button>
                {periodos.map(periodo => (
                  <button key={periodo} type="button" onClick={() => { setPeriodoActivo(periodo); setEvidenciaActiva(null); }}
                    className={periodoActivo === periodo ? 'rounded border border-violet-500 px-2.5 py-1 text-[10px] text-violet-200' : 'rounded border border-zinc-800 px-2.5 py-1 text-[10px] text-zinc-500'}>
                    {periodo} · {evidenciaPeriodos[periodo]?.length ?? 0}
                  </button>
                ))}
              </div>
              <EventosEvidencia
                eventos={evidenciaVisible}
                colorimetria={data!.colorimetria}
                productoras={data!.productoras}
                activo={evidenciaActiva}
                onSelect={id => { setEvidenciaActiva(id); setProductoraActiva(null); }}
              />
            </section>
          )}

          {vista === 'jornadas' && evidencia && (
            <section className="rounded-xl border border-violet-700/60 bg-zinc-950/60 p-4 sm:p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-violet-300"><BarChart3 className="h-3.5 w-3.5" /> Resumen del evento fuente</div>
                  <h2 className="mt-1 text-lg font-bold text-zinc-100">{evidencia.nombre}</h2>
                  <p className="mt-1 text-xs text-zinc-500">{evidencia.hoja} · <code>{evidencia.event_id}</code> · {evidencia.filas} filas de datos</p>
                </div>
                <button type="button" onClick={() => setEvidenciaActiva(null)} className="min-h-8 rounded-lg border border-zinc-800 px-3 text-xs text-zinc-500 hover:text-zinc-200">cerrar</button>
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <DistributionCard title="Muestra declarada (campo format_raw)" total={evidencia.muestra_declarada.total} values={evidencia.muestra_declarada.distribucion} color="violet" />
                <DistributionCard title="Resultados colorimétricos observados" total={evidencia.resultados_colorimetricos.total} values={evidencia.resultados_colorimetricos.distribucion} color="amber" />
              </div>
              {evidencia.procedencia && (
                <div className="mt-4 grid gap-2 text-xs sm:grid-cols-2 lg:grid-cols-4">
                  <div className="rounded-lg border border-zinc-800 p-3"><span className="block text-[10px] uppercase tracking-wider text-zinc-600">Filas fuente</span><span className="text-zinc-300">{evidencia.procedencia.filas_brutas}</span></div>
                  <div className="rounded-lg border border-zinc-800 p-3"><span className="block text-[10px] uppercase tracking-wider text-zinc-600">Muestras propias</span><span className="text-emerald-300">{evidencia.procedencia.primera_aparicion}</span></div>
                  <div className="rounded-lg border border-zinc-800 p-3"><span className="block text-[10px] uppercase tracking-wider text-zinc-600">Repetidas en hoja</span><span className="text-amber-300">{evidencia.procedencia.repetidas_en_hoja}</span></div>
                  <div className="rounded-lg border border-zinc-800 p-3"><span className="block text-[10px] uppercase tracking-wider text-zinc-600">Copiadas de otra jornada</span><span className="text-violet-300">{evidencia.procedencia.copiadas_de_otra_jornada}</span></div>
                </div>
              )}
              <div className="mt-4 grid gap-2 text-xs sm:grid-cols-3">
                <div className="rounded-lg border border-zinc-800 p-3"><span className="block text-[10px] uppercase tracking-wider text-zinc-600">Productora / venue</span><span className="text-zinc-400">{evidencia.productora_fuente || 'sin enlace'} · {evidencia.venue_fuente || 'sin enlace'}</span></div>
                <div className="rounded-lg border border-zinc-800 p-3"><span className="block text-[10px] uppercase tracking-wider text-zinc-600">Enlace</span><span className="text-zinc-400">{evidencia.estado_enlace || 'pendiente de revisión humana'}</span></div>
                <div className="rounded-lg border border-zinc-800 p-3"><span className="block text-[10px] uppercase tracking-wider text-zinc-600">Duplicados</span><span className="text-zinc-400">{evidencia.estado_duplicado || 'sin estado'}{evidencia.tamano_grupo_duplicado && evidencia.tamano_grupo_duplicado > 1 ? ` · grupo ${evidencia.tamano_grupo_duplicado}` : ''}</span></div>
              </div>
              <p className="mt-4 flex items-start gap-2 text-[11px] leading-relaxed text-zinc-600"><Radio className="mt-0.5 h-3.5 w-3.5 shrink-0" /> Los porcentajes describen la distribución literal de los campos fuente y no interpretan identidad, pureza, dosis ni seguridad.</p>
            </section>
          )}

          {vista === 'campo' && data!.venues.length > 0 && (
            <section className="rounded-xl border border-zinc-800 bg-zinc-900/40">
              <div className="border-b border-zinc-800 px-4 py-3 text-sm font-bold">Venues</div>
              <div className="divide-y divide-zinc-800/60">
                {data!.venues.map(v => (
                  <div key={v.id} className="flex items-center gap-3 px-4 py-2 text-[13px]">
                    <span className="flex-1 text-zinc-200">{v.nombre}</span>
                    <span className="text-[11px] text-zinc-600">{v.tipo}</span>
                    <span className="text-[11px] text-zinc-600">{v.escala}</span>
                    <span className="text-[11px] text-zinc-600">cap. {v.capacidad}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {vista === 'campo' && data!.excluido_a_proposito && (
            <p className="text-[11px] text-zinc-600">
              Excluido a propósito de este panel: {data!.excluido_a_proposito.join(', ')}. El endpoint usa allowlist de
              campos: un campo nuevo en el origen no se publica solo.
            </p>
          )}
        </>
      )}
    </div>
  );
}

/**
 * La matriz colorimetrica de todos los periodos cargados.
 *
 * Es lo que la planilla no dejaba ver: que color se observo con que reactivo
 * para cada sustancia declarada. Un resultado compuesto se dibuja partido en
 * diagonal porque son dos colores, no uno; colapsarlo al primero seria
 * inventar una observacion que nadie hizo.
 */
function ColorimetriaSection({ c }: { c: Colorimetria }) {
  const [sel, setSel] = useState<{ s: string; r: string } | null>({ s: 'mdma', r: 'marquis' });

  const reactivos = Object.entries(c.por_reactivo)
    .filter(([r, n]) => n >= 20 && r !== 'sin_reactivo').map(([r]) => r);
  const sustancias = Object.entries(c.por_sustancia)
    .filter(([, n]) => n >= 10).map(([s]) => s);
  const et = (k: string) => c.etiquetas[k] ?? k;
  const er = (k: string) => c.etiquetas_reactivo[k] ?? k.charAt(0).toUpperCase() + k.slice(1);
  const nombreColor = (k: string) => k.toLowerCase().replace(/_/g, ' ').replace('+', ' + ');
  // NEGRO es #1a1a1a sobre un panel casi negro: sin contorno la celda mas
  // frecuente (1.230 observaciones) se lee como vacia. Se le agrega un borde
  // interior claro en vez de aclarar el color, que mentiria sobre lo observado.
  const pintar = (clave: string): CSSProperties => {
    const oscuro = (x: string) => ['NEGRO', 'SIN_REACCION', 'NO_INTERPRETABLE'].includes(x);
    const partes = clave.split('+');
    const contorno = partes.some(oscuro) ? { boxShadow: 'inset 0 0 0 1px rgba(255,255,255,.28)' } : {};
    if (partes.length === 1) return { background: c.hex[clave] ?? '#5a5a5a', ...contorno };
    const a = c.hex[partes[0]] ?? '#888', b = c.hex[partes[1]] ?? '#888';
    return { backgroundImage: `linear-gradient(135deg, ${a} 0 50%, ${b} 50% 100%)`, ...contorno };
  };

  const celda = sel ? c.matriz[sel.s]?.[sel.r] : undefined;
  const orden = celda ? Object.entries(celda).sort((a, b) => b[1] - a[1]) : [];
  const totalCelda = orden.reduce((acc, [, n]) => acc + n, 0);
  const esperado = sel ? c.paleta_rd[sel.r] ?? [] : [];
  const expectativa = sel ? c.esperado[sel.s]?.[sel.r] : undefined;
  const esperadoSet = new Set(expectativa?.colores ?? []);
  const idEnColor = c.pendientes.filter(p => p.estado === 'identidad_en_columna_de_color');

  return (
    <section className="rounded-xl border border-zinc-800 bg-zinc-900/30">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-zinc-800 px-4 py-4">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-bold text-zinc-100">
            <FlaskConical className="h-4 w-4 text-violet-300" /> Colorimetría · todos los períodos
          </h2>
          <p className="mt-1 max-w-3xl text-xs leading-relaxed text-zinc-500">
            Qué color se observó con cada reactivo, por sustancia declarada. Las celdas rayadas
            en diagonal son resultados compuestos: dos colores en una observación, conservados
            como dos. Tocá una para ver el detalle.
          </p>
        </div>
        <span className="rounded bg-zinc-800/80 px-2 py-1 text-[10px] text-zinc-400">
          {c.muestras} muestras · {c.observaciones} observaciones
        </span>
      </div>

      {c.concordancia.length > 0 && (
        <div className="border-b border-zinc-800 px-4 py-4">
          <h3 className="text-[10px] font-bold uppercase tracking-wider text-zinc-500">
            Dónde el color observado no calza con lo declarado
          </h3>
          <p className="mb-3 mt-1 max-w-3xl text-[11px] leading-relaxed text-zinc-600">
            Compara lo observado contra la reacción que el catálogo de reactivos de RD espera
            para esa sustancia. Que no calce <b className="text-zinc-500">no dice que sea otra
            sustancia</b>: dice que la observación merece una mirada.
          </p>
          <div className="space-y-2">
            {c.concordancia.slice(0, 5).map(f => {
              const noCalza = f.sin_reaccion + f.discrepa;
              const pct = (noCalza / f.evaluadas) * 100;
              const fuerte = pct >= 50;
              return (
                <button
                  key={`${f.sustancia}-${f.reactivo}`}
                  type="button"
                  onClick={() => setSel({ s: f.sustancia, r: f.reactivo })}
                  className="flex w-full flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-zinc-800 bg-zinc-950/40 px-3 py-2 text-left hover:border-violet-600"
                >
                  <span className="text-xs font-medium text-zinc-300">{et(f.sustancia)}</span>
                  <span className="text-[10px] uppercase tracking-wider text-zinc-600">con</span>
                  <span className="text-xs text-zinc-400">{er(f.reactivo)}</span>
                  <span className="flex items-center gap-1">
                    {f.esperado.map(col => (
                      <span key={col} className="h-3 w-3 rounded-sm border border-zinc-700" style={pintar(col)} title={`esperado: ${nombreColor(col)}`} />
                    ))}
                    <span className="text-[10px] text-zinc-600">esperado</span>
                  </span>
                  <span className="ml-auto flex items-center gap-2">
                    <span className={`text-xs font-bold tabular-nums ${fuerte ? 'text-amber-400' : 'text-zinc-400'}`}>
                      {pct.toFixed(0)}%
                    </span>
                    <span className="text-[10px] text-zinc-600">no calza · {noCalza} de {f.evaluadas}</span>
                  </span>
                  <span className="h-1.5 w-full overflow-hidden rounded-full bg-zinc-800">
                    <span className={`block h-full rounded-full ${fuerte ? 'bg-amber-500' : 'bg-violet-500'}`} style={{ width: `${pct}%` }} />
                  </span>
                  <span className="w-full text-[10px] text-zinc-600">
                    {f.sin_reaccion > 0 && <>sin reacción {f.sin_reaccion}</>}
                    {f.sin_reaccion > 0 && f.discrepa > 0 && ' · '}
                    {f.discrepa > 0 && <>otro color {f.discrepa}</>}
                    {' · '}el catálogo espera «{f.reaccion_texto}»
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Ancho: la tabla cruzada. Angosto: una sustancia por bloque con sus
          reactivos apilados. Una tabla de ocho columnas en un telefono obliga
          a scrollear de lado y deja visibles tres reactivos de ocho. */}
      <div className="hidden overflow-x-auto px-4 py-4 sm:block">
        <table className="w-full min-w-[640px] border-collapse">
          <thead>
            <tr>
              <th className="pb-2 text-left text-[10px] font-bold uppercase tracking-wider text-zinc-600">Sustancia declarada</th>
              {reactivos.map(r => (
                <th key={r} className="px-1 pb-2 text-left text-[10px] font-bold uppercase tracking-wider text-zinc-600">
                  {er(r)}<span className="block font-normal normal-case tracking-normal text-zinc-700">{c.por_reactivo[r]}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sustancias.map(s => (
              <tr key={s} className="border-t border-zinc-800/70">
                <th scope="row" className="py-2 pr-3 text-left align-middle">
                  <span className="text-xs font-medium text-zinc-300">{et(s)}</span>
                  <span className="block text-[10px] text-zinc-600">{c.por_sustancia[s]} obs.</span>
                </th>
                {reactivos.map(r => {
                  const cel = c.matriz[s]?.[r];
                  if (!cel) return <td key={r} className="px-1 py-2"><div className="h-5 min-w-[70px] rounded border border-dashed border-zinc-800 opacity-40" /></td>;
                  const tot = Object.values(cel).reduce((a, b) => a + b, 0);
                  const segs = Object.entries(cel).sort((a, b) => b[1] - a[1]);
                  const activa = sel?.s === s && sel?.r === r;
                  return (
                    <td key={r} className="px-1 py-2">
                      <button
                        type="button"
                        onClick={() => setSel({ s, r })}
                        title={`${et(s)} con ${er(r)}: ${tot} observaciones`}
                        className={`flex h-5 w-full min-w-[70px] overflow-hidden rounded border ${activa ? 'border-violet-400' : 'border-zinc-800'} hover:border-violet-500`}
                      >
                        {segs.map(([clave, n]) => (
                          <span key={clave} style={{ flex: `0 0 ${(n / tot) * 100}%`, ...pintar(clave) }} />
                        ))}
                      </button>
                      <span className="mt-0.5 block text-[9px] text-zinc-600">{tot}</span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="space-y-3 px-4 py-4 sm:hidden">
        {sustancias.map(s => {
          const fila = c.matriz[s] ?? {};
          const conDato = reactivos.filter(r => fila[r]);
          if (!conDato.length) return null;
          return (
            <div key={s} className="rounded-lg border border-zinc-800 bg-zinc-950/40 p-3">
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-xs font-medium text-zinc-200">{et(s)}</span>
                <span className="text-[10px] tabular-nums text-zinc-600">{c.por_sustancia[s]} obs.</span>
              </div>
              <div className="mt-2 space-y-1.5">
                {conDato.map(r => {
                  const cel = fila[r]!;
                  const tot = Object.values(cel).reduce((a, b) => a + b, 0);
                  const segs = Object.entries(cel).sort((a, b) => b[1] - a[1]);
                  const activa = sel?.s === s && sel?.r === r;
                  return (
                    <button
                      key={r}
                      type="button"
                      onClick={() => setSel({ s, r })}
                      className="grid w-full grid-cols-[4.5rem_minmax(0,1fr)_2.2rem] items-center gap-2 text-left"
                    >
                      <span className="truncate text-[11px] text-zinc-400">{er(r)}</span>
                      <span className={`flex h-4 overflow-hidden rounded border ${activa ? 'border-violet-400' : 'border-zinc-800'}`}>
                        {segs.map(([clave, n]) => (
                          <span key={clave} style={{ flex: `0 0 ${(n / tot) * 100}%`, ...pintar(clave) }} />
                        ))}
                      </span>
                      <span className="text-right text-[10px] tabular-nums text-zinc-600">{tot}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {sel && celda && (
        <div className="mx-4 mb-4 rounded-lg border border-zinc-800 bg-zinc-900/60 p-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h3 className="text-xs font-bold text-zinc-200">{et(sel.s)} · {er(sel.r)}</h3>
            <span className="text-[10px] text-zinc-600">{totalCelda} observaciones en la evidencia cargada</span>
          </div>
          {expectativa && (
            <div className="mb-3 mt-2 flex flex-wrap items-center gap-2 rounded-md border border-zinc-800 bg-zinc-950/60 px-2.5 py-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-600">El catálogo espera</span>
              {expectativa.colores.map(col => (
                <span key={col} className="flex items-center gap-1 text-[11px] text-zinc-400">
                  <span className="h-3 w-3 rounded-sm border border-zinc-700" style={pintar(col)} />
                  {nombreColor(col)}
                </span>
              ))}
            </div>
          )}
          {!expectativa && <p className="mb-3 mt-1 text-[10px] text-zinc-600">El catálogo no declara una reacción esperada para este par: no se evalúa concordancia.</p>}
          <div className="space-y-2">
            {orden.map(([clave, n]) => (
              <div key={clave}>
                <div className="flex items-center justify-between gap-3 text-[11px]">
                  <span className="flex min-w-0 items-center gap-2 text-zinc-400">
                    <span className="h-3 w-3 shrink-0 rounded-sm border border-zinc-700" style={pintar(clave)} />
                    <span className="truncate">{nombreColor(clave)}</span>
                    {expectativa && (
                      clave.split('+').some(x => esperadoSet.has(x))
                        ? <span className="shrink-0 rounded bg-emerald-950/60 px-1 text-[9px] text-emerald-400">calza</span>
                        : <span className="shrink-0 rounded bg-amber-950/60 px-1 text-[9px] text-amber-400">no calza</span>
                    )}
                  </span>
                  <span className="shrink-0 text-zinc-500">{n} · {((n / totalCelda) * 100).toFixed(1).replace('.0', '')}%</span>
                </div>
                <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-zinc-800">
                  <div className="h-full rounded-full" style={{ width: `${(n / totalCelda) * 100}%`, ...pintar(clave) }} />
                </div>
              </div>
            ))}
          </div>
          {esperado.length > 0 && (
            <div className="mt-4 border-t border-zinc-800 pt-3">
              <p className="text-[10px] font-bold uppercase tracking-wider text-zinc-600">Reacción esperada de {er(sel.r)}</p>
              <ul className="mt-1 space-y-0.5">
                {esperado.map(x => (
                  <li key={x.familia} className="flex items-center gap-2 text-[11px] text-zinc-500">
                    <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ background: x.hex }} />
                    <b className="text-zinc-400">{x.familia}</b> — {x.reaccion}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <div className="border-t border-zinc-800 px-4 py-3">
        <p className="text-[11px] leading-relaxed text-zinc-500">
          <AlertTriangle className="mr-1 inline h-3 w-3 text-amber-400" />
          <b className="text-zinc-400">Un resultado colorimétrico es presuntivo.</b> {c.limitacion}.
          {' '}{c.pendientes_total > 0 && <>Quedan <b className="text-zinc-400">{c.pendientes_total}</b> observaciones que no se pudieron leer; ninguna se descartó.</>}
          {idEnColor.length > 0 && (
            <> {idEnColor.length} de ellas traen un nombre de sustancia escrito en la columna de color
            ({idEnColor.slice(0, 3).map(p => <code key={p.crudo} className="mx-0.5 rounded bg-zinc-800 px-1 text-[10px]">{p.crudo.trim()}</code>)}):
            es una identificación puesta donde va una observación, y requiere revisión humana.</>
          )}
        </p>
      </div>
    </section>
  );
}

function DistributionCard({
  title,
  total,
  values,
  color,
}: {
  title: string;
  total: number;
  values: Distribucion[];
  color: 'violet' | 'amber';
}) {
  const bar = color === 'violet' ? 'bg-violet-400' : 'bg-amber-400';
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4">
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-xs font-bold text-zinc-300">{title}</h3>
        <span className="shrink-0 text-[10px] text-zinc-600">n={total}</span>
      </div>
      <div className="mt-3 space-y-2">
        {values.slice(0, 8).map(item => (
          <div key={item.valor}>
            <div className="flex items-center justify-between gap-3 text-[11px]">
              <span className="min-w-0 truncate text-zinc-400" title={item.valor}>{item.valor}</span>
              <span className="shrink-0 text-zinc-500">{item.conteo} · {item.porcentaje.toFixed(1).replace('.0', '')}%</span>
            </div>
            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-zinc-800">
              <div className={`h-full rounded-full ${bar}`} style={{ width: `${Math.min(item.porcentaje, 100)}%` }} />
            </div>
          </div>
        ))}
        {values.length > 8 && <p className="text-[10px] text-zinc-600">Se muestran los 8 valores más frecuentes; el total incluye todos.</p>}
        {!values.length && <p className="text-[11px] text-zinc-600">Sin valores registrados.</p>}
      </div>
    </div>
  );
}

/**
 * Las hojas de cada período, ordenadas por tamano.
 *
 * Reemplaza las tres barras moradas sin eje ni etiqueta que habia antes: eran
 * decoracion, no informacion. Cada hoja muestra ahora los COLORES que se
 * observaron realmente en ella, en proporcion, y cuantas muestras aporta
 * comparada con el resto. La confianza de la fecha y el estado de enlace
 * viajan como texto, no como adorno: las fechas deducidas
 * del periodo y casi todas esperan un enlace humano a productora y venue.
 */
function EventosEvidencia({
  eventos, colorimetria, productoras, activo, onSelect,
}: {
  eventos: Evidencia[];
  colorimetria?: Colorimetria;
  productoras: Productora[];
  activo: string | null;
  onSelect: (id: string) => void;
}) {
  const [abierto, setAbierto] = useState<string | null>('dame');
  const hex = colorimetria?.hex ?? {};
  const porEvento = colorimetria?.por_evento ?? {};
  const nombreProd = new Map(productoras.map(p => [p.slug, p.nombre]));

  const pintar = (clave: string) => {
    const partes = clave.split('+');
    if (partes.length === 1) return { background: hex[clave] ?? '#5a5a5a' };
    const a = hex[partes[0]] ?? '#888', b = hex[partes[1]] ?? '#888';
    return { backgroundImage: `linear-gradient(135deg, ${a} 0 50%, ${b} 50% 100%)` };
  };
  const tira = (conteos: Record<string, number>) => {
    const pares = Object.entries(conteos).sort((a, b) => b[1] - a[1]);
    const total = pares.reduce((a, [, n]) => a + n, 0);
    return { pares, total };
  };

  // Las hojas se agrupan por la productora que su propio nombre propone. Es
  // una propuesta, no un enlace: la fuente las marca `pending_human_link` y
  // esto no lo cambia. Antes se mostraban planas y «Dame» aparecia catorce
  // veces seguidas sin decir que era la misma.
  const grupos = new Map<string, Evidencia[]>();
  for (const ev of eventos) {
    const k = ev.productora_candidata ?? '__sin__';
    if (!grupos.has(k)) grupos.set(k, []);
    grupos.get(k)!.push(ev);
  }
  const orden = [...grupos.entries()].sort((a, b) => {
    if (a[0] === '__sin__') return 1;
    if (b[0] === '__sin__') return -1;
    return b[1].reduce((s, e) => s + e.filas, 0) - a[1].reduce((s, e) => s + e.filas, 0);
  });

  return (
    <div className="divide-y divide-zinc-800/60">
      {orden.map(([slug, hojas]) => {
        const muestras = hojas.reduce((s, e) => s + e.filas, 0);
        const colores: Record<string, number> = {};
        for (const ev of hojas) {
          for (const [k, n] of Object.entries(porEvento[ev.event_id] ?? {})) {
            colores[k] = (colores[k] ?? 0) + n;
          }
        }
        const { pares, total } = tira(colores);
        const sinIdentificar = slug === '__sin__';
        const aprox = hojas.some(h => h.match_candidata === 'aproximado');
        // Una sigla puede ser de mas de una productora: se muestra distinto
        // de un match exacto para que se confirme, no se asuma.
        const sigla = hojas.some(h => h.match_candidata === 'abreviatura');
        const open = abierto === slug;
        return (
          <div key={slug}>
            <button
              type="button"
              onClick={() => setAbierto(open ? null : slug)}
              className="flex w-full flex-wrap items-center gap-x-3 gap-y-2 px-4 py-3 text-left hover:bg-zinc-900/50"
            >
              <ChevronRight className={`h-3.5 w-3.5 shrink-0 text-zinc-600 transition-transform ${open ? 'rotate-90' : ''}`} />
              <span className={`text-sm font-medium ${sinIdentificar ? 'text-zinc-500' : 'text-zinc-200'}`}>
                {sinIdentificar ? 'Sin productora identificada' : nombreProd.get(slug) ?? slug}
              </span>
              {aprox && !sinIdentificar && (
                <span className="rounded bg-amber-950/50 px-1.5 py-0.5 text-[9px] text-amber-500">una hoja por aproximación</span>
              )}
              {sigla && !sinIdentificar && (
                <span className="rounded bg-amber-950/50 px-1.5 py-0.5 text-[9px] text-amber-500">atribuida por sigla</span>
              )}
                <span className="text-[11px] tabular-nums text-zinc-600">
                {hojas.reduce((s, e) => s + (e.procedencia?.primera_aparicion ?? e.filas), 0)} propias · {muestras} filas fuente
              </span>
              {total > 0 && (
                <span className="ml-auto flex h-3 w-full max-w-[280px] overflow-hidden rounded-sm border border-zinc-800"
                      title={pares.map(([k, n]) => `${k.toLowerCase().replace(/_/g, ' ')}: ${n}`).join(' · ')}>
                  {pares.map(([clave, n]) => (
                    <span key={clave} style={{ flex: `0 0 ${(n / total) * 100}%`, ...pintar(clave) }} />
                  ))}
                </span>
              )}
            </button>

            {open && (
              <div className="bg-zinc-950/40 pb-1">
                {sinIdentificar && (
                  <p className="px-4 pb-2 pt-1 text-[10px] leading-relaxed text-zinc-600">
                    El nombre de estas hojas no coincide con ninguna ficha de productora. No se
                    les asigna una: la fuente las marca pendientes de enlace humano.
                  </p>
                )}
                {[...hojas].sort((a, b) => b.filas - a.filas).map(ev => {
                  const t = tira(porEvento[ev.event_id] ?? {});
                  const sel = activo === ev.event_id;
                  const firme = ev.estado_fecha === 'parsed_candidate';
                  return (
                    <button
                      key={ev.event_id}
                      type="button"
                      onClick={() => onSelect(ev.event_id)}
                      className={`grid w-full grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-1 px-4 py-2 pl-10 text-left ${sel ? 'bg-violet-950/30' : 'hover:bg-zinc-900/60'}`}
                    >
                      <span className="min-w-0 truncate text-[12px] text-zinc-300">{ev.nombre}</span>
                      <span className="shrink-0 text-[11px] tabular-nums text-zinc-500">
                        {ev.procedencia ? `${ev.procedencia.primera_aparicion} propias · ${ev.filas} filas` : ev.filas}
                      </span>
                      <span className="col-span-2 flex items-center gap-2">
                        {t.total > 0 ? (
                          <span className="flex h-2.5 min-w-0 flex-1 overflow-hidden rounded-sm border border-zinc-800"
                                title={t.pares.map(([k, n]) => `${k.toLowerCase().replace(/_/g, ' ')}: ${n}`).join(' · ')}>
                            {t.pares.map(([clave, n]) => (
                              <span key={clave} style={{ flex: `0 0 ${(n / t.total) * 100}%`, ...pintar(clave) }} />
                            ))}
                          </span>
                        ) : <span className="flex-1 text-[10px] text-zinc-700">sin color registrado</span>}
                        <span className={`shrink-0 text-[10px] ${firme ? 'text-zinc-600' : 'text-amber-700'}`}>
                          {ev.fecha_iso ? (firme ? ev.fecha_iso : `${ev.fecha_iso} aprox.`) : 'sin fecha'}
                        </span>
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
