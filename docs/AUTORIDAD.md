# Document authority in MAK

> Registro de una medición histórica (2026-08-28), no contrato vigente. La
> autoridad actual es `/home/mak/AGENTS.md`; el estado se obtiene con
> `.venv/bin/python tools/mak_status.py`.

Measured and written 2026-08-28. This file exists because **nine documents in
this repo declared themselves canonical and the loader reads three.**

Language: English, ASCII. `AGENTS.md` is the current contract for operational metadata, and
the well-formed operational documents of this repo already comply -- see
`docs/admissibility.md`, `context/OBJECTIVE_AUDIT.md`,
`context/OWNER_MANIFEST.md` and `context/DEPENDENCY_SURFACE.md`, all English
with zero non-ASCII characters. The first version of this file was Spanish with
diacritics, which was the wrong side of the same rule it was written to enforce.

## The real read order

The current entry point is `/home/mak/AGENTS.md`, followed by a machine measurement:

```
AGENTS.md -> .venv/bin/python tools/mak_status.py -> context/HANDOFF_HISTORICO.md
```

That is the authority. It is not this file's recommendation: it is what an agent
receives at start. Every other document in the repo is one of three things --
dated evidence, domain doctrine, or a navigation index -- and none of the three
is promoted to authority by writing "canonical" in its header.

## The nine that claimed authority

| Document | Claimed | What it actually is |
|---|---|---|
| `AGENTS.md` | "This file is canonical" | **Historical row.** The current contract is the root file. |
| `docs/MAK_CURRENT_STATE.md` | "Fuente canonica de orientacion" | **Authority. Correct.** #2 in the order. |
| `context/LAST_HANDOFF.md` | continuity | **Authority. Correct.** #3 in the order. |
| `docs/MAK_SYSTEM_DIRECTIVE.md` | "canonical direction for agents as of 2026-08-25" | **Mission doctrine.** Says what MAK wants to become, not what it is. Not in the order. |
| `docs/system_learning/master/action_plan.md` | "plan maestro unico de accion" (894 lines) | **Evidence from one session.** Its own first section admits a single commit versioned it. |
| `docs/INFLECTION_POINT_ARTISTIC_ARCHIVE_2026-08-24.md` | "decision arquitectonica vigente" (530 lines) | **Dated record of a direction change.** Good as the history of why. |
| `docs/PORTAFOLIO_PRODUCCION.md` | "doctrina de trabajo desde 2026-08-28" (647 lines) | **Domain doctrine**: how a portfolio is produced. Does not govern the rest of MAK. |
| `MAPA.md` | command map | **Generated index.** Useful and honest: zero broken paths, zero prose figures. |
| `CAPACIDADES_FLUJO.md` | master registry (79 KB) | **Tool inventory.** See below: the one that lies most, and because of how it is written. |
| `context/MD_CONTEXT_MASTER.md` | "this file is the consolidation layer" | **Navigation index.** |
| `PLAN.md` | "Plan Maestro -- ISKVW" | **Historical (2026-07-20).** Business context, not technical state. Gitignored at `.gitignore:230`. |
| `context/PHASE_REPORTS_INDEX.md` | gave a fourth list of truth sources | **Corrected 2026-08-28**: it now repeats the bootstrap order instead of inventing its own. |

## Why it rots: the measurement

Claims were extracted from the twelve documents and each was classified by
whether a machine can decide if it is true. **653 claims:**

| Class | Count | Verifiable |
|---|---:|---|
| Cites a path that exists | 200 (31%) | today, untouched |
| Cites a name with no path | 229 (35%) | only if given the path |
| Cites a broken path | 57 (9%) | already false |
| Figure written in prose | 29 (4%) | rots on its own |
| State in prose (`VIVO`, `integridad OK`, `activo`) | 138 (21%) | **never** |

Per document, what matters:

```
CAPACIDADES_FLUJO.md                     95 ok   143 no path   15 broken   17 figures   116 states
docs/SCRIPTS_INVENTORY.md           6 ok    27 no path   26 broken    0 figures     3 states
docs/MAK_CURRENT_STATE.md          38 ok     8 no path    4 broken    3 figures     6 states
docs/PORTAFOLIO_PRODUCCION.md      15 ok    12 no path    7 broken    8 figures     0 states
MAPA.md                             6 ok     0 no path    0 broken    0 figures     2 states
AGENTS.md                           historical row; current contract is measured at the root
```

