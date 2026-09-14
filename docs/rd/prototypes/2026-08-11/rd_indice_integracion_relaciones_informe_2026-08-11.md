# Índice de integración por relación

Este índice conecta cada relación con sus distintas superficies de uso sin duplicar el grafo.

## Superficies

- `rd_pages`: fichas de sustancias o páginas propias de RD;
- `testing_guides`: guías de reactivos, tiras o procedimientos de testeo;
- `product_resources`: productos y recursos disponibles en la tienda;
- `research_posts`: research o contenido editorial relacionado;
- `scientific_sources`: fuentes externas utilizadas como apoyo de alcance o limitación;
- `other_sources`: URLs que todavía necesitan clasificación más fina.

## Regla de integración

POST puede leer `research_posts` y `rd_pages`.
Research puede leer `scientific_sources`, `testing_guides` y las notas de alcance.
La tabla web puede leer todos los grupos, pero debe mostrar el tipo de fuente.
La tienda puede enlazar `product_resources`, sin transformar el enlace en recomendación automática.

Ninguna de esas vistas puede cambiar `relation_type`, `status` o `evidence_contract`. Si una vista necesita otra interpretación, debe crear una propuesta separada y no sobrescribir el vínculo original.
