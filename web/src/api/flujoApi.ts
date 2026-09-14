export type Ping = {
  status?: string;
  version?: string;
  root?: string;
  connected?: boolean;
  mode?: string;
  note?: string;
};

export type JobItem = {
  name: string;
  path?: string;
  estado?: string;
  tipo_pieza?: string;
  proyecto?: string;
  pendientes?: string[] | string;
};

export type JobsResponse = {
  jobs: JobItem[];
  count: number;
  connected?: boolean;
  source?: string;
  error?: string;
};

export type ResearchJob = {
  id: number;
  question: string;
  domain?: string;
  adapter?: string;
  status?: string;
  next_process?: string;
  created_at?: string;
  steps?: number;
  done_steps?: number;
};

export type ResearchJobsResponse = {
  available?: boolean;
  jobs?: ResearchJob[];
  count?: number;
  error?: string;
};

export type ResearchJobSource = {
  id: number;
  url?: string;
  title?: string;
  capture_status?: string;
  http_status?: number;
  raw_sha256?: string;
  text_sha256?: string;
  license_state?: string;
  license_evidence?: string;
};

export type ResearchStep = {
  order?: number;
  process?: string;
  status?: string;
  provider_policy?: string;
};

export type ResearchJobDetail = Omit<ResearchJob, 'steps'> & {
  description?: string;
  source_policy?: string;
  constraint_policy?: string;
  steps?: ResearchStep[];
  relations?: Array<{ type?: string; from?: string; to?: string; rationale?: string }>;
  sources?: ResearchJobSource[];
  extract_input_sha256?: string;
};

export type ResearchJobResponse = {
  available?: boolean;
  job?: ResearchJobDetail;
  error?: string;
};

export type ResearchNormalizeReadinessResponse = {
  schema?: string;
  algorithm_version?: string;
  available?: boolean;
  read_only?: boolean;
  job_id?: number;
  job_status?: string;
  next_process?: string;
  input_sha256?: string;
  current_input_sha256?: string;
  human_attestation?: { present?: boolean; actor_id?: string | null; actor_kind?: string | null; matches_input_sha256?: boolean };
  execution?: { normalize_execution?: boolean };
  normalization_allowed?: boolean;
  next_action?: string;
  control?: { database_write?: boolean; decision_write?: boolean; state_advance?: boolean; promotion?: string; publication?: boolean };
  error?: string;
};

export type ResearchNormalizePlanResponse = {
  schema?: string;
  algorithm_version?: string;
  available?: boolean;
  read_only?: boolean;
  job_id?: number;
  job_status?: string;
  next_process?: string;
  input_sha256?: string;
  human_attestation?: { present?: boolean; actor_id?: string | null; actor_kind?: string | null; matches_input_sha256?: boolean };
  plan?: { record_count?: number; operations?: string[]; preview?: Array<{ source_ref?: string; title?: string; raw_sha256?: string; text_sha256?: string; license_state?: string; candidate_kind?: string }>; semantic_claims_created?: boolean };
  execution_allowed?: boolean;
  next_action?: string;
  control?: { database_write?: boolean; decision_write?: boolean; state_advance?: boolean; promotion?: string; publication?: boolean };
  error?: string;
};

export type ResearchNormalizeDryRunResponse = {
  schema?: string;
  algorithm_version?: string;
  available?: boolean;
  read_only?: boolean;
  job_id?: number;
  job_status?: string;
  next_process?: string;
  input_sha256?: string;
  human_attestation?: { present?: boolean; actor_id?: string | null; actor_kind?: string | null; matches_input_sha256?: boolean };
  dry_run?: { would_preserve?: Array<{ source_ref?: string; title?: string; raw_sha256?: string; text_sha256?: string; license_state?: string; candidate_kind?: string }>; records?: number; semantic_transform_performed?: boolean; database_rows_created?: number };
  execution?: { attempted?: boolean; normalize_execution?: boolean; model_calls?: number; external_calls?: number };
  control?: { database_write?: boolean; decision_write?: boolean; state_advance?: boolean; promotion?: string; publication?: boolean; learning_demonstrated?: boolean };
  next_action?: string;
  error?: string;
};

export type ResearchLicenseReviewResponse = {
  schema?: string;
  algorithm_version?: string;
  available?: boolean;
  read_only?: boolean;
  job_id?: number;
  job_status?: string;
  next_process?: string;
  input_sha256?: string;
  sources?: Array<{ source_ref?: string; title?: string; license_state?: string; license_evidence?: string; verification?: string }>;
  counts?: Record<string, number>;
  ready_for_attestation?: boolean;
  next_action?: string;
  control?: { database_write?: boolean; decision_write?: boolean; state_advance?: boolean; promotion?: string; publication?: boolean };
  error?: string;
};

export type ResearchLicenseSourceReviewResponse = {
  schema?: string;
  algorithm_version?: string;
  available?: boolean;
  read_only?: boolean;
  job_id?: number;
  input_sha256?: string;
  source_review_sha256?: string;
  findings?: Array<{ source_ref?: string; license_state?: string; official_license?: string | null; evidence_ref?: string; evidence_sha256?: string; http_status?: number; action?: string }>;
  conflicts?: number;
  unknown_or_pending?: number;
  ready_for_attestation?: boolean;
  next_action?: string;
  control?: { database_write?: boolean; decision_write?: boolean; state_advance?: boolean; promotion?: string; publication?: boolean };
  error?: string;
};

