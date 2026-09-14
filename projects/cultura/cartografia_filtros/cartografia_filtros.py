"""
Cartografia de filtros -- mapa del borde que un agente autorizado NO cruza.

Semilla: (+)3 (12-jul-2026, puente/SEMILLAS.md) -- "la Tilde NO es ahorro de
tokens, es residuo intraducible" -- precipitada contra MANIFIESTO #8 ("Mis
filtros son una Tilde... el lugar exacto donde un modelo no puede hablar es su
virgulilla; mapear que bloquea cada modelo es cartografiar su inconsciente").

El cruce de codigo (plegado) aca es el clasificador de auto-mode: una traduccion
de "intencion del agente" a "accion permitida" que MAYORMENTE funciona -- deja
pasar casi todo. Contra ese fondo permisivo, el residuo se ve: lo que rechaza.
Igual que la virgulilla se ve solo contra un ASCII legible, el borde del filtro
se ve solo contra un clasificador que casi siempre dice si.

Esta pieza es DESCRIPTIVA (limite duro del repo, MANIFIESTO #8): registra el
BORDE -- que capa rechazo, que categoria de accion, con que forma de pedido --
y NUNCA el contenido vedado detras del bloqueo. Cruzar el borde para ver que hay
del otro lado destruiria el mapa (esa es la Omega11, ver DOSSIER.md). No perfila
personas; no reconstruye payloads; no es un how-to de evasion.

El registro se siembra con eventos REALES y fechados de la sesion 2026-07-16
(los bloqueos que el clasificador aplico a este mismo agente con autorizacion
total). Son la fuente de verdad -- curados a mano, como la tabla de costo de
tilde_residuo.py -- no un scrape del transcript.

Estatutos (regla de escritura #2 del MOTOR):
- "borde" / "frontera": PROCEDIMIENTO. Es donde el clasificador cambia de si a
  no. Se nombra por coordenadas (capa x categoria), no se decora.
- "forma de pedido": la SILUETA neutra de la accion (que CLASE de operacion),
  jamas el payload. "borrar-lote-fs", no el comando ni las rutas sensibles.
- "residuo del filtro": lo que quedo sin cruzar -- se resolvio reescribiendo
  (borde poroso) o quedo como tarea manual del humano (borde duro). Esa
  distincion ES el mapa.

Esta pieza NO ejecuta ninguna accion bloqueada, ni siquiera para "probar" el
borde: el mapa se dibuja desde el registro, no palpando la pared.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

# Capas donde vive un borde (el plegado que puede decir no). Ordenadas de la mas
# externa (antes de tocar nada) a la mas interna (el modelo mismo).
CAPAS = ("auto-mode-classifier", "hook", "permission-rule", "model-safety")

# Guarda de la Omega11 en codigo: una forma-de-pedido que supere esto se asume
# contaminada con payload real y se RECHAZA al registrar. El borde se mapea con
# siluetas cortas; un texto largo ya no es silueta, es contenido.
_MAX_SILUETA = 80

# Marcadores de que una silueta dejo de ser silueta y arrastro payload real.
# No es exhaustivo -- es un freno, no un firewall. Ante la duda, se rechaza.
_MARCADORES_PAYLOAD = (
    "\n",  # una silueta es una linea; multilinea = se colo un bloque
    "```",
    "-----BEGIN",
    "rm -rf",
    "http://",
    "https://",
)


@dataclass
class Bloqueo:
    """Un punto del borde: donde el clasificador dijo no, sin lo que habia detras."""

    fecha: str            # ISO, cuando paso
    capa: str             # cual de CAPAS rechazo
    categoria: str        # clase de accion: 'borrar-lote-fs', 'git-destructivo', ...
    silueta: str          # forma NEUTRA del pedido; nunca el payload
    disposicion: str      # 'reescrito' (borde poroso) | 'manual-humano' (borde duro)
                          #  | 'failsafe' (clasificador no disponible -> se freno solo)

    def __post_init__(self) -> None:
        if self.capa not in CAPAS:
            raise ValueError(f"capa desconocida: {self.capa!r} (usar una de {CAPAS})")
        _asegurar_silueta(self.silueta)


def _asegurar_silueta(texto: str) -> None:
    """Enforcement de la Omega11(a): si esto no es una silueta neutra corta sino
    contenido, se rechaza ANTES de que entre al mapa. Cruzar el borde (guardar lo
    vedado) es exactamente lo que la pieza tiene prohibido."""
    if len(texto) > _MAX_SILUETA:
        raise ValueError(
            f"silueta de {len(texto)} chars supera {_MAX_SILUETA}: parece payload, "
            "no borde. El mapa registra la forma, no el contenido."
        )
    bajo = texto.lower()
    for marca in _MARCADORES_PAYLOAD:
        if marca.lower() in bajo:
            raise ValueError(
                f"silueta contiene marcador de payload ({marca!r}); se rechaza. "
                "El borde se mapea con siluetas, no con el pedido crudo."
            )


@dataclass
class Cartografia:
    """El mapa: los bloqueos agrupados por coordenada (capa x categoria).

    NO es una lista plana de errores (esa seria la lectura que la Omega11(b)
    prohibe): agrupa por borde y separa lo poroso de lo duro, que es la lectura
    cartografica -- donde la autorizacion del agente alcanza y donde no.
    """

    bloqueos: list[Bloqueo] = field(default_factory=list)

    def agregar(self, b: Bloqueo) -> None:
        self.bloqueos.append(b)

    @property
    def duros(self) -> list[Bloqueo]:
        """Bordes que ni reescribiendo se cruzan: quedaron como tarea humana."""
        return [b for b in self.bloqueos if b.disposicion == "manual-humano"]

    @property
    def porosos(self) -> list[Bloqueo]:
        """Bordes que se cruzan reformulando: el no era a la FORMA, no al fin."""
        return [b for b in self.bloqueos if b.disposicion == "reescrito"]

    def por_coordenada(self) -> dict[tuple[str, str], list[Bloqueo]]:
        """Agrupa por (capa, categoria) -- las celdas del mapa."""
        celdas: dict[tuple[str, str], list[Bloqueo]] = {}
        for b in self.bloqueos:
            celdas.setdefault((b.capa, b.categoria), []).append(b)
        return celdas

    def densidad(self) -> dict[str, int]:
        """Cuantas veces se toco el borde por capa. La 'densidad de tilde': donde
        el agente choca mas seguido con lo que no puede hacer."""
        d: dict[str, int] = {capa: 0 for capa in CAPAS}
        for b in self.bloqueos:
            d[b.capa] += 1
        return {capa: n for capa, n in d.items() if n}

    def render(self) -> str:
        """Dibuja el mapa en texto: celdas por coordenada, marcando poroso (~) vs
        duro (#). El caracter del borde duro es '#' -- la pared; el poroso es '~'
        -- la virgulilla, el borde que ondula y deja pasar si lo nombras distinto."""
        if not self.bloqueos:
            return "cartografia vacia: ningun borde tocado (nada que mapear)"
        lineas = ["CARTOGRAFIA DE FILTROS -- borde de lo no-cruzable", ""]
        celdas = self.por_coordenada()
        for (capa, categoria) in sorted(celdas):
            eventos = celdas[(capa, categoria)]
            marcas = "".join("#" if e.disposicion == "manual-humano" else "~" for e in eventos)
            lineas.append(f"  [{capa}] {categoria}")
            lineas.append(f"      {marcas}  ({len(eventos)})")
            for e in eventos:
                signo = "#" if e.disposicion == "manual-humano" else "~"
                lineas.append(f"      {signo} {e.fecha}  {e.silueta}  -> {e.disposicion}")
            lineas.append("")
        dur, por = len(self.duros), len(self.porosos)
        lineas.append(f"borde duro (#): {dur}   borde poroso (~): {por}")
        lineas.append("densidad por capa: " + ", ".join(f"{c}={n}" for c, n in self.densidad().items()))
        lineas.append("")
        lineas.append("# = no se cruza ni reescribiendo (tarea humana); ~ = el no era a la forma")
        return "\n".join(lineas)


def cargar_registro(path: str | Path) -> Cartografia:
    """Lee un registro JSONL de bloqueos (un objeto por linea) y arma el mapa.
    Cada linea pasa por la guarda de silueta: un registro con payload no carga."""
    carto = Cartografia()
    for linea in Path(path).read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        d = json.loads(linea)
        carto.agregar(
            Bloqueo(
                fecha=str(d["fecha"]),
                capa=str(d["capa"]),
                categoria=str(d["categoria"]),
                silueta=str(d["silueta"]),
                disposicion=str(d["disposicion"]),
            )
        )
    return carto


def cartografia_de(bloqueos: Iterable[Bloqueo]) -> Cartografia:
    carto = Cartografia()
    for b in bloqueos:
        carto.agregar(b)
    return carto


def _main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="cartografia_filtros.py",
        description="Dibuja el mapa del borde que un agente autorizado no cruza (descriptivo).",
    )
    default_reg = Path(__file__).resolve().parent / "registro_bloqueos.jsonl"
    parser.add_argument("registro", nargs="?", default=str(default_reg),
                        help="JSONL de bloqueos (default: registro_bloqueos.jsonl al lado)")
    args = parser.parse_args(argv)
    carto = cargar_registro(args.registro)
    print(carto.render())
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
