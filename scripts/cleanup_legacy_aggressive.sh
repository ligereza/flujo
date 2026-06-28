#!/usr/bin/env bash
# cleanup_legacy_aggressive.sh — Archiva scripts legacy duplicados

set -e

ARCHIVE="_archive/legacy_$(date +%Y%m%d_%H%M)"
mkdir -p "$ARCHIVE"

LEGACY_SCRIPTS=(
  flyer_analyze.py
  flyer_create_project.py
  flyer_from_email.py
  flyer_index.py
  flyer_index.sh
  flyer_latest.sh
  flyer_list.sh
  flyer_status.py
  flyer_status_latest.sh
  ig_download.py
  ig_redownload.py
  job_activate.py
  job_complete.py
  job_extract_brief.py
  job_from_text.py
  job_new.sh
  job_next_actions.py
  job_prepare.py
  job_report.py
  job_set_status.py
  job_status.py
  job_validate.py
  piezas_add_component.py
  piezas_check_outputs.py
  piezas_components.py
  piezas_formatos.py
  piezas_generar.py
  piezas_project_summary.py
  piezas_validate_config.py
  privacy_check_job.py
  privacy_sanitize_text.py
  privacy_scan_text.py
  project_clone_variant.py
  project_delivery_manifest.py
  project_inspect.py
  project_new_from_template.py
  project_render.py
  rider_new.py
  rider_presets.py
)

echo "Archivando scripts legacy en $ARCHIVE..."

for script in "${LEGACY_SCRIPTS[@]}"; do
    if [ -f "scripts/$script" ]; then
        mv "scripts/$script" "$ARCHIVE/" 2>/dev/null || true
        echo "  ✓ $script"
    fi
done

echo ""
echo "Listo. Scripts archivados en: $ARCHIVE"