export type ResearchLicenseCompatibilityPlanResponse = {
  schema?: string;
  algorithm_version?: string;
  available?: boolean;
  read_only?: boolean;
  job_id?: number;
  input_sha256?: string;
  source_review_sha256?: string;
  items?: Array<{ source_ref?: string; license_state?: string; official_license?: string | null; compatibility_action?: string }>;
  candidate_count?: number;
  blocked_count?: number;
  ready_for_attestation?: boolean;
  legal_conclusion?: boolean;
  next_action?: string;
  control?: { database_write?: boolean; decision_write?: boolean; state_advance?: boolean; promotion?: string; publication?: boolean };
  error?: string;
};

export type ResearchContinuationResponse = {
  schema?: string;
  algorithm_version?: string;
  available?: boolean;
  read_only?: boolean;
  idempotent_replay?: boolean;
  request_id?: string;
  job_id?: number;
  process?: string;
  status?: string;
  execution?: { kind?: string; model_calls?: number; external_calls?: number; process_advanced?: boolean; normalize_execution?: boolean };
  previous_next_process?: string;
  next_process?: string;
  done_steps?: number;
  output_ref?: string;
  input_sha256?: string;
  control?: { database_write?: boolean; decision_write?: boolean; state_advance?: boolean; promotion?: string; publication?: boolean };
  provenance?: { source?: string; deterministic?: boolean; interpretation_performed?: boolean; human_confirmation_required_for_next_transition?: boolean };
  error?: string;
  detail?: string;
};

export type ResearchHumanConfirmationResponse = ResearchContinuationResponse & {
  actor_id?: string;
  actor_kind?: string;
  execution?: { kind?: string; process_advanced?: boolean; normalize_execution?: boolean };
};

export type ParsePedidoResponse = {
  tipo?: string;
  medidas?: string;
  formato?: string;
  tool?: string;
  pub?: string;
  warnings?: string[];
  match?: boolean;
  source?: string;
  error?: string;
  [key: string]: unknown;
};

export type CreateJobResponse = {
  created?: boolean;
  job_path?: string;
  name?: string;
  next?: string;
  error?: string;
};

export type LearningEpisode = {
  episode_id?: string;
  project_id?: string;
  status?: string;
  phase?: string;
  objective?: string;
  started_at?: string;
  finished_at?: string;
};

export type ProjectLearningSummary = {
  available?: boolean;
  database?: string;
  reason?: string;
  projects?: Record<string, number>;
  episodes?: Record<string, number>;
  rules?: Record<string, number>;
  contracts?: {
    available?: boolean;
    counts?: Record<string, number>;
    statuses?: Record<string, number>;
    reason?: string;
  };
  audits?: {
    available?: boolean;
    latest_run?: string | null;
    statuses?: Record<string, number>;
    attention?: Array<{ contract_id?: string; status?: string; missing?: string[] }>;
    reason?: string;
  };
  latest_abstain?: LearningEpisode | null;
};

export type OperationalAttention = {
  id?: string;
  kind?: string;
  status?: string;
  severity?: 'info' | 'attention' | 'blocked' | string;
  reason?: string;
  next_action?: string;
  ref?: string;
};

export type OperationalComponent = {
  id?: string;
  label?: string;
  status?: 'ready' | 'active' | 'attention' | 'blocked' | string;
  severity?: 'none' | 'info' | 'attention' | 'blocked' | string;
  read_only?: boolean;
  evidence?: Record<string, unknown>;
  next_action?: string;
};

export type OperationalStatus = {
  schema?: 'mak-system-status-v1' | 'mak-operational-status-v1' | string;
  status?: 'ready' | 'attention' | 'blocked' | 'unknown' | string;
  generated_at?: string;
  database?: string;
  read_only?: boolean;
  repo_root?: string | null;
  physical_root?: string | null;
  learning?: ProjectLearningSummary;
  ledger?: Record<string, unknown>;
  components?: Record<string, OperationalComponent>;
  attention?: OperationalAttention[];
  counts?: { attention?: number; blocked?: number; info?: number; components?: number };
  next_actions?: string[];
};

export type HubStatus = {
  status?: string;
  version?: string;
  root?: string;
  has_svg?: boolean;
  has_projects?: boolean;
  connected?: boolean;
  time?: number;
  operational?: OperationalStatus;
};

export type ProjectProbeResponse = {
  ok?: boolean;
  error?: string;
  decision?: Record<string, unknown>;
  probe?: Record<string, unknown>;
  learning?: ProjectLearningSummary;
  recorded?: boolean;
};

export type ProjectReviewQueueItem = {
  project_id: string;
  title: string;
  state: string;
  role: string;
  scope: string;
  assets: number;
  bytes_direct: number;
  bytes_subtree: number;
  media_mix: Record<string, number>;
  parent: string | null;
  rejection_leverage: number;
  pending_descendants: string[];
  unknowns: string[];
  evidence: Array<Record<string, unknown>>;
  updated_at: string;
  decisions_available: string[];
};

export type ProjectReviewQueueResponse = {
  schema?: string;
  available?: boolean;
  read_only?: boolean;
  review_pass?: string;
  summary?: {
    pending?: number;
    roots?: number;
    max_rejection_leverage?: number;
    answers_to_clear_by_containment?: number;
    bytes?: number;
    assets?: number;
    by_role?: Record<string, number>;
    by_scope?: Record<string, number>;
  };
  items?: ProjectReviewQueueItem[];
  controls?: {
    database_write?: boolean;
    decision_write?: boolean;
    promotion?: string;
    publication?: boolean;
  };
  provenance?: {
    source?: string;
    database?: string;
    deterministic?: boolean;
    decisions_require_external_human_actor?: boolean;
  };
  error?: string;
  detail?: string;
};

