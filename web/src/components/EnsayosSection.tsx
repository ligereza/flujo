import { useMemo, useState } from 'react';
import { ChevronRight, Plus, X } from 'lucide-react';
import ParalelasRD, { nombreValor, type Dim, type MuestraRD } from './ParalelasRD';

/** Una dimension del catalogo, con el grupo al que pertenece. */
type DimCat = Dim & { grupo: string };

/**
 * Un ensayo es: el reactivo X dio el color C sobre una muestra que alguien
 * declaro como S. Nada mas.
 *
 * Esta vista NO emite veredicto: no dice que sustancia hay, no mide pureza ni
 * dosis, y no compara lo observado contra lo esperado. Ese juicio es de la
 * persona a cargo de la mesa.
 *
 * Lo que si hace es ser fidedigna: recibe las observaciones CRUDAS y calcula
 * cada cifra aca, en el navegador. Ninguna barra viene precocinada, y
 * cualquier bloque del grafico se abre hasta la celda de la planilla.
 *
 * El eje de comparacion NO esta decidido por el grafico: se elige. Ahi estaba
 * el atajo de las versiones anteriores -- fijar los reactivos como ejes
 * respondia una sola pregunta. Con los ejes abiertos, la misma pieza compara
 * periodos, productoras, jornadas o reactivos entre si.
 */

export interface Ensayos {
  politica: string;
  jornadas: {
    hoja: string; nombre: string; periodo: string;
    fecha: string | null; estado_fecha: string; confianza_fecha: string;
    productora: string | null; match_productora: string;
  }[];
  crudo: { sustancia: string[]; reactivo: string[]; resultado: string[] };
  mapa: { sustancia: (string | null)[]; reactivo: (string | null)[]; resultado: (string | null)[] };
  estado: { sustancia: string[]; reactivo: string[]; resultado: string[] };
  procedencia: string[];
  /** [jornada, fila_fuente, sustancia, reactivo, resultado, procedencia] */
  obs: number[][];
  hex: Record<string, string>;
}

const J = 0, FILA = 1, SUS = 2, REA = 3, RES = 4, PROC = 5;
const NO_APLICADO = 'no se aplicó';

// Cada clase de eje con su marca visible. No es decoracion: sin esto el
// control cerrado no dice si lo que hay en el eje es un reactivo, la
// productora o lo que la persona declaro.
const CLASES: Record<string, { texto: string; color: string }> = {
  'Lo que declara quien la trae': { texto: 'declarado', color: 'text-sky-500/80' },
  'Contexto de la jornada': { texto: 'contexto', color: 'text-emerald-500/80' },
  'Reactivo aplicado · color observado': { texto: 'reactivo', color: 'text-amber-500/80' },
};

