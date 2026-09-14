"""Deterministic AST import map for bounded pytest execution lanes.

The classifier is read-only. It records imports, not a test's complete
behavior; unresolved sources remain in ``review`` and never break collection.
"""
from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Iterable

REPO = Path(__file__).resolve().parents[1]
TESTS = REPO / "tests"
LANE_MAP_CONTRACT = REPO / "context" / "test_lane_map.json"
LANES = ("flujo", "mak", "integration", "repo_hygiene", "review")
_TREE_ONLY_WORDS = ("git", "repo", "tree", "docs", "readme", "handoff")


@dataclass(frozen=True)
class LaneRecord:
    lane: str
    imports: tuple[str, ...]
    reason: str


def _imports_and_text(path: Path) -> tuple[tuple[str, ...], str]:
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(path))
    except (OSError, SyntaxError):
        return (), ""
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return tuple(sorted(imported)), source.lower()


def _is_motor(name: str) -> bool:
    return name == "flujo" or name.startswith("flujo.") or name.startswith("src.flujo.")


def _is_local_box_import(name: str) -> bool:
    top = name.split(".", 1)[0]
    if _is_motor(name) or top in {"__future__", "tests"}:
        return False
    return (REPO / f"{top}.py").is_file() or (REPO / top).is_dir()


def classify(path: Path) -> LaneRecord:
    """Classify one test from AST imports, then bounded tree/git/docs signals."""
    imported, source = _imports_and_text(path)
    motor = any(_is_motor(name) for name in imported)
    box = any(_is_local_box_import(name) for name in imported)
    if motor and box:
        return LaneRecord("integration", imported, "imports motor and box layer")
    if motor:
        return LaneRecord("flujo", imported, "imports motor")
    if box:
        return LaneRecord("mak", imported, "imports box layer")
    stem = path.stem.lower()
    if any(word in stem or word in source for word in _TREE_ONLY_WORDS):
        return LaneRecord("repo_hygiene", imported, "no local import; tree/git/docs signal")
    return LaneRecord("review", imported, "mapping incomplete")


def build_test_lane_map(paths: Iterable[Path] | None = None) -> dict[str, LaneRecord]:
    """Make the in-process persisted map in one AST pass per test module."""
    selected = sorted(paths if paths is not None else TESTS.glob("test_*.py"))
    return {str(path.resolve().relative_to(REPO)): classify(path) for path in selected}