export type ArchivePortfolioFormat = {
  format_id: string;
  purpose?: string;
  item_ids?: string[];
  omitted_count?: number;
};

export type ArchivePortfolioViewResponse = {
  schema?: string;
  algorithm_version?: string;
  scope?: string;
  status?: string;
  source?: {
    path_hint?: string;
    input_hash?: string;
    fuente?: string;
  };
  formats?: ArchivePortfolioFormat[];
  selection?: {
    declared_work_count?: number;
    documented_record_count?: number;
    observed_field_count?: number;
    practice_context_count?: number;
    selected_item_count?: number;
    omitted_piece_count?: number;
  };
  reconciliation?: {
    source_piece_count?: number;
    selected_item_count?: number;
    omitted_piece_count?: number;
    truth_promotions?: number;
  };
  control?: {
    dispatch?: boolean;
    promotion?: string;
    publication?: boolean;
    source_mutation?: boolean;
    submission?: boolean;
    training_permitted?: boolean;
  };
  provenance?: {
    deterministic?: boolean;
    filename_is_not_authorship?: boolean;
    observed_text_is_not_author_statement?: boolean;
    unselected_source_items_remain_in_input?: boolean;
  };
  gaps?: string[];
  contracurator?: {
    status?: string;
    input?: { visible_item_count?: number };
    result?: {
      selected_thesis_id?: string;
      exhibition?: {
        title?: string;
        why_in?: Array<Record<string, unknown>>;
        why_out?: Array<Record<string, unknown>>;
      };
      limits?: string[];
    };
    theses?: Array<{
      thesis_id?: string;
      position?: string;
      assessment?: { status?: string; rejection_reasons?: string[] };
      counterevidence?: Array<{ statement?: string; reason?: string; source_refs?: string[] }>;
    }>;
  };
  error?: string;
  detail?: string;
};

export type ArchiveOrientationResponse = {
  schema?: string;
  algorithm_version?: string;
  available?: boolean;
  read_only?: boolean;
  source?: { schema?: string; path_hint?: string; input_hash?: string; source_piece_count?: number; source_link_count?: number; projected_link_count?: number };
  axes?: Array<{ format_id?: string; role?: string; purpose?: string; selection_rule?: string[]; item_count?: number; omitted_count?: number }>;
  selection?: { visible_item_count?: number; declared_work_count?: number; documented_record_count?: number; observed_field_count?: number; practice_context_count?: number; omitted_piece_count?: number };
  boundary?: { filename_is_not_authorship?: boolean; observed_text_is_not_author_statement?: boolean; unselected_source_items_remain_in_input?: boolean; semantic_claim?: boolean };
  control?: { database_write?: boolean; decision_write?: boolean; state_advance?: boolean; selection_effect?: string; promotion?: string; publication?: boolean };
  next_action?: string;
  error?: string;
  detail?: string;
};

export type AreaOrientationArea = {
  id?: string;
  label?: string;
  kind?: string;
  observed_status?: string;
  status_basis?: string[];
  route?: string;
  contract_ref?: string;
  checks?: string[];
  next_action?: string;
  read_only?: boolean;
  semantic_claim?: boolean;
  execution_allowed?: boolean;
};

export type AreaOrientationResponse = {
  schema?: string;
  algorithm_version?: string;
  available?: boolean;
  read_only?: boolean;
  generated_at?: string;
  system?: { observed_status?: string; attention_count?: number; next_actions?: string[] };
  areas?: AreaOrientationArea[];
  departments?: Array<{ id?: string; label?: string; surface?: string; observed_status?: string; runtime_mode?: string; contract_dir?: string; handoff_exists?: boolean; tool_routes?: string[]; read_only?: boolean; semantic_claim?: boolean; execution_allowed?: boolean }>;
  boundary?: { status_is_operational_observation?: boolean; catalogue_is_not_semantic_knowledge?: boolean; learning_is_not_promotion?: boolean; vizz_measurement_refusal_is_preserved?: boolean; semantic_claim?: boolean };
  control?: { database_write?: boolean; decision_write?: boolean; state_advance?: boolean; selection_effect?: string; promotion?: string; publication?: boolean; execution?: boolean };
  next_action?: string;
  error?: string;
  detail?: string;
};

export type OperationsReadOnlyMapEntry = {
  domain?: string;
  endpoint?: string;
  source_schema?: string;
  surface_kind?: string;
  observed_status?: string;
  counts?: Record<string, number>;
  source_hash_or_ref?: string;
  next_action?: string;
  controls?: Record<string, unknown>;
  claims?: { semantic_claim?: boolean; relation_inference?: boolean; learning_demonstrated?: string };
};

export type OperationsReadOnlyMapResponse = {
  schema?: string;
  algorithm_version?: string;
  available?: boolean;
  read_only?: boolean;
  generated_at?: string;
  entries?: OperationsReadOnlyMapEntry[];
  boundary?: Record<string, unknown>;
  control?: Record<string, unknown>;
  next_action?: string;
  error?: string;
  detail?: string;
};

