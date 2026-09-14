# Three-plane local surface contract

This contract keeps three physical planes distinct while no material is moved:

- `windows_director` is the Windows director and creative workspace. It is a
  local authority for material that exists there.
- `mak_operational` is the MAK operational knowledge surface. It is a separate
  local authority for MAK material and evidence.
- `git_transport` is a reviewed transport and reproducibility projection. It
  is never runtime authority and cannot decide whether local material exists.

The contract is implemented by `flujo.knowledge.three_plane` and validated by
`schemas/knowledge/three_plane_manifest.schema.json`. It reuses the existing
knowledge boundary; it does not create a second database, ledger, graph, or
sync engine.

## Manifest rules

Each surface records its physical node, plane, owner, producer, root URI,
provenance, SHA-256 evidence, and transport eligibility. Hashes are computed
only for files explicitly supplied by the caller. Directories are never
scanned, and an omitted hash is marked `not_computed`; it does not mean empty,
current, or trusted.

The manifest has these permanent safety assertions:

- local surfaces precede the catalog and Git projection in authority order;
- Git is `projection_only`;
- bidirectional sync is false and the primary writer is not configured;
- materialization is `not_applied`, with zero copied files and no source writes;
- every transport path requires a human gate.

## Usage

Build a declaration without touching source material:

```text
py -m flujo.knowledge three-plane
```

Write a canonical ASCII manifest and hash explicitly listed evidence:

```text
py -m flujo.knowledge three-plane --output out/three_plane_manifest.json --artifact windows_director=path/to/evidence.json
```

Repeat `--artifact` for more files. This command does not copy, move, delete,
or update any source surface.