export default function EnsayosSection({ e }: { e: Ensayos }) {
  const [periodo, setPeriodo] = useState('todos');
  // Por defecto solo las anotaciones propias: las repetidas dentro de la hoja
  // y las copiadas de otra jornada son rastro de la planilla heredada, no
  // ensayos nuevos. Se pueden volver a incluir; nunca se borran.
  const [soloPropias, setSoloPropias] = useState(true);
  /**
   * Filtros acumulables, no «resaltado». Hacer clic en `mdma` antes solo
   * apagaba el resto: los ejes de Marquis y Simon's seguian mostrando su
   * reparto sobre TODAS las muestras, asi que el grafico no asociaba nada.
   * Ahora un clic RECALCULA todo el diagrama sobre las muestras que quedan, y
   * los porcentajes pasan a ser condicionales: «de las declaradas mdma,
   * Marquis dio negro en X%».
   */
  const [filtros, setFiltros] = useState<{ dimId: string; valor: string }[]>([]);
  const [verTabla, setVerTabla] = useState(false);

  const periodos = useMemo(
    () => [...new Set(e.jornadas.map(j => j.periodo))].sort(), [e.jornadas]);

  /** Una fila por MUESTRA, no por observacion: la muestra es la unidad real. */
  const todas = useMemo<MuestraRD[]>(() => {
    const porMuestra = new Map<string, MuestraRD & { propia: boolean }>();
    for (const o of e.obs) {
      const k = `${o[J]}:${o[FILA]}`;
      const jr = e.jornadas[o[J]];
      if (!jr) continue;
      let m = porMuestra.get(k);
      if (!m) {
        m = {
          j: o[J], fila: o[FILA], periodo: jr.periodo,
          productora: jr.productora ?? 'sin identificar',
          jornada: jr.nombre, sustancia: e.mapa.sustancia[o[SUS]] ?? 'sin declarar',
          colores: {}, propia: o[PROC] === 0,
        };
        porMuestra.set(k, m);
      }
      const r = e.mapa.reactivo[o[REA]];
      if (r) m.colores[r] = e.mapa.resultado[o[RES]] ?? 'sin anotar';
    }
    return [...porMuestra.values()];
  }, [e]);

  const base = useMemo(() => todas.filter(m => {
    if (soloPropias && !(m as MuestraRD & { propia: boolean }).propia) return false;
    if (periodo !== 'todos' && m.periodo !== periodo) return false;
    return true;
  }), [todas, soloPropias, periodo]);

  /** Las dimensiones disponibles. Los reactivos salen del propio dato. */
  const catalogo = useMemo<DimCat[]>(() => {
    const reactivos = new Map<string, number>();
    for (const m of base) {
      for (const r of Object.keys(m.colores)) reactivos.set(r, (reactivos.get(r) ?? 0) + 1);
    }
    const porUso = [...reactivos.entries()].sort((a, b) => b[1] - a[1]).map(([r]) => r);
    // Agrupadas por lo que SON. Un reactivo y una productora no son la misma
    // clase de cosa, y en una lista plana se elegian igual: el desplegable no
    // decia que estabas poniendo en el eje.
    return [
      { id: 'sustancia', grupo: 'Lo que declara quien la trae',
        etiqueta: 'sustancia declarada', valor: m => m.sustancia },
      { id: 'periodo', grupo: 'Contexto de la jornada', etiqueta: 'período', valor: m => m.periodo },
      { id: 'productora', grupo: 'Contexto de la jornada', etiqueta: 'productora', valor: m => m.productora },
      { id: 'jornada', grupo: 'Contexto de la jornada', etiqueta: 'jornada', valor: m => m.jornada },
      ...porUso.map(r => ({
        id: `r:${r}`, grupo: 'Reactivo aplicado · color observado', etiqueta: r.toLowerCase(),
        valor: (m: MuestraRD) => m.colores[r] ?? NO_APLICADO,
        // Se declara cual valor es AUSENCIA de medicion. Antes `no se aplicó`
        // era una categoria mas del eje, al lado de los colores: el grafico
        // decia `negro 54%` sobre TODAS las muestras, incluidas aquellas a las
        // que nadie le puso Marquis. Ahora el porcentaje va sobre las medidas
        // y la ausencia se dibuja como hueco.
        ausencia: NO_APLICADO,
      })),
    ];
  }, [base]);

  /**
   * Que puede ir en cada eje, segun su posicion.
   *
   * El eje 1 es QUE muestra es: lo que la persona declaro, o el contexto de la
   * jornada. Los ejes siguientes son QUE LE HICIMOS: un reactivo cada uno.
   * Mezclarlos en una sola lista dejaba armar `marquis → marquis` y ponia un
   * reactivo donde va el sujeto de la comparacion.
   */
  const GRUPOS_EJE_1 = ['Lo que declara quien la trae', 'Contexto de la jornada'];
  const opcionesPara = (i: number) => catalogo.filter(d =>
    i === 0 ? GRUPOS_EJE_1.includes(d.grupo) : !GRUPOS_EJE_1.includes(d.grupo));

  const grupos = useMemo(() => {
    const m = new Map<string, Dim[]>();
    for (const d of catalogo) m.set(d.grupo, [...(m.get(d.grupo) ?? []), d]);
    return [...m.entries()] as [string, DimCat[]][];
  }, [catalogo]);

  const [ejes, setEjes] = useState<string[]>(['sustancia', 'r:MARQUIS', 'r:SIMONS']);
  const dims = useMemo(
    () => ejes.map(id => catalogo.find(d => d.id === id)).filter(Boolean) as Dim[],
    [ejes, catalogo]);

  const muestras = useMemo(() => base.filter(m => filtros.every(f => {
    const d = catalogo.find(x => x.id === f.dimId);
    return d ? d.valor(m) === f.valor : true;
  })), [base, filtros, catalogo]);

  /** Clic en un bloque: pone el filtro, o lo saca si ya estaba. */
  const alternar = (dimId: string, valor: string) => setFiltros(fs =>
    fs.some(f => f.dimId === dimId && f.valor === valor)
      ? fs.filter(f => !(f.dimId === dimId && f.valor === valor))
      : [...fs, { dimId, valor }]);

  /**
   * Clic en una cinta: pone los DOS extremos, sin alternar.
   *
   * Con `alternar` habia un error real: una cinta llama al handler dos veces,
   * y si uno de sus extremos ya estaba filtrado, esa primera llamada lo SACABA.
   * El usuario creia estar profundizando y estaba ampliando. Una cinta siempre
   * acota; nunca puede devolver muestras.
   */
  const agregarPar = (pares: [string, string][]) => setFiltros(fs => {
    const nuevos = pares.filter(([dimId, valor]) =>
      !fs.some(f => f.dimId === dimId && f.valor === valor));
    return [...fs, ...nuevos.map(([dimId, valor]) => ({ dimId, valor }))];
  });

  const boton = (activo: boolean) => `rounded-lg border px-3.5 py-2 text-xs transition-colors ${
    activo ? 'border-violet-500 bg-violet-500/10 text-violet-200'
           : 'border-zinc-700 text-zinc-400 hover:border-zinc-500 hover:text-zinc-200'}`;
  const select = 'w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2.5 text-xs '
    + 'text-zinc-200 focus:border-violet-500 focus:outline-none';

  return (
    <section className="space-y-3">
      <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => setPeriodo('todos')} className={boton(periodo === 'todos')}>
            Todos los años
          </button>
          {periodos.map(p => (
            <button key={p} type="button" onClick={() => setPeriodo(p)} className={boton(periodo === p)}>
              {p}
            </button>
          ))}
          <button type="button" onClick={() => setSoloPropias(v => !v)}
                  className={boton(soloPropias) + ' ml-auto'}>
            {soloPropias ? 'solo anotaciones propias' : 'incluye repetidas y copiadas'}
          </button>
        </div>
        <p className="mt-2.5 text-[11px] leading-relaxed text-zinc-500">
          <strong className="tabular-nums text-zinc-200">{muestras.length.toLocaleString('es-CL')}</strong> muestras.{' '}
          {e.politica}
        </p>
      </div>

      <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
        <div className="mb-2 flex items-baseline gap-2">
          <h4 className="text-[10px] uppercase tracking-[.08em] text-zinc-500">Ejes de comparación</h4>
          <span className="text-[10px] text-zinc-600">el punto en común lo eliges tú</span>
        </div>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {ejes.map((id, i) => {
            const d = catalogo.find(x => x.id === id);
            const clase = CLASES[d?.grupo ?? ''] ?? { texto: '', color: 'text-zinc-500' };
            return (
            <div key={i}>
              {/* La clase del eje va FUERA del desplegable. Agruparlas solo
                  adentro dejaba el control cerrado idéntico al anterior: el
                  arreglo existía y no se veía, que es como no existir. */}
              <div className="mb-1 flex items-baseline gap-1.5 px-0.5">
                <span className="text-[10px] tabular-nums text-zinc-600">{i + 1}</span>
                <span className={`text-[10px] uppercase tracking-[.07em] ${clase.color}`}>
                  {clase.texto}
                </span>
                <span className="text-[10px] text-zinc-600">
                  {i === 0 ? '· qué muestra es' : '· qué le hicimos'}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
              <select value={id} className={select}
                      onChange={ev => { const n = [...ejes]; n[i] = ev.target.value; setEjes(n); }}>
                {grupos
                  .map(([grupo, ds]) => [grupo, ds.filter(d => opcionesPara(i).includes(d))] as const)
                  .filter(([, ds]) => ds.length)
                  .map(([grupo, ds]) => (
                    <optgroup key={grupo} label={grupo}>
                      {ds.map(d => (
                        // Lo ya puesto en OTRO eje se deshabilita: `marquis →
                        // marquis` no es una comparacion, es la diagonal.
                        <option key={d.id} value={d.id}
                                disabled={d.id !== id && ejes.includes(d.id)}>
                          {d.etiqueta}{d.id !== id && ejes.includes(d.id) ? ' — ya está en otro eje' : ''}
                        </option>
                      ))}
                    </optgroup>
                  ))}
              </select>
              {i > 0 && ejes.length > 2 && (
                <button type="button" aria-label="quitar eje"
                        onClick={() => { setEjes(ejes.filter((_, k) => k !== i)); }}
                        className="shrink-0 rounded-lg border border-zinc-700 p-2 text-zinc-500 hover:border-zinc-500 hover:text-zinc-300">
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
              </div>
            </div>
            );
          })}
          {ejes.length < 5 && opcionesPara(1).some(d => !ejes.includes(d.id)) && (
            <button type="button"
                    onClick={() => { const libre = opcionesPara(1).find(d => !ejes.includes(d.id)); if (libre) { setEjes([...ejes, libre.id]); } }}
                    className="flex items-center justify-center gap-1.5 self-end rounded-lg border border-dashed border-zinc-700 px-3 py-2.5 text-xs text-zinc-500 hover:border-zinc-500 hover:text-zinc-300">
              <Plus className="h-3.5 w-3.5" /> otro eje
            </button>
          )}
        </div>
      </div>

      {filtros.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 rounded-lg border border-violet-900/50 bg-violet-950/10 px-3 py-2.5">
          <span className="text-[10px] uppercase tracking-[.07em] text-violet-400/80">Filtrando por</span>
          {filtros.map((f, i) => {
            const d = catalogo.find(x => x.id === f.dimId);
            return (
              <button key={i} type="button" onClick={() => alternar(f.dimId, f.valor)}
                      className="flex items-center gap-1.5 rounded-lg border border-violet-600/60 bg-violet-500/10 px-3 py-1.5 text-xs text-violet-100 hover:border-violet-400">
                <span className="text-violet-400/70">{d?.etiqueta}</span>
                {nombreValor(f.valor)}
                <X className="h-3 w-3 opacity-60" />
              </button>
            );
          })}
          <button type="button" onClick={() => setFiltros([])}
                  className="ml-auto rounded-lg px-2.5 py-1.5 text-[11px] text-zinc-500 hover:text-zinc-200">
            quitar todo
          </button>
        </div>
      )}

      {dims.length >= 2 && muestras.length > 0 && (
        <ParalelasRD dims={dims} muestras={muestras} hex={e.hex}
                     filtros={filtros} onFiltrar={alternar} onFiltrarPar={agregarPar} />
      )}

      {/* El detalle es el interior del grafico, no una segunda
          representacion: muestra exactamente las filas que quedaron despues
          de los filtros que estan puestos arriba. */}
      <div className="rounded-lg border border-zinc-800 bg-zinc-950/60">
        <button type="button" onClick={() => setVerTabla(v => !v)}
                className="flex w-full items-center gap-2 px-3 py-2.5 text-left hover:bg-zinc-900/50">
          <ChevronRight className={`h-3.5 w-3.5 shrink-0 text-zinc-600 transition-transform ${verTabla ? 'rotate-90' : ''}`} />
          <span className="text-xs text-zinc-200">Las filas de la planilla</span>
          <span className="text-[11px] tabular-nums text-zinc-500">
            {muestras.length.toLocaleString('es-CL')}
            {filtros.length > 0 && ` de ${base.length.toLocaleString('es-CL')} · ${((muestras.length / (base.length || 1)) * 100).toFixed(1)}%`}
          </span>
        </button>
        {verTabla && (
          <div className="max-h-96 overflow-auto border-t border-zinc-900">
            <table className="w-full text-[11px]">
              <thead className="sticky top-0 bg-zinc-950 text-[10px] uppercase tracking-wider text-zinc-600">
                <tr>
                  <th className="px-2.5 py-2 text-left font-normal">jornada</th>
                  <th className="px-2.5 py-2 text-left font-normal">fila</th>
                  {dims.map(d => (
                    <th key={d.id} className="px-2.5 py-2 text-left font-normal">{d.etiqueta}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-900/60">
                {muestras.slice(0, 300).map((m, i) => (
                  <tr key={i} className="text-zinc-400">
                    <td className="px-2.5 py-1.5 text-zinc-300">{m.jornada}</td>
                    <td className="px-2.5 py-1.5 tabular-nums text-zinc-600">{m.fila}</td>
                    {dims.map(d => (
                      <td key={d.id} className="px-2.5 py-1.5 text-zinc-200">{nombreValor(d.valor(m))}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {muestras.length > 300 && (
              <p className="px-3 py-2 text-[10px] text-zinc-600">
                se muestran 300 de {muestras.length} — acota con un filtro
              </p>
            )}
          </div>
        )}
      </div>

      {filtros.length === 0 && (
        <p className="px-1 text-[11px] text-zinc-600">
          Toca un bloque del gráfico para filtrar por él: todo el diagrama se recalcula
          sobre las muestras que quedan, y los porcentajes pasan a ser de ese subconjunto.
        </p>
      )}
    </section>
  );
}
