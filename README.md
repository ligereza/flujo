# flujo — Dimensiones del Orden

**arte + automatización**

Sistema de automatización para flujos creativos.

## Estado actual (v0.15)

- CLI unificado (`flujo`)
- Descarga Instagram con instaloader
- Análisis de colores + OCR opcional
- Export ZIP con integración directa para Photoshop e Illustrator (lee palette.json real)
- Sistema de airdrop

## Flujo principal

```bash
flujo flyer-import inbox/correo.txt
flujo analyze
flujo export <proyecto>
flujo open <proyecto> --ps
```

## Estructura

```
projects/
├── flyer_eventos/
├── piezas_vectoriales/
└── tapiz/

src/flujo/                # CLI moderno
```

## Reglas

- No automatizar Photoshop / Illustrator / Blender
- Solo instaloader para Instagram
- Mantener checkpoints y contexto

---

**Versión:** v0.15 — Track M (paleta real)