export type RdReadOnlyContextResponse = {
  schema?: string;
  algorithm_version?: string;
  available?: boolean;
  read_only?: boolean;
  generated_at?: string;
  source?: { summary_schema?: string; canonical_projection?: string; legacy_runtime_boundary?: string; crosswalk_status?: string };
  topics?: { schema?: string; read_only?: boolean; mutation?: string; topic_count?: number; canonical_rows?: number; runtime_rows?: number };
  crosswalk?: { schema?: string; status?: string; mutation?: string; identity_join?: string; entity_count?: number };
  relations?: { schema?: string; status?: string; mutation?: string; join_rule?: string; producer_count?: number; venue_count?: number; relation_count?: number };
  boundary?: { crosswalk_is_review_only?: boolean; candidate_graph_is_unconfirmed?: boolean; identity_requires_explicit_provenance?: boolean; counts_are_checkout_local?: boolean; semantic_claim?: boolean };
  control?: Record<string, unknown>;
  next_action?: string;
  error?: string;
  detail?: string;
};

export type CulturaResearchReadOnlyContextResponse = {
  schema?: string;
  algorithm_version?: string;
  available?: boolean;
  read_only?: boolean;
  generated_at?: string;
  cultura?: { sources_schema?: string; root_count?: number; entry_count?: number; truncated?: boolean; capabilities_schema?: string; offline?: Record<string, boolean>; output_format_count?: number; opportunity_gate_schema?: string; opportunity_mode?: string; required_field_count?: number; provider_policy?: Record<string, string> };
  research?: { catalog_schema?: string; jobs_schema?: string; adapter_count?: number; catalog_job_count?: number; observed_job_count?: number; job_status_counts?: Record<string, number> };
  boundary?: Record<string, unknown>;
  control?: Record<string, unknown>;
  next_action?: string;
  error?: string;
  detail?: string;
};

export type PortfolioVizzReadOnlyContextResponse = {
  schema?: string;
  algorithm_version?: string;
  available?: boolean;
  read_only?: boolean;
  generated_at?: string;
  source?: { measurement_schema?: string; lineage_schema?: string; delta_schema?: string; preview_schema?: string };
  measurement?: { status?: string; calibration_status?: string; triangulation_attempted?: boolean; depth_result_present?: boolean; claim_allowed?: boolean };
  lineage?: { status?: string; current_status?: string; revision_status?: string; current_state_replaced?: boolean; current_ref?: string };
  delta?: { status?: string; shared_keys?: number; residue_keys?: number; serialized_savings_bytes?: number; learning_demonstrated?: boolean };
  preview?: { task_id?: string; state?: string; human_gate?: string; project_id?: string; relation_status?: string; preview_only?: boolean; execution_allowed?: boolean; task_execution?: boolean };
  boundary?: Record<string, unknown>;
  control?: Record<string, unknown>;
  next_action?: string;
  error?: string;
  detail?: string;
};

export type LearningReadOnlyContextResponse = {
  schema?: string;
  algorithm_version?: string;
  available?: boolean;
  read_only?: boolean;
  generated_at?: string;
  source?: { status_schema?: string; learning_database?: string; learning_available?: boolean };
  policy?: { schema?: string; status?: string; reason?: string; eligible_examples?: number; excluded?: Record<string, number>; recordable?: boolean; train_count?: number; holdout_count?: number; holdout_accuracy?: number; holdout_baseline?: number };
  ledger?: { projects?: Record<string, number>; episodes?: Record<string, number>; episodes_open?: Record<string, number>; rules?: Record<string, number> };
  boundary?: Record<string, unknown>;
  control?: Record<string, unknown>;
  next_action?: string;
  error?: string;
  detail?: string;
};

export type PortfolioReviewContextResponse = {
  schema?: string;
  algorithm_version?: string;
  available?: boolean;
  read_only?: boolean;
  archive?: {
    schema?: string;
    source_hash?: string;
    source_ref?: string;
    visible_item_count?: number;
    omitted_item_count?: number;
  };
  project?: {
    project_id?: string | null;
    episode_id?: string | null;
    title?: string | null;
    state?: string | null;
    found_in_review_queue?: boolean;
    unknowns?: string[];
    evidence?: Array<Record<string, unknown>>;
    next_action?: string;
  };
  relation?: {
    status?: string;
    typed_relation_present?: boolean;
    evidence_refs?: string[];
    selection_effect?: string;
    reason?: string;
  };
  control?: {
    database_write?: boolean;
    decision_write?: boolean;
    promotion?: string;
    publication?: boolean;
  };
  provenance?: {
    archive_source?: string;
    project_source?: string;
    deterministic?: boolean;
    relation_inference?: boolean;
    name_or_path_matching?: boolean;
    decisions_require_external_human_actor?: boolean;
  };
  error?: string;
  detail?: string;
};

export type PortfolioRelationEvidencePlanResponse = {
  schema?: string;
  algorithm_version?: string;
  available?: boolean;
  read_only?: boolean;
  project?: { project_id?: string; title?: string; state?: string; unknown_count?: number; observed_evidence_count?: number };
  relation?: { status?: string; typed_relation_present?: boolean; selection_effect?: string; evidence_refs?: string[] };
  requirements?: Array<{ requirement_id?: string; unknown?: string; expected_evidence_kind?: string; status?: string; candidate_count?: number }>;
  observed_evidence?: Array<{ kind?: string; status?: string; reference_present?: boolean; reference_class?: string }>;
  unresolved_count?: number;
  next_action?: string;
  control?: { database_write?: boolean; decision_write?: boolean; state_advance?: boolean; selection_effect?: string; promotion?: string; publication?: boolean };
  provenance?: { source_schema?: string; deterministic?: boolean; relation_inference?: boolean; path_or_name_matching?: boolean; semantic_claim?: boolean; learning_demonstrated?: boolean; decisions_require_external_human_actor?: boolean };
  error?: string;
  detail?: string;
};