# Persisted assignment generated from one AST pass on 2026-08-31 and a bounded
# source-path review of the former ``review`` bucket on 2026-09-01.  The
# persisted map is the execution contract; new or changed tests absent here
# deliberately fall into ``review`` until their graph evidence is inspected.
PERSISTED_LANE_DATA = {
  "tests/test_admissibility.py": "flujo",
  "tests/test_adobe_panel.py": "repo_hygiene",
  "tests/test_aepfile.py": "flujo",
  "tests/test_agent_bootstrap.py": "mak",
  "tests/test_airdrop.py": "flujo",
  "tests/test_airdrop_checkpoint.py": "flujo",
  "tests/test_airdrop_signing.py": "flujo",
  "tests/test_analyze.py": "flujo",
  "tests/test_analyze_export.py": "flujo",
  "tests/test_application_research_package.py": "flujo",
  "tests/test_archive_memory.py": "flujo",
  "tests/test_archive_observer.py": "flujo",
  "tests/test_archive_pipeline.py": "flujo",
  "tests/test_archive_portfolio_department.py": "flujo",
  "tests/test_archive_project_ir_adapter.py": "flujo",
  "tests/test_archive_project_ir_evaluator.py": "flujo",
  "tests/test_archive_reconstruction.py": "flujo",
  "tests/test_archive_relation_evaluator.py": "flujo",
  "tests/test_archive_relation_inference.py": "flujo",
  "tests/test_archive_toolchain.py": "flujo",
  "tests/test_archive_unit_evaluator.py": "flujo",
  "tests/test_archive_unit_reconstruction.py": "flujo",
  "tests/test_archivo_ensayos.py": "repo_hygiene",
  "tests/test_archivo_iskvw_posicion.py": "repo_hygiene",
  "tests/test_artistic_program_evaluator.py": "flujo",
  "tests/test_artistic_program_hypotheses.py": "flujo",
  "tests/test_auto_pending_flyers.py": "flujo",
  "tests/test_autofit.py": "flujo",
  "tests/test_autonomia_cli.py": "flujo",
  "tests/test_autonomy_plan.py": "flujo",
  "tests/test_backlog_descargar_concurrency.py": "repo_hygiene",
  "tests/test_becas_calendario.py": "mak",
  "tests/test_becas_calendario_missing_dir.py": "repo_hygiene",
  "tests/test_blender_nodes.py": "flujo",
  "tests/test_blender_nodes_video.py": "flujo",
  "tests/test_blender_scene_probe.py": "mak",
  "tests/test_blendfile.py": "flujo",
  "tests/test_borradura_ascii.py": "repo_hygiene",
  "tests/test_brand.py": "flujo",
  "tests/test_build_application_intake.py": "integration",
  "tests/test_busqueda_ciega.py": "repo_hygiene",
  "tests/test_calidad_loop.py": "mak",
  "tests/test_campo_filtro.py": "repo_hygiene",
  "tests/test_canary.py": "flujo",
  "tests/test_canva_and_blender.py": "flujo",
  "tests/test_capas_iskvw.py": "repo_hygiene",
  "tests/test_capataz.py": "mak",
  "tests/test_capataz_enrutamiento.py": "repo_hygiene",
  "tests/test_cartografia_filtros.py": "repo_hygiene",
  "tests/test_catalog_federation.py": "flujo",
  "tests/test_certified_engine.py": "flujo",
  "tests/test_certified_identity.py": "flujo",
  "tests/test_check_mak_trabajo.py": "repo_hygiene",
  "tests/test_classification_queue.py": "flujo",
  "tests/test_cli_doctor_git_working_tree_defect.py": "flujo",
  "tests/test_cli_github_sync.py": "flujo",
  "tests/test_cli_micelio.py": "flujo",
  "tests/test_cli_more_commands.py": "flujo",
  "tests/test_cli_smoke.py": "flujo",
  "tests/test_cli_v035.py": "flujo",
  "tests/test_code_index.py": "flujo",
  "tests/test_codex_cadena.py": "mak",
  "tests/test_codex_no_es_sandbox.py": "repo_hygiene",
  "tests/test_coherence.py": "repo_hygiene",
  "tests/test_coherence_boundaries.py": "mak",
  "tests/test_comandos_manifiesto.py": "repo_hygiene",
  "tests/test_comercial_multiformato.py": "flujo",
  "tests/test_comparar_cobertura.py": "repo_hygiene",
  "tests/test_compete_engine.py": "repo_hygiene",
  "tests/test_compilador_navegador.py": "repo_hygiene",
  "tests/test_consolidar_fichas.py": "repo_hygiene",
  "tests/test_construir_mapa_visual.py": "mak",
  "tests/test_consulta_busqueda.py": "repo_hygiene",
  "tests/test_contract_audit.py": "flujo",
  "tests/test_contracurator.py": "flujo",
  "tests/test_contrato_archivo.py": "repo_hygiene",
  "tests/test_copilot.py": "mak",
  "tests/test_corpus_a_micelio.py": "repo_hygiene",
  "tests/test_corpus_olvido.py": "repo_hygiene",
  "tests/test_cotizaciones_base.py": "flujo",
  "tests/test_cron_nocturno.py": "repo_hygiene",
  "tests/test_cron_state_atomic.py": "repo_hygiene",
  "tests/test_crontab_mak_referencias.py": "repo_hygiene",
  "tests/test_cross_archive_relations.py": "flujo",
  "tests/test_cross_archive_research_frontier.py": "flujo",
  "tests/test_cultura_sin_automerge.py": "repo_hygiene",
  "tests/test_curaduria.py": "mak",
  "tests/test_curaduria_roundtrip.py": "repo_hygiene",
  "tests/test_curatoria_ordenes.py": "repo_hygiene",
  "tests/test_curatoria_percepcion.py": "repo_hygiene",
  "tests/test_curatoria_portfolio_critica.py": "mak",
  "tests/test_curatoria_triangular.py": "mak",
  "tests/test_curatoria_watchdog_panel.py": "repo_hygiene",
  "tests/test_dashboard.py": "flujo",
  "tests/test_datadrop_scan.py": "flujo",
  "tests/test_datadrops_pdf_support.py": "flujo",
  "tests/test_debate_modelos.py": "repo_hygiene",
  "tests/test_deep_learning_gate.py": "flujo",
  "tests/test_delegate_creative_director.py": "flujo",
  "tests/test_departments.py": "flujo",
  "tests/test_diagnostico_proyectos.py": "mak",
  "tests/test_diagnostics.py": "flujo",
  "tests/test_director.py": "flujo",
  "tests/test_empaquetar_assets.py": "mak",
  "tests/test_energia_log.py": "mak",
  "tests/test_entity_crosswalk.py": "flujo",
  "tests/test_entregar_concurrency.py": "mak",
  "tests/test_entregar_iconos_guard.py": "repo_hygiene",
  "tests/test_entregar_micelio.py": "repo_hygiene",
  "tests/test_entregar_smoke_gate.py": "repo_hygiene",
  "tests/test_episode_runner.py": "flujo",
  "tests/test_epistemics.py": "flujo",
  "tests/test_eventos_flyer_auto.py": "flujo",
  "tests/test_evidence_return.py": "flujo",
  "tests/test_extraccion_db.py": "repo_hygiene",
  "tests/test_feature_policy.py": "flujo",
  "tests/test_fila_cero.py": "repo_hygiene",
  "tests/test_flujo_dispatcher.py": "repo_hygiene",
  "tests/test_flujo_port_contract.py": "flujo",
  "tests/test_flyer_auto_parth.py": "flujo",
  "tests/test_flyer_carousel_index.py": "flujo",
  "tests/test_formato_ensayo.py": "repo_hygiene",
  "tests/test_formatos_mak.py": "repo_hygiene",
  "tests/test_formats_catalogo.py": "flujo",
  "tests/test_fuentes.py": "repo_hygiene",
  "tests/test_gen_animadas_obras.py": "mak",
  "tests/test_gen_archivo_iskvw.py": "repo_hygiene",
  "tests/test_gen_propuestas_rd.py": "repo_hygiene",
  "tests/test_generar_catalogo_rd.py": "flujo",
  "tests/test_git_state_measurement_defect.py": "flujo",
  "tests/test_git_web_contract.py": "repo_hygiene",
  "tests/test_higiene_docs.py": "repo_hygiene",
  "tests/test_higiene_repo.py": "repo_hygiene",
  "tests/test_hotfix_03411.py": "flujo",
  "tests/test_hub_archive_portfolio_view.py": "repo_hygiene",
  "tests/test_hub_comando_seguro.py": "flujo",
  "tests/test_hub_comandos.py": "flujo",
  "tests/test_hub_dependency_degradation.py": "repo_hygiene",
  "tests/test_hub_durable_writers.py": "mak",
  "tests/test_hub_execution_routes.py": "repo_hygiene",
  "tests/test_hub_post_dispatch_errors.py": "mak",
  "tests/test_hub_render_and_rescue_routes.py": "repo_hygiene",
  "tests/test_hub_second_witness_routes.py": "repo_hygiene",
  "tests/test_hub_static_content_routes.py": "repo_hygiene",
  "tests/test_iconos_conjunto.py": "repo_hygiene",
  "tests/test_identity_ties.py": "flujo",
  "tests/test_idioma_ratchet.py": "repo_hygiene",
  "tests/test_ig_cffi_fallback.py": "flujo",
  "tests/test_ig_download.py": "flujo",
  "tests/test_ig_download_parth.py": "flujo",
  "tests/test_ig_metadatos.py": "repo_hygiene",
  "tests/test_ig_url_canonica.py": "flujo",
  "tests/test_ig_usuario.py": "flujo",
  "tests/test_illustrator_bridge.py": "flujo",
  "tests/test_imap_apagado.py": "flujo",
  "tests/test_index_db.py": "flujo",
  "tests/test_inferential_archaeology.py": "mak",
  "tests/test_informe_plantilla.py": "repo_hygiene",
  "tests/test_ingesta_archivo.py": "mak",
  "tests/test_ingesta_evidence_gate.py": "mak",
  "tests/test_intake.py": "flujo",
  "tests/test_intake_json.py": "flujo",
  "tests/test_intake_json_cli.py": "flujo",
  "tests/test_interfaz_jobs_concurrency.py": "mak",
  "tests/test_iskvw_archive_view_ui.py": "repo_hygiene",
  "tests/test_iskvw_editor_contract.py": "repo_hygiene",
  "tests/test_iskvw_librerias.py": "repo_hygiene",
  "tests/test_iskvw_piel_medir.py": "repo_hygiene",
  "tests/test_iskvw_piel_smoke.py": "repo_hygiene",
  "tests/test_iskvw_semilla.py": "repo_hygiene",
  "tests/test_iskvw_vinculos.py": "repo_hygiene",
  "tests/test_jobs_brief.py": "flujo",
  "tests/test_jobs_lifecycle.py": "flujo",
  "tests/test_knowledge_dossiers.py": "flujo",
  "tests/test_knowledge_reconciliation.py": "flujo",
  "tests/test_knowledge_scanner_skips.py": "repo_hygiene",
  "tests/test_laser.py": "flujo",
  "tests/test_latido.py": "repo_hygiene",
  "tests/test_learning_policy.py": "flujo",
  "tests/test_learning_v2.py": "flujo",
  "tests/test_logo_clean_lab_dataset.py": "repo_hygiene",
  "tests/test_mak_backlog.py": "repo_hygiene",
  "tests/test_mak_benchmark.py": "mak",
  "tests/test_mak_codex_nodos.py": "repo_hygiene",
  "tests/test_mak_conductor.py": "mak",
  "tests/test_mak_conductor_registry.py": "mak",
  "tests/test_mak_delegar.py": "mak",
  "tests/test_mak_diagnostics.py": "repo_hygiene",
  "tests/test_mak_discernment.py": "mak",
  "tests/test_mak_fallback.py": "repo_hygiene",
  "tests/test_mak_fructificacion.py": "mak",
  "tests/test_mak_fusion.py": "mak",
  "tests/test_mak_gpu_activity.py": "mak",
  "tests/test_mak_grafo_fallback.py": "mak",
  "tests/test_mak_heartbeat.py": "repo_hygiene",
  "tests/test_mak_hub_eventos.py": "mak",
  "tests/test_mak_hub_salud.py": "repo_hygiene",
  "tests/test_mak_iconos.py": "repo_hygiene",
  "tests/test_mak_ideas.py": "mak",
  "tests/test_mak_interfaz_config.py": "mak",
  "tests/test_mak_ledger.py": "mak",
  "tests/test_mak_micelio_ideas.py": "mak",
  "tests/test_mak_mirror_fixes.py": "mak",
  "tests/test_mak_organos_visibles.py": "mak",
  "tests/test_mak_pausa.py": "mak",
  "tests/test_mak_portfolio_bridge.py": "mak",
  "tests/test_mak_post.py": "mak",
  "tests/test_mak_post_registry.py": "mak",
  "tests/test_mak_process_guard.py": "mak",
  "tests/test_mak_reanudar.py": "mak",
  "tests/test_mak_research_iconos_auto.py": "repo_hygiene",
  "tests/test_mak_research_interfaz_http.py": "repo_hygiene",
  "tests/test_mak_research_interfaz_pure.py": "repo_hygiene",
  "tests/test_mak_research_lib.py": "mak",
  "tests/test_mak_research_memoria_degradation.py": "repo_hygiene",
  "tests/test_mak_research_router.py": "repo_hygiene",
  "tests/test_mak_research_watchdog.py": "repo_hygiene",
  "tests/test_mak_retencion.py": "repo_hygiene",
  "tests/test_mak_reviews.py": "mak",
  "tests/test_mak_revision.py": "mak",
  "tests/test_mak_revision_episodios.py": "mak",
  "tests/test_mak_salud_proveedores.py": "mak",
  "tests/test_mak_sin_gptmini.py": "mak",
  "tests/test_mak_sync_safe.py": "repo_hygiene",
  "tests/test_mak_tandas.py": "mak",
  "tests/test_mak_tandas_surface.py": "flujo",
  "tests/test_mak_trabajo_resp.py": "repo_hygiene",
  "tests/test_mak_ua.py": "mak",
  "tests/test_manifest.py": "flujo",
  "tests/test_mantenimiento.py": "mak",
  "tests/test_mapa_completo.py": "flujo",
  "tests/test_marca_sin_precio.py": "mak",
  "tests/test_marco_no_va_al_buscador.py": "mak",
  "tests/test_material_ocurrencias.py": "repo_hygiene",
  "tests/test_math_kernel.py": "flujo",
  "tests/test_mecanismo_residuo.py": "mak",
  "tests/test_medir_organismo.py": "mak",
  "tests/test_memoria_projection.py": "mak",
  "tests/test_metricas_capataz.py": "mak",
  "tests/test_micelio.py": "flujo",
  "tests/test_micelio_cosecha.py": "flujo",
  "tests/test_micelio_deposito.py": "mak",
  "tests/test_migrate_unified_knowledge.py": "integration",
  "tests/test_mineria_rd.py": "repo_hygiene",
  "tests/test_motor_semantico.py": "repo_hygiene",
  "tests/test_motor_semantico_rasterizador.py": "repo_hygiene",
  "tests/test_mutaciones.py": "mak",
  "tests/test_node_runtime_requirement.py": "flujo",
  "tests/test_noisette_real_fixture.py": "flujo",
  "tests/test_open_episode_state.py": "flujo",
  "tests/test_operating_world_experiment.py": "mak",
  "tests/test_operational_bridge.py": "flujo",
  "tests/test_operational_entrypoints.py": "repo_hygiene",
  "tests/test_operational_memberships.py": "flujo",
  "tests/test_operational_status.py": "flujo",
  "tests/test_opportunity_constraints.py": "integration",
  "tests/test_opportunity_delta.py": "integration",
  "tests/test_opportunity_fit.py": "flujo",
  "tests/test_opportunity_validity_capture.py": "integration",
  "tests/test_optional_dependencies_absence.py": "integration",
  "tests/test_osc_sender.py": "repo_hygiene",
  "tests/test_paleta_reactivos.py": "mak",
  "tests/test_physical_projections.py": "repo_hygiene",
  "tests/test_piel_manifiesto.py": "mak",
  "tests/test_pilot_run_manifest.py": "flujo",
  "tests/test_plano_module.py": "flujo",
  "tests/test_plano_packs.py": "flujo",
  "tests/test_plano_simbolos_alta.py": "flujo",
  "tests/test_plano_simbolos_catalogo.py": "flujo",
  "tests/test_plano_stands.py": "repo_hygiene",
  "tests/test_plano_trazador.py": "flujo",
  "tests/test_plano_validation.py": "flujo",
  "tests/test_png_xmp_witness.py": "mak",
  "tests/test_portfolio_decision_drafts.py": "mak",
  "tests/test_portfolio_dossier.py": "flujo",
  "tests/test_portfolio_evidence.py": "flujo",
  "tests/test_portfolio_gen.py": "repo_hygiene",
  "tests/test_portfolio_production.py": "flujo",
  "tests/test_portfolio_works.py": "mak",
  "tests/test_possibility_field.py": "flujo",
  "tests/test_postgres_migration.py": "flujo",
  "tests/test_postgres_runtime.py": "flujo",
  "tests/test_practice_evidence_state.py": "flujo",
  "tests/test_practice_receipt_adapter.py": "flujo",
  "tests/test_presets.py": "flujo",
  "tests/test_privacidad_repo.py": "repo_hygiene",
  "tests/test_privacy.py": "flujo",
  "tests/test_product_episode.py": "flujo",
  "tests/test_product_learning.py": "flujo",
  "tests/test_product_plan.py": "flujo",
  "tests/test_product_view.py": "flujo",
  "tests/test_project_api.py": "flujo",
  "tests/test_project_context.py": "flujo",
  "tests/test_project_contracts.py": "flujo",
  "tests/test_project_evidence.py": "flujo",
  "tests/test_project_ir.py": "flujo",
  "tests/test_project_lanes.py": "mak",
  "tests/test_project_reconstruction.py": "integration",
  "tests/test_project_research.py": "flujo",
  "tests/test_project_router.py": "flujo",
  "tests/test_psicosis_agente.py": "repo_hygiene",
  "tests/test_puente_issues.py": "mak",
  "tests/test_rd_database.py": "flujo",
  "tests/test_rd_datos.py": "flujo",
  "tests/test_rd_db_logos.py": "flujo",
  "tests/test_rd_eventos.py": "flujo",
  "tests/test_rd_informe.py": "flujo",
  "tests/test_reactivo_matcher.py": "flujo",
  "tests/test_readme_svg.py": "repo_hygiene",
  "tests/test_reception.py": "flujo",
  "tests/test_reconcile_iskvw_media.py": "mak",
  "tests/test_reconstruction_adapter.py": "flujo",
  "tests/test_recovered_import.py": "mak",
  "tests/test_refutar_orden.py": "repo_hygiene",
  "tests/test_render_flyer_mak.py": "repo_hygiene",
  "tests/test_render_formats.py": "flujo",
  "tests/test_render_output_edges.py": "integration",
  "tests/test_render_rescale.py": "flujo",
  "tests/test_render_video_rd.py": "repo_hygiene",
  "tests/test_render_video_sequence_mak.py": "mak",
  "tests/test_replay.py": "flujo",
  "tests/test_repo_audit.py": "mak",
  "tests/test_repo_scan.py": "repo_hygiene",
  "tests/test_research_event_log.py": "mak",
  "tests/test_research_evidence_triangulation.py": "flujo",
  "tests/test_research_frontier_bridge.py": "flujo",
  "tests/test_research_mutations_concurrency.py": "mak",
  "tests/test_research_registry_contract.py": "flujo",
  "tests/test_research_simulation.py": "flujo",
  "tests/test_research_source_capture.py": "mak",
  "tests/test_resolume_automator.py": "flujo",
  "tests/test_resolume_composition.py": "flujo",
  "tests/test_resolume_screen_setup.py": "flujo",
  "tests/test_resolution.py": "flujo",
  "tests/test_review_queue.py": "flujo",
  "tests/test_revisor_gates.py": "repo_hygiene",
  "tests/test_route_resolver.py": "flujo",
  "tests/test_run_airdrop_checks.py": "flujo",
  "tests/test_scene_snapshot.py": "integration",
  "tests/test_scoring_fallback_parser.py": "flujo",
  "tests/test_selective_recompute_receipt.py": "flujo",
  "tests/test_serve_api.py": "flujo",
  "tests/test_showcontrol_token.py": "repo_hygiene",
  "tests/test_smoke.py": "flujo",
  "tests/test_source_learning.py": "flujo",
  "tests/test_source_pipeline.py": "repo_hygiene",
  "tests/test_ssd_order_operator_frontier.py": "flujo",
  "tests/test_steg_changelog.py": "flujo",
  "tests/test_substrate.py": "flujo",
  "tests/test_suplementos_config.py": "flujo",
  "tests/test_suplementos_svg_validator.py": "flujo",
  "tests/test_svg_illustrator_integration.py": "flujo",
  "tests/test_svg_index_real.py": "flujo",
  "tests/test_system_status.py": "flujo",
  "tests/test_tapiz_vibecode.py": "repo_hygiene",
  "tests/test_tarifa_una_sola_fuente.py": "flujo",
  "tests/test_tennis_mcp.py": "flujo",
  "tests/test_test_taxonomy.py": "repo_hygiene",
  "tests/test_thing_registro.py": "repo_hygiene",
  "tests/test_three_plane_manifest.py": "flujo",
  "tests/test_tilde_meter.py": "repo_hygiene",
  "tests/test_tilde_paridad.py": "repo_hygiene",
  "tests/test_tilde_render.py": "mak",
  "tests/test_tilde_residuo.py": "mak",
  "tests/test_tilde_sobrevivencia.py": "mak",
  "tests/test_title_resolution.py": "flujo",
  "tests/test_trabajo_concurrency.py": "mak",
  "tests/test_un_solo_documento.py": "repo_hygiene",
  "tests/test_utilidades_mak_sanidad.py": "mak",
  "tests/test_validar_curaduria.py": "repo_hygiene",
  "tests/test_validate_airdrop.py": "repo_hygiene",
  "tests/test_venue.py": "repo_hygiene",
  "tests/test_venue3d_smoke.py": "repo_hygiene",
  "tests/test_vigia.py": "repo_hygiene",
  "tests/test_vigia_capture_bridge.py": "integration",
  "tests/test_vigia_opportunity_queue.py": "mak",
  "tests/test_vinculos_iskvw.py": "repo_hygiene",
  "tests/test_vision_feedback_memory.py": "flujo",
  "tests/test_visual_index.py": "mak",
  "tests/test_vj_git_performance.py": "repo_hygiene",
  "tests/test_web_hub_endpoints.py": "flujo",
  "tests/test_wifi_intelligence_plugin.py": "repo_hygiene",
  "tests/test_xio_evidence.py": "mak",
  "tests/test_xio_portfolio_link.py": "mak",
  "tests/test_xio_puente_monitor.py": "repo_hygiene",
  "tests/test_xio_puente_staged.py": "repo_hygiene",
  "tests/test_xio_superficie.py": "repo_hygiene",
  "tests/test_zipper.py": "flujo"
}
# A file is not a hygiene test merely because it mentions ``repo`` or touches
# a fixture.  Keep this lane deliberately small: these modules assert tree,
# Git, manifest, privacy, handoff, or language invariants.  Other historical
# assignments remain visible in ``review`` until their real subject is
# assigned to ``flujo`` or ``mak``; they must not inflate the hygiene gate.
HYGIENE_CANONICAL_STEMS = frozenset({
    "test_comandos_manifiesto",
    "test_git_web_contract",
    "test_higiene_docs",
    "test_higiene_repo",
    "test_idioma_ratchet",
    "test_operational_entrypoints",
    "test_physical_projections",
    "test_privacidad_repo",
    "test_repo_audit",
    "test_repo_scan",
    "test_test_taxonomy",
    "test_un_solo_documento",
})

