from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
EDITOR = REPO_ROOT / "iskvw" / "editor.html"
NODE_AVAILABLE = pytest.mark.skipif(
    shutil.which("node") is None, reason="node no esta en el PATH")
pytestmark = pytest.mark.flujo


def _html() -> str:
    return EDITOR.read_text(encoding="utf-8")


def _function(name: str) -> str:
    text = _html()
    declaration = re.search(
        rf"(?m)^(?:async )?function {re.escape(name)}\(", text)
    assert declaration, f"no pude encontrar {name}()"
    following = re.search(
        r"(?m)^(?:async )?function ", text[declaration.end():])
    end = declaration.end() + following.start() if following else len(text)
    return text[declaration.start():end].strip()


def _run_node(script: str) -> dict:
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_archive_view_is_integrated_read_only_and_accessible() -> None:
    text = _html()

    assert "fetch('/api/portfolio/archive-view',{cache:'no-store'})" in text
    assert "id=\"archive-portfolio-view\"" in text
    assert "aria-labelledby=\"archive-portfolio-title\"" in text
    assert "role=\"status\"" in text
    assert "role=\"alert\"" in text
    assert "onclick=\"estudioRail('portfolio')\"" in text
    assert "void cargarArchivePortfolioView();" in text
    loader = _function("cargarArchivePortfolioView")
    assert "method:" not in loader
    assert "/api/portfolio/select" not in loader
    assert "/api/portfolio/classify" not in loader
    assert "/api/portfolio/dispatch" not in loader


def test_four_contract_formats_and_epistemic_boundaries_are_visible() -> None:
    text = _html()
    constant = re.search(
        r"const ARCHIVE_VIEW_FORMAT_IDS = \[([^\]]+)\];", text)
    assert constant
    assert re.findall(r"'([^']+)'", constant.group(1)) == [
        "declared-works", "documented-record", "observed-field", "practice-context"]
    assert "no es título autoral" in text
    assert "contexto técnico · no obra automáticamente" in text
    assert "es registro de una obra, no la obra" in text
    assert "No infiere autor, serie, publicación ni elegibilidad" in text
    assert "publicación=false · submission=false · dispatch=false · promotion=none" in text


@NODE_AVAILABLE
def test_untitled_rows_use_only_a_neutral_item_reference() -> None:
    script = "\n".join([
        _function("esc"),
        _function("archiveViewText"),
        _function("archiveViewDisplayLabel"),
        _function("archiveViewFormatNote"),
        _function("archiveViewItem"),
        _function("archiveViewReference"),
        "const item={item_id:'artist-name/Famous-Work-FINAL',title:null,summary:null,observed_description:'Machine-observed blue form.',date:null,tags:['archive'],link_degree:2,source_ref:'iskvw:piece:artist-name/Famous-Work-FINAL',epistemic_status:'observed_source_record'};",
        "const localTitle=archiveViewDisplayLabel({item_id:'local',title:'~/private-work'});",
        "const label=archiveViewDisplayLabel(item);",
        "const html=archiveViewItem(item,'observed-field');",
        "const note=archiveViewFormatNote('observed-field');",
        "console.log(JSON.stringify({label,localTitle,html,note}));",
    ])
    result = _run_node(script)

    assert result["label"] == {
        "text": "ref · artist-name/Famous-Work-FINAL", "neutral": True}
    assert result["localTitle"] == {"text": "referencia local", "neutral": True}
    assert 'data-neutral="true"' in result["html"]
    assert "etiqueta de referencia · no es título autoral" in result["html"]
    assert "observación de fuente · no declaración del artista" not in result["html"]
    assert result["note"] == {
        "role": "observación de fuente · no declaración del artista",
        "status": "observed_source_record",
    }


@NODE_AVAILABLE
def test_editor_redacts_absolute_evidence_references_but_keeps_logical_refs() -> None:
    script = "\n".join([
        _function("esc"),
        _function("archiveViewReference"),
        _function("archiveViewText"),
        _function("archiveViewMediaPath"),
        _function("archiveViewEvidenceList"),
        "const html=archiveViewEvidenceList([{statement:'missing',source_ref:'/home/mak/private.json'},{statement:'logical',source_ref:'iskvw:piece:declared'}],'Evidencia');",
        "console.log(JSON.stringify({local:archiveViewReference('/home/mak/private.json'),windows:archiveViewReference('C:\\\\Users\\\\<usuario>.json'),file:archiveViewReference('file:///home/mak/private.json'),logical:archiveViewReference('iskvw:piece:declared'),media_local:archiveViewMediaPath('/home/mak/private.jpg'),media_relative:archiveViewMediaPath('posts/private.jpg'),html}));",
    ])
    result = _run_node(script)

    assert result["local"] == "referencia local"
    assert result["windows"] == "referencia local"
    assert result["file"] == "referencia local"
    assert result["logical"] == "iskvw:piece:declared"
    assert result["media_local"] == ""
    assert result["media_relative"] == "posts/private.jpg"
    assert "/home/mak/private.json" not in result["html"]
    assert "referencia local" in result["html"]
    assert "iskvw:piece:declared" in result["html"]


