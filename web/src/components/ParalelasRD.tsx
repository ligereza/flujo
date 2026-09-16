import { useEffect, useMemo, useState } from 'react';

/**
 * Parallel Sets sobre los ensayos RD.
 *
 * La forma tiene nombre y no la invente: «parallel sets» / «parsets»
 * (Kosara et al.; implementacion de referencia: github.com/jasondavies/d3-parsets).
 * Cada eje es una dimension categorica, cada bloque una categoria dimensionada
 * por su frecuencia, y las cintas son los casos que pasan de una a la otra.
 *
 * Lo que la version canonica tiene y una version fija no: LOS EJES SE ELIGEN.
 * Ahi esta la respuesta a «cual es el punto en comun»: no lo decide el grafico.
 *
 *     sustancia → marquis → simons     el panel de MDMA
 *     periodo   → marquis              2024 contra 2025 con el mismo reactivo
 *     productora → sustancia           que se testea en cada fiesta
 *     jornada   → morris               una noche contra el resto
 *
 * Tres reglas de este dibujo:
 *
 * - FONDO CLARO. El vocabulario incluye NEGRO, GRIS y «sin reaccion»: sobre un
 *   panel casi negro los tres son el mismo rectangulo. Toda carta de reactivos
 *   publicada es sobre claro, porque la reaccion se lee sobre superficie clara.
 * - EN CELULAR GIRA. Un SVG escala con su contenedor: a 400px el texto de 11px
 *   se dibuja a 6px. En vertical cada eje es una banda de ancho completo.
 * - CLIC ENTRA AL DATO. Un bloque o una cinta filtran, y el detalle muestra
 *   las celdas de la planilla que los formaron. Sin eso es un adorno.
 *
 * No emite veredicto: dice que reactivo dio que color y en que proporcion.
 */

export interface Dim {
  id: string; etiqueta: string; valor: (m: MuestraRD) => string;
  /**
   * El valor que significa QUE NO SE MIDIO, distinto de haber medido y no ver
   * nada. «Sin reaccion» es una observacion: se aplico el reactivo y no viro.
   * «No se aplico» es la ausencia de esa observacion, y ademas es una ausencia
   * NO aleatoria -- alguien decidio no aplicarlo. Tratarlos como dos categorias
   * hermanas del mismo eje invalida todo porcentaje que cruce ese eje.
   */
  ausencia?: string;
}
export interface MuestraRD {
  j: number; fila: number;
  periodo: string; productora: string; jornada: string; sustancia: string;
  colores: Record<string, string>;
}
/** Un filtro puesto: dimension + valor. Se acumulan. */
export interface Filtro { dimId: string; valor: string }

const MIN_SEG = 3;
const TINTA = '#23201c';
const PAPEL = '#f4f1ea';
const CLARO = ['AMARILLO', 'BLANCO', 'CELESTE', 'ROSADO', 'GRIS'];

// «Sin reaccion» es una observacion y se dibuja como tal. «No se aplico»
// no entra aca: no es un color ni la falta de uno, es que no se midio.
const VACIO = (c: string) => c === 'SIN_REACCION' || c === 'sin anotar';
const ILEGIBLE = (c: string) => c === 'NO_INTERPRETABLE' || c === '(otros)';

export const nombreValor = (c: string) =>
  c.replace(/_/g, ' ').replace(/\+/g, ' + ').toLowerCase();

// Rampa neutra para las dimensiones que NO son color -- periodo, productora,
// sustancia, jornada. Inventarles color las haria parecer una lectura de
// reactivo, que es justo lo que no son; pero dejarlas todas del mismo beige
// las volvia ocho bloques identicos sin etiqueta. Un escalon de gris calido
// por categoria las separa sin afirmar nada.
const RAMPA = ['#8f8878', '#a49d8c', '#b8b1a0', '#c9c3b4', '#d8d3c6',
               '#e2ddd1', '#eae6dc', '#f0ece4'];

function relleno(v: string, hex: Record<string, string>, orden = 0) {
  if (VACIO(v)) return 'url(#ps-vacio)';
  if (ILEGIBLE(v)) return 'url(#ps-ilegible)';
  if (v.includes('+')) return `url(#ps-g-${v.replace(/\+/g, '_')})`;
  return hex[v] ?? RAMPA[Math.min(orden, RAMPA.length - 1)];
}