# The remaining former-review modules were inspected at their real import/path
# boundary.  They are not hygiene checks: they exercise MAK departments,
# tooling, or the cross-layer HTTP hubs.  Keeping the decisions explicit makes
# the review bucket finite and auditable instead of another dumping ground.
REVIEW_LANE_ASSIGNMENTS = {
    "tests/test_adobe_panel.py": "repo_hygiene",
    "tests/test_archivo_iskvw_posicion.py": "mak",
    "tests/test_becas_calendario_missing_dir.py": "mak",
    "tests/test_busqueda_ciega.py": "mak",
    "tests/test_capas_iskvw.py": "mak",
    "tests/test_codex_no_es_sandbox.py": "mak",
    "tests/test_coherence.py": "mak",
    "tests/test_consolidar_fichas.py": "mak",
    "tests/test_consulta_busqueda.py": "mak",
    "tests/test_corpus_a_micelio.py": "mak",
    "tests/test_debate_modelos.py": "mak",
    "tests/test_entregar_iconos_guard.py": "mak",
    "tests/test_entregar_smoke_gate.py": "mak",
    "tests/test_formatos_mak.py": "mak",
    "tests/test_fuentes.py": "mak",
    "tests/test_hub_execution_routes.py": "integration",
    "tests/test_hub_render_and_rescue_routes.py": "integration",
    "tests/test_iconos_conjunto.py": "mak",
    "tests/test_ig_metadatos.py": "mak",
    "tests/test_informe_plantilla.py": "mak",
    "tests/test_iskvw_editor_contract.py": "repo_hygiene",
    "tests/test_iskvw_vinculos.py": "repo_hygiene",
    "tests/test_knowledge_scanner_skips.py": "mak",
    "tests/test_logo_clean_lab_dataset.py": "mak",
    "tests/test_mak_backlog.py": "mak",
    "tests/test_mak_codex_nodos.py": "mak",
    "tests/test_mak_diagnostics.py": "integration",
    "tests/test_mak_fallback.py": "mak",
    "tests/test_mak_hub_salud.py": "integration",
    "tests/test_mak_iconos.py": "mak",
    "tests/test_mak_research_iconos_auto.py": "mak",
    "tests/test_mak_research_interfaz_http.py": "mak",
    "tests/test_mak_research_memoria_degradation.py": "mak",
    "tests/test_mak_research_watchdog.py": "mak",
    "tests/test_mak_sync_safe.py": "mak",
    "tests/test_material_ocurrencias.py": "mak",
    "tests/test_motor_semantico.py": "mak",
    "tests/test_motor_semantico_rasterizador.py": "mak",
    "tests/test_readme_svg.py": "repo_hygiene",
    "tests/test_refutar_orden.py": "mak",
    "tests/test_source_pipeline.py": "mak",
    "tests/test_validate_airdrop.py": "flujo",
    "tests/test_vinculos_iskvw.py": "mak",
    "tests/test_wifi_intelligence_plugin.py": "mak",
}


