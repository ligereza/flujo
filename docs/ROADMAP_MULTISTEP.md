# Roadmap multistep por dificultad

La idea es avanzar en bloques de 2–4 pasos y revisar cada 3 bloques.

## Fácil / bajo riesgo

- Integrar privacidad a scripts existentes sin cambiar flujo.
- Agregar docs/checklists/recetas.
- Agregar scripts de status/listado.
- Mejorar prompts para IA.
- Agregar plantillas JSON nuevas.
- Usar hub datadrop section (o `flujo datadrop scan/list/prepare`) para capturar entregas reales (prepara linea v4.1).

## Medio / requiere pruebas

- Convertir `brief.yaml` a proyectos con selección automática de plantilla.
- Crear componentes reutilizables: logo, footer, QR, tabla nutricional.
- Generar reportes de entrega por job.
- Integrar privacidad en jobs/artifacts.
- Crear GitHub Actions más parametrizable.
- Integrar datadrops (manifests + for_future_ai) como ejemplos reales en linea_editorial v4.1 (inverse airdrop + §10 validación).
- Preparar auto-compact de LAST_HANDOFF/contexto para trabajo paralelo de agentes (supervisor + cycles).

## Difícil / revisar antes

- Generación automática de diseños completos desde briefs largos.
- Export PDF/AI robusto desde servidor.
- OCR/análisis visual de PDFs/Canva.
- Automatización con APIs externas o datos sensibles.
- Sistema legal/compliance completo para Ley 21.719.
- Auto-compact + supervisor robusto para delegación multi-agente paralela real (datadrops + linea join + hub).

## Regla de avance

1. Hacer 2–3 pasos fáciles o 1 mediano.
2. Actualizar `flujo_airdrop_latest.zip`.
3. Cada 3 multisteps, revisar estructura antes de seguir.
4. **Nuevo:** siempre vía `flujo app` + hub (incl. Datadrop) + LAST_HANDOFF. Prepara parallel + auto-compact; usa datadrops para v4.1 examples.
