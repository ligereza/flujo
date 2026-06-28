# 🤝 Handoff 2026-06-18 — flujo v0.31.0 — Proyecto satélite `plano`

## Contexto

El dueño compartió un proyecto que desarrolló hace meses (en otro chat): un
**generador paramétrico de planos de teatro** (GUI customtkinter + matplotlib,
geometría radial). Quiere dejarlo como **proyecto por desarrollar** dentro de
`flujo`, al estilo de `projects/tapiz/`, y evolucionarlo hacia **planos de stands
de eventos** generados por "**matemáticas a partir de constantes de realidad**"
(mesas cuadradas, toldos rectangulares, sillas = voluntarios, etc.) + un **brief
modificable por reglas** (>4h colación, >5 personas +1 mesa, etc.).

## Qué incluye

```
projects/plano/
├── README.md                      # concepto, constantes, reglas, arquitectura
├── feedback.md                    # qué refinar (estilo tapiz)
├── plano_stands.py                # NUEVO motor headless (prototipo funcional)
├── referencia_plano_teatro.py     # generador radial original del dueño (referencia)
└── ejemplos/evento_ejemplo.json   # parámetros de un evento + reglas
```

## El motor `plano_stands.py` (prototipo, ya funciona)

Capas puras y testeables:
1. **CONSTANTES** — medidas reales (m): mesa 2,0×0,7; sillas 0,5; toldos 3×3/3×4.5/6×3; pasillo 1,2.
2. **reglas_rider(ev)** — parámetros → requerimientos: >4h colación, >5h
   alimentación, +1 mesa por cada 5 voluntarios, testeo → +stand, masivo → zona contención.
3. **solve_layout(ev)** — coloca stands en fila con pasillo; mesas y sillas dentro.
4. **render_svg / render_rider** — SVG a escala (1m=Npx) + rider de texto.

Uso:
```bash
cd projects/plano
python plano_stands.py ejemplos/evento_ejemplo.json          # SVG por stdout
python plano_stands.py ejemplos/evento_ejemplo.json --rider  # rider de texto
```

## Verificación hecha

```
✅ ejemplo (6h, 7 voluntarios, testeo, masivo) → 3 módulos: Informativo + Testeo + Contención
   rider: alimentación (>5h) + 2 mesas (7 vol.) + stand testeo + zona contención
✅ evento chico (3h, 3 vol, sin testeo) → 1 stand, 1 mesa, sin alimentación ni contención
✅ render visual revisado (PNG): stands con mesas (beige) y sillas (rojo) a escala
✅ sintaxis OK en plano_stands.py y referencia_plano_teatro.py
```

## Importante / decisiones

- **Es "por desarrollar"**: prototipo, NO integrado a la CLI todavía (igual que
  tapiz). No toca el core de flujo.
- `referencia_plano_teatro.py` requiere `customtkinter` (GUI) — es solo
  referencia matemática (fórmula de la sagita para escenario curvo radial). El
  motor nuevo es **headless** (sin GUI, sin AutoCAD).
- Las **constantes son supuestos razonables**: hay que confirmarlas con el dueño
  (tamaño real de toldos/mesas de RD).

## Próximos pasos (ver feedback.md)
1. Confirmar constantes reales + completar todas las reglas operativas en el JSON.
2. Layout respecto a escenario/accesos/baños/zona médica (reusar idea radial).
3. **Editor `plano_editor.html`** (estilo flujo) con export PC + móvil vertical.
4. Insertar plano+rider como página del brief para productoras.
5. Desglose de **costos** por reglas (la cotización aumenta con cada cambio).

## Cómo aplicar
```bash
flujo airdrop apply "v0.31.0 - proyecto plano (por desarrollar)"
py -m pip install -e .
flujo version            # 0.31.0
cd projects/plano && python plano_stands.py ejemplos/evento_ejemplo.json --rider
```
