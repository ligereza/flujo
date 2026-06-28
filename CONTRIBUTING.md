# Cómo contribuir a flujo

Repo personal de organización creativa con CLI unificada (`flujo`).

## Si quieres proponer cambios

1. Abre un issue o mensaje describiendo el cambio.
2. Si se acepta, crea un airdrop en `_airdrop/vX.YZ/` o un PR.
3. Asegúrate de que pasen los checks:
   ```bash
   py -m pip install -e .
   flujo version
   flujo health
   py -m pytest tests/ -q
   ```
4. Guarda un checkpoint con `bash scripts/checkpoint.sh "mensaje"`.

## Reglas

- Avanzar paso a paso (sin airdrops pequeños).
- No subir archivos pesados.
- No automatizar Photoshop/Blender sin acuerdo.
- No borrar sin confirmación.
- Usar `py` en Windows y `python3` en Linux/macOS.
- Después de cada mejora, hacer checkpoint.
- Toda la lógica nueva debería ir como módulo en `src/flujo/` con tests.

## Estilo de código

- Python 3.10+
- Sin `print()` en módulos; usar `rich.console` o logging.
- Tipado con `from __future__ import annotations`.
- Sin dependencias pesadas; preferir stdlib.
- Tests con pytest, colocarlos en `tests/test_<modulo>.py`.