def _module_locations() -> dict[str, tuple[Path, ...]]:
    """Index importable project modules once for unresolved test modules."""
    locations: dict[str, list[Path]] = {}
    for root_name in ("src", "cultura", "tools", "iskvw", "scripts", "xio", "projects"):
        root = REPO / root_name
        if not root.is_dir():
            continue
        for candidate in root.rglob("*.py"):
            if any(part in {"_archive", ".venv", "__pycache__", "node_modules"}
                   for part in candidate.parts):
                continue
            locations.setdefault(candidate.stem, []).append(candidate)
    return {stem: tuple(paths) for stem, paths in locations.items()}


_MODULE_LOCATIONS = _module_locations()


def _infer_review_lane(path: Path) -> str:
    """Resolve an old broad hygiene assignment from executable evidence.

    Imports and explicit source paths are stronger than a filename.  If they
    do not identify one subject, the test remains in ``review`` rather than
    being silently assigned to a functional lane.
    """
    imported, source = _imports_and_text(path)
    lanes: set[str] = set()
    for name in imported:
        stem = name.rsplit(".", 1)[-1]
        for candidate in _MODULE_LOCATIONS.get(stem, ()):
            candidate_text = candidate.relative_to(REPO).as_posix()
            if candidate_text.startswith("src/flujo/"):
                lanes.add("flujo")
            elif candidate_text.startswith("projects/tapiz/"):
                lanes.add("flujo")
            elif candidate_text.startswith(("cultura/", "tools/", "iskvw/", "scripts/", "xio/", "projects/")):
                lanes.add("mak")

    if "src/flujo/" in source or "scripts/flujo.py" in source or "projects/tapiz/" in source:
        lanes.add("flujo")
    if any(token in source for token in ("cultura/", "tools/", "iskvw/", "xio/", "projects/cultura/", "projects/plano/")):
        lanes.add("mak")

    # Dynamic-import tests often name the module only in a docstring.  Resolve
    # those explicit ``module.py`` mentions against the same index.
    for stem in set(re.findall(r"(?<![\w-])([a-zA-Z_][\w-]*)\.py", source)):
        for candidate in _MODULE_LOCATIONS.get(stem, ()):
            candidate_text = candidate.relative_to(REPO).as_posix()
            if candidate_text.startswith("src/flujo/"):
                lanes.add("flujo")
            elif candidate_text.startswith("projects/tapiz/"):
                lanes.add("flujo")
            elif candidate_text.startswith(("cultura/", "tools/", "iskvw/", "scripts/", "xio/", "projects/")):
                lanes.add("mak")

    if len(lanes) > 1:
        return "integration"
    return next(iter(lanes), "review")