function useAngosto() {
  const [a, setA] = useState(
    typeof window !== 'undefined' && window.matchMedia('(max-width: 640px)').matches);
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 640px)');
    const on = () => setA(mq.matches);
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, []);
  return a;
}

/**
 * La leyenda. No existia, y sin ella la mitad del vocabulario visual habia que
 * adivinarlo: que significa el punteado, que el rayado, por que hay huecos, y
 * si los beiges codifican algo (no codifican nada).
 *
 * Va en HTML y no dentro del SVG a proposito: asi el texto conserva su tamano
 * real en cualquier ancho, en vez de encogerse con el viewBox.
 */
function Leyenda() {
  const caja = 'h-3.5 w-6 shrink-0 rounded-[2px] border';
  const items: { estilo: React.CSSProperties; clase?: string; texto: string }[] = [
    { estilo: { background: '#2f5fd0' }, texto: 'color observado' },
    { estilo: { backgroundImage: 'linear-gradient(135deg,#1a1a1a 0 50%,#e8813a 50%)' },
      texto: 'dos colores · viró a los dos' },
    { estilo: { backgroundColor: PAPEL,
                backgroundImage: 'radial-gradient(rgba(35,32,28,.34) .8px, transparent .8px)',
                backgroundSize: '5px 5px' },
      texto: 'sin reacción · se aplicó y no viró' },
    { estilo: { backgroundColor: '#e6e1d6',
                backgroundImage: 'repeating-linear-gradient(45deg,rgba(35,32,28,.26) 0 2px,transparent 2px 6px)' },
      texto: 'no interpretable' },
    { estilo: { background: 'transparent', borderStyle: 'dashed' },
      texto: 'no se aplicó · queda fuera del %' },
    { estilo: { background: '#b8b1a0' },
      texto: 'no es un color · el tono no significa nada' },
  ];
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 border-b px-3 py-2"
         style={{ borderColor: 'rgba(35,32,28,.12)' }}>
      {items.map((it, i) => (
        <span key={i} className="flex items-center gap-1.5 text-[10.5px]"
              style={{ color: 'rgba(35,32,28,.70)' }}>
          <span className={caja} style={{ borderColor: 'rgba(35,32,28,.30)', ...it.estilo }} />
          {it.texto}
        </span>
      ))}
    </div>
  );
}


