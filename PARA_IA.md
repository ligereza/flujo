# PARA IA — Cómo continuar este repo

Este repo se llama `flujo`.

Su idea central es: **Dimensiones del Orden**.

Funciona como una zapatilla/alargador organizador para proyectos creativos, automatizaciones e IAs.

No reemplaza el trabajo manual del diseñador. Ordena contexto, proyectos, herramientas, inputs, outputs y checkpoints para no empezar desde cero en cada chat.

## Leer en este orden

1. `README.md`
2. `docs/DIMENSIONES_DEL_ORDEN.md`
3. `context/ESTADO.md`
4. último archivo en `checkpoints/`
5. herramienta activa en `tools/flyer_eventos/SPEC.md`

## Estado actual

La herramienta activa es:

```txt
flyer_eventos
```

## Flujo actual probado

Crear proyecto manual:

```bash
bash scripts/new_flyer_evento.sh "nombre evento"
```

Crear proyectos desde correo con links de Instagram:

```bash
py scripts/flyer_from_email.py "inbox/correo_prueba.txt"
```

Listar proyectos:

```bash
bash scripts/flyer_list.sh
```

Ver último proyecto:

```bash
bash scripts/flyer_latest.sh
```

Setear imagen demo en último proyecto:

```bash
bash scripts/flyer_set_input_latest_demo.sh
```

Ver estado del último proyecto:

```bash
bash scripts/flyer_status_latest.sh
```

Ver estado general:

```bash
bash scripts/orden_status.sh
```

Aplicar paquete de mejoras airdrop:

```bash
bash scripts/apply_airdrop.sh --dry-run
bash scripts/apply_airdrop.sh --apply
```

Guardar avance:

```bash
bash scripts/checkpoint.sh "mensaje"
```

## Qué ya hace

- Crea estructura de proyectos flyer.
- Mantiene carpetas con `.gitkeep`.
- Copia imagen input demo.
- Actualiza `manifest.json`.
- Lista proyectos.
- Detecta último proyecto.
- Lee un correo `.txt`.
- Extrae links de Instagram.
- Crea un proyecto por cada link.
- Marca esos proyectos como `from_email_pending_download`.
- Permite aplicar mejoras completas mediante `_airdrop/`.

## Qué NO hace todavía

- No descarga Instagram automáticamente.
- No analiza la imagen/video.
- No extrae texto del flyer.
- No detecta si es video.
- No abre Photoshop.
- No abre Blender.
- No borra archivos.

## Sistema airdrop

Para acelerar cambios:

1. Crear archivos dentro de `_airdrop/` respetando rutas.
2. Probar:

```bash
bash scripts/apply_airdrop.sh --dry-run
```

3. Aplicar:

```bash
bash scripts/apply_airdrop.sh --apply
```

4. Guardar:

```bash
bash scripts/checkpoint.sh "aplicar mejoras airdrop"
```

## Próximo paso recomendado

Mejorar `flyer_from_email.py`.

Siguiente mejora lógica:

- detectar si el link es `/p/`, `/reel/` o `/tv/`
- guardar `instagram_type` en el manifest
- marcar `/reel/` como posible video
- mantener `needs_manual_review: true`

## Reglas

- Avanzar paso a paso.
- No hacer cambios gigantes.
- No automatizar Photoshop/Blender todavía.
- No subir archivos pesados.
- No borrar nada sin confirmación.
- Usar `py` para scripts Python.
- Mantener compatibilidad con Git Bash en Windows.
- Después de cada mejora pequeña, hacer checkpoint.
