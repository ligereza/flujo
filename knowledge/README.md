# Knowledge base flujo

Memoria operacional versionable para productoras, venues, logos, eventos y ejemplos reales.

Principio: cada pedido debe mejorar la memoria del sistema.

Estructura:

```txt
knowledge/productoras/*.yaml
knowledge/venues/*.yaml
knowledge/logos/*.yaml
knowledge/events/*.yaml
knowledge/examples/*/manifest.json
knowledge/learning_cases/*.json
knowledge/math_targets/*.json
knowledge/lane_registry/*.json
```

Los datos pueden ser incompletos. Usar `confidence`, `source` y `notes` antes que inventar certezas.

`learning_cases/` conecta memoria historica con investigacion posterior sin
copiar los arboles fuente. Cada caso conserva hashes, clase epistemica,
limites de afirmacion y acciones aprendibles. Validar primero en modo
read-only; registrar en el ledger requiere una base explicita:

```bash
PYTHONPATH=src .venv/bin/python tools/source_learning_bridge.py knowledge/learning_cases/<case>.json
PYTHONPATH=src .venv/bin/python tools/source_learning_bridge.py knowledge/learning_cases/<case>.json --db data/mak_knowledge.db --record
```

Un episodio verificado por este puente certifica integridad y trazabilidad de
la ingestion. No certifica la verdad de las hipotesis contenidas en el caso.

`math_targets/` usa la misma primera capa cultural-investigativa para targets
matematicos. El Math Kernel solo agenda requests y conserva `ResultCard`
metadata-only; formulas, pruebas y contraejemplos quedan sellados por hash y
referencia. `MILLENNIUM-PNP-001` es una capsula inicial con fidelidad semantica
`UNTRUSTED`, por lo que ninguna tarjeta puede convertirse en solucion.

`lane_registry/` es el mapa operativo transversal, no un segundo handoff. La
registry `mak_cross_domain_registry_2026-08-20.json` mantiene 19 lineas bajo
`cultural_research_first` (incluye tenis, scraping, deep learning, simulacion,
eventos, transpilacion, geometria y P=NP), con estado, dialectos, evidencia, consumidor,
guardrails y siguiente gate. Consultar sin mutar con:

```bash
PYTHONPATH=src .venv/bin/python tools/project_lanes.py summary
```

El lane de tenis expone además el consumidor read-only
`tools/tennis_shot_events.py`, que adapta la notación MCP al contrato local
`schemas/tennis/shot_event.schema.json` sin completar coordenadas, spin,
fatiga ni contrafactuales ausentes.

Para investigación web, `tools/research_source_capture.py URL` solo prepara
un plan; `--record` es la mutación explícita de una única captura al almacén
local. Para deep learning, `tools/deep_learning_gate.py MANIFEST.json`
verifica labels, holdout independiente y validador; incluso con `eligible`,
`training_permitted` permanece `false`.

Research 4 dispone de `tools/research_simulation.py` para manifiestos L-system
explícitos. Su trayectoria es una proyección simbólica, con presupuesto de
símbolos y `model_not_reality=true`; no simula ni prueba crecimiento biológico.
