# Perfiles del hub + Plano/Rider compartible

Sistema de perfiles del hub React (`web/src/`) y el build standalone que
permite compartir SOLO el editor de Plano/Rider con alguien fuera del equipo
(ej. la jefa de area en la ONG Reduciendo Dano), sin darle el resto de la app.

## 1. Sistema de perfiles

Fuente de verdad: `web/src/data/profiles.ts`. Antes ese estado vivia en
`AppShell.tsx` como `useState` + ternarios de color repetidos por todo el
componente; ahora es un objeto declarativo por perfil (`Profile`) y el shell
solo lee `profile.accent.*` / `profile.nav` / etc.

```ts
export interface Profile {
  id: WorkspaceMode;
  label: string;        // "Modo RD"
  shortLabel: string;   // "RD" (badge mobile)
  tagline: string;      // descripcion de 1 linea bajo el selector
  footerLabel: string;  // "Reduciendo Dano"
  navTitle: string;     // titulo de la seccion editable del nav
  selectorIcon: LucideIcon;
  footerIcon: LucideIcon;
  accent: {
    selectorActive: string; // clases del boton selector activo
    accentText: string;     // color del icono de nav activo
    editBadge: string;      // badge "edit" junto al label
    mobileBadge: string;    // badge de perfil en el header mobile
    footerIcon: string;     // color del icono en el footer
  };
  nav: NavItem[];
  hidden?: boolean; // true = no aparece en el selector de workspace
}
```

Perfiles actuales: `rd`, `studio`, `cultura` (visibles, selector de
workspace) y `rd-plano` (`hidden: true`, perfil de distribucion, ver seccion 3).

### Agregar un perfil nuevo

1. En `web/src/data/profiles.ts`: agregar el `id` a `WorkspaceMode`, definir
   su `NavItem[]` (que vistas de `AppView` incluye), y agregar la entrada en
   `PROFILES` con label/tagline/accent/nav. Elegir un color Tailwind que no
   choque con los existentes (emerald=rd, violet=studio, amber=cultura,
   sky=rd-plano).
2. Si el perfil necesita una vista (`AppView`) nueva que no existe: agregarla
   al union type `AppView` y registrar el panel en `App.tsx`
   (`{view === 'x' && <XPanel />}`).
3. No hace falta tocar `AppShell.tsx`: lee todo de `profiles.ts`.
4. Si el perfil es de distribucion (no debe aparecer en el selector normal),
   marcar `hidden: true`. Sigue siendo alcanzable por `?perfil=<id>` o
   localStorage, solo queda afuera de `VISIBLE_PROFILES`.

### Persistencia y seleccion

Orden de resolucion (`resolveInitialProfileId` en `profiles.ts`):
`?perfil=<id>` en la URL > `localStorage['flujo.perfil']` > default `rd`.
Un id invalido en cualquiera de las dos fuentes cae al default sin romper.
Al resolver un perfil desde la URL, o al cambiarlo a mano con el selector,
queda persistido en localStorage (un link `?perfil=studio` mandado una vez
"pega": desde ahi ese navegador recuerda `studio` aunque se saque el
parametro de la URL).

## 2. El bundle standalone de Plano/Rider

Objetivo: un solo archivo `.html` que se abre con doble click, sin backend,
sin instalar nada, para compartir con alguien fuera del equipo.

### Generarlo

```bash
cd web
npm run build:plano
```

Esto corre un build de Vite **separado** del build normal del hub (config
propio, `web/vite.plano.config.ts`, entry `web/plano.html` ->
`web/src/mainPlano.tsx`), y copia el resultado a:

```
dist_compartir/plano_rd.html
```

Esa carpeta esta en `.gitignore` (`dist_compartir/`) -- es un artefacto de
build, no se commitea. Regenerar el archivo cuando se necesite mandarlo de
nuevo (ej. despues de un cambio en `PlanoTool.tsx` o en los packs).

`npm run build:context` (el build normal del hub) NO se toca por esto: usa
`vite.config.ts` a secas, sin el entry de plano. Los dos builds son
independientes a proposito.

### Compartirlo

Mandar `dist_compartir/plano_rd.html` como archivo (mail, Drive, WhatsApp).
La persona lo abre con doble click en cualquier navegador moderno. No
necesita Python, ni Node, ni conexion a internet para la herramienta en si
(ver excepcion del boton "Motor Python" abajo).

### Que puede hacer la persona que lo recibe

- Usar el editor de Plano/Rider completo: elegir pack (Informativo / Testeo /
  Completo), armar el layout, exportar el rider como Markdown/print, generar
  el checklist de requerimientos.
- Editar el **precio** de cada pack desde un panel de configuracion arriba de
  la herramienta (sin recompilar). El precio editado se usa de inmediato en
  toda la herramienta (selector de pack, desglose, export).
- Exportar su configuracion actual (precios editados) como un archivo
  `.json` (boton "Exportar configuracion") para respaldarla o mandarla de
  vuelta.
