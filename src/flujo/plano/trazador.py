"""Convierte una imagen (PNG/JPG) en el contorno vectorial de un simbolo.

Para que la jefa de eventos pueda subir un icono aunque no lo tenga en SVG
(pedido del usuario, 2026-07-26). El resultado se le MUESTRA antes de guardar:
un trazado automatico puede salir sucio y quien decide si sirve es ella, no el
programa.

Por que se traza y no se incrusta la imagen tal cual: el simbolo termina en un
A4 impreso que recibe el productor tecnico del recinto. Un PNG chico incrustado
se ve pixelado al imprimir; un contorno vectorial escala limpio a cualquier
tamano y ademas obedece el color que se le declare, igual que los iconos de
fabrica.

Alcance honesto: esto traza SILUETAS, que es lo que es un icono. No reproduce
degradados, ni fotos, ni medios tonos. Si le das una foto vas a obtener una
mancha, y por eso existe la vista previa.

Solo usa Pillow, que es la unica dependencia de imagen declarada en
pyproject.toml. numpy/opencv estarian mas a mano pero no viajan con el paquete.
"""
from __future__ import annotations

import io
from typing import Dict, List, Sequence, Tuple

Punto = Tuple[float, float]
Lazo = List[Punto]

# Lado maximo de la grilla que se analiza. Mas resolucion no mejora un icono y
# multiplica los puntos del contorno (y el peso del SVG que se imprime).
LADO_MAX = 256

# Tolerancia de simplificacion, en celdas de la grilla. Sin esto el contorno
# sale con un vertice por pixel: pesado y con el borde dentado.
TOLERANCIA = 0.75

# Superficie minima de un lazo para conservarlo, como fraccion del total. Filtra
# el ruido suelto (motas del JPG) sin comerse detalles reales del icono.
AREA_MINIMA = 0.0006


class TrazadoImposible(Exception):
    """La imagen no da un contorno utilizable; el motivo va en el mensaje."""


def _mascara(imagen, umbral: int | None) -> Tuple[List[List[bool]], int, int]:
    """Grilla booleana: True donde hay tinta.

    Si la imagen trae transparencia, la tinta es lo opaco -- es el caso normal
    de un icono exportado. Si no, es lo oscuro sobre lo claro.
    """
    from PIL import Image

    imagen = imagen.copy()
    ancho, alto = imagen.size
    if max(ancho, alto) > LADO_MAX:
        escala = LADO_MAX / max(ancho, alto)
        imagen = imagen.resize((max(1, int(ancho * escala)), max(1, int(alto * escala))),
                               Image.LANCZOS)
    ancho, alto = imagen.size

    if imagen.mode in ("RGBA", "LA") or "transparency" in imagen.info:
        alfa = imagen.convert("RGBA").getchannel("A")
        datos = list(alfa.getdata())
        corte = 128 if umbral is None else umbral
        plano = [v > corte for v in datos]
        if any(plano):
            return [plano[f * ancho:(f + 1) * ancho] for f in range(alto)], ancho, alto

    gris = imagen.convert("L")
    datos = list(gris.getdata())
    corte = _umbral_otsu(datos) if umbral is None else umbral
    # `<=` y no `<`: en Otsu el umbral es el ULTIMO valor de la clase oscura,
    # no el primero de la clara. Con `<` una imagen de dos tonos puros (negro
    # 0 sobre blanco 255) da umbral 0, nada cumple `v < 0`, y el trazador
    # respondia "la imagen salio vacia" sobre un dibujo perfectamente legible.
    # Se veia solo con iconos nitidos: los suavizados tienen grises intermedios
    # y el umbral caia lejos del cero.
    plano = [v <= corte for v in datos]
    # Si el icono es claro sobre fondo oscuro, lo anterior toma el fondo.
    if sum(plano) > len(plano) * 0.6:
        plano = [not v for v in plano]
    return [plano[f * ancho:(f + 1) * ancho] for f in range(alto)], ancho, alto


def _umbral_otsu(valores: Sequence[int]) -> int:
    """Corte automatico entre tinta y fondo (Otsu), sin numpy."""
    histo = [0] * 256
    for v in valores:
        histo[v] += 1
    total = len(valores)
    suma_total = sum(i * histo[i] for i in range(256))
    suma_fondo = 0.0
    peso_fondo = 0
    mejor_var = -1.0
    mejor_corte = 128
    for i in range(256):
        peso_fondo += histo[i]
        if peso_fondo == 0:
            continue
        peso_frente = total - peso_fondo
        if peso_frente == 0:
            break
        suma_fondo += i * histo[i]
        media_fondo = suma_fondo / peso_fondo
        media_frente = (suma_total - suma_fondo) / peso_frente
        var = peso_fondo * peso_frente * (media_fondo - media_frente) ** 2
        if var > mejor_var:
            mejor_var, mejor_corte = var, i
    return mejor_corte


# Marching squares: por cada celda de 2x2, que segmentos de borde emite. Las
# claves son el caso (esquinas ocupadas como bits) y los valores, pares de
# puntos medios de los lados: 0=arriba 1=derecha 2=abajo 3=izquierda.
_LADOS = {0: (0.5, 0.0), 1: (1.0, 0.5), 2: (0.5, 1.0), 3: (0.0, 0.5)}
_CASOS: Dict[int, List[Tuple[int, int]]] = {
    1: [(3, 0)], 2: [(0, 1)], 3: [(3, 1)], 4: [(1, 2)], 5: [(3, 2), (0, 1)],
    6: [(0, 2)], 7: [(3, 2)], 8: [(2, 3)], 9: [(2, 0)], 10: [(0, 3), (2, 1)],
    11: [(2, 1)], 12: [(1, 3)], 13: [(1, 0)], 14: [(0, 3)],
}