def _build_embedded_lane_map() -> dict[str, LaneRecord]:
    """Fallback for checkouts created before the JSON contract existed."""
    result: dict[str, LaneRecord] = {}
    for key, lane in PERSISTED_LANE_DATA.items():
        if key in REVIEW_LANE_ASSIGNMENTS:
            result[key] = LaneRecord(
                REVIEW_LANE_ASSIGNMENTS[key], (), "reviewed module/path assignment"
            )
            continue
        if lane == "repo_hygiene" and Path(key).stem not in HYGIENE_CANONICAL_STEMS:
            inferred = _infer_review_lane(REPO / key)
            result[key] = LaneRecord(
                inferred, (),
                "resolved from imports/source paths"
                if inferred != "review"
                else "historical hygiene assignment; subject not canonical",
            )
        else:
            result[key] = LaneRecord(lane, (), "persisted AST assignment")
    return result


def _load_lane_contract() -> dict[str, LaneRecord]:
    """Load the machine-readable contract, falling back during bootstrap."""
    try:
        payload = json.loads(LANE_MAP_CONTRACT.read_text(encoding="utf-8"))
        assignments = payload.get("assignments", {})
        result: dict[str, LaneRecord] = {}
        for key, value in assignments.items():
            if not isinstance(value, dict) or value.get("lane") not in LANES:
                continue
            result[str(key)] = LaneRecord(
                str(value["lane"]),
                tuple(str(item) for item in value.get("imports", ())),
                str(value.get("reason", "JSON lane contract")),
            )
        if result:
            return result
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return _build_embedded_lane_map()


