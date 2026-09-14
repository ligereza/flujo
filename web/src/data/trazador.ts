// trazador.ts -- imagen -> contorno SVG, DENTRO del navegador.
//
// Por que existe: el trazador bueno es Python (`src/flujo/plano/trazador.py`) y
// vive en el servidor. En el HTML suelto que se le manda a la encargada de
// eventos no hay servidor, asi que subir un PNG le devolvia un error. Y decirle
// "abri la app con py -m flujo app" es mandarla a una consola que no tiene:
// justamente por eso se le pasa un archivo y no un repositorio.
//
// Es el MISMO algoritmo, con las mismas constantes, para que un icono trazado
// aca y uno trazado alla no salgan distintos: umbral de Otsu, marching squares,
// y Douglas-Peucker iterativo (recursivo desborda con contornos largos).
// Si alguna vez se cambia uno, hay que cambiar el otro.

export class TrazadoImposible extends Error {}

const LADO_MAX = 256;
const TOLERANCIA = 0.75;
const AREA_MINIMA = 0.0006;

type Punto = [number, number];

/** Corte que mejor separa dos poblaciones de gris. Igual que `_umbral_otsu`. */
function umbralOtsu(hist: number[], total: number): number {
  let suma = 0;
  for (let i = 0; i < 256; i++) suma += i * hist[i];
  let sumaB = 0, pesoB = 0, mejorVar = -1, corte = 128;
  for (let t = 0; t < 256; t++) {
    pesoB += hist[t];
    if (pesoB === 0) continue;
    const pesoF = total - pesoB;
    if (pesoF === 0) break;
    sumaB += t * hist[t];
    const mediaB = sumaB / pesoB;
    const mediaF = (suma - sumaB) / pesoF;
    const entre = pesoB * pesoF * (mediaB - mediaF) * (mediaB - mediaF);
    if (entre > mejorVar) { mejorVar = entre; corte = t; }
  }
  return corte;
}

/** Grilla booleana: true donde hay tinta. */
function mascara(img: ImageData): { m: boolean[][]; ancho: number; alto: number } {
  const { width: ancho, height: alto, data } = img;
  const n = ancho * alto;

  // Con transparencia, la tinta es lo opaco: es el caso normal de un icono
  // exportado. Se prueba primero porque da un recorte mucho mas limpio.
  let plano: boolean[] = new Array(n);
  let conTinta = 0;
  for (let i = 0; i < n; i++) {
    const opaco = data[i * 4 + 3] > 128;
    plano[i] = opaco;
    if (opaco) conTinta++;
  }
  if (conTinta > 0 && conTinta < n) {
    return { m: aFilas(plano, ancho, alto), ancho, alto };
  }

  // Sin transparencia: lo oscuro sobre lo claro, con el corte de Otsu.
  const hist = new Array(256).fill(0);
  const gris = new Array(n);
  for (let i = 0; i < n; i++) {
    const g = Math.round(0.299 * data[i * 4] + 0.587 * data[i * 4 + 1]
                         + 0.114 * data[i * 4 + 2]);
    gris[i] = g;
    hist[g]++;
  }
  const corte = umbralOtsu(hist, n);
  plano = gris.map(g => g <= corte);
  // Si el icono es claro sobre fondo oscuro, lo anterior tomo el fondo.
  const tinta = plano.reduce((a, b) => a + (b ? 1 : 0), 0);
  if (tinta > n * 0.6) plano = plano.map(v => !v);
  return { m: aFilas(plano, ancho, alto), ancho, alto };
}

function aFilas(plano: boolean[], ancho: number, alto: number): boolean[][] {
  const filas: boolean[][] = [];
  for (let f = 0; f < alto; f++) filas.push(plano.slice(f * ancho, (f + 1) * ancho));
  return filas;
}

const LADOS: Record<number, [number, number]> = {
  0: [0.5, 0.0], 1: [1.0, 0.5], 2: [0.5, 1.0], 3: [0.0, 0.5],
};
const CASOS: Record<number, Array<[number, number]>> = {
  1: [[3, 0]], 2: [[0, 1]], 3: [[3, 1]], 4: [[1, 2]], 5: [[3, 2], [0, 1]],
  6: [[0, 2]], 7: [[3, 2]], 8: [[2, 3]], 9: [[2, 0]], 10: [[0, 3], [2, 1]],
  11: [[2, 1]], 12: [[1, 3]], 13: [[1, 0]], 14: [[0, 3]],
};

/** Lazos cerrados que bordean la tinta, por marching squares. */
function contornos(m: boolean[][], ancho: number, alto: number): Punto[][] {
  const ocupado = (f: number, c: number) =>
    f >= 0 && f < alto && c >= 0 && c < ancho && m[f][c];

  const segmentos = new Map<string, Punto[]>();
  const clave = (p: Punto) => `${p[0]},${p[1]}`;

  for (let f = -1; f < alto; f++) {
    for (let c = -1; c < ancho; c++) {
      const caso = (ocupado(f, c) ? 1 : 0) | (ocupado(f, c + 1) ? 2 : 0)
        | (ocupado(f + 1, c + 1) ? 4 : 0) | (ocupado(f + 1, c) ? 8 : 0);
      for (const [desde, hasta] of CASOS[caso] || []) {
        const a: Punto = [c + LADOS[desde][0], f + LADOS[desde][1]];
        const b: Punto = [c + LADOS[hasta][0], f + LADOS[hasta][1]];
        const k = clave(a);
        const lista = segmentos.get(k);
        if (lista) lista.push(b); else segmentos.set(k, [b]);
      }
    }
  }

  const puntoDe = (k: string): Punto => {
    const [x, y] = k.split(',');
    return [Number(x), Number(y)];
  };

  const lazos: Punto[][] = [];
  while (segmentos.size) {
    const kInicio = segmentos.keys().next().value as string;
    const inicio = puntoDe(kInicio);
    const lazo: Punto[] = [inicio];
    let actual = inicio;
    for (;;) {
      const salidas = segmentos.get(clave(actual));
      if (!salidas || !salidas.length) break;
      const siguiente = salidas.pop() as Punto;
      if (!salidas.length) segmentos.delete(clave(actual));
      if (clave(siguiente) === kInicio) break;
      lazo.push(siguiente);
      actual = siguiente;
    }
    if (lazo.length > 3) lazos.push(lazo);
  }
  return lazos;
}