export default function ParalelasRD({
  dims, muestras, hex, filtros, onFiltrar, onFiltrarPar,
}: {
  dims: Dim[]; muestras: MuestraRD[]; hex: Record<string, string>;
  filtros: Filtro[]; onFiltrar: (dimId: string, valor: string) => void;
  onFiltrarPar: (pares: [string, string][]) => void;
}) {
  // Que bloque tiene el puntero encima. Sin esto las cintas son una nube: con
  // ~200 cruces del mismo gris no se puede seguir ninguna, que es justamente
  // lo que el diagrama existe para mostrar.
  const [encima, setEncima] = useState<{ eje: number; valor: string } | null>(null);
  const vertical = useAngosto();
  const n = dims.length;

  const largo = vertical ? 330 : 300;
  const grosor = vertical ? 52 : 90;
  const salto = vertical ? 78 : 0;
  const PAD_I = vertical ? 4 : 14;
  // El ultimo eje rotula hacia su derecha; sin margen esos rotulos y el final
  // del denominador se cortaban contra el borde del contenedor.
  const PAD_F = vertical ? 4 : 96;
  const anchoLienzo = vertical ? largo + PAD_I + PAD_F : 860;

  const modelo = useMemo(() => {
    const total = muestras.length || 1;
    const ejes = dims.map(d => {
      const cuenta = new Map<string, number>();
      for (const m of muestras) {
        const v = d.valor(m);
        cuenta.set(v, (cuenta.get(v) ?? 0) + 1);
      }
      // La ausencia sale de la cuenta de categorias: ocupa su espacio real en
      // el eje -- las cintas tienen que seguir cuadrando -- pero NO compite en
      // el ranking ni entra al denominador. `negro 54%` significa 54% de las
      // muestras a las que se les aplico Marquis, no 54% de todas.
      const ausentes = d.ausencia ? (cuenta.get(d.ausencia) ?? 0) : 0;
      if (d.ausencia) cuenta.delete(d.ausencia);
      const medidas = total - ausentes || 1;
      const pares = [...cuenta.entries()].sort((a, b) => b[1] - a[1]);
      const grandes = pares.filter(([, v]) => (v / total) * largo >= MIN_SEG);
      const colaN = pares.filter(([, v]) => (v / total) * largo < MIN_SEG)
        .reduce((s, [, v]) => s + v, 0);
      const lista: [string, number][] = colaN ? [...grandes, ['(otros)', colaN]] : grandes;
      let a = 0;
      const segs = lista.map(([valor, v]) => {
        const seg = { valor, n: v, a0: a, ancho: (v / total) * largo,
                      pct: (v / medidas) * 100, ausente: false };
        a += seg.ancho;
        return seg;
      });
      if (ausentes) {
        segs.push({ valor: d.ausencia as string, n: ausentes, a0: a,
                    ancho: (ausentes / total) * largo, pct: 0, ausente: true });
      }
      return Object.assign(segs, { ausentes, medidas, total });
    });

    const cintas: { i: number; de: string; a: string; n: number; a0: number; a1: number; ancho: number }[] = [];
    for (let i = 0; i < n - 1; i++) {
      const enEje = (idx: number, v: string) =>
        ejes[idx].some(s => s.valor === v) ? v : '(otros)';
      const cuenta = new Map<string, number>();
      for (const m of muestras) {
        const de = enEje(i, dims[i].valor(m));
        const a = enEje(i + 1, dims[i + 1].valor(m));
        const k = `${de}→${a}`;
        cuenta.set(k, (cuenta.get(k) ?? 0) + 1);
      }
      const offDe = new Map<string, number>(), offA = new Map<string, number>();
      for (const [k, v] of [...cuenta.entries()].sort((a, b) => b[1] - a[1])) {
        const [de, a] = k.split('→');
        const sd = ejes[i].find(s => s.valor === de), sa = ejes[i + 1].find(s => s.valor === a);
        if (!sd || !sa) continue;
        const ancho = (v / total) * largo;
        const a0 = sd.a0 + (offDe.get(de) ?? 0), a1 = sa.a0 + (offA.get(a) ?? 0);
        offDe.set(de, (offDe.get(de) ?? 0) + ancho);
        offA.set(a, (offA.get(a) ?? 0) + ancho);
        cintas.push({ i, de, a, n: v, a0, a1, ancho });
      }
    }
    return { ejes, cintas, total };
  }, [dims, muestras, n, largo]);

  const banda = (i: number) => vertical
    ? 30 + i * (grosor + salto)
    : PAD_I + i * ((anchoLienzo - PAD_I - PAD_F - grosor) / Math.max(n - 1, 1));
  const altoLienzo = vertical
    ? 30 + n * (grosor + salto) - salto + 14
    : largo + 34;

  const caja = (i: number, a0: number, ancho: number) => vertical
    ? { x: PAD_I + a0, y: banda(i), width: Math.max(ancho, 1.5), height: grosor }
    : { x: banda(i), y: a0, width: grosor, height: Math.max(ancho, 1.5) };

  const rutaCinta = (c: typeof modelo.cintas[number]) => {
    const g1 = banda(c.i) + grosor, g2 = banda(c.i + 1), m = (g1 + g2) / 2;
    const p0 = PAD_I + c.a0, p1 = PAD_I + c.a1;
    return vertical
      ? `M${p0},${g1} C${p0},${m} ${p1},${m} ${p1},${g2} `
        + `L${p1 + c.ancho},${g2} C${p1 + c.ancho},${m} ${p0 + c.ancho},${m} ${p0 + c.ancho},${g1} Z`
      : `M${g1},${c.a0} C${m},${c.a0} ${m},${c.a1} ${g2},${c.a1} `
        + `L${g2},${c.a1 + c.ancho} C${m},${c.a1 + c.ancho} ${m},${c.a0 + c.ancho} ${g1},${c.a0 + c.ancho} Z`;
  };

  // El diagrama ya viene calculado SOBRE lo filtrado, asi que no hay nada que
  // apagar: lo que se dibuja es el subconjunto. Lo unico que se marca es el
  // bloque que corresponde a un filtro puesto, para poder sacarlo de un clic.
  const filtrado = (i: number, v: string) =>
    filtros.some(f => f.dimId === dims[i]?.id && f.valor === v);

  return (
    <div className="overflow-hidden rounded-lg" style={{ background: PAPEL }}>
      <Leyenda />
      <svg viewBox={`0 0 ${anchoLienzo} ${altoLienzo}`} className="w-full" role="img"
           aria-label={`${modelo.total} muestras por ${dims.map(d => d.etiqueta).join(', ')}`}>
        <defs>
          <pattern id="ps-vacio" width="7" height="7" patternUnits="userSpaceOnUse">
            <rect width="7" height="7" fill={PAPEL} />
            <circle cx="3.5" cy="3.5" r="0.8" fill="rgba(35,32,28,.30)" />
          </pattern>
          <pattern id="ps-ilegible" width="6" height="6" patternUnits="userSpaceOnUse"
                   patternTransform="rotate(45)">
            <rect width="6" height="6" fill="#e6e1d6" />
            <rect width="2" height="6" fill="rgba(35,32,28,.24)" />
          </pattern>
          {[...new Set(modelo.ejes.flat().map(s => s.valor))].filter(v => v.includes('+'))
            .map(v => {
              const [a, b] = v.split('+');
              return (
                <linearGradient key={v} id={`ps-g-${v.replace(/\+/g, '_')}`} x1="0" y1="0" x2="1" y2="1">
                  <stop offset="50%" stopColor={hex[a] ?? '#b9b3a6'} />
                  <stop offset="50%" stopColor={hex[b] ?? '#b9b3a6'} />
                </linearGradient>
              );
            })}
        </defs>

        {modelo.cintas.map((c, k) => {
          const col = VACIO(c.de) || ILEGIBLE(c.de) ? '#8a857c' : hex[c.de.split('+')[0]] ?? '#a8a296';
          const desdeAusencia = dims[c.i]?.ausencia === c.de;
          const tocada = encima
            && ((encima.eje === c.i && encima.valor === c.de)
             || (encima.eje === c.i + 1 && encima.valor === c.a));
          return (
            <path key={k} d={rutaCinta(c)} fill={col}
                  opacity={tocada ? 0.62
                    : encima ? 0.035
                    : desdeAusencia ? 0.12 : c.de === 'NEGRO' ? 0.13 : 0.2}
                  style={{ cursor: 'pointer' }}
                  onClick={() => onFiltrarPar([[dims[c.i].id, c.de], [dims[c.i + 1].id, c.a]])}>
              <title>{`${nombreValor(c.de)} → ${nombreValor(c.a)}: ${c.n} muestras `
                + `(${((c.n / modelo.total) * 100).toFixed(1)}%) — clic para filtrar`}</title>
            </path>
          );
        })}

        {modelo.ejes.map((eje, i) => (
          <g key={i}>
            {eje.map((s, k) => {
              const r = caja(i, s.a0, s.ancho);
              const cabe = vertical ? s.ancho >= 62 : s.ancho >= 28;
              // Espacio disponible para una tercera linea de texto dentro del
              // bloque: en vertical lo da el grosor de la banda, en horizontal
              // el largo del segmento.
              const holgura = vertical ? grosor : s.ancho;
              const esColor = !!hex[s.valor.split('+')[0]];
              const tinta = VACIO(s.valor) || ILEGIBLE(s.valor) || !esColor
                || CLARO.includes(s.valor) ? TINTA : '#fff';
              return (
                <g key={s.valor} style={{ cursor: 'pointer' }}
                   onMouseEnter={() => setEncima({ eje: i, valor: s.valor })}
                   onMouseLeave={() => setEncima(null)}
                   onClick={() => onFiltrar(dims[i].id, s.valor)}>
                  {s.ausente ? (
                    // Hueco: ni relleno ni borde completo, solo una linea de
                    // base. No se midio no es un resultado, y un bloque con
                    // contorno se lee como uno.
                    <g>
                      <line x1={r.x} y1={r.y + r.height} x2={r.x + r.width} y2={r.y + r.height}
                            stroke="rgba(35,32,28,.28)" strokeWidth={1} strokeDasharray="3 3" />
                      <line x1={vertical ? r.x : r.x} y1={vertical ? r.y : r.y}
                            x2={vertical ? r.x : r.x + r.width} y2={vertical ? r.y + r.height : r.y}
                            stroke="rgba(35,32,28,.16)" strokeWidth={1} strokeDasharray="3 3" />
                    </g>
                  ) : (
                  <rect {...r} fill={relleno(s.valor, hex, k)} rx={2}
                        stroke={filtrado(i, s.valor) ? TINTA
                          : encima?.eje === i && encima.valor === s.valor
                            ? 'rgba(35,32,28,.75)' : 'rgba(35,32,28,.30)'}
                        strokeWidth={filtrado(i, s.valor) ? 2.4
                          : encima?.eje === i && encima.valor === s.valor ? 1.8 : 0.8} />
                  )}
                  <title>{`${dims[i].etiqueta} · ${nombreValor(s.valor)}: ${s.n} `
                    + `(${s.pct.toFixed(1)}%) — clic para filtrar`}</title>
                  {s.ausente ? (
                    // Sin porcentaje: no se midio no tiene cuota de nada.
                    <text x={r.x + (vertical ? 5 : r.width / 2)}
                          y={r.y + r.height / 2 + 3}
                          textAnchor={vertical ? 'start' : 'middle'}
                          fontSize="9.5" fill="rgba(35,32,28,.50)" pointerEvents="none">
                      no se aplicó · {s.n}
                    </text>
                  ) : cabe ? (
                    <text x={r.x + r.width / 2} y={r.y + r.height / 2 - (vertical ? 3 : 0)}
                          textAnchor="middle" fontSize="12" fontWeight={700} fill={tinta} pointerEvents="none">
                      {s.pct.toFixed(0)}%
                      <tspan x={r.x + r.width / 2} dy="12.5" fontSize="9.5" fontWeight={400} opacity={0.85}>
                        {nombreValor(s.valor).slice(0, vertical ? 26 : 13)}
                      </tspan>
                      {/* El conteo absoluto vivia solo en el tooltip nativo:
                          tarda un segundo, no sale en una captura y en celular
                          no existe. Va escrito cuando el bloque da el alto. */}
                      {holgura >= 44 && (
                        <tspan x={r.x + r.width / 2} dy="11" fontSize="8.5" fontWeight={400} opacity={0.62}>
                          {s.n} de {eje.medidas}
                        </tspan>
                      )}
                    </text>
                  ) : (s.ancho >= 7 && (
                    // No cabe adentro: se rotula afuera. Una categoria sin
                    // nombre obliga a pasar el mouse para saber que es, y en
                    // celular no hay mouse.
                    //
                    // En vertical va DEBAJO de la banda y no al costado: al
                    // costado se corta contra el borde derecho de la pantalla,
                    // que es justo donde caen los bloques mas chicos.
                    <text x={vertical ? Math.min(r.x, largo - 70) : r.x + r.width + 5}
                          y={vertical ? r.y + r.height + 11 : r.y + r.height / 2 + 3}
                          fontSize="9" fill="rgba(35,32,28,.70)" pointerEvents="none">
                      {nombreValor(s.valor).slice(0, 16)}
                      <tspan dx="4" fill="rgba(35,32,28,.45)">{s.pct.toFixed(0)}%</tspan>
                    </text>
                  ))}
                </g>
              );
            })}
            <text x={vertical ? PAD_I : banda(i)} y={vertical ? banda(i) - 8 : largo + 18}
                  fontSize="12" fontWeight={700} fill={TINTA}>
              {dims[i].etiqueta}
            </text>
            {/* El denominador va escrito SIEMPRE. Un `54%` sin decir sobre
                que se calculo no es una cifra, es una impresion -- y en este
                eje el denominador no es el total de muestras. */}
            <text x={vertical ? PAD_I : banda(i)} y={vertical ? banda(i) - 8 : largo + 30}
                  dx={vertical ? dims[i].etiqueta.length * 6.9 + 8 : 0}
                  fontSize="9.5" fill="rgba(35,32,28,.55)">
              {eje.ausentes
                ? `aplicado en ${eje.medidas} de ${eje.total} · % sobre aplicados`
                : `${eje.length} ${eje.length === 1 ? 'categoría' : 'categorías'} · ${eje.total} muestras`}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
