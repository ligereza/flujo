# Ordering research snapshot

This is a durable snapshot of the read-only discovery workflow that preceded
the ordering policy. It is evidence for future classification, not an active
catalogue and not an automatic promotion of any project.

## Provenance

- Run: `wmff24999`
- Source session: Claude Code session `3428381a-02ad-4101-9da5-8176cf72c147`
- Date: 2026-08-23
- Scope: SSD index and MAK evidence used to identify artist, venue and VJ work
- Method: read-only local measurements plus external discography lookup
- Agents: 14 launched, 9 completed, 5 stopped by the Claude session quota
- Result: 7 identity records and 2 measurement probes; no synthesis agent result
- Rule: preserve evidence and abstain when a name, date or role is not resolved

The raw result lived under `/tmp/claude-1000/` and is not an authority by
itself. This snapshot records the durable conclusions and their limitations so
that a future run can resume the missing probes instead of silently repeating
or promoting them.

## Identity findings

| container | interpreted identity | confidence | durable reason |
|---|---|---|---|
| `LYON` | Lyon La F, music artist and VJ client | confirmed | Five named work folders match released 2025 singles; the work unit is the track. |
| `HARRY` | Harry Nach, music artist and VJ client | confirmed | `TITI`, `gta` and the Chillan visualizer evidence match the artist catalogue and press. |
| `DREFGIRA` | DrefQuila tour material for *Despues del Sol*, November 2025 | confirmed | `01 CDR.mov` maps to track 01 and the tour/date evidence agrees. |
| `MARLONLOLLA` | Marlon Breeze work for Lollapalooza Chile 2026 | confirmed | `Le Trap 4`, show audio and After Effects names agree with public release/event evidence. |
| `DREFMOVISTAR` | DrefQuila at Movistar Arena, 2025-11-02 | confirmed | Venue, date and event title were independently found in public sources. |
| `FELINA` | unresolved visual/logo project, not a music identity | unknown | The local material is a 2D/3D logo and jewelry build; no artist identity was established. |
| `SCD` | SCD venue project, likely Salas SCD | probable | Local repo venue geometry and theatre-plan tools agree; the exact SCD venue remains open. |

Names such as `CIUDAD`, `CORAZON`, `golden`, `LOGO` and `LOGO ENTREGA` were not
promoted to tracks. The workflow found no reliable catalogue match and local
structure suggests visual, asset or branding work. They remain candidates for a
later project-level review.

## Measurements preserved

The SSD index contains 917 projects and 45,536 assets. Applying the declared
source-anchor rule produced:

- 774 projects with only `.blend` anchors: 85.29 GB
- 43 projects with only `.aep`, `.psd`, `.ai` or `.svg` anchors: 159.63 GB
- 25 projects with both 3D and 2D anchors: 502.18 GB
- 75 projects with no declared source anchor: 193.61 GB

The existing `projects.dimensionality` value matches the 774-project 3D class
exactly. The important correction is that most substantial finished VJ work is
in the mixed class, while many small `.blend` files are downloaded or generated
assets rather than finished works.

The collaboration probe found repeated production families around DrefQuila,
Marlon/Lolla and Harry. For RD, `TABLA_RD` is the only explicit RD design
container found: 54 assets, about 2.14 GB, 2D-only with Illustrator anchors and
no `.blend`. A literal `RDFLYER` search returned 1,499 assets inside a mixed
download container, so that hit is not evidence of an RD cartelera project.

## Recovered probes from the quota cutoff

Two probes had already written their intermediate outputs before their agents
lost the final response. They were recovered from the read-only workflow
workspace and checked without rerunning the scan.

### SSD-to-IG/media reconciliation

The source state contains 2,034 indexed IG records: 1,818 records carry a
numeric media ID (1,599 distinct IDs) and 216 do not. The media join found:

- 1,591 IDs with one unambiguous file on one media surface;
- 8 IDs present on two different surfaces;
- 0 orphan IDs;
- 0 duplicate matches within the same surface.

The eight collisions are not eight duplicate works: each pairs a real `posts` or
`reels` file with its generated `_contact_sheets` derivative. They must remain
one record with a derivative relation, not be merged by deleting either file.
This gives the ordering system a safe join key, while the 216 records without a
numeric ID still need a different relation and remain unresolved.

### The `other` surface

The `other` surface contains 330 files: 300 JPG, 29 MP4 and one SRT. Geometry
alone gives 265 square or near-square files, 50 portrait files and 15 landscape
files. The videos include square, 9:16 portrait and 16:9 landscape material,
so `other` is a mixed media surface, not a semantic class.

All 330 filesystem mtimes fall between `2026-07-22T14:20:15` and
`2026-07-22T14:21:10`. That concentration is evidence of an export or copy
operation, not original creation dates. The ordering system must not use these
mtimes as artwork chronology.

## Incomplete work and safe continuation

The following subagents did not return because the Claude session quota ended:

- reconciliation
- histories
- `other`
- track key
- synthesis

The reconciliation and `other` measurements above are therefore complete as
bounded probes, but the history join, remaining track key and final synthesis
are still incomplete. No row should be promoted to authorship, publication,
consumer or postulation from this snapshot alone.

## Policy connection

`data/ordering_features.json` declares which observations may decide which
questions. `src/flujo/knowledge/feature_policy.py` enforces that declaration;
`src/flujo/knowledge/classification_queue.py` now consults it before emitting
automatic virtual-environment or content-identity proposals. A failed or
undeclared authority is a closed gate, not a reason to guess.
