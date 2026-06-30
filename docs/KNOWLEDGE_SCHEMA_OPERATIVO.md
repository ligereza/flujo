# Knowledge schema operativo - productoras, venues y trato

Este documento define la primera estructura estable para que flujo recuerde como trabajar con cada productora, venue y servicio preferente.

## Productora (`knowledge/productoras/<id>.yaml`)

Campos recomendados:

```yaml
id: thegrid
name: The Grid
aliases: []
scale_default: base # under | base | mainstream
confidence: 0.55

relationship:
  status: prospect # prospect | active | trusted | paused
  trato: cordial_directo # formal | cordial_directo | tecnico | urgente
  decision_maker: unknown
  preferred_contact: instagram # instagram | whatsapp | email | productor
  notes: []

service_preferences:
  default_service: informativo # informativo | testeo | mixto | capacitacion | unknown
  testeo: unknown # true | false | unknown | maybe
  rider_level: base # light | base | full
  quote_style: simple # simple | detailed | institutional
  preferred_deliverables:
    - rider_plano
    - flyer_10x14

brand_assets:
  logo_id: thegrid_primary
  logo_status: source_needed
  preferred_logo_source: unknown

venues_recurrentes: []
sources:
  - type: human
    note: pendiente completar
```

## Venue (`knowledge/venues/<id>.yaml`)

```yaml
id: espacio_riesco
name: Espacio Riesco
scale_default: mainstream
capacity_bucket: high

operations:
  electricity_default: true
  water_default: unknown
  security_coordination: required
  medical_access: required
  load_in_notes: []

recommended_service:
  rider_level: full
  default_preset: MAINSTREAM
  volunteers_min: 8
  tables_min: 3
  chairs_min: 8
```

## Logo (`knowledge/logos/<id>.yaml`)

```yaml
id: thegrid_primary
producer_id: thegrid
status: source_needed # source_needed | needs_vectorization | in_progress | final_svg_ready
source_quality: unknown
sources: []
outputs: {}
```

## Regla

Cada pedido real debe mejorar al menos un dato si aparece informacion nueva: productora, venue, logo, trato o servicio preferente.