The last two rows are the conclusion. The root contract and machine measurement
are intentionally kept outside this historical comparison.
-- not because anyone maintains them, but because they are written in a form
that does not admit a lie: full paths, zero prose figures. `CAPACIDADES_FLUJO.md`
carries 116 prose states and is therefore architecturally unverifiable.

Repo-wide, over the 348 tracked `*.md` files: **79 references point at files
absent from the whole tree**, and another 66 exist but are written relative
without a root anchor.

## The rule

1. **A document outside the read order does not use the words "canonical",
   "vigente", "maestro" or "unico".** It declares its domain and its date.
2. **Every file reference carries its path from the repo root.** A bare name
   (`hub.py`, `copilot.py`) is not a reference: this repo has two `hub.py`,
   with 121 and 50 endpoints.
3. **No measured figure is written without its measurement date.**
   `tests/test_higiene_docs.py` already enforces this for the suite total, the
   invariant range and the version.
4. **A prose state (`VIVO`, `activo`, `integridad OK`) states next to it how it
   was checked**, or it is not written.
5. **Operational metadata is English ASCII** (`AGENTS.md`, Language section).
   Human-facing RD and Portfolio material keeps correct Spanish with diacritics.

### The gates exist and have two measured blind spots

`tests/test_higiene_docs.py` already enforces rules 3 and 4 in part, and was
born (2026-07-25) of the identical failure: `context/WALKTHROUGH.md` claimed a
version four minors behind what `pyproject.toml` said. Two holes verified
2026-08-28:

| Gate | Escapes when | Real example |
|---|---|---|
| `test_la_version_afirmada_coincide_con_pyproject` | the figure follows a colon and a `v` (`Version:` + `v` + number) instead of the word "version" followed by the number, or `v` + number + ` live` | `docs/SCRIPTS_INVENTORY.md:3` held a version four minors stale for 41 days with the gate green |
| `test_ningun_doc_vivo_afirma_el_total_de_la_suite` | the line does not also carry a scope word (`suite`, `green tests`, `0 rojos`) | a line reading "Python 3.11, CLI Typer, N tests" passes unseen |

Neither is a design error: the gate required a co-occurrence to avoid false
positives on historical deltas, which are dated facts and do not rot. The price
is that a claim can escape on punctuation. Widening them edits tests, so it is
declared below and not done here.

The concrete cause of rule 2: the `auditar_capacidades_mak` audit left its only
list of retirement candidates pointing at **line numbers** in `CAPACIDADES_FLUJO.md`
(`rows 391, 413, 425, 426, 428, 430`). It was already broken when written --
391 and 413 are prose lines -- and every row added since pushed it further. A
complete audit was made unusable by its addressing.

### The language ratchet already exists

`tools/idioma.py` classifies comments and docstrings of every tracked `*.py` as
es/en/mixed/none, and `tests/test_idioma_ratchet.py` pins the Spanish-carrying
set at `tests/fixtures/idioma_baseline.txt`. It never fails when the count goes
down. Measured 2026-08-28 over 1039 tracked files: **405 carrying Spanish, 435
English, 49 mixed, 199 with no language evidence.**

The pin was tightened by hand from 406 to 405 on 2026-08-28, after
`cultura/mak_plataforma/hub.py` left the Spanish-carrying set. The ratchet's own
docstring says it only tightens by hand; leaving a cleaned file in the pin means
the ceiling stops describing the tree.

It measures Python comments only, never identifiers, never product strings and
never Markdown. Markdown compliance with rule 5 is unenforced, which is how this
file was born in Spanish -- the first version of the very document that states
the rule broke it.

## Corrected on 2026-08-28

| Document | Claimed | Measured |
|---|---|---|
| `context/PHASE_REPORTS_INDEX.md` | 748 PHASE files, "untracked" | 13 files, all tracked |
| `docs/SCRIPTS_INVENTORY.md` | four minors behind; `checkpoint.sh` nonexistent; `scripts/app.py` active; legacy under `_archive/**` | version matches `pyproject.toml`; `checkpoint.sh` exists and `src/flujo/airdrop.py` invokes it; `app.py` does not exist; `_archive/` did not exist |
| `CAPACIDADES_FLUJO.md` | 4 databases with "integridad OK" under `research/**` and `labs/**` | neither tree exists |
| `CAPACIDADES_FLUJO.md` | `mak_knowledge.db` 35 tables / 387.089 rows | 48 tables / 387.104 rows per `tools/repo_audit.py`, which runs in CI and excludes SQLite internal tables |
| `CAPACIDADES_FLUJO.md` | runbooks at `xio/RUNBOOK.md` | were absent locally; **restored 2026-08-28** from `/home/mak/WIN/flujo/xio/` |
| `docs/GLOSSARY.md` | Spanish comments outnumbering English several times over (2026-07-30) | inverted, per `tools/idioma.py` over 1039 tracked files: 405 carrying Spanish, 435 English, 49 mixed, 199 with no evidence |
| `README.md` | 113 bytes, an ASCII image and nothing else | real entry point with the read order and a minimal map |