@NODE_AVAILABLE
def test_full_archive_render_redacts_embedded_local_text() -> None:
    script = "\n".join([
        _function("esc"),
        _function("archiveViewText"),
        _function("archiveViewReference"),
        _function("archiveViewDisplayLabel"),
        _function("archiveViewFormatLabel"),
        _function("archiveViewFormatNote"),
        _function("archiveViewItem"),
        _function("archiveViewContracurator"),
        _function("archiveViewReadyContent"),
        "const view={catalog:{piece_count:1,link_count:0},selection:{selected_item_count:1,omitted_piece_count:0},source:{path_hint:'iskvw/datos/archivo.json',fuente:'file:///home/mak/source.json',generated:'today',input_hash:'sha256:'+'a'.repeat(64)},formats:[{format_id:'declared-works',purpose:'declared',item_ids:['private'],omitted_count:0},{format_id:'documented-record',purpose:'documented',item_ids:[],omitted_count:0},{format_id:'observed-field',purpose:'observed',item_ids:[],omitted_count:0},{format_id:'practice-context',purpose:'practice',item_ids:[],omitted_count:0}],items:[{item_id:'private',title:'obra ~/private',summary:'ver /home/mak/secret',tags:['/tmp/tag'],link_degree:0,source_ref:'iskvw:piece:private'}],gaps:[],contracurator:null};",
        "const html=archiveViewReadyContent(view);",
        "console.log(JSON.stringify({html}));",
    ])
    result = _run_node(script)

    assert "~/private" not in result["html"]
    assert "/home/mak/secret" not in result["html"]
    assert "/tmp/tag" not in result["html"]
    assert "file:///home/mak/source.json" not in result["html"]
    assert "referencia local" in result["html"]


@NODE_AVAILABLE
def test_client_contract_accepts_all_four_formats_and_rejects_partial_data() -> None:
    text = _html()
    formats = re.search(
        r"const ARCHIVE_VIEW_FORMAT_IDS = \[[^\]]+\];", text)
    assert formats
    payload = {
        "schema": "mak-archive-portfolio-view-v1",
        "scope": "general_archive_portfolio",
        "status": "draft_only",
        "source": {
            "kind": "iskvw_archive_projection",
            "path_hint": "iskvw/datos/archivo.json",
            "input_hash": "sha256:" + "a" * 64,
        },
        "formats": [
            {"format_id": "declared-works", "purpose": "declared",
             "item_ids": ["declared"], "omitted_count": 0},
            {"format_id": "documented-record", "purpose": "documented record",
             "item_ids": ["documented"], "omitted_count": 0},
            {"format_id": "observed-field", "purpose": "observed",
             "item_ids": ["observed"], "omitted_count": 4},
            {"format_id": "practice-context", "purpose": "practice",
             "item_ids": ["practice"], "omitted_count": 2},
        ],
        "items": [
            {"item_id": item_id, "source_ref": f"iskvw:piece:{item_id}",
             "roles": [role], "title": title, "summary": None,
             "observed_description": None, "medium": {"tipo": "ninguno"},
             "epistemic_status": epistemic,
             "observed_description_is_not_author_statement": False}
            for item_id, role, title, epistemic in [
                ("declared", "declared_work", "Declared", "declared_source_record"),
                ("documented", "documented_record", None, "human_declared_record"),
                ("observed", "observed_archive_piece", None, "observed_source_record"),
                ("practice", "practice_context", None, "observed_source_record"),
            ]
        ],
        "relationships": [],
        "gaps": ["omitted_bounded_selection"],
        "catalog": {"piece_count": 9, "link_count": 0},
        "selection": {"selected_item_count": 4, "declared_work_count": 1,
                      "documented_record_count": 1,
                      "observed_field_count": 1, "practice_context_count": 1},
        "control": {"publication": False, "submission": False,
                    "dispatch": False, "source_mutation": False,
                    "promotion": "none"},
        "provenance": {"filename_is_not_authorship": True,
                       "observed_text_is_not_author_statement": True,
                       "source_hash": "sha256:" + "a" * 64},
        "reconciliation": {"truth_promotions": 0,
                           "source_preserved_by_hash": True},
    }
    script = "\n".join([
        formats.group(0),
        _function("archiveViewValidate"),
        f"const complete={json.dumps(payload)};",
        "const partial=structuredClone(complete);partial.formats.pop();",
        "console.log(JSON.stringify({complete:archiveViewValidate(complete),partial:archiveViewValidate(partial)}));",
    ])
    result = _run_node(script)

    assert result == {"complete": True, "partial": False}