TEST_LANE_MAP: dict[str, LaneRecord] = _load_lane_contract()
def lane_for_test_path(path: str | Path) -> str:
    """Return a declared lane or ``review``; do not raise during collection."""
    try:
        key = str(Path(path).resolve().relative_to(REPO))
    except ValueError:
        return "review"
    return TEST_LANE_MAP.get(key, LaneRecord("review", (), "outside map")).lane


def sethash(paths: Iterable[str]) -> str:
    return hashlib.sha256("\n".join(sorted(paths)).encode()).hexdigest()


def report() -> dict[str, object]:
    grouped: dict[str, list[str]] = {lane: [] for lane in LANES}
    uncovered: dict[str, str] = {}
    for path, record in TEST_LANE_MAP.items():
        grouped[record.lane].append(path)
        if record.lane == "review":
            uncovered[path] = record.reason
    contract_summary: dict[str, object] = {}
    try:
        payload = json.loads(LANE_MAP_CONTRACT.read_text(encoding="utf-8"))
        value = payload.get("summary", {})
        if isinstance(value, dict):
            contract_summary = value
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return {"schema": "mak-test-lane-map-v3", "lanes": {
        lane: {"N": len(paths), "SETHASH": sethash(paths), "paths": sorted(paths)}
        for lane, paths in grouped.items()},
        "not_covered": uncovered,
        "total": len(TEST_LANE_MAP),
        "contract_path": str(LANE_MAP_CONTRACT),
        "contract_disagreements": int(contract_summary.get("disagreements", 0) or 0),
    }


