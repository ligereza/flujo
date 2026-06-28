# EVENTOS - presets para rider/plano

Estos presets son estimaciones operativas iniciales. La informacion fina del evento debe salir del flyer/post de la productora: fecha, venue, horario, lineup, productora y formato visual.

Cuando el jefe pida cambios, se ajustan los campos y se regenera rider/plano.

## Preset UNDER

Uso:

```txt
club chico / bajo flujo / presencia ligera RD
```

Base:

```txt
voluntarios: 2
mesas: 1
sillas: 2
electricidad: 1 punto electrico basico
luz: luz ambiente o 1 foco simple
asistentes estimados: 350
duracion estimada: 4h
servicios: stand informativo
```

## Preset BASE

Uso:

```txt
evento mediano / flujo moderado / stand + testeo
```

Base:

```txt
voluntarios: 4
mesas: 2
sillas: 4
electricidad: 1 punto electrico estable + alargador/zapatilla
luz: iluminacion de mesa para testeo + luz stand
asistentes estimados: 1200
duracion estimada: 6h
servicios: stand informativo + testeo
```

## Preset MAINSTREAM

Uso:

```txt
festival / Espacio Riesco / alto flujo / coordinacion y contencion
```

Base:

```txt
voluntarios: 8
mesas: 3
sillas: 8
electricidad: 2 puntos electricos o circuito dedicado + alargadores/zapatillas
luz: iluminacion dedicada para stand, testeo y lectura nocturna
asistentes estimados: 6000
duracion estimada: 8h
servicios: stand informativo + testeo + contencion + coordinacion + descanso
```

## Mapeo para correos con Instagram

Ejemplo:

```txt
Hola Ligereza, te recuerdo que tenemos este evento,
https://www.instagram.com/thegrid.club/p/DYz0HOrFhJO/?hl=es

necesito que me mandes el Rider completo y subas el flyer de la cartelera.
```

Mapeo inicial:

```yaml
area: eventos
route: eventos_instagram_rider_cartelera
source: correo_jefe
instagram_url: https://www.instagram.com/thegrid.club/p/DYz0HOrFhJO/?hl=es
entregables:
  - rider_completo
  - flyer_cartelera
preset_operativo: mainstream  # si el flyer/post indica Espacio Riesco o evento masivo
acciones:
  - descargar post Instagram
  - leer datos del flyer/post
  - generar rider con preset MAINSTREAM
  - preparar/subir cartelera
```

## Regla practica

- Si es club pequeno o evento under: `UNDER`.
- Si es evento normal con testeo: `BASE`.
- Si es festival/Espacio Riesco/alto flujo: `MAINSTREAM`.

Los presets son punto de partida, no contrato fijo.
