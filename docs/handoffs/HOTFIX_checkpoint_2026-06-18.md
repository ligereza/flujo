# 🩹 Hotfix 2026-06-18 — `checkpoint.sh` robusto frente a pre-commit hooks

> Arregla el síntoma: "tengo que correr `bash scripts/checkpoint.sh` DOS veces
> para que se haga el push".

## Causa raíz

El repo tiene `.pre-commit-config.yaml` con hooks `trailing-whitespace` y
`end-of-file-fixer`. Estos hooks **modifican archivos** (quitan espacios al
final, arreglan el salto de línea final) y **abortan el commit** a propósito
para que revises lo que cambiaron.

El `checkpoint.sh` viejo usaba `set -e` (abortar ante el primer error), así que:

1. **1ra corrida:** `git commit` → el hook arregla archivos y falla → el script
   se aborta por `set -e` → **nunca llega al `git push`**.
2. **2da corrida:** los archivos ya están arreglados → el commit pasa → push OK.

Por eso "funcionaba a la segunda". No era magia: la 1ra corrida la consumían
los hooks.

## Solución

`checkpoint.sh` ahora **reintenta el commit automáticamente** (hasta 3 veces):
si un hook modifica archivos y aborta, re-agrega los cambios y vuelve a
commitear. Con **una sola corrida** queda commiteado y pusheado.

Mejoras extra incluidas:
- Pushea a la **rama actual** (`git rev-parse --abbrev-ref HEAD`) en vez de
  asumir `main` siempre.
- Mensajes claros de qué pasó (reintento, push completado).

## Archivos incluidos

```
_airdrop/
├── HOTFIX_checkpoint_2026-06-18.md   # este archivo
└── scripts/
    └── checkpoint.sh                 # versión robusta (reintento + rama dinámica)
```

## Aplicar

```bash
bash scripts/apply_airdrop.sh --apply
# o, con la CLI:
flujo airdrop apply "fix checkpoint.sh - push en una sola corrida"
```

> Nota: como este airdrop cambia `checkpoint.sh`, el primer `apply`/checkpoint
> que lo incluya todavía usa el script VIEJO (porque el nuevo aún no está en su
> sitio en el momento del commit). A partir del SIGUIENTE checkpoint ya corre
> el script nuevo y bastará una sola corrida. Si te pide dos veces ESTA vez, es
> normal y la última.

## Verificación hecha

```
✅ Reproducido el bug con un pre-commit hook que modifica archivos y aborta.
✅ Con el script nuevo: UNA sola corrida → commit + push OK.
✅ Confirmado: hash local == hash en origin/main.
```