def lanes_for_changed_paths(paths: Iterable[str]) -> tuple[str, ...]:
    """Select lanes from changed paths, following consumers when indexed."""
    code_index: dict[str, object] | None = None

    def load_code_index() -> dict[str, object]:
        nonlocal code_index
        if code_index is None:
            try:
                payload = json.loads(
                    (REPO / "context" / "code_structure_index.json").read_text(
                        encoding="utf-8"
                    )
                )
                code_index = payload if isinstance(payload, dict) else {}
            except (OSError, json.JSONDecodeError, TypeError):
                code_index = {}
        return code_index

    def normalise(raw_path: str) -> str:
        path = raw_path.strip().replace("\\", "/")
        if path.startswith(("a/", "b/")):
            path = path[2:]
        try:
            candidate = Path(path)
            if candidate.is_absolute():
                path = candidate.resolve().relative_to(REPO).as_posix()
        except (OSError, ValueError):
            pass
        return path

    def consumers_for(path: str) -> set[str]:
        payload = load_code_index()
        items = payload.get("files", []) if isinstance(payload, dict) else []
        if not isinstance(items, list):
            return set()
        for item in items:
            if not isinstance(item, dict) or item.get("path") != path:
                continue
            result: set[str] = set()
            for module in item.get("imported_by", []):
                if isinstance(module, str) and module.startswith("tests."):
                    result.add("tests/" + module[len("tests."):].replace(".", "/") + ".py")
            return result
        return set()

    selected: set[str] = set()
    for raw in paths:
        path = normalise(raw)
        if not path:
            continue
        if path in TEST_LANE_MAP:
            selected.add(TEST_LANE_MAP[path].lane)
        elif path in {
            "pyproject.toml",
            "tests/conftest.py",
            "tools/test_lane_map.py",
            "context/code_structure_index.json",
            str(LANE_MAP_CONTRACT.relative_to(REPO)),
        }:
            selected.update(LANES)
        else:
            consumers = consumers_for(path)
            for consumer in consumers:
                selected.add(TEST_LANE_MAP.get(
                    consumer, LaneRecord("review", (), "outside map")
                ).lane)
            if consumers:
                continue
            if path.startswith("src/flujo/"):
                selected.add("flujo")
            elif path.startswith(("tools/", "cultura/")) or path.endswith(".py"):
                selected.add("mak")
            elif any(word in path.lower() for word in _TREE_ONLY_WORDS):
                selected.add("repo_hygiene")
            else:
                selected.add("review")
    return tuple(lane for lane in LANES if lane in selected)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    parser.add_argument(
        "--select-changed", action="store_true",
        help="read git diff --name-only paths from stdin and print selected lanes",
    )
    args = parser.parse_args()
    if args.select_changed:
        print(" ".join(lanes_for_changed_paths(sys.stdin)))
        return 0
    data = report()
    if args.format == "json":
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for lane, value in data["lanes"].items():
            print(f"{lane}: N={value['N']} SETHASH={value['SETHASH']}")
        print("contract_disagreements=" + str(data["contract_disagreements"]))
        print("not_covered=" + ", ".join(sorted(data["not_covered"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
