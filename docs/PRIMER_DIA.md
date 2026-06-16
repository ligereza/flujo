# Guía del primer día con flujo

Este documento resume el flujo diario recomendado para usar el repo con la ONG.

## Instalación inicial (una sola vez)

```bash
py -m pip install -r requirements.txt
py -m pip install -r requirements-dev.txt
py -m pre_commit install
```

O simplemente:

```bash
bash scripts/setup.sh
```

## Flujo diario recomendado

### 1. Al empezar el día

Generar el dashboard y ver qué hay pendiente:

```bash
py scripts/flujo.py daily
bash scripts/abrir_dashboard.sh
```

### 2. Cuando llega un nuevo pedido por correo

Si el correo tiene un pedido de diseño/impresión:

```bash
bash scripts/nuevo_pedido.sh "nombre pedido" inbox/correo.txt
```

Esto crea un job, infiere tipo/medidas, genera el proyecto y abre el dashboard.

Si el correo tiene links de Instagram para flyers:

```bash
py scripts/flyer_from_email.py inbox/correo.txt
```

### 3. Revisar y completar datos

Abrir el dashboard y revisar los items de prioridad alta. Completar los datos faltantes en:

- `jobs/YYYY-MM-DD_nombre/brief.yaml`
- `projects/flyer_eventos/YYYY-MM-DD_nombre/manifest.json`

### 4. Generar assets

Para piezas vectoriales:

```bash
py scripts/piezas_generar.py projects/piezas_vectoriales/NOMBRE/config.json
```

Para flyers (después de descargar la imagen de Instagram):

- Abrir Photoshop manualmente con la imagen descargada.
- Trabajar en `projects/flyer_eventos/YYYY-MM-DD_nombre/working/`.

### 5. Antes de terminar

```bash
py scripts/flujo.py clean
py scripts/flujo.py health
bash scripts/checkpoint.sh "avance del día"
```

## Plantillas disponibles

- `projects/piezas_vectoriales/plantillas_rd/etiqueta_rd_165x65.config.json`
- `projects/piezas_vectoriales/plantillas_rd/flyer_rd_a4.config.json`

Copiar una plantilla como base:

```bash
cp projects/piezas_vectoriales/plantillas_rd/etiqueta_rd_165x65.config.json projects/piezas_vectoriales/nuevo_proyecto/config.json
```

## Comandos rápidos

```bash
py scripts/flujo.py health      # health check
py scripts/flujo.py clean       # limpiar basura
py scripts/flujo.py daily       # dashboard
py -m pytest tests/ -q           # tests
bash scripts/nuevo_pedido.sh "nombre" inbox/correo.txt
```

## Reglas de oro

- No subir archivos pesados.
- No automatizar Photoshop/Blender todavía.
- No compartir datos personales con IA externa sin sanitizar.
- Hacer checkpoint después de cada avance importante.
