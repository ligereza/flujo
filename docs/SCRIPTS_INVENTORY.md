# Script inventory

Measured version: **0.56.1** (`pyproject.toml` + `src/flujo/version.py`),
verified 2026-08-28 against `ls scripts/`, `Makefile`,
`.github/workflows/*.yml` and a grep for invokers across `src/`, `tools/`,
`cultura/` and `scripts/`.

This inventory keeps agents from mistaking a legacy wrapper for the live core.
Every row declares its invoker so the claim is checkable: if the column says
`Makefile`, then `grep -n <script> Makefile` must return something.

Language: English ASCII, per the Language section of `agents.md` for operational
metadata.

## The 24 scripts, measured

A script with NO INVOKER is not dead: it may be a utility a person runs by hand.
What the column asserts is that no `Makefile`, workflow or module calls it --
that nothing will exercise it on its own.

| Script | Measured invoker |
|---|---|
| `piezas_generar.py` | `render_piezas_vectoriales.yml`, `Makefile`, `brief_to_project.py` |
| `flujo.py` | `src/flujo/version.py`, `flujo_health.py`, `generar_catalogo_rd.py` |
| `flujo_daily.py` | `Makefile`, `abrir_dashboard.sh`, `nuevo_pedido.sh` |
| `hub_smoke.py` | `src/flujo/cli.py` |
| `abrir_dashboard.sh` | `Makefile`, `nuevo_pedido.sh` |
| `flujo_pipeline.py` | `Makefile`, `nuevo_pedido.sh` |
| `flujo_health.py` | `render_piezas_vectoriales.yml` |
| `piezas_check_outputs.py` | `render_piezas_vectoriales.yml` |
| `flyer_create_project.py` | `Makefile` (`make new-flyer`) |
| `limpiar_basura.sh` | `Makefile` (`make clean`) |
| `setup.sh` | `Makefile` (`make install`) |
| `_common.py` | `flujo_health.py` |
| `backlog_list.py` | NO INVOKER |
| `brief_to_project.py` | NO INVOKER |
| `export_propuesta_pdf.py` | NO INVOKER |
| `find_duplicates.py` | NO INVOKER |
| `flyer_duplicates_report.py` | NO INVOKER |
| `flyer_set_input.py` | NO INVOKER |
| `generar_catalogo_rd.py` | NO INVOKER |
| `github_setup_labels.py` | NO INVOKER |
| `nuevo_pedido.sh` | NO INVOKER |
| `pdf_probe_basic.py` | NO INVOKER |
| `sanitize_sensitive.py` | NO INVOKER |
| `suggest_repo_hygiene.py` | NO INVOKER |

12 with an invoker, 12 with none. Five airdrop scripts and `checkpoint.sh` were retired 2026-08-28.

## Airdrop: retired 2026-08-28