@NODE_AVAILABLE
def test_503_and_invalid_contract_fail_closed_without_previous_rows() -> None:
    loader = _function("cargarArchivePortfolioView")
    script = f"""
let ARCHIVE_PORTFOLIO_VIEW={{items:[{{item_id:'stale-partial-row'}}]}};
let ARCHIVE_PORTFOLIO_STATE='ready';
const snapshots=[];
function archiveViewRefreshPanel(){{snapshots.push({{state:ARCHIVE_PORTFOLIO_STATE,view:ARCHIVE_PORTFOLIO_VIEW}});}}
function archiveViewValidate(payload){{return payload?.schema==='mak-archive-portfolio-view-v1';}}
let response={{ok:false,status:503,json:async()=>({{items:[{{item_id:'partial-from-error'}}]}})}};
async function fetch(){{return response;}}
{loader}
await cargarArchivePortfolioView();
const after503={{state:ARCHIVE_PORTFOLIO_STATE,view:ARCHIVE_PORTFOLIO_VIEW}};
ARCHIVE_PORTFOLIO_VIEW={{items:[{{item_id:'second-stale-row'}}]}};
ARCHIVE_PORTFOLIO_STATE='ready';
response={{ok:true,status:200,json:async()=>({{schema:'wrong',items:[{{item_id:'partial-invalid-row'}}]}})}};
await cargarArchivePortfolioView();
console.log(JSON.stringify({{after503,afterInvalid:{{state:ARCHIVE_PORTFOLIO_STATE,view:ARCHIVE_PORTFOLIO_VIEW}},snapshots}}));
"""
    result = _run_node(script)

    assert result["after503"] == {"state": "unavailable", "view": None}
    assert result["afterInvalid"] == {"state": "unavailable", "view": None}
    assert all(snapshot["view"] is None for snapshot in result["snapshots"])


