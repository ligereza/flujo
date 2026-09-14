# RD matrix semantic scrape

Date: 2026-08-11
Crawler: Firecrawl
Scope: selected public pages from reduciendodano.cl
Raw result: rd_firecrawl_matriz_2026-08-11.json

## Result

The focused crawl completed 80 pages. It includes substance sheets, testing guides, reagent pages, selected testing products, the guided testing page, and related research articles.

The crawl still contains some residual shop and supplement pages because the public WordPress route structure exposes related links during discovery. Those pages are preserved as source evidence but must not be treated as direct substance associations without a human review.

## Entity coverage

The matrix contains 14 entities. The public site currently has direct substance sheets equivalent to these matrix entries:

- cannabis / marijuana;
- LSD;
- psilocybin / mushrooms;
- MDMA / ecstasy;
- ketamine;
- Tusi;
- GHB / GBL;
- cocaine;
- benzodiazepines;
- amphetamines;
- methamphetamine.

The site also has a separate MDA sheet, which is not yet a row or column in the supplied matrix.

Alcohol, poppers, and Viagra do not appear as equivalent standalone substance sheets in the focused result. They do appear in articles or interaction contexts, especially the alcohol and poppers articles and the Viagra interaction with poppers.

## Useful semantic relations

### Substance to substance

- MDMA <-> MDA: a dedicated relation is already supported by the MDA sheet, the MDMA sheet, and reagent guidance. The planned post can become a first-class relation rather than a disconnected article.
- Popper <-> Viagra: the site contains a specific high-priority interaction article.
- GHB <-> alcohol: the Chemsex article and GHB sheet treat this as a central interaction.
- GHB <-> ketamine: the Chemsex article identifies the combination as a depressant-risk relation.
- MDMA <-> caffeine and cocaine <-> caffeine: an interaction article exists and can be stored as a related, external-to-matrix relation.

### Substance to reagent

- MDMA: Marquis, Froehde, Simon's, and Mecke appear in the testing material; Simon's is especially relevant to the MDMA/MDA distinction.
- MDA: Simon's and Robadope are present in the reagent guidance; this should be validated against the final RD testing protocol before publication.
- LSD and mushrooms: Ehrlich and Hofmann are central; Marquis is used as a complementary or exclusion step in the mushroom guide.
- Cocaine: Morris and Liebermann are linked as primary and secondary testing paths.
- Ketamine: Morris is central, with Marquis, Liebermann, and other complementary reagents in the kit material.
- Amphetamine and methamphetamine: Marquis, Simon's, Robadope, and Mecke appear in the guides.
- Tusi / 2C-B: Marquis, Froehde, Robadope, and Zimmermann appear across the testing material.
- Benzodiazepines: the benzodiazepine strip and Zimmermann-related material appear as distinct testing resources.
- Cannabis: a THC/CBD reagent product is present.
- GHB: RD explicitly states that its ordinary colorimetric reagents do not detect GHB or GBL; there is a specific beverage test product. This must be represented as a limitation, not as a missing link.

## Proposed relation record

Each relation should preserve the distinction between evidence types:

```text
relation_id
entity_a
entity_b
relation_type
matrix_level
evidence_urls[]
research_urls[]
post_urls[]
testing_urls[]
product_urls[]
testing_limitations[]
status
last_reviewed
human_gate
```

`relation_type` may be `interaction`, `comparison`, `test_path`, `context`, or `absence_or_limit`.

`matrix_level` must remain separate from the article's wording. A yellow or red cell is a visual classification from the supplied matrix; it is not automatically a medical conclusion.

## First implementation set

The first records to normalize should be:

1. MDMA <-> MDA;
2. GHB <-> alcohol;
3. popper <-> Viagra;
4. cocaine <-> ketamine;
5. MDMA <-> caffeine;
6. GHB <-> ketamine;
7. ketamine <-> methamphetamine;
8. Tusi <-> MDMA.

This set covers comparison, interaction, reagent limitation, and content that already exists in the RD site.

## Important content boundary

Colorimetric testing should be stored as `probable_presence`, not chemical certainty. The scraped material repeatedly states that reagents do not quantify dose or purity and that a negative reaction does not prove that a sample is safe or inactive.

The interactive table should therefore expose both the visual risk level and the evidence limitation. It should never turn a product link into an implied recommendation or a test result into a guarantee.