- Importar un archivo de configuracion `.json` (boton "Importar
  configuracion") para aplicar cambios que le mandes. Un archivo invalido o
  de otra version NO rompe nada: se muestra un aviso y no se aplica ningun
  cambio.
- Ver, como referencia, la lista de productoras RD embebida en el archivo.

### Que NO puede hacer (y por que)

- **No puede agregar iconos nuevos al catalogo de simbolos**, ni **guardar
  presets de layout por productora** (ej. "Dame = 2 stands de testeo + 1
  informativo al centro"). Estas dos features se evaluaron en la sesion del
  2026-07-25 y estan bloqueadas: `PlanoTool.tsx` no expone props ni contexto
  -- es un componente sin parametros que guarda su `elements` (el layout) en
  estado interno, sin forma de leerlo/escribirlo desde afuera, y el catalogo
  de simbolos (`SYMBOL_CATALOG`, `renderSymbolGlyph`, `symbolIconMarkup`) es
  un switch hardcodeado dentro del mismo archivo. `PlanoTool.tsx` estaba
  fuera de alcance para editar en esa sesion (otro agente lo tenia tomado
  agregando iconos nativos). El formato de configuracion
  (`web/src/data/planoConfig.ts`) ya reserva los campos `customSymbols` y
  `presets` para cuando esto se desbloquee -- no se pierden datos si alguien
  ya los llena a mano en el JSON, pero la UI de esta version no ofrece
  botones para editarlos porque no harian nada real.
  - **Propuesta concreta para desbloquear** (para quien toque
    `PlanoTool.tsx` despues): agregar props opcionales
    `initialElements?: Element[]` + `onElementsChange?: (els: Element[]) => void`
    (desbloquea presets: leer/escribir el layout desde afuera sin mover el
    estado fuera del componente) y un prop opcional
    `customSymbols?: { key: string; label: string; color: string; lucideIcon: string }[]`
    consumido como fallback en `renderSymbolGlyph`/`symbolIconMarkup` antes
    del caso `default` (desbloquea iconos custom, reusando
    `lucide-react` que ya esta en el bundle -- nunca dibujar SVG a mano).
- **No tiene acceso a nada del resto del hub**: no hay Dashboard, Jobs,
  Intake, Cotizacion, SVG Studio, Studio/Eventos ni Cultura en este bundle
  (el entry point `mainPlano.tsx` solo importa `PlanoStandalone` ->
  `PlanoTool`, asi que Vite los deja afuera por tree-shaking). Verificado
  con `grep` sobre el HTML generado: 0 apariciones de "Intake", "Cultura",
  "Jobs", "psicosis", "tapiz", nombres de los otros paneles.
- **El boton "Motor Python" de `PlanoTool` no funciona sin backend** (llama a
  `/api/plano/render`, que solo existe corriendo `py -m flujo app`).
  `PlanoTool.tsx` ya maneja esto: si `window.location.protocol === 'file:'`
  usa el modo demo local directamente; si el fetch falla por cualquier otro
  motivo, atrapa el error y lo muestra como texto en pantalla en vez de
  romper la app. El resto de la herramienta (armar el plano, exportar,
  precios) no depende de ese boton.

### Precios de packs: como funciona el override sin backend

Los montos reales viven en dos lugares que deben coincidir manualmente
(`src/flujo/plano/packs.py` para el motor Python, `web/src/rdBrand.ts` para
el hub): 250.000 / 300.000 / 500.000 para Informativo / Testeo / Completo.
`PlanoTool.tsx` lee `PACKS[pack].precio` en vivo en cada render (no lo copia
al importar), asi que `web/src/rdBrand.ts` expone
`applyPackPriceOverrides(overrides)`, que **muta** el objeto `PACKS` en su
lugar. Esa funcion nunca se llama sola -- solo el entry `mainPlano.tsx` la
invoca, con los valores guardados en `localStorage['flujo.planoConfig']`,
antes de montar React. El bundle del hub normal (`main.tsx` -> `App.tsx`)
nunca la llama, asi que los precios de codigo quedan intactos ahi.

### Productoras RD embebidas

Fuente real: `data/productoras/*.json` (20 archivos, versionados en el repo,
NO gitignored -- `data/rd.db` si lo esta, es una proyeccion regenerable de
esos mismos JSON via `src/flujo/rd/database.py`). El slug de cada productora
es el nombre de archivo sin extension; el nombre viene del campo `"name"`.
El snapshot entregable se regenera con `tools/gen_rd_standalone.py` desde la
misma allowlist que usa el hub y queda en `web/src/data/rdDbEmbebida.json`.
`web/src/data/productoras.ts` solo adapta esa proyeccion para Plano/Rider; no
mantiene otra lista manual. Es solo de referencia visual en este bundle --
todavia no se puede asociar un preset de layout a una productora (ver
"Que NO puede hacer" arriba).

## 3. Archivos involucrados

| Archivo | Rol |
|---|---|
| `web/src/data/profiles.ts` | Perfiles del hub (Parte 1-2) |
| `web/src/components/AppShell.tsx` | Shell que consume `profiles.ts`, sin ternarios de modo |
| `web/src/data/planoConfig.ts` | Config versionada del bundle standalone (precios, placeholders de iconos/presets) |
| `web/src/data/productoras.ts` | Adaptador `{slug, name}` de `rdDbEmbebida.json` |
| `web/src/rdBrand.ts` | `applyPackPriceOverrides` / `resetPackPrices` / `PACKS_DEFAULT_PRICES` |
| `web/src/components/PlanoStandalone.tsx` | Panel de configuracion + `<PlanoTool/>`, sin tocar `PlanoTool.tsx` |
| `web/src/mainPlano.tsx` | Entry point separado (tree-shaking deja afuera el resto del hub) |
| `web/plano.html` | HTML de entrada del bundle standalone |
| `web/vite.plano.config.ts` | Config de Vite separado (`outDir: dist-plano`) |
| `web/scripts/copy-plano-share.mjs` | Copia el build a `dist_compartir/plano_rd.html` |