export type OperationReceiptResponse = {
  schema?: string;
  algorithm_version?: string;
  available?: boolean;
  read_only?: boolean;
  status?: string;
  source?: { kind?: string; ref?: string; sha256?: string };
  operation?: {
    name?: string;
    dialect?: string;
    expanded_keys?: string[];
    expanded_count?: number;
    execution_reason?: string;
  };
  provenance?: {
    library_source_ref?: string;
    evaluation_source_ref?: string;
    package_sha256?: string;
  };
  rejected_attempts?: Array<{ kind?: string; reason?: string }>;
  control?: {
    database_write?: boolean;
    decision_write?: boolean;
    selection_effect?: string;
    promotion?: string;
    publication?: boolean;
    semantic_equivalence_authorized?: boolean;
  };
  limitations?: string[];
  error?: string;
  detail?: string;
};

export type VizzMeasurementStatusResponse = {
  schema?: string;
  algorithm_version?: string;
  available?: boolean;
  read_only?: boolean;
  status?: string;
  measurement?: {
    status?: string;
    unknown?: boolean;
    triangulation_attempted?: boolean;
    depth_result_present?: boolean;
    calibration_status?: string;
  };
  reason?: string;
  provenance?: { ref?: string; sha256?: string; source_schema?: string; calibration_audit_sha256?: string | null; calibration_provenance_ref?: string | null };
  next_action?: string;
  control?: {
    database_write?: boolean;
    decision_write?: boolean;
    selection_effect?: string;
    promotion?: string;
    publication?: boolean;
  };
  error?: string;
  detail?: string;
};

export type VizzLineageStatusResponse = {
  schema?: string;
  algorithm_version?: string;
  available?: boolean;
  read_only?: boolean;
  status?: string;
  current?: { ref?: string; sha256?: string; status?: string };
  revision?: { revision_id?: string; previous_artifact_sha256?: string; current_artifact_sha256?: string; status?: string };
  provenance?: { ref?: string; sha256?: string; source_schema?: string };
  control?: {
    database_write?: boolean;
    decision_write?: boolean;
    selection_effect?: string;
    promotion?: string;
    publication?: boolean;
    current_state_replaced?: boolean;
  };
  error?: string;
  detail?: string;
};

export type StructuralDeltaStatusResponse = {
  schema?: string;
  algorithm_version?: string;
  available?: boolean;
  read_only?: boolean;
  status?: string;
  delta?: {
    revision_only_key?: string;
    evaluated_keys?: number;
    shared_keys?: number;
    residue_keys?: number;
    baseline_bytes?: number;
    library_total_bytes?: number;
    serialized_savings_bytes?: number;
  };
  provenance?: { ref?: string; sha256?: string; library_pin?: string; evaluation_pin?: string };
  control?: {
    database_write?: boolean;
    decision_write?: boolean;
    selection_effect?: string;
    promotion?: string;
    publication?: boolean;
    learning_demonstrated?: boolean;
  };
  limits?: string[];
  error?: string;
  detail?: string;
};

export type PortfolioDirectionContextResponse = {
  schema?: string;
  algorithm_version?: string;
  available?: boolean;
  read_only?: boolean;
  purpose?: string;
  frame?: {
    vision?: {
      state?: string;
      archive_status?: string;
      source_hash?: string;
      visible_item_count?: number;
      declared_work_count?: number;
      internal_hypothesis_status?: string;
      semantic_claim_established?: boolean;
      next_action?: string;
    };
    order?: {
      state?: string;
      operation_status?: string;
      operation_name?: string;
      expanded_count?: number;
      delta_status?: string;
      evaluated_keys?: number;
      shared_keys?: number;
      residue_keys?: number;
      semantic_equivalence_established?: boolean;
      next_action?: string;
    };
    culture_computation?: {
      state?: string;
      practice_context_count?: number;
      observed_field_count?: number;
      documented_record_count?: number;
      omitted_piece_count?: number;
      project_relation_status?: string;
      project_evidence_count?: number;
      project_unknown_count?: number;
      relation_inference?: boolean;
      next_action?: string;
    };
    instrument?: {
      state?: string;
      measurement_status?: string;
      measurement_unknown?: boolean;
      triangulation_attempted?: boolean;
      depth_result_present?: boolean;
      lineage_status?: string;
      measurement_claim_allowed?: boolean;
      next_action?: string;
    };
  };
  directions?: Array<{ id?: string; kind?: string; state?: string; human_gate?: string }>;
  next_action?: string;
  control?: {
    database_write?: boolean;
    decision_write?: boolean;
    state_advance?: boolean;
    selection_effect?: string;
    promotion?: string;
    publication?: boolean;
    normalize_execution?: boolean;
    measurement_execution?: boolean;
  };
  provenance?: {
    components?: string[];
    deterministic?: boolean;
    relation_inference?: boolean;
    semantic_claim?: boolean;
    semantic_equivalence?: boolean;
    learning_demonstrated?: boolean;
    decisions_require_external_human_actor?: boolean;
  };
  error?: string;
  detail?: string;
};