The chain is gone. It had been dead since **2026-08-14**: at 12:41-12:44 that
day thirteen Codex commits ("chore: remove legacy instruction docs") deleted
the airdrop protocol document, and at 13:10 `032822b61` ("chore: remove
obsolete agent routes") cleaned the routes. The purge only touched `docs/`, so
the module, six scripts, a workflow, a CLI sub-app and 42 tests were left
standing for fourteen days. `_airdrop/` itself has **zero events in the whole
Git history**: it was a gitignored staging directory.

Removed on 2026-08-28 to
`/home/mak/_archive/orden-limpieza-20260828/por-razon/subsistema-retirado-20260814/`:
`src/flujo/airdrop.py`, `src/flujo/intake/reception.py` (the email channel,
called by nothing but its own tests), four `scripts/*airdrop*`,
`scripts/checkpoint.sh`, `.github/workflows/airdrop_gate.yml` and five test
files. 194 lines came out of `src/flujo/cli.py`: the Typer sub-app, eight
subcommands, `_validate_airdrop_or_exit` and the `flujo doctor` check that
reported `airdrop pendiente: OK -- no` while looking at a directory that does
not exist.

`datadrop` was never part of this: `grep airdrop src/flujo/datadrops.py` is
empty. Its "inverse airdrop" phrasing was an analogy and was reworded.

## Corrections against the previous version (2026-07-18)

| Previous claim | Measurement 2026-08-28 |
|---|---|
| version pinned four minors behind | real version is `0.56.1`, per `pyproject.toml` |
| "`finish_airdrop.sh` mentions checkpoint.sh, **already nonexistent**" | it existed and had **no invoker**. The first correction in this session claimed `src/flujo/airdrop.py` invoked it; that was a grep matching a docstring which says the opposite (`airdrop.py:380`: *"No depende de `bash` ni de `scripts/checkpoint.sh`"*). Retired 2026-08-28 |
| `scripts/app.py` listed as an active Web/dashboard script | **does not exist** |
| legacy archived in `_archive/legacy_20260703_1413/` | `_archive/` **does not exist**; the cited destination cannot be inspected |
| legacy archived in `_archive/legacy_20260718_0110/scripts_oneshot/` | same |
| airdrop protocol document | **does not exist** |
| "Detalle en the repository hygiene tests." | a sentence cut in half in the previous version |
| `generar_catalogo_rd.py` | exists in `scripts/` and was missing from the inventory |

The common cause: the inventory asserted state in prose and named files without
a verifiable path. That is why the table above carries an invoker column.

## Retired legacy wrappers

The `job_*.py`/`job_new.sh`, `privacy_*.py`, `project_*.py`,
`piezas_formatos.py`, `piezas_validate_config.py`, `piezas_add_component.py`,
`piezas_components.py`, `piezas_project_summary.py`, `flyer_from_email.py`,
`flyer_analyze.py`, `flyer_index*.py/.sh`, `flyer_status*.py/.sh`,
`flyer_latest.sh`, `flyer_list.sh`, `ig_download.py`, `ig_redownload.py`,
`rider_new.py`, `rider_presets.py` family, plus the one-shot `cleanup_*.sh/py`,
`flujo_clean_generated.py`, `soft_cleanup.py`, `cleanup_demo_artifacts.sh` and
`cleanup_ig_temp_folders.sh`, are no longer in `scripts/`.

**Where they went cannot be verified**: the two archive paths the previous
version cited (`_archive/legacy_20260703_1413/`,
`_archive/legacy_20260718_0110/`) do not exist. The CLI equivalence table is in
`docs/CLI.md`, section "Migracion desde scripts legacy". Use `flujo job`,
`flujo flyer-import`, `flujo analyze`, `flujo index`, `flujo ig-redownload`.

## CLI equivalent where one exists

| Script | Prefer |
|---|---|
| `flujo_daily.py` | `flujo daily` |
| `flujo_health.py` | `flujo health` |
| `flujo.py` | `flujo ...` |
| `brief_to_project.py` | `flujo brief to-project` |
| `piezas_generar.py` | `flujo render run` (the script stays live: `make render` and CI call it) |
| `flyer_create_project.py` | no direct equivalent; stays live through `make new-flyer` |

## Hygiene: it exists and nothing triggers it

Three scripts do exactly the cleanup work this repo needs and none has an
invoker:

- `find_duplicates.py` -- duplicates by content hash
- `suggest_repo_hygiene.py` -- flags files pointing at dead docs or dead code
- `sanitize_sensitive.py` -- replaces credentials with placeholders

`limpiar_basura.sh` is called by `make clean`, but it only removes
`__pycache__` and generated outputs.

## Rule for future script changes

If a change touches a legacy script, it must explain why it does not touch the
CLI at `src/flujo/cli.py` or the live module under `src/flujo/` first.

And if it adds a row to this inventory, the row declares an invoker or declares
NO INVOKER. There is no third option: prose without a path is what left this
document four minor versions stale with nothing noticing.
