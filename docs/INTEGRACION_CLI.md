# Integrar los subcomandos del hub local en la CLI de flujo

Estado actual: el repo ya tiene una CLI Typer completa en `src/flujo/cli.py` y `src/flujo/__main__.py` debe delegar siempre a esa CLI.

Los comandos nuevos del hub local se registran bajo el namespace `hub` para no ocultar comandos existentes:

```bash
py -m flujo hub serve --open
py -m flujo hub index agent-brief "etiqueta creatina"
py -m flujo hub route where --area eventos --pieza flyer
```

## Regla importante

No reemplaces `src/flujo/__main__.py` por un dispatcher propio. Debe quedar asi:

```python
from .cli import app

if __name__ == "__main__":
    app()
```

## Integracion en Typer

La integracion viva esta en `src/flujo/cli_addons.py`:

```python
from flujo.cli_addons import register_addons
register_addons(app)
```

Eso agrega:

```txt
py -m flujo hub serve
py -m flujo hub index
py -m flujo hub route
```

## Verificacion

```bash
py -m flujo health
py -m flujo doctor
py -m flujo hub serve --help
py -m flujo hub route where --area eventos --pieza flyer
py -m flujo hub index agent-brief "etiqueta creatina"
```

## Airdrop

Aplicar via airdrop seguro:

```bash
py scripts/validate_airdrop.py
py scripts/run_airdrop_checks.py "fix: integrar hub addons"
```

Reglas del repo:

- Windows + `py`.
- Los resultados deben quedar verificables en el checkout actual.
- No tokens ni datos sensibles.
- No caches, builds ni binarios pesados en airdrops.
