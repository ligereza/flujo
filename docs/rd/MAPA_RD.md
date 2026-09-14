# MAPA RD — qué hay, quién lo usa, cómo se abre

Entrada de la línea `rd`. Si llegaste acá sin contexto, esto alcanza.

RD es una ONG de reducción de daños. Este repositorio le da tres cosas: un
**plano de intervención en terreno**, una **cotización** y una **base de datos
de productoras y venues**. Todo lo demás del repositorio es de otras áreas.

---

## 1. Lo que se entrega, y a quién

Nada de esto necesita instalar nada, ni abrir una consola, ni tener internet.
Son archivos que se abren con doble clic.

| archivo | para quién | qué hace |
|---|---|---|
| `dist_compartir/plano_rd.html` | encargada de eventos | Arma el plano del stand, exporta el SVG y el rider en PDF, guarda su trabajo como preset |
| `dist_compartir/herramientas_rd.html` | encargada / dirección | Base de datos, cotización, eventos y lectura de pedidos |
| `docs/rd/propuesta_directiva.html` | la directiva | Qué ofrece RD, qué tiene y qué hay que aprobar |

**Se regeneran así** (esto sí es consola, y es del director):

```bash
py tools/gen_rd_standalone.py     # hornea la base de datos adentro
cd web && npm run build:rd        # -> herramientas_rd.html
cd web && npm run build:plano     # -> plano_rd.html
py tools/gen_propuesta_directiva.py --out docs/rd/propuesta_directiva.html
```

---

## 2. El ciclo del plano, que es el que más se usa

1. La encargada abre `plano_rd.html` y arma el layout.
2. Exporta el **SVG** para el diseño y el **rider en PDF** para el recinto.
3. Aprieta **Guardar preset**: baja un `.json` con dónde puso cada cosa, el
   evento, el pack, el tema y los símbolos que ella misma creó.
4. Manda ese archivo. El director lo asocia a la productora en la base y se lo
   devuelve.
5. Ella lo abre con **Abrir preset** y sigue trabajando desde ahí.

**Puede agregar sus propios símbolos** sin pedirle nada a nadie: sube un `.svg`,
o una imagen que el archivo traza solo. El símbolo queda en su navegador y viaja
dentro del preset.

Lo único que el archivo suelto NO hace es escribir en el repositorio. Para que
un símbolo quede en el catálogo de todos hace falta la aplicación completa.

---

## 3. Dónde vive cada cosa

| ruta | qué es |
|---|---|
| `data/productoras/*.json` | La base: una productora por archivo. **Fuente de verdad** |
| `knowledge/venues/*.yaml` | Los recintos |
| `knowledge/logos/` | Los logos, con su ficha |
| `data/rd_packs.json` | La tarifa de los tres packs de terreno |
| `data/cotizacion_servicios.json` | Los ítems de la cotización: diseño, impresión, digital |
| `data/plano_simbolos.json` + `data/plano_simbolos/` | Los símbolos propios del plano |
| `data/piezas_tipos.json` | Los tipos de pieza: flyer, contraportada, pendón… |
| `svg/suplementos_rd/_master_contraportadas.json` | El texto de las contraportadas |
| `svg/suplementos_rd/09_contraportadas_dark/` | Las 8 contraportadas generadas |
| `svg/eventos_rd/` | Los packs de servicio en SVG |
| `src/flujo/rd/` | La base de datos como código: proyección, consultas, panel |
| `src/flujo/plano/` | El motor del plano y el trazador de imágenes |
| `src/flujo/eventos/` | Flyers, descarga de Instagram y render en Blender |
| `docs/rd/` | Documentación del área y la propuesta a la directiva |

**Todos los archivos de `data/` se editan a mano.** No hay que tocar código para
cambiar un precio, un símbolo o un tipo de pieza. Cada uno lleva sus
instrucciones adentro, en castellano.

---

## 4. Los comandos, si estás en consola

```bash
py -m flujo app                       # la aplicación completa, en el navegador
py -m flujo suplementos list          # los 8 productos reales
py -m flujo rd-db build               # reconstruye data/rd.db desde las fuentes
py -m flujo rd-db productora <nombre> # qué se sabe de una productora
py -m flujo brief paquete-cotizacion jobs/<job>
py -m flujo eventos flyer-auto "<link de instagram>"
```

---

## 5. Reglas del área que no se negocian

**El texto de los suplementos lo manda el encargado de RD, y su archivo gana.**
Nunca se inventa un nombre de producto, ni se buscan propiedades, ni se escribe
una descripción. Hubo cuatro productos inventados viviendo en el código como si
fueran reales; por eso existe esta regla.

**Todo lo que lee una persona va en castellano correcto, con tildes y eñes.**
Un título que diga "reduciendo dano" no es un error de tipeo.

**El rider no lleva contactos.** Es una orden del área, y el endpoint que arma
los datos tiene una lista blanca campo por campo para que un dato de contacto no
se filtre solo. Los archivos que se entregan se generan con esa misma función:
si mañana alguien agrega un campo de contacto, no sale por la puerta de atrás.

**Ningún elemento afirma un dato que no tiene.** Si una productora no está
confirmada, dice que no está confirmada. Si un logo falta, dice que falta.

---

## 6. Lo que falta, dicho de frente

- **Los logos**: 6 de 20 productoras tienen el logo en vector. El resto está
  pendiente, y el material está en el disco del director.
- **La triangulación**: de 7 eventos registrados, sólo 1 tiene fecha y line-up
  completos. Sin las dos cosas no se puede cruzar quién organizó qué.
- **Asociar un preset a una productora** se hace a mano contra la base; no hay
  todavía un paso automático.
