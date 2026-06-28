# plano — generador paramétrico de planos para eventos

> Integrado con flujo (estilos) y cotizaciones (dual productora/ONG).
> Estado: mejorado para línea estética + cotizaciones.

## Idea

Diseñar **planos y riders de stands sin entrar a AutoCAD**, generándolos por
**matemáticas a partir de "constantes de realidad"**: las cosas del mundo real
tienen forma y proporciones conocidas, así que el plano se calcula, no se dibuja
a mano.

> Antecedente: el dueño ya construyó (en otro chat) un generador de planos de
> **teatro/sala** con geometría **radial** real (fórmula de la sagita para el
> escenario curvo, bloques de butacas con alineación radial, balcón). Ese código
> está en `referencia_plano_teatro.py` como base/inspiración. Aquí lo
> generalizamos a **stands de intervención en terreno** (la ONG Reduciendo Daño).

## Constantes de realidad (la clave del enfoque)

Cada elemento real tiene dimensiones y reglas. El plano se arma combinándolas:

| Elemento | Constante / forma | Regla derivada |
|---|---|---|
| **Mesa** | cuadrada/rectangular (ej. 2,0 × 0,7 m) | ocupa área fija; N mesas → fila |
| **Stand (toldo)** | rectángulo estándar (3×3 m, 3×4,5 m, 6×3 m) | define el área base del módulo |
| **Silla / asiento** | ~0,5 × 0,5 m | **n.º asientos = n.º voluntarios** |
| **Zona de descanso** | sección opcional | se agrega como módulo aparte |
| **Pasillo de circulación** | ancho mínimo ~1,2 m | separa módulos |

## Brief modificable por reglas (constantes operativas)

El rider no es estático: **se recalcula con reglas** sobre los parámetros del evento.
Ejemplos de constantes operativas:

- `duración > 4 h` → agregar **colación / viático** al equipo.
- `duración > 5 h` → **alimentación obligatoria** (producción o costo extra).
- `voluntarios > 5` → **+1 mesa**.
- `asistentes > N` → escalar tamaño de stand / cantidad de personal.
- `incluye testeo` → **+1 stand contiguo** + mesa extra para reactivos.
- `evento masivo` → agregar **zona de contención/descanso**.

Estas reglas viven en un JSON/config y el documento (plano + rider + costos) se
regenera solo al cambiar los parámetros — igual que la generación por lote de
flyers, pero para documentos operativos.

## Arquitectura propuesta (modular)

```
projects/plano/
├── README.md                      # este archivo
├── feedback.md                    # qué refinar (para la próxima IA)
├── referencia_plano_teatro.py     # generador radial original (base, requiere customtkinter)
├── plano_stands.py                # NUEVO: motor headless de stands (sin GUI) — prototipo
├── ejemplos/
│   └── evento_ejemplo.json        # parámetros de un evento + reglas
└── (futuro) plano_editor.html     # editor visual web, estilo de los editores HTML de flujo
```

Diseño en capas (modular, para crecer):
1. **Constantes** (`CONSTANTES`): medidas reales de mesas, toldos, sillas, pasillos.
2. **Reglas** (`REGLAS`): funciones puras parámetros → requerimientos (colación, mesas extra…).
3. **Layout** (`solve_layout`): coloca los módulos en coordenadas (m) sin solaparse.
4. **Render**: a SVG (web) o matplotlib (PDF). Reusa el enfoque SVG de flujo.

## Cómo encaja en flujo

- Es el **rider técnico / plano** que pide el área de eventos para el brief de
  productoras (ver `data_brief_intervencion_terreno.json` y `brief_demo.html`).
- Salida: SVG/PDF en **PC horizontal** y **móvil vertical** (mismo requisito del brief).
- A futuro: `flujo plano <evento.json>` genera el plano + el rider con costos.

## Próximo paso

Ver `feedback.md`. En resumen: validar el motor headless `plano_stands.py`,
afinar las constantes con medidas reales del dueño, y luego un editor HTML.
