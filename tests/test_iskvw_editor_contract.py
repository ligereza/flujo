from pathlib import Path


EDITOR = Path(__file__).parents[1] / "iskvw" / "editor.html"
MESA = Path(__file__).parents[1] / "iskvw" / "mesa_montaje.js"


def test_editor_surfaces_mak_contract_without_making_hub_required():
    source = EDITOR.read_text(encoding="utf-8")
    mesa = MESA.read_text(encoding="utf-8")

    assert "id=\"inbox-contrato\"" in source
    assert "fetch('/api/portfolio/contract'" in source
    assert 'id="inbox-copiloto-externos-lista"' in source
    assert "/api/portfolio/external-candidates" in source
    assert "fetch('/api/portfolio/review-queue'" in source
    assert "fetch('/api/portfolio/triangulation'" in source
    assert "/api/portfolio/triangulation/context-link" in source
    assert "function enlazarContexto" in source
    assert "enlazar a grupo..." in source
    assert 'id="inbox-revision"' in source
    assert "function cargarRevision" in source
    assert "evidencia humana" in source
    assert "Contexto humano aceptado" in source
    assert "sin grupo de triangulacion enlazado" in source
    assert 'id="inbox-indice-lista"' in source
    assert "/api/portfolio/index" in source
    assert "Usuarios mencionados, no entidades resueltas" in source
    assert 'id="inbox-foco"' in source
    assert "MAK · campo de orden" in source
    assert "abrir en estudio" in source
    assert "function mostrarAccionPieza" in source
    assert "function cargarTriangulacionPieza" in source
    assert "foco-visual-field" in source
    assert "foco-orbit-item" in source
    assert "foco-dock" in source
    assert "/api/portfolio/copilot/vision" in source
    assert "visión AWS" in source
    assert "previsualizar orden" in source
    assert 'id="inbox-herramientas"' in source
    assert "no se ha movido ningun archivo" in source
    assert "function pintarFoco" in source
    assert "ID exacto para enfocar" in source
    assert "resolverCandidatoExterno" in source
    assert "copiloto-candidato-media" in source
    assert "mediaInbox(item)" in source
    assert "candidato pendiente" in source
    assert "contexto visual" in source
    assert "medios visibles" in source
    assert "foco-visual-legend" in source
    assert "estudio-review-queue" in source
    assert "estudioPendingItems" in source
    assert "estudioOpenReview" in source
    assert "estudioResolveCandidate" in source
    assert "estudio-learning-summary" in source
    assert "estudioLoadLearning" in source
    assert "/api/portfolio/copilot/learning" in source
    assert "source_id:sourceId" in source
    assert "Decisión guardada" in source
    assert "source_id_requerido" not in source
    assert "await cargarPendientesRevision()" in source
    assert "data-role=\"candidate\"" in source
    assert "data-role=\"context\"" in source
    assert "no publica automaticamente" in source
    assert "consentimiento registrado antes de publicar" in source
    assert "archivo visual · obras editoriales" in source
    assert "estudioArchiveUnits" in source
    assert "fecha antigua → nueva" in source
    assert "20 unidades" in source
    assert "function estudioLiveSelect" in source
    assert "ESTUDIO_SESSION_ID" in source
    assert "medios dentro de esta pasada" in source
    assert "estudio-live-suggestion-grid" in source
    assert "estudioSuggestionOpen" in source
    assert "estudioEnableSuggestionDrag" in source
    assert "data-item-id=\"${esc(neighbor.id)}\"" in source
    assert "estudio-live-suggestion-layer" in source
    assert "estudio-suggestion-popover" in source
    assert "estudioSuggestionDecision" in source
    assert "descartar · no es obra" in source
    assert "ESTUDIO_FEEDBACK_BUSY" in source
    assert "seleccionada'" in source
    assert "mesa_montaje.js?v=20260811-atlas-context-map" in source
    assert "/api/portfolio/inbox?surface=mesa" in mesa
    assert "<title>MAK · Campo de orden · archivo vivo</title>" in source
    assert "MAK · campo de orden" in source
    assert "campo de orden" in mesa
    assert "La geometría permanece" in mesa
    assert 'data-field-mode="uncertainty"' in mesa
    assert 'data-field-mode="coverage"' in mesa
    assert 'data-field-mode="evidence"' in mesa
    assert 'data-field-mode="resonance"' in mesa
    assert "mesa-field-layer" in mesa
    assert "renderField" in mesa
    assert "relaxVisiblePositions" in mesa
    assert "selectOrderRegion" in mesa
    assert "mesa-order-compass" in mesa
    assert "mesa-map-legend" in mesa
    assert "visual_similarity" in mesa
    assert "MobileCLIP-S0" in mesa
    assert "centerNodeInView" in mesa
    assert "processedHumanSeed" in mesa
    assert "fetchSceneCached" in mesa
    assert "ficha activa · la decisión no crea vínculos" in mesa
    assert "advanceSeedFromPopover" in mesa
    assert "prefetchNextHumanSeed" in mesa
    assert "await loadHumanSeed({ refresh: false, excludeId: record.source_id });" in mesa
    assert "advanceAfterOrderDecision" not in mesa
    assert "nextAvailableRecord" not in mesa
    assert 'data-editor-mode="order"' in mesa
    assert 'data-editor-mode="relate"' in mesa
    assert 'data-learning-action="next-seed"' in mesa
    assert "async function loadHumanSeed" in mesa
    assert "humanSeedItemId" in mesa
    assert "state.humanSeedActive && id === state.humanSeedItemId" in mesa
    assert "centerNodeInView(candidateId)" in mesa
    assert "seedCandidateAllowed" in mesa
    assert "if (!response.ok) throw new Error(`HTTP ${response.status}`);" in mesa
    assert 'fetchSceneCached(candidateId, "copilot", "order")' in mesa
    assert 'query.set("surface", surface)' in mesa
    assert 'fetchScene(first.id, "copilot", "order")' in mesa
    assert 'const surface = state.editorMode === "order" ? "order" : "";' in mesa
    assert "ficha activa · la decisión no crea vínculos" in mesa
    assert 'state.feedbackBusy.has("advance-seed")' in mesa
    assert 'state.feedbackBusy.add("advance-seed")' in mesa
    assert 'await loadHumanSeed({ refresh: false, excludeId:' in mesa
    assert "state.orderSelectedIds = new Set(" in mesa
    assert "/api/portfolio/copilot/learning" in mesa
    assert "toggleOrderSelection" in mesa
    assert "draftFor" in mesa
    assert "draftHasContent" in mesa
    assert "saveDraft" in mesa
    assert "commitDraft" in mesa
    assert "cancelDraft" in mesa
    assert "undoLastAction" in mesa
    assert "undoRelationDecision" in mesa
    assert "syncRecordFromItem(anchor, data.item)" in mesa
    assert "clearDraftState(anchor, data.item?.decision_draft" in mesa
    assert 'portfolioPost("/api/portfolio/draft"' in mesa
    assert 'portfolioPost("/api/portfolio/commit"' in mesa
    assert 'portfolioPost("/api/portfolio/undo"' in mesa
    assert "window.confirm" in mesa
    assert "advanceAfterOrderDecision" not in mesa
    assert "una pieza, sus relaciones, ninguna copia" not in mesa
    assert "arrastra el vacío: recorrer el atlas" in mesa
    assert 'actionButton("relate"' in mesa
    assert 'actionButton("accept"' in mesa
    assert 'actionButton("reject"' in mesa
    assert 'actionButton("open"' in mesa
    assert 'actionButton("center"' in mesa
    assert "selectedId" in mesa
    assert "selectRelation" in mesa
    assert "const suggestionsDrawerMarkup = active && usefulSuggestions.length" in mesa
    assert "return relation?.relation_id ? selectRelation(relation.relation_id)" in mesa
    assert "window.open" in mesa
    assert "requestAnimationFrame" in mesa
    assert "work_group" in mesa
    assert "shuffle" in mesa
    assert "reloadSuggestions" in mesa
    assert 'item.selection !== "descartar"' in mesa
    assert "classificationMarkup" in mesa
    assert "classify-toggle" in mesa
    assert '[data-class-field="context_kind"].is-active' in mesa
    assert 'clearFields.push("context_value")' in mesa
    assert "context_fields: contextFields" in mesa
    assert "const contextFields = {" in mesa
    assert 'const pieceContext = `${groupNote}${workGroupNote}`' in mesa
    assert "viewRequestId" in mesa
    assert "if (requestId !== state.viewRequestId) return;" in mesa
    assert "sceneCacheRevision" in mesa
    assert "invalidateSceneCache" in mesa
    assert "state.sceneCachePromises.clear()" in mesa
    assert "classificationPending" in mesa
    assert "const normalizedMode = mode === \"all\" ? \"copilot\" : mode" in mesa
    assert "const excluded = new Set(state.processedHumanSeed)" in mesa
    assert "return candidates.find((record) => !isDecidedRecord(record)) || null" not in mesa
    assert "state.editorMode === \"order\" && record.source_id !== state.activeId" in mesa
    assert "acquireRecordActions" in mesa
    assert 'field === "context_kind" && fields.context_kind !== value' in mesa
    assert "relationCounterpartId" in mesa
    assert "linkedIds.add(relation.source_id)" in mesa
    assert 'fetch("/api/portfolio/select"' not in mesa
    assert 'fetch("/api/portfolio/classify"' not in mesa
    assert 'fetch("/api/portfolio/feedback"' not in mesa
    assert "replaceChildren" in mesa
    assert "data-pop-note" in mesa
    assert "mesa-suggestion-card" in mesa
    assert "relationHasUsefulEvidence" in mesa
    assert "mesa-decision-note" in mesa
    assert "mesa-popover-flow" in mesa
    assert "mesa-popover-grid" not in mesa
    assert "sugerencias · ${usefulSuggestions.length}" in mesa
    assert "mesa-popover-media-note" not in mesa
    assert "ver descripción original" not in mesa
    assert "const description =" in mesa
    assert "note" in mesa
    assert "distancia adaptada" in mesa
    assert 'id="mesa-external-queue"' in mesa
    assert "loadExternalQueue" in mesa
    assert "externalReviewMarkup" in mesa
    assert "/api/portfolio/external-candidates/review" in mesa
    assert 'data-pop-action="external-review"' in mesa
    assert 'id="mesa-audit"' in mesa
    assert "/api/portfolio/audit" in mesa
    assert "Atlas de decisiones verificable" in mesa
    assert "Estado actual de selección" in mesa
    assert "Etiquetas de aprendizaje · no son piezas activas" in mesa
    assert "Línea temporal" in mesa
    assert "current_selection" in mesa
    assert "triage_labels" in mesa
    assert 'contentType.includes("application/json")' in mesa
    assert "la auditoría aún no está desplegada" in mesa

    order_decision = mesa[mesa.index("function applyOrderDecision") : mesa.index("function rebuildScene")]
    assert "updateDraft(record" in order_decision
    assert "revisa y efectúa la acción explícitamente" in order_decision

    assert "if(!r.ok)throw new Error(`HTTP ${r.status}`);" in source
    assert "Selección parcial del carrusel" in source
    assert "la selección visible fue restaurada" in source
    assert "tableros no disponibles temporalmente" in source
    assert "No se pudieron cargar las sugerencias; la pieza sigue disponible." in source