## Restored, not deleted

Four operational documents were missing from `/home/mak/flujo` while four active
documents cited them -- nine dangling references, including the show-day
runbook. They existed only in `/home/mak/WIN/flujo/xio/`, and they were not
stale: `xio/FACES.md` is byte-identical in both trees, so WIN never diverged.
Copied with `cp -p`; the legacy tree was not modified.

`xio/RUNBOOK.md` (23 KB), `xio/HOTSPOT_SHOW_RUNBOOK.md`, `xio/XIO_CAPABILITIES.md`,
`xio/PLAN_SERVICIOS_SIN_ROOT.md`.

## Declared and not executed

All of the following requires touching code, tests or workflows, not files:

- ~~Airdrop chain~~ **done 2026-08-28.** Retired whole: the module, the email
  channel in `intake/reception.py`, six scripts, the workflow, the Typer sub-app
  and 194 lines of `cli.py`, plus five test files. It had been dead since
  2026-08-14 12:44. Detail in `docs/SCRIPTS_INVENTORY.md`.
- **Three independent portfolio implementations.**
  `cultura/mak_plataforma/contrato_archivo.py`,
  `tools/portfolio/generar_works.py`, `src/flujo/knowledge/portfolio_*.py`. They
  share no data path. 14 suites, ~200 tests, three incompatible definitions of
  "obra".
- **Ten endpoint names implemented twice.** `cultura/mak_plataforma/hub.py` (:8900) is a frame that embeds the other in an iframe and proxies research and codex; `src/flujo/web/hub.py` (:8765) is the workspace app. They are not duplicates -- an earlier version of this file said they were, from counting endpoints without opening either. What is duplicated is ten endpoint names implemented separately in both: `/api/status`, `/api/organismo`, `/api/research/{job,jobs,catalog}`, `/api/project/{context,learning,probe,route}`, `/api/rd/topics`. Two implementations of one contract, free to diverge.
- **Two skill trees with different owners.** `.claude/skills/` is the
  versioned/runtime skill tree and is the canon for the shared RD generators;
  `.agents/skills/` contains additional local skills. The 8 byte-identical
  skill assets formerly under `.agents/skills/` were consolidated into the
  `.claude/skills/` paths, and the remaining `.agents` skill documents now
  point there. The two trees still exist because their unique skill sets are
  different; they are not two copies of one implementation.
- **`xio/new-plugins/` vs `xio/new/plugins/`.** `xio/new/server.py` does
  `from plugins import PluginRegistry` and its comment declares the priority
  `PLUGINS_DIR` -> `xio/new-plugins`. Runtime resolution, not a file problem.
- **The two blind spots in `tests/test_higiene_docs.py`** above. Closing them
  widens two regular expressions in a test.
- **`data/ssd_evidence/ties_full.db` (3.4 MB) stays out of Git**, excluded by the
  global `*.db` rule at `.gitignore:187`. That rule is right -- databases do not
  belong in history -- but `data/ssd_evidence/MANIFEST.json` describes this
  directory as a durable copy so the portfolio chain would not depend on a
  scratch tmp. With the database unversioned the promise is half kept: the two
  JSON inputs travel, the ties database does not. Either the chain declares it
  optional or the file needs a storage decision outside Git.
- **A Markdown language gate.** Rule 5 has no instrument. `tools/idioma.py`
  covers `*.py` only.
- **`docs/MAK_CURRENT_STATE.md`** is #2 in the read order and carries 275
  non-ASCII characters in Spanish prose, against the historical rule. It
  also cites 4 dead paths, two of them PHASE files that no longer exist.
  Correcting the second authority deserves its own pass.

## The scope error this document was also built on

Every figure above measures `/home/mak/flujo`. MAK is `/home/mak`. See
`docs/MAK_ORGANISMO.md`, which measures the machine and records the finding
that outranks all document hygiene: **the organism has been paused since
2026-08-14 19:03 and no document said so.**

## Retirement condition

When the read order is generated from the repo and no document outside it
declares itself canonical, this file is unnecessary. While it exists, it is the
tie-breaker.