def _contornos(mascara: List[List[bool]], ancho: int, alto: int) -> List[Lazo]:
    """Lazos cerrados que bordean la tinta, por marching squares."""
    def ocupado(f: int, c: int) -> bool:
        return 0 <= f < alto and 0 <= c < ancho and mascara[f][c]

    segmentos: Dict[Punto, List[Punto]] = {}
    for f in range(-1, alto):
        for c in range(-1, ancho):
            caso = (
                (1 if ocupado(f, c) else 0)
                | (2 if ocupado(f, c + 1) else 0)
                | (4 if ocupado(f + 1, c + 1) else 0)
                | (8 if ocupado(f + 1, c) else 0)
            )
            for desde, hasta in _CASOS.get(caso, []):
                a = (c + _LADOS[desde][0], f + _LADOS[desde][1])
                b = (c + _LADOS[hasta][0], f + _LADOS[hasta][1])
                segmentos.setdefault(a, []).append(b)

    lazos: List[Lazo] = []
    while segmentos:
        inicio = next(iter(segmentos))
        lazo: Lazo = [inicio]
        actual = inicio
        while True:
            salidas = segmentos.get(actual)
            if not salidas:
                break
            siguiente = salidas.pop()
            if not salidas:
                segmentos.pop(actual, None)
            if siguiente == inicio:
                break
            lazo.append(siguiente)
            actual = siguiente
        if len(lazo) > 3:
            lazos.append(lazo)
    return lazos


def _area(lazo: Lazo) -> float:
    s = 0.0
    for i in range(len(lazo)):
        x1, y1 = lazo[i]
        x2, y2 = lazo[(i + 1) % len(lazo)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def _simplificar(puntos: Lazo, tol: float) -> Lazo:
    """Douglas-Peucker iterativo (recursivo desborda con contornos largos)."""
    if len(puntos) < 3:
        return puntos
    conservar = [False] * len(puntos)
    conservar[0] = conservar[-1] = True
    pila = [(0, len(puntos) - 1)]
    while pila:
        ini, fin = pila.pop()
        if fin <= ini + 1:
            continue
        x1, y1 = puntos[ini]
        x2, y2 = puntos[fin]
        dx, dy = x2 - x1, y2 - y1
        norma = (dx * dx + dy * dy) ** 0.5
        peor, peor_i = -1.0, ini
        for i in range(ini + 1, fin):
            px, py = puntos[i]
            if norma == 0:
                d = ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
            else:
                d = abs(dy * px - dx * py + x2 * y1 - y2 * x1) / norma
            if d > peor:
                peor, peor_i = d, i
        if peor > tol:
            conservar[peor_i] = True
            pila.append((ini, peor_i))
            pila.append((peor_i, fin))
    return [p for p, keep in zip(puntos, conservar) if keep]


def trazar(datos: bytes, umbral: int | None = None, lado: int = 160) -> str:
    """Imagen -> SVG del contorno, en un lienzo cuadrado de `lado`.

    El trazo usa `currentColor`, que es la convencion que ya entiende el resto
    del catalogo: asi el mismo archivo sirve para el plano oscuro y el blanco.
    """
    from PIL import Image, UnidentifiedImageError

    try:
        imagen = Image.open(io.BytesIO(datos))
        imagen.load()
    except UnidentifiedImageError:
        raise TrazadoImposible("Ese archivo no es una imagen que pueda leer.")
    except Exception as e:  # noqa: BLE001
        raise TrazadoImposible(f"No pude abrir la imagen ({e}).")

    mascara, ancho, alto = _mascara(imagen, umbral)
    tinta = sum(sum(fila) for fila in mascara)
    if tinta == 0:
        raise TrazadoImposible("La imagen salio vacia: probá con una de más contraste.")
    if tinta == ancho * alto:
        raise TrazadoImposible("La imagen salio toda llena: no tiene contraste.")

    lazos = _contornos(mascara, ancho, alto)
    if not lazos:
        raise TrazadoImposible("No encontré un contorno en esa imagen.")

    area_total = max(_area(l) for l in lazos)
    utiles = [l for l in lazos if _area(l) >= area_total * AREA_MINIMA]

    escala = lado / max(ancho, alto)
    dx = (lado - ancho * escala) / 2.0
    dy = (lado - alto * escala) / 2.0

    partes: List[str] = []
    for lazo in utiles:
        simple = _simplificar(lazo, TOLERANCIA)
        if len(simple) < 3:
            continue
        pts = [f"{x * escala + dx:.2f} {y * escala + dy:.2f}" for x, y in simple]
        partes.append("M " + " L ".join(pts) + " Z")
    if not partes:
        raise TrazadoImposible("El contorno quedó demasiado chico para usarlo.")

    # evenodd para que los huecos del icono queden calados y no rellenos.
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {lado} {lado}">'
        f'<path d="{" ".join(partes)}" fill="currentColor" fill-rule="evenodd"/>'
        f'</svg>'
    )