@NODE_AVAILABLE
def test_editor_inline_javascript_parses_as_a_whole() -> None:
    text = _html()
    start = text.index("<script>") + len("<script>")
    end = text.index("</script>")
    result = subprocess.run(
        ["node", "--input-type=module", "--check", "-"],
        input=text[start:end],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert result.returncode == 0, result.stderr


@NODE_AVAILABLE
def test_operator_frontier_renders_evidence_and_never_claims_an_answer() -> None:
    script = "\n".join([
        _function("esc"),
        _function("archiveViewBytes"),
        _function("archiveViewReference"),
        _function("archiveViewEvidenceList"),
        _function("archiveViewSideNote"),
        _function("archiveViewOperatorQuestion"),
        _function("archiveViewOperatorSection"),
        """
const basis={
  crosswalk_binding_audit:{candidates_checked:52,with_shared_content_hash:0,
    with_delivery_receipt:0,with_typed_reference:0,derived_locator_echoes:3,
    operational_possible_links:44,
    operational_possible_link_classes:{'possible_consumer_or_origin/path_token':44},
    bases_scanned:['a#b','c#d','e#f','g#h','i#j','k#l','m#n'],
    conclusion:'measured, not assumed: every row stays a candidate'},
  research_frontier:{status:'abstain',scope:'ssd_order_frontier',compiled:false,
    job_count:0,dispatch:false,create_job_invoked:false,
    reason:'no_ssd_order_input_reaches_a_typed_relation_without_a_forbidden_inference',
    precision_note:'a valid payload exists at pilot scope and is cited, not adopted',
    reopen_when:'un hash de contenido completo compartido',
    existing_pilot_chain:{status:'present_pilot_scope',
      scope:'pilot_case_run_not_the_ssd_order_frontier',
      relations_ref:'experiments/pilots/DREFQUILA/runs/x/relations.json',
      relations_sha256:'bb9e7a8e1f3bc707a97ba5ea910200a3',relation_count:6,
      relation_statuses:{candidate:6},
      research_frontier:{job_count:1,dispatched_job_count:0,status:'compiled_not_dispatched'},
      why_not_adopted:['descansa en una identidad de artista declarada'],
      not_usable_for:['responder cualquiera de los 50 empates']},
    blocking_gates:[{gate:'archive_missing_artist_identity',
      why_refused:'asignar un artista seria una inferencia de autoria',
      source_ref:'src/flujo/knowledge/cross_archive_relations.py#_descriptor'}]},
  operator_review:{
    asked_count:1,deferred_count:1,machine_answerable:false,selection_effect:'none',
    attestation_queue_status:'pending_human_input',answers_recorded:0,
    attestation_queue:[{rank:1,answered:false,selection_effect:'none'}],
    evidence_sources:[{role:'byte_identity_ledger',path:'/tmp/ties_full.db',sha256:'f08bd5ffad651859'}],
    identity_tiers:{recomputed_from_ledger:{T2_crosses_roots_needs_an_answer:18},
      reproduces_declared_totals:true},
    index_relation_reality:{relation_total:113,exact_duplicate_on_empty_content:111,
      exact_duplicate_substantive:0,typed_non_duplicate_relations:2,
      cross_container_typed_non_duplicate_relations:0,
      questions_with_a_binding_typed_relation:0},
    triage:{grade_counts:{substantive:1,metadata_only:1},
      questions_reproduced_from_independent_ledger:2,
      questions_with_actionable_evidence:1,questions_without_actionable_evidence:1,
      unbound_containers:['Spotlight-V100']},
    question_samples:[{
      question_id:'order-question:ask:00',left:'DREFGIRA',right:'DrefQuila',
      question:'Es una obra bajo dos nombres?',answers:['same_work_under_two_names'],
      examples:['DREFGIRA/ESCARLATA.mp4'],shared_bytes:16972411695,shared_classes:18,
      evidence_grade:'substantive',substantive_shared_bytes:16972411695,unbound_containers:[],
      machine_answerable:false,selection_effect:'none',
      identity_tiers:{T2_crosses_roots_needs_an_answer:18},
      actionable_evidence_kinds:['bounded_intake_candidate','substantive_shared_bytes'],
      adds_actionable_evidence:true,deferral_reason:'',
      typed_relation_binding_this_pair:0,
      typed_relations:{binding_this_pair:0,relations_touching_either_container:4,
        empty_content_duplicates_touching_either_container:4,
        index_typed_non_duplicate_relations:2,
        index_cross_container_typed_non_duplicate_relations:0},
      reopen_when:'el operador atestigua',reopen_when_source:'derived:byte_identity_recomputation',
      evidence_ref:'questions.json#/ask/0',
      byte_identity:{recomputed_shared_classes:18,recomputed_shared_bytes:16972411695,
        matches_declared_question:true,substantive_class_count:18,zero_byte_class_count:0,
        appledouble_class_count:0,classes_spanning_more_than_two_containers:1,
        other_containers_in_shared_classes:['HARRY']},
      sides:{left:{container:'DREFGIRA',container_binding:'bound_to_ssd_index_container_root',
        ssd_project_count:8,ssd_asset_count:467,hash_pending_assets:0,
        authority:{status:'authority_bound_context'},
        intake:{candidate_count:1,status:'candidate_selected'},
        reconstruction:{decided_project_count:8,role_counts:{project_unit:1,subproject:4}},
        index_relations:{touching_container:0,crossing_containers:0}},
        right:{container:'DrefQuila',container_binding:'bound_to_ssd_index_container_root',
        ssd_project_count:1,ssd_asset_count:136,hash_pending_assets:132,
        authority:{status:'missing_or_unbound'},
        intake:{candidate_count:0,status:'not_selected'},
        reconstruction:{decided_project_count:0,role_counts:{}},
        index_relations:{touching_container:4,crossing_containers:0}}},
      evidence_for:[{statement:'18 clases comparten bytes',source_ref:'ties_full.db#identity_class'}],
      evidence_against:[{statement:'la identidad de bytes no prueba la comision',source_ref:'questions.json#/ask/0'}],
      missing_evidence:[{statement:'una atestacion del operador',source_ref:'questions.json#/ask/0'}],
      resolution:{resolved_by:'operator_attestation_only',status:'unresolved'}}],
    deferred_samples:[{question_id:'order-question:deferred:41',left:'Spotlight-V100',
      right:'abril2026post',answers:['same_work_under_two_names'],examples:['x'],
      shared_bytes:0,shared_classes:1,evidence_grade:'metadata_only',
      substantive_shared_bytes:0,unbound_containers:['Spotlight-V100'],
      actionable_evidence_kinds:[],adds_actionable_evidence:false,
      typed_relation_binding_this_pair:0,identity_tiers:{},
      deferral_reason:'no substantive shared bytes and nothing else moves it',
      evidence_ref:'questions.json#/deferred/41'}]}};
const html=archiveViewOperatorSection(basis);
console.log(JSON.stringify({
  humanWarning:html.includes('Son preguntas para una persona, no respuestas de MAK'),
  notForSelection:html.includes('no usada para seleccionar'),
  missingTypedRef:html.includes('falta referencia tipada'),
  noWrite:html.includes('database_write=false'),
  noTraining:html.includes('training=false'),
  grades:html.includes('substantive')&&html.includes('metadata_only'),
  evidenceFor:html.includes('Evidencia a favor'),
  evidenceAgainst:html.includes('Evidencia en contra'),
  evidenceMissing:html.includes('Evidencia faltante'),
  sourceRefs:html.includes('ties_full.db#identity_class')&&html.includes('questions.json#/ask/0'),
  answerOptions:html.includes('same_work_under_two_names'),
  authorityPerSide:html.includes('autoridad externa disponible')&&html.includes('sin autoridad externa ligada'),
  unbound:html.includes('sin contenedor indexado: Spotlight-V100'),
  unboundSide:archiveViewSideNote({container:'Spotlight-V100',container_binding:'unbound'}).includes('no ligado al índice SSD'),
  counts:html.includes('1 preguntas prioritarias + 1 diferidas'),
  queuePending:html.includes('pending_human_input')&&html.includes('0 respuestas registradas'),
  frontierAbstains:html.includes('Frontera de investigación (ssd_order_frontier): abstain')&&html.includes('0 jobs'),
  gateShown:html.includes('archive_missing_artist_identity'),
  machineAnswerable:html.includes('machine_answerable=false')&&html.includes('selection_effect=none'),
  reopen:html.includes('reabrir cuando'),
  bytes:html.includes('15.8 GB'),
  identityTiers:html.includes('Tiers de identidad recomputados')&&html.includes('T2_crosses_roots_needs_an_answer=18'),
  tiersReproduce:html.includes('reproduce los totales declarados por la proyección de orden: sí'),
  relationReality:html.includes('111 son duplicados exactos sobre contenido vacío')&&html.includes('0 de ellas cruzan contenedores'),
  bindingAudit:html.includes('52 candidatos')&&html.includes('con referencia tipada 0')&&html.includes('no son referencias'),
  basesScanned:html.includes('sobre 7 superficies'),
  operationalLinks:html.includes('enlaces operacionales preexistentes 44')&&html.includes('possible_consumer_or_origin/path_token')&&html.includes('no vinculan'),
  pilotCited:html.includes('Cadena piloto preexistente, citada y no adoptada'),
  pilotNotUsable:html.includes('responder cualquiera de los 50 empates'),
  actionableKinds:html.includes('evidencia accionable'),
  deferralReason:html.includes('diferida: no substantive shared bytes and nothing else moves it'),
  intakeSide:html.includes('candidato(s) intake')&&html.includes('sin candidato intake'),
  reconSide:html.includes('decisión(es) de reconstrucción')&&html.includes('sin reconstrucción'),
  sharedMembers:html.includes('miembros compartidos'),
  noVerdictWord:!/respuesta de MAK\\b/.test(html)
}));
""",
    ])
    result = _run_node(script)

    assert result == {key: True for key in result}, result


def test_editor_operator_frontier_keeps_its_epistemic_labels() -> None:
    text = _html()

    assert "archiveViewOperatorSection" in text
    assert "no usada para seleccionar" in text
    assert "falta referencia tipada" in text
    assert "no es titulo autoral" in text or "no es título autoral" in text
    assert "database_write=false" in text
    assert "training=false" in text
    assert "Son preguntas para una persona, no respuestas de MAK" in text
    # The UI must not offer a way to answer or dispatch from the frontier.
    section = _function("archiveViewOperatorSection")
    for forbidden in ("fetch(", "method:", "<input", "<button", "<form"):
        assert forbidden not in section, forbidden