def test_mesa_uses_explicit_draft_gate_and_keeps_targets_visible():
    mesa = MESA.read_text(encoding="utf-8")

    assert 'data-order-action="save-draft-all"' in mesa
    assert 'data-order-action="commit-draft-all"' in mesa
    assert 'data-order-action="cancel-draft-all"' in mesa
    assert 'actionButton("save-draft"' in mesa
    assert 'actionButton("commit-draft"' in mesa
    assert 'actionButton("cancel-draft"' in mesa
    assert 'actionButton("undo"' in mesa
    assert 'actionButton("undo-relation"' in mesa
    assert "mesa-relation-pending" in mesa
    assert "mesa-order-targets" in mesa
    assert "state.selectedId = itemIds.length === 1 ? itemIds[0] : state.activeId" in mesa
    assert "window.confirm" in mesa
    assert "advanceAfterOrderDecision" not in mesa


def test_editor_keeps_search_board_filter_and_association_tray_separate():
    source = EDITOR.read_text(encoding="utf-8")

    assert 'id="inbox-buscar"' in source
    assert 'id="inbox-tablero"' in source
    assert 'id="inbox-asociacion"' in source
    assert 'id="inbox-resumen"' in source
    assert 'data-inbox-view="pendientes"' in source
    assert 'data-inbox-view="archivo"' in source
    assert 'data-inbox-view="mesa"' in source
    assert 'let INBOX_VIEW = "pendientes"' in source
    assert 'class="inbox-tools"' in source
    assert "inbox-pin-media" in source
    assert "inbox-action-primary" in source
    assert "const INBOX_SELECTED = new Set()" in source
    assert "anadirSeleccionAlTablero" in source