function area(lazo: Punto[]): number {
  let s = 0;
  for (let i = 0; i < lazo.length; i++) {
    const [x1, y1] = lazo[i];
    const [x2, y2] = lazo[(i + 1) % lazo.length];
    s += x1 * y2 - x2 * y1;
  }
  return Math.abs(s) / 2;
}

/** Douglas-Peucker iterativo: el recursivo desborda con contornos largos. */
function simplificar(puntos: Punto[], tol: number): Punto[] {
  if (puntos.length < 3) return puntos;
  const conservar = new Array(puntos.length).fill(false);
  conservar[0] = conservar[puntos.length - 1] = true;
  const pila: Array<[number, number]> = [[0, puntos.length - 1]];
  while (pila.length) {
    const [ini, fin] = pila.pop() as [number, number];
    if (fin <= ini + 1) continue;
    const [x1, y1] = puntos[ini];
    const [x2, y2] = puntos[fin];
    const dx = x2 - x1, dy = y2 - y1;
    const norma = Math.hypot(dx, dy);
    let peor = -1, peorI = ini;
    for (let i = ini + 1; i < fin; i++) {
      const [px, py] = puntos[i];
      const d = norma === 0
        ? Math.hypot(px - x1, py - y1)
        : Math.abs(dy * px - dx * py + x2 * y1 - y2 * x1) / norma;
      if (d > peor) { peor = d; peorI = i; }
    }
    if (peor > tol) {
      conservar[peorI] = true;
      pila.push([ini, peorI], [peorI, fin]);
    }
  }
  return puntos.filter((_, i) => conservar[i]);
}

/** Lee la imagen a un lienzo, achicandola si hace falta. */
async function aImageData(archivo: File): Promise<ImageData> {
  const url = URL.createObjectURL(archivo);
  try {
    const img = await new Promise<HTMLImageElement>((ok, mal) => {
      const el = new Image();
      el.onload = () => ok(el);
      el.onerror = () => mal(new TrazadoImposible('Ese archivo no es una imagen que pueda leer.'));
      el.src = url;
    });
    let { naturalWidth: w, naturalHeight: h } = img;
    if (!w || !h) throw new TrazadoImposible('Esa imagen no tiene tamaño.');
    const escala = Math.min(1, LADO_MAX / Math.max(w, h));
    w = Math.max(1, Math.round(w * escala));
    h = Math.max(1, Math.round(h * escala));
    const lienzo = document.createElement('canvas');
    lienzo.width = w; lienzo.height = h;
    const ctx = lienzo.getContext('2d', { willReadFrequently: true });
    if (!ctx) throw new TrazadoImposible('El navegador no me dejó leer la imagen.');
    ctx.drawImage(img, 0, 0, w, h);
    return ctx.getImageData(0, 0, w, h);
  } finally {
    URL.revokeObjectURL(url);
  }
}

/** El nucleo, sobre pixeles crudos. Separado de la lectura del archivo para
 *  poder compararlo contra el trazador de Python con los MISMOS pixeles. */
export function trazarDesdePixeles(datos: ImageData, lado = 160): string {
  const { m, ancho, alto } = mascara(datos);

  let tinta = 0;
  for (const fila of m) for (const v of fila) if (v) tinta++;
  if (tinta === 0) {
    throw new TrazadoImposible('La imagen salió vacía: probá con una de más contraste.');
  }
  if (tinta === ancho * alto) {
    throw new TrazadoImposible('La imagen salió toda llena: no tiene contraste.');
  }

  const lazos = contornos(m, ancho, alto);
  if (!lazos.length) throw new TrazadoImposible('No encontré un contorno en esa imagen.');

  const mayor = Math.max(...lazos.map(area));
  const utiles = lazos.filter(l => area(l) >= mayor * AREA_MINIMA);

  const escala = lado / Math.max(ancho, alto);
  const dx = (lado - ancho * escala) / 2;
  const dy = (lado - alto * escala) / 2;

  const partes: string[] = [];
  for (const lazo of utiles) {
    const simple = simplificar(lazo, TOLERANCIA);
    if (simple.length < 3) continue;
    const pts = simple.map(([x, y]) =>
      `${(x * escala + dx).toFixed(2)} ${(y * escala + dy).toFixed(2)}`);
    partes.push(`M ${pts.join(' L ')} Z`);
  }
  if (!partes.length) {
    throw new TrazadoImposible('El contorno quedó demasiado chico para usarlo.');
  }

  // evenodd para que los huecos del icono queden calados y no rellenos.
  // currentColor es la convencion del resto del catalogo: el mismo archivo
  // sirve para el plano oscuro y para el blanco.
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${lado} ${lado}">`
    + `<path d="${partes.join(' ')}" fill="currentColor" fill-rule="evenodd"/>`
    + `</svg>`;
}

/** Imagen -> SVG del contorno, en un lienzo cuadrado de `lado`. */
export async function trazarEnNavegador(archivo: File, lado = 160): Promise<string> {
  return trazarDesdePixeles(await aImageData(archivo), lado);
}
