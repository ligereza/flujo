# Illustrator tools - Logo Clean Master

Esta carpeta contiene scripts locales para Adobe Illustrator usados por `flujo`.

## Script incluido

```txt
tools/illustrator/scripts/logo_clean_master.jsx
```

## Objetivo

Limpiar logos/palabras ya hechas sin redibujarlas:

- alinear nodos casi verticales/horizontales;
- enderezar segmentos casi H/V;
- cerrar solo handles del segmento recto, no del nodo completo;
- preservar curvas vecinas en B/R/P/D;
- corregir tangentes evidentes en letras redondas;
- eliminar puntos extra solo en tramos rectos.

## Uso en Illustrator

1. Convertir texto a contornos si corresponde:

```txt
Type > Create Outlines
```

2. Seleccionar palabra, letra o logo.
3. Ejecutar:

```txt
File > Scripts > Other Script...
```

4. Elegir:

```txt
tools/illustrator/scripts/logo_clean_master.jsx
```

## Modos del script

```txt
A = Audit, no modifica
W = Word, escribir palabra
M = Micro, sin palabra
O = Ortho, tratar seleccion como recta
R = Round, tratar seleccion como curva/redonda
```

## Reglas aprendidas

- No usar baseline global automatico: deforma letras.
- No forzar diagonales a 45 grados.
- No cerrar todos los handles de un nodo en letras mixtas.
- Para un segmento recto p1 -> p2, cerrar solo `p1.rightDirection` y `p2.leftDirection`.
- Para redondas, corregir tangentes solo en extremos evidentes.
- Si el resultado no gusta, usar `Ctrl+Z`.

## Estado

Proyecto experimental. No es herramienta final.

---

# Puente JSON agente <-> Adobe (Illustrator / Photoshop / After Effects)

Cierra la comunicacion agente-sin-contexto <-> app de Adobe SIN pasar el archivo nativo
ni el SVG completo: la app exporta su estado a JSON, el agente devuelve un JSON de ops.

## Loop
```
App --(export)--> ~/Desktop/ai_illustrator/state.json --> agente lee (texto/pos/estilo)
agente --> ~/Desktop/ai_illustrator/ops.json --(apply)--> App aplica
```

## Scripts
| Archivo | App | Ops |
|---|---|---|
| `ai_illustrator_bridge.jsx` | Illustrator | setText, setSize, setFill, setFont, move, addText |
| `ai_photoshop_bridge.jsx` | Photoshop | setText, setSize, setFill |
| `ai_ae_bridge.jsx` | After Effects | setText, setSize |
| `ai_export_svg_png.jsx` | Illustrator | exporta el doc activo a SVG + PNG (para el LLM) |

Contrato de `ops.json`: ver `ai_illustrator_ops.example.json`.

## Uso
1. App: Archivo > Secuencias de comandos > Otra secuencia... > el `.jsx` con `MODE="export"`.
2. Pasa `state.json` al agente; devuelve `ops.json`.
3. `MODE="apply"`, corre de nuevo -> la app aplica.

## Notas
- Targetea por NOMBRE de capa/frame -> nombra las capas (no "Layer 1").
- Parsea JSON con `eval` (ExtendScript no trae `JSON.parse`); solo archivos locales tuyos.
- No probados en las apps reales: validada la logica, no el import. Si un op falla, sigue con
  los demas y reporta cuantos targets no encontro.