export type PortfolioWorkPacketResponse = {
  schema?: string;
  algorithm_version?: string;
  available?: boolean;
  read_only?: boolean;
  source?: { schema?: string; purpose?: string; next_action?: string; project_id?: string | null; relation_status?: string };
  tasks?: Array<{ id?: string; area?: string; layer?: string; state?: string; evidence?: string; action?: string; human_gate?: string; execution_allowed?: boolean }>;
  execution?: { task_count?: number; executed_task_count?: number; execution_allowed?: boolean; state_advance?: boolean };
  next_action?: string;
  control?: { database_write?: boolean; decision_write?: boolean; state_advance?: boolean; selection_effect?: string; promotion?: string; publication?: boolean; normalize_execution?: boolean; measurement_execution?: boolean };
  provenance?: { direction_schema?: string; deterministic?: boolean; task_execution?: boolean; semantic_claim?: boolean; learning_demonstrated?: boolean; decisions_require_external_human_actor?: boolean };
  error?: string;
  detail?: string;
};

export type PortfolioWorkPreviewResponse = {
  schema?: string;
  algorithm_version?: string;
  available?: boolean;
  read_only?: boolean;
  preview_only?: boolean;
  source?: { schema?: string; task_id?: string; task_count?: number; project_id?: string | null; relation_status?: string };
  task?: { id?: string; area?: string; layer?: string; state?: string; evidence?: string; action?: string; human_gate?: string; execution_allowed?: boolean };
  next_action?: string;
  control?: { database_write?: boolean; decision_write?: boolean; state_advance?: boolean; selection_effect?: string; promotion?: string; publication?: boolean; normalize_execution?: boolean; measurement_execution?: boolean };
  provenance?: { packet_schema?: string; project_id?: string | null; relation_status?: string; typed_relation_present?: boolean; deterministic?: boolean; task_execution?: boolean; semantic_claim?: boolean; learning_demonstrated?: boolean; decisions_require_external_human_actor?: boolean };
  error?: string;
  detail?: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json() as Promise<T>;
}

function isFileMode(): boolean {
  return typeof window !== 'undefined' && window.location.protocol === 'file:';
}

export const demoJobs: JobsResponse = {
  jobs: [
    { name: 'demo_eventos_flyer', estado: 'por-revisar', tipo_pieza: 'flyer', proyecto: 'EVENTOS', pendientes: ['link Instagram', 'confirmar fecha'] },
    { name: 'demo_suplementos_etiqueta', estado: 'en-diseno', tipo_pieza: 'etiqueta', proyecto: 'SUPLEMENTOS', pendientes: ['tabla nutricional'] },
    { name: 'demo_sticker_pack', estado: 'entregado', tipo_pieza: 'sticker', proyecto: 'SUPLEMENTOS', pendientes: [] },
    { name: 'demo_pendon_evento', estado: 'revision', tipo_pieza: 'pendon', proyecto: 'EVENTOS', pendientes: ['ajustar medidas', 'confirmar logo'] },
  ],
  count: 4,
  source: 'demo',
};

