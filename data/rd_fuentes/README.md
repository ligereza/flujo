# RD source evidence

This directory stores controlled machine-readable projections from RD
research. It is not a public claim store and it is not a replacement for the
canonical RD content files.

## Imported evidence

- `testeo_eventos_2025_evidence.json` preserves the 2025 workbook as source
  evidence: sheet names, source rows, repeated headers, duplicate candidates,
  raw wording, color observations, source hash, and review queues.
- `candidates/` contains research registries and relation candidates from the
  isolated RD work. They remain candidate material until an RD human gate
  approves their use.

The original workbook is intentionally not copied into the repository. Its
SHA-256 is preserved in the evidence JSON and in the generated SQLite
projection.

## Safety boundary

A colorimetric observation is a presence signal only. It does not establish
identity, purity, dose, quality, or safety. The event-to-venue and
event-to-producer queues remain unlinked until an explicit evidence-backed
human review. No public endpoint should expose these tables without a separate
allowlist and publication gate.

## Projection

`src/flujo/rd/database.py` imports this evidence into isolated `testeo_*`
tables in the regenerable `data/rd.db`. It does not insert rows into the
accumulative `data/rd_datos.db` tables and does not alter `data/rd_datos_demo`.