export const flujoApi = {
  isFileMode,

  async ping(): Promise<Ping> {
    if (isFileMode()) return { status: 'demo', version: 'offline', connected: false, mode: 'file' };
    try {
      return await request<Ping>('/api/ping');
    } catch {
      // Sin backend no hay version que informar: mentir con una vieja es peor que omitirla.
      return { status: 'demo', version: '', connected: false, note: 'Backend no disponible' };
    }
  },

  async jobs(): Promise<JobsResponse> {
    if (isFileMode()) return demoJobs;
    try {
      return await request<JobsResponse>('/api/list-jobs');
    } catch (error) {
      return { ...demoJobs, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async researchJobs(): Promise<ResearchJobsResponse> {
    if (isFileMode()) return { available: false, jobs: [], error: 'file_mode' };
    try {
      return await request<ResearchJobsResponse>('/api/research/jobs');
    } catch (error) {
      return { available: false, jobs: [], error: error instanceof Error ? error.message : String(error) };
    }
  },

  async researchJob(jobId: number): Promise<ResearchJobResponse> {
    if (isFileMode()) return { available: false, error: 'file_mode' };
    try {
      return await request<ResearchJobResponse>(`/api/research/job?id=${encodeURIComponent(jobId)}`);
    } catch (error) {
      return { available: false, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async confirmResearchExtraction(jobId: number, actor: string, inputSha256: string, requestId: string): Promise<ResearchHumanConfirmationResponse> {
    if (isFileMode()) return { available: false, read_only: false, error: 'file_mode' };
    try {
      return await request<ResearchHumanConfirmationResponse>('/api/research/job/confirm-extraction', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: jobId, actor, input_sha256: inputSha256, request_id: requestId }),
      });
    } catch (error) {
      return { available: false, read_only: false, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async researchNormalizeReadiness(jobId: number): Promise<ResearchNormalizeReadinessResponse> {
    if (isFileMode()) return { available: false, read_only: true, error: 'file_mode' };
    try {
      return await request<ResearchNormalizeReadinessResponse>(`/api/research/job/normalize-readiness?id=${encodeURIComponent(jobId)}`);
    } catch (error) {
      return { available: false, read_only: true, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async researchNormalizePlan(jobId: number): Promise<ResearchNormalizePlanResponse> {
    if (isFileMode()) return { available: false, read_only: true, error: 'file_mode' };
    try {
      return await request<ResearchNormalizePlanResponse>(`/api/research/job/normalize-plan?id=${encodeURIComponent(jobId)}`);
    } catch (error) {
      return { available: false, read_only: true, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async researchNormalizeDryRun(jobId: number): Promise<ResearchNormalizeDryRunResponse> {
    if (isFileMode()) return { available: false, read_only: true, error: 'file_mode' };
    try {
      return await request<ResearchNormalizeDryRunResponse>(`/api/research/job/normalize-dry-run?id=${encodeURIComponent(jobId)}`);
    } catch (error) {
      return { available: false, read_only: true, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async researchLicenseReview(jobId: number): Promise<ResearchLicenseReviewResponse> {
    if (isFileMode()) return { available: false, read_only: true, error: 'file_mode' };
    try {
      return await request<ResearchLicenseReviewResponse>(`/api/research/job/license-review?id=${encodeURIComponent(jobId)}`);
    } catch (error) {
      return { available: false, read_only: true, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async researchLicenseSourceReview(jobId: number): Promise<ResearchLicenseSourceReviewResponse> {
    if (isFileMode()) return { available: false, read_only: true, error: 'file_mode' };
    try {
      return await request<ResearchLicenseSourceReviewResponse>(`/api/research/job/license-source-review?id=${encodeURIComponent(jobId)}`);
    } catch (error) {
      return { available: false, read_only: true, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async researchLicenseCompatibilityPlan(jobId: number): Promise<ResearchLicenseCompatibilityPlanResponse> {
    if (isFileMode()) return { available: false, read_only: true, error: 'file_mode' };
    try {
      return await request<ResearchLicenseCompatibilityPlanResponse>(`/api/research/job/license-compatibility-plan?id=${encodeURIComponent(jobId)}`);
    } catch (error) {
      return { available: false, read_only: true, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async resumeResearchJob(jobId: number, expectedProcess: string, requestId: string): Promise<ResearchContinuationResponse> {
    if (isFileMode()) return { available: false, read_only: false, error: 'file_mode' };
    try {
      return await request<ResearchContinuationResponse>('/api/research/job/resume', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: jobId, expected_process: expectedProcess, request_id: requestId }),
      });
    } catch (error) {
      return { available: false, read_only: false, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async projectLearning(): Promise<ProjectLearningSummary> {
    if (isFileMode()) return { available: false, reason: 'file_mode' };
    try {
      return await request<ProjectLearningSummary>('/api/project/learning');
    } catch (error) {
      return { available: false, reason: error instanceof Error ? error.message : String(error) };
    }
  },

  async status(): Promise<HubStatus> {
    if (isFileMode()) {
      return {
        status: 'demo',
        connected: false,
        operational: { status: 'unknown', next_actions: ['open the local Hub backend to read MAK status'] },
      };
    }
    try {
      return await request<HubStatus>('/api/status');
    } catch (error) {
      return {
        status: 'unavailable',
        connected: false,
        operational: {
          status: 'unknown',
          next_actions: [error instanceof Error ? error.message : String(error)],
        },
      };
    }
  },

  async areaOrientation(): Promise<AreaOrientationResponse> {
    if (isFileMode()) return { available: false, read_only: true, error: 'file_mode' };
    try {
      return await request<AreaOrientationResponse>('/api/mak/area-orientation');
    } catch (error) {
      return { available: false, read_only: true, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async operationsReadOnlyMap(): Promise<OperationsReadOnlyMapResponse> {
    if (isFileMode()) return { available: false, read_only: true, error: 'file_mode' };
    try {
      return await request<OperationsReadOnlyMapResponse>('/api/operations/read-only-map');
    } catch (error) {
      return { available: false, read_only: true, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async rdReadOnlyContext(): Promise<RdReadOnlyContextResponse> {
    if (isFileMode()) return { available: false, read_only: true, error: 'file_mode' };
    try {
      return await request<RdReadOnlyContextResponse>('/api/rd/read-only-context');
    } catch (error) {
      return { available: false, read_only: true, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async culturaResearchReadOnlyContext(): Promise<CulturaResearchReadOnlyContextResponse> {
    if (isFileMode()) return { available: false, read_only: true, error: 'file_mode' };
    try {
      return await request<CulturaResearchReadOnlyContextResponse>('/api/cultura/research-read-only-context');
    } catch (error) {
      return { available: false, read_only: true, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async portfolioVizzReadOnlyContext(projectId?: string): Promise<PortfolioVizzReadOnlyContextResponse> {
    if (isFileMode()) return { available: false, read_only: true, error: 'file_mode' };
    try {
      const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : '';
      return await request<PortfolioVizzReadOnlyContextResponse>(`/api/portfolio/vizz-read-only-context${query}`);
    } catch (error) {
      return { available: false, read_only: true, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async learningReadOnlyContext(): Promise<LearningReadOnlyContextResponse> {
    if (isFileMode()) return { available: false, read_only: true, error: 'file_mode' };
    try {
      return await request<LearningReadOnlyContextResponse>('/api/project/learning-read-only-context');
    } catch (error) {
      return { available: false, read_only: true, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async projectProbe(project: unknown): Promise<ProjectProbeResponse> {
    if (isFileMode()) return { ok: false, error: 'file_mode' };
    try {
      return await request<ProjectProbeResponse>('/api/project/probe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project }),
      });
    } catch (error) {
      return { ok: false, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async projectReviewQueue(): Promise<ProjectReviewQueueResponse> {
    if (isFileMode()) return { available: false, read_only: true, error: 'file_mode' };
    try {
      return await request<ProjectReviewQueueResponse>('/api/project/review-queue?pass=prune');
    } catch (error) {
      return { available: false, read_only: true, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async archivePortfolioView(): Promise<ArchivePortfolioViewResponse> {
    if (isFileMode()) return { status: 'unavailable', error: 'file_mode' };
    try {
      return await request<ArchivePortfolioViewResponse>('/api/portfolio/archive-view');
    } catch (error) {
      return { status: 'unavailable', error: error instanceof Error ? error.message : String(error) };
    }
  },

  async archiveOrientation(): Promise<ArchiveOrientationResponse> {
    if (isFileMode()) return { available: false, read_only: true, error: 'file_mode' };
    try {
      return await request<ArchiveOrientationResponse>('/api/portfolio/archive-orientation');
    } catch (error) {
      return { available: false, read_only: true, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async portfolioReviewContext(projectId?: string): Promise<PortfolioReviewContextResponse> {
    if (isFileMode()) return { available: false, read_only: true, error: 'file_mode' };
    try {
      const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : '';
      return await request<PortfolioReviewContextResponse>(`/api/portfolio/review-context${query}`);
    } catch (error) {
      return { available: false, read_only: true, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async portfolioRelationEvidencePlan(projectId?: string): Promise<PortfolioRelationEvidencePlanResponse> {
    if (isFileMode()) return { available: false, read_only: true, error: 'file_mode' };
    try {
      const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : '';
      return await request<PortfolioRelationEvidencePlanResponse>(`/api/portfolio/relation-evidence-plan${query}`);
    } catch (error) {
      return { available: false, read_only: true, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async operationReceipt(): Promise<OperationReceiptResponse> {
    if (isFileMode()) return { available: false, read_only: true, error: 'file_mode' };
    try {
      return await request<OperationReceiptResponse>('/api/portfolio/operation-receipt');
    } catch (error) {
      return { available: false, read_only: true, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async vizzMeasurementStatus(): Promise<VizzMeasurementStatusResponse> {
    if (isFileMode()) return { available: false, read_only: true, error: 'file_mode' };
    try {
      return await request<VizzMeasurementStatusResponse>('/api/portfolio/vizz-measurement-status');
    } catch (error) {
      return { available: false, read_only: true, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async vizzLineageStatus(): Promise<VizzLineageStatusResponse> {
    if (isFileMode()) return { available: false, read_only: true, error: 'file_mode' };
    try {
      return await request<VizzLineageStatusResponse>('/api/portfolio/vizz-lineage-status');
    } catch (error) {
      return { available: false, read_only: true, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async structuralDeltaStatus(): Promise<StructuralDeltaStatusResponse> {
    if (isFileMode()) return { available: false, read_only: true, error: 'file_mode' };
    try {
      return await request<StructuralDeltaStatusResponse>('/api/portfolio/structural-delta-status');
    } catch (error) {
      return { available: false, read_only: true, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async portfolioDirectionContext(projectId?: string): Promise<PortfolioDirectionContextResponse> {
    if (isFileMode()) return { available: false, read_only: true, error: 'file_mode' };
    try {
      const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : '';
      return await request<PortfolioDirectionContextResponse>(`/api/portfolio/direction-context${query}`);
    } catch (error) {
      return { available: false, read_only: true, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async portfolioWorkPacket(projectId?: string): Promise<PortfolioWorkPacketResponse> {
    if (isFileMode()) return { available: false, read_only: true, error: 'file_mode' };
    try {
      const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : '';
      return await request<PortfolioWorkPacketResponse>(`/api/portfolio/work-packet${query}`);
    } catch (error) {
      return { available: false, read_only: true, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async portfolioWorkPreview(taskId: string, projectId?: string): Promise<PortfolioWorkPreviewResponse> {
    if (isFileMode()) return { available: false, read_only: true, error: 'file_mode' };
    try {
      const query = new URLSearchParams({ task_id: taskId });
      if (projectId) query.set('project_id', projectId);
      return await request<PortfolioWorkPreviewResponse>(`/api/portfolio/work-preview?${query.toString()}`);
    } catch (error) {
      return { available: false, read_only: true, error: error instanceof Error ? error.message : String(error) };
    }
  },

  async parsePedido(text: string): Promise<ParsePedidoResponse> {
    if (isFileMode()) {
      const low = text.toLowerCase();
      return {
        tipo: low.includes('plano') ? 'plano' : low.includes('suplement') ? 'etiqueta' : 'flyer',
        medidas: low.includes('instagram') ? '1080x1350' : 'segun pedido',
        formato: low.includes('suplement') ? 'sup_etiqueta_165x65' : 'evt_flyer_fisico_10x14',
        tool: low.includes('plano') ? 'plano' : 'render',
        warnings: ['Demo local: abre con py -m flujo app para parse real'],
        match: true,
        source: 'demo',
      };
    }
    return request<ParsePedidoResponse>('/api/parse-real-pedido', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
  },

  async createJobDraft(text: string, name = '', parsed?: ParsePedidoResponse | null): Promise<CreateJobResponse> {
    if (isFileMode()) return { created: false, error: 'Demo local: abre con py -m flujo app para crear jobs reales' };
    return request<CreateJobResponse>('/api/create-job-draft', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, name, parsed }),
    });
  },
};
