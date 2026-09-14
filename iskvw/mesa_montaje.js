(function () {
  "use strict";

  const state = {
    items: [],
    scene: null,
    activeId: "",
    selectedId: "",
    selectedRelationId: "",
    editorMode: "order",
    orderSelectedIds: new Set(),
    humanSeed: [],
    humanSeedActive: false,
    humanSeedItemId: "",
    processedHumanSeed: new Set(),
    sceneCache: new Map(),
    sceneCachePromises: new Map(),
    sceneCacheRevision: 0,
    viewRequestId: 0,
    fieldMode: "uncertainty",
    lens: "all",
    suggestionMode: "copilot",
    classificationAxis: "lane",
    camera: { x: 0, y: 0, zoom: 1 },
    visualFrame: { queued: false, jobs: new Map(), lastTimestamp: 0, samples: [], fps: 60, quality: "full" },
    flowCanvas: null,
    flowContext: null,
    flowRender: { cursor: 0, total: 0, complete: false, records: [], positions: new Map() },
    cameraTween: 0,
    externalCandidates: [],
    feedbackBusy: new Set(),
    classificationPending: new Map(),
    drafts: new Map(),
    draftDirty: new Set(),
    nodes: new Map(),
    lines: new Map(),
    sessionId: "mesa-" + Date.now().toString(36),
    root: null,
    stage: null,
    world: null,
    fieldLayer: null,
    edgeLayer: null,
    cardLayer: null,
    popover: null,
    timeline: null,
    status: null,
    orderHud: null,
    fieldReadout: null,
  };

  const byId = (id) => state.scene?.records?.find((row) => row.source_id === id);
  const escMesa = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[character]));

  // Derivado de Ascii-Motion/src/types/easing.ts:
  // interpolateBetweenKeyframes/evaluateEasing. No se carga Ascii-Motion como runtime.
  const ASCII_MOTION_EASING = { "ease-out": [0, 0, 0.58, 1] };

  function asciiMotionEase(progress, preset = "ease-out") {
    const value = Math.max(0, Math.min(1, Number(progress) || 0));
    const [x1, y1, x2, y2] = ASCII_MOTION_EASING[preset] || ASCII_MOTION_EASING["ease-out"];
    const bezier = (t, a, b) => 3 * (1 - t) * (1 - t) * t * a + 3 * (1 - t) * t * t * b + t * t * t;
    const derivative = (t, a, b) => 3 * a * (1 - t) * (1 - t) + 6 * (b - a) * (1 - t) * t + 3 * (1 - b) * t * t;
    let t = value;
    for (let attempt = 0; attempt < 8; attempt += 1) {
      const error = bezier(t, x1, x2) - value;
      const slope = derivative(t, x1, x2);
      if (Math.abs(error) < 1e-7 || Math.abs(slope) < 1e-7) break;
      t = Math.max(0, Math.min(1, t - error / slope));
    }
    return Math.max(0, Math.min(1, bezier(t, y1, y2)));
  }

  function asciiMotionInterpolate(start, end, progress, preset = "ease-out") {
    return Number(start) + (Number(end) - Number(start)) * asciiMotionEase(progress, preset);
  }

  function actionGlyph(name) {
    const glyphs = {
      center: '<circle cx="12" cy="12" r="6"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/>',
      relate: '<path d="M9.5 14.5 8 16a4 4 0 0 1-5.5-5.8l2.4-2.4a4 4 0 0 1 5.7 0"/><path d="m14.5 9.5 1.5-1.5a4 4 0 0 1 5.5 5.8l-2.4 2.4a4 4 0 0 1-5.7 0"/><path d="m8.5 15.5 7-7"/>',
      open: '<path d="M14 3h7v7"/><path d="m21 3-9 9"/><path d="M19 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h6"/>',
      accept: '<path d="m4 12 5 5L20 6"/>',
      reject: '<path d="m6 6 12 12M18 6 6 18"/>',
      discard: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7l1-3h4l1 3"/>',
      work: '<path d="M4 19V7l8-4 8 4v12l-8 2-8-2Z"/><path d="M8 10h8M8 14h8"/>',
      record: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="2"/><path d="M12 2v4M12 18v4"/>',
      review: '<path d="M4 5h16v12H8l-4 4V5Z"/><path d="M8 9h8M8 13h5"/>',
      region: '<circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="8" stroke-dasharray="2 3"/>',
      detail: '<circle cx="11" cy="11" r="6"/><path d="m16 16 4 4"/>',
      next: '<path d="M4 12h14"/><path d="m13 5 7 7-7 7"/>',
      undo: '<path d="M9 7 4 12l5 5"/><path d="M4 12h10a5 5 0 1 1 0 10h-2"/>',
      "undo-relation": '<path d="M9 7 4 12l5 5"/><path d="M4 12h10a5 5 0 1 1 0 10h-2"/>',
    };
    return `<svg class="mesa-action-icon" viewBox="0 0 24 24" aria-hidden="true">${glyphs[name] || glyphs.open}</svg>`;
  }

  function actionButton(action, label, extra = "") {
    return `<button type="button" class="mesa-pop-action mesa-pop-action-${escMesa(action)}" data-pop-action="${escMesa(action)}" aria-label="${escMesa(label)}" title="${escMesa(label)}" ${extra}>${actionGlyph(action)}<span>${escMesa(label)}</span></button>`;
  }

  function mediaMarkup(record) {
    if (!record?.asset_available || !record.asset_path) {
      return '<span class="mesa-empty">media no sincronizada</span>';
    }
    const path = escMesa(record.asset_path);
    const extension = path.split("?")[0].split(".").pop().toLowerCase();
    if (["mp4", "mov", "webm", "m4v"].includes(extension)) {
      return `<video src="${path}" muted playsinline preload="metadata"></video>`;
    }
    return `<img src="${path}" loading="lazy" decoding="async" alt="registro visual">`;
  }

  function publicationSummary(record) {
    const group = record?.publication_group;
    if (!group || group.count < 2) return "";
    const index = Number.isFinite(Number(record.publication_index))
      ? Number(record.publication_index) + 1 : "?";
    return ` · carrusel ${index}/${group.count}`;
  }

  function workGroupSummary(record) {
    const group = record?.work_group;
    return group && group.count > 1 ? ` · misma obra ${group.count} piezas` : "";
  }

  function workGroupMedia(record) {
    const group = record?.work_group;
    if (!group || group.count < 2) return mediaMarkup(record);
    const members = Array.isArray(group.members) ? group.members : [record];
    return `<span class="mesa-node-group-media">${members.slice(0, 4).map((member) => (
      `<span>${mediaMarkup(member)}</span>`
    )).join("")}</span>`;
  }

  function displayRecords() {
    const records = state.scene?.records || [];
    const hidden = new Set();
    records.forEach((record) => {
      const group = record.work_group;
      const memberIds = Array.isArray(group?.member_ids) ? group.member_ids : [];
      if (memberIds.includes(state.activeId)) {
        memberIds.forEach((memberId) => {
          if (memberId !== state.activeId) hidden.add(memberId);
        });
      }
      if (state.editorMode === "order" && record.source_id !== state.activeId
          && isDecidedRecord(record)) {
        hidden.add(record.source_id);
      }
    });
    return records.filter((record) => !hidden.has(record.source_id));
  }

  function isDecidedRecord(record) {
    const triage = record?.classification?.triage;
    return record?.selection === "descartar"
      || ["work", "record", "review", "discard"].includes(triage);
  }

  function seedCandidateAllowed(row, excluded = new Set()) {
    const itemId = String(row?.item_id || "").trim();
    if (!itemId || excluded.has(itemId) || itemId === String(state.activeId)) return false;
    if (row.asset_available === false) return false;
    const liveRecords = [...(state.items || []), ...(state.scene?.records || [])];
    const live = liveRecords.find((record) => String(record?.id || record?.source_id || "") === itemId);
    if (live && (live.asset_available === false || isDecidedRecord(live))) return false;
    const publicationId = String(live?.publicacion_id || row.publicacion_id || "").trim();
    if (publicationId && liveRecords.some((record) => (
      String(record?.publicacion_id || "").trim() === publicationId && isDecidedRecord(record)
    ))) return false;
    return true;
  }

  function applyWorkGroups() {
    const records = state.scene?.records || [];
    const parent = new Map(records.map((record) => [record.source_id, record.source_id]));
    const find = (id) => {
      let root = parent.get(id) || id;
      while (parent.get(root) && parent.get(root) !== root) root = parent.get(root);
      return root;
    };
    const union = (left, right) => {
      if (!parent.has(left) || !parent.has(right)) return;
      const leftRoot = find(left);
      const rightRoot = find(right);
      if (leftRoot !== rightRoot) parent.set(rightRoot, leftRoot);
    };
    records.forEach((record) => {
      (Array.isArray(record.work_group?.member_ids)
        ? record.work_group.member_ids : []).forEach((memberId) => union(record.source_id, memberId));
    });
    (state.scene?.relations || []).forEach((relation) => {
      const facet = relation.feedbackFacet || relation.feedback_facet || "";
      if (relation.status === "accepted" && ["obra", "work", "same_work"].includes(facet)) {
        union(relation.source_id, relation.target_id);
      }
    });
    records.forEach((record) => { record.work_group = null; });
    const components = new Map();
    records.forEach((record) => {
      const root = find(record.source_id);
      if (!components.has(root)) components.set(root, []);
      components.get(root).push(record);
    });
    components.forEach((members) => {
      if (members.length < 2) return;
      const memberIds = members.map((member) => member.source_id).sort();
      const group = {
        id: `work:${memberIds.join(":")}`,
        label: "misma obra",
        count: members.length,
        member_ids: memberIds,
        members: members.map((member) => ({
          source_id: member.source_id,
          asset_path: member.asset_path || "",
          asset_available: Boolean(member.asset_available),
          date: member.date || "",
        })),
        basis: "human_feedback",
      };
      members.forEach((member) => { member.work_group = group; });
    });
  }

  function channelColor(channel) {
    return {
      date: "#d4a259", publication: "#d6b9e8", event: "#8ab8d8",
      venue: "#80c6a0", artist: "#c6a2d6", client: "#d68a7a",
      text: "#a69c88", visual: "#8d9ed6", visual_similarity: "#8d9ed6",
      format: "#9f9dca",
    }[channel] || "#9e9587";
  }

  function relationColor(relation) {
    return channelColor((relation.channels || [])[0] || relation.relation_type);
  }

  function mapRowFor(id) {
    return (state.scene?.map?.items || []).find((row) => (
      String(row.item_id) === String(id)
    ));
  }

  function relationSpace(relation) {
    if (relation?.relation_type === "map_neighbor") return "topology";
    return ["evidence", "resonance", "topology"].includes(relation?.space)
      ? relation.space : "resonance";
  }

  const relationFacetLabels = {
    obra: "misma obra",
    registro: "registro emocional",
    date: "fecha",
    publication: "misma publicación / carrusel",
    event: "evento",
    venue: "venue",
    artist: "artista",
    client: "cliente / productora",
    collab: "colaboración",
    text: "concepto / texto", visual_similarity: "similitud visual",
    visual: "visual",
    audio: "audio",
    process: "proceso",
    period: "periodo",
  };

  const classificationLabels = {
    triage: "orden rápido", lane: "capa de trabajo", ownership: "propiedad", purpose: "propósito",
    nature: "naturaleza", format: "formato", context_kind: "contexto",
  };

  const classificationOptions = {
    triage: [["work", "obra"], ["record", "registro"], ["review", "revisar"], ["discard", "descartar"]],
    lane: [["rd", "RD"], ["iskvw", "iskvw"], ["mak", "MAK"],
      ["personal", "personal"], ["research", "research"], ["system", "sistema"]],
    ownership: [["personal", "propia"], ["client", "cliente"]],
    purpose: [["expression", "expresión"], ["research", "investigación"],
      ["narrative", "narrativo"], ["commercial", "comercial"],
      ["expositive", "expositivo"], ["editorial", "editorial"]],
    nature: [["2d", "2D"], ["3d", "3D"], ["hybrid", "híbrida"]],
    format: [["video", "video"], ["illustration", "ilustración"],
      ["print", "impresa"], ["web", "web"]],
    context_kind: [["artist", "artista"], ["venue", "venue"], ["event", "evento"],
      ["client", "cliente"], ["collab", "colaboración"], ["record", "registro"]],
  };

  function draftFor(record) {
    const itemId = String(record?.source_id || record?.id || "");
    const stored = state.drafts.get(itemId) || record?.decision_draft || {};
    const storedStatus = String(stored.status || "");
    const hasDraft = state.draftDirty.has(itemId)
      || ["local_draft", "saved", "partial"].includes(storedStatus);
    const draftFields = hasDraft ? (stored.fields || {}) : {};
    const fields = { ...(record?.classification || {}), ...draftFields };
    const clearFields = hasDraft && Array.isArray(stored.clear_fields)
      ? stored.clear_fields : [];
    clearFields.forEach((field) => delete fields[field]);
    return {
      item_id: itemId,
      action: String(stored.action || ""),
      fields,
      clear_fields: [...clearFields],
      context_fields: hasDraft ? { ...(stored.context_fields || {}) } : {},
      relations: hasDraft && Array.isArray(stored.relations)
        ? stored.relations.map((row) => ({ ...row })) : [],
      note: hasDraft ? String(stored.note || "") : "",
      status: storedStatus,
      draft_id: String(stored.draft_id || ""),
      session_id: String(stored.session_id || state.sessionId),
      hasDraft,
    };
  }

  function draftIsPending(record) {
    return draftFor(record).hasDraft;
  }

  function draftHasContent(draft) {
    return Boolean(draft?.hasDraft && (draft.action
      || Object.keys(draft.fields || {}).length
      || (draft.clear_fields || []).length
      || Object.keys(draft.context_fields || {}).length
      || (draft.relations || []).length || draft.note));
  }

  function recordCanUndo(record) {
    const stored = state.drafts.get(String(record?.source_id || ""))
      || record?.decision_draft || {};
    const storedStatus = String(stored.status || "");
    if (storedStatus === "undone") return false;
    return !draftIsPending(record) && (storedStatus === "committed"
      || record?.selection !== "pendiente"
      || Object.keys(record?.classification || {}).length > 0);
  }

  function updateDraft(record, changes = {}) {
    const current = draftFor(record);
    const next = {
      ...current,
      ...changes,
      fields: changes.fields ? { ...changes.fields } : { ...current.fields },
      clear_fields: Array.isArray(changes.clear_fields)
        ? [...new Set(changes.clear_fields)] : [...current.clear_fields],
      context_fields: changes.context_fields
        ? { ...changes.context_fields } : { ...current.context_fields },
      relations: Array.isArray(changes.relations)
        ? changes.relations.map((row) => ({ ...row })) : current.relations,
      status: "local_draft",
      session_id: state.sessionId,
    };
    state.drafts.set(next.item_id, next);
    state.draftDirty.add(next.item_id);
    if (record) record.decision_draft = next;
    return next;
  }

  function classificationOptionLabel(field, value) {
    return (classificationOptions[field] || []).find((option) => option[0] === value)?.[1] || value;
  }

  function classificationAxisPanel(record, axis) {
    const classification = draftFor(record).fields;
    if (axis === "context_kind") {
      const contextValue = classification.context_value || "";
      return `<div class="mesa-classification-section"><span>elige el tipo y nómbralo</span><div class="mesa-classification-toggles">${classificationOptions.context_kind.map(([value, label]) => (
        `<button type="button" class="mesa-classification-toggle${classification.context_kind === value ? " is-active" : ""}" data-pop-action="classify-toggle" data-class-field="context_kind" data-class-value="${escMesa(value)}">${escMesa(label)}</button>`
      )).join("")}</div><div class="mesa-classification-context"><input data-class-context-value value="${escMesa(contextValue)}" placeholder="dref, Sala Metronomo…" aria-label="nombre del contexto"><button type="button" data-pop-action="classify-context">guardar nombre</button></div></div>`;
    }
    const options = classificationOptions[axis] || [];
      return `<div class="mesa-classification-section"><span>${escMesa(classificationLabels[axis])}</span><div class="mesa-classification-toggles">${options.map(([value, label]) => (
      `<button type="button" class="mesa-classification-toggle${classification[axis] === value ? " is-active" : ""}" data-pop-action="classify-toggle" data-class-field="${escMesa(axis)}" data-class-value="${escMesa(value)}">${escMesa(label)}</button>`
    )).join("")}</div></div>`;
  }

  function classificationMarkup(record) {
    const classification = draftFor(record).fields;
    const draft = draftFor(record);
    const axes = Object.keys(classificationOptions);
    const activeAxis = axes.includes(state.classificationAxis) ? state.classificationAxis : "lane";
    const marks = axes.filter((axis) => classification[axis]).map((axis) => (
      `<span>${escMesa(classificationLabels[axis])}: ${escMesa(classificationOptionLabel(axis, classification[axis]))}</span>`
    )).join("");
    const axisButtons = axes.map((axis) => (
      `<button type="button" class="mesa-classification-axis${axis === activeAxis ? " is-active" : ""}${classification[axis] ? " has-value" : ""}" data-pop-action="classify-axis" data-class-axis="${escMesa(axis)}"><b>${escMesa(classificationLabels[axis])}</b><small>${escMesa(classification[axis] ? classificationOptionLabel(axis, classification[axis]) : "sin marcar")}</small></button>`
    )).join("");
    const hasDraft = draftHasContent(draft);
    const canUndo = recordCanUndo(record);
    const status = draftIsPending(record)
      ? "borrador pendiente · todavía no ejecutado"
      : canUndo ? "última acción confirmada · historial conservado"
        : Object.keys(classification).length ? "sin cambios pendientes" : "";
    const draftControls = `<div class="mesa-draft-controls" data-draft-controls="${escMesa(record.source_id)}">`+
      `<span class="mesa-draft-status">${escMesa(status)}</span>`+
      `${hasDraft ? actionButton("save-draft", "guardar borrador") : ""}`+
      `${hasDraft ? actionButton("commit-draft", "efectuar acción") : ""}`+
      `${draftIsPending(record) ? actionButton("cancel-draft", "volver sin aplicar") : ""}`+
      `${canUndo ? actionButton("undo", "deshacer última") : ""}`+
      `</div>`;
    return `<section class="mesa-classification"><div class="mesa-classification-head"><span>clasificación</span><small>se prepara en borrador</small></div><div class="mesa-classification-summary">${marks || "<span>sin marcas</span>"}</div><div class="mesa-classification-axes">${axisButtons}</div><div class="mesa-classification-panel">${classificationAxisPanel(record, activeAxis)}</div><div class="mesa-classification-status" data-classification-status>${escMesa(status)}</div>${draftControls}</section>`;
  }

  function relationFacetOptions(relation, target) {
    const options = [...(relation.channels || [])];
    const feedbackFacet = relation.feedbackFacet || relation.feedback_facet || "";
    if (feedbackFacet && !options.includes(feedbackFacet)) options.unshift(feedbackFacet);
    if (relation.relation_type === "same_carousel" && !options.includes("publication")) {
      options.unshift("publication");
    }
    if (!options.includes("obra")) options.push("obra");
    if (target.record_kind === "story_record" || target.semantic_layer === "registro") {
      if (!options.includes("registro")) options.push("registro");
    }
    return [...new Set(options)].filter((facet) => relationFacetLabels[facet]);
  }

  function relationEvidenceEntries(relation) {
    const entries = (relation?.evidence || []).map((evidence) => {
      const value = evidence.source_value || evidence.candidate_value || (evidence.values || []).join(" · ");
      if (!value) return null;
      return {
        value,
        label: evidence.facet || evidence.kind || "dato",
        strength: evidence.strength || "",
      };
    }).filter(Boolean);
    const visual = relation?.visual || {};
    if (visual.score !== undefined && visual.score !== null) {
      entries.unshift({
        value: `score ${(Number(visual.score) || 0).toFixed(4)} · margen ${(Number(visual.margin) || 0).toFixed(4)} · ${visual.model || "MobileCLIP-S0"}`,
        label: "visual_similarity", strength: "medium",
      });
    }
    return entries;
  }

  function relationHasUsefulEvidence(relation) {
    if (relation?.status === "accepted") return true;
    const evidence = relationEvidenceEntries(relation);
    if (!evidence.length) return false;
    const declared = relation.scope === "declared";
    const weakLabels = new Set(["text", "description_term", "title", "name", "shared_concept", "shared_term"]);
    const structured = evidence.some((entry) => !weakLabels.has(entry.label));
    const stronger = evidence.some((entry) => entry.strength && entry.strength !== "low");
    return declared || structured || stronger;
  }

  function candidateRelations() {
    return (state.scene?.relations || []).filter((relation) => (
      relation.status !== "rejected" &&
      (state.lens === "all" || (relation.channels || []).includes(state.lens))
    ));
  }

  function visibleRelations() {
    return candidateRelations().filter((relation) => (
      relation.status === "accepted" || relationHasUsefulEvidence(relation)
    ));
  }

  function pendingRelations() {
    return visibleRelations().filter((relation) => relation.status === "candidate");
  }

  function relationCounterpartId(relation, anchorId = state.activeId) {
    if (String(relation?.source_id) === String(anchorId)) return relation.target_id;
    if (String(relation?.target_id) === String(anchorId)) return relation.source_id;
    return relation?.target_id || "";
  }

  function suggestionMarkup(relation, target) {
    const evidence = relationEvidenceEntries(relation).slice(0, 2);
    const evidenceText = evidence.map((entry) => `${entry.label}: ${entry.value}`).join(" · ");
    const relationText = (relation.channels || []).map((channel) => (
      relationFacetLabels[channel] || channel
    )).join(" · ") || relation.relation_type || "vínculo";
    return `<button type="button" class="mesa-suggestion-card" data-pop-action="relation" data-relation-id="${escMesa(relation.relation_id)}"><span class="mesa-suggestion-thumb">${mediaMarkup(target)}</span><span class="mesa-suggestion-copy"><small>${escMesa(relationText)}</small><b>${escMesa(target.source_id || relation.target_id)}</b><span>${escMesa(evidenceText || "evidencia estructurada")}</span></span><span class="mesa-suggestion-open">ver</span></button>`;
  }

  function relationForTarget(targetId) {
    return (state.scene?.relations || []).find((relation) => (
      (relation.source_id === state.activeId && relation.target_id === targetId)
      || (relation.target_id === state.activeId && relation.source_id === targetId)
    ));
  }

  function layout() {
    const records = displayRecords();
    const positions = new Map();
    const mapById = new Map((state.scene?.map?.items || []).map((row) => [
      String(row.item_id), row,
    ]));
    const mappedRecords = records.map((record) => mapById.get(String(record.source_id))).filter(Boolean);
    const activePoint = mapById.get(String(state.activeId));
    const centerX = Number(activePoint?.x ?? (mappedRecords.reduce((sum, row) => sum + Number(row.x || 0), 0) / Math.max(1, mappedRecords.length)));
    const centerY = Number(activePoint?.y ?? (mappedRecords.reduce((sum, row) => sum + Number(row.y || 0), 0) / Math.max(1, mappedRecords.length)));
    const maxDelta = mappedRecords.reduce((largest, row) => Math.max(
      largest, Math.abs(Number(row.x || 0) - centerX), Math.abs(Number(row.y || 0) - centerY)), 0);
    const localScale = Math.min(900, 36 / Math.max(.004, maxDelta));
    const collisions = new Map();
    const fallbackColumns = Math.max(2, Math.ceil(Math.sqrt(records.length)));
    records.forEach((record, index) => {
      const mapRow = mapById.get(String(record.source_id));
      const hasMapPosition = mapRow && Number.isFinite(Number(mapRow.x))
        && Number.isFinite(Number(mapRow.y));
      let x;
      let y;
      if (hasMapPosition) {
        const projectedX = 50 + (Number(mapRow.x) - centerX) * localScale;
        const projectedY = 50 + (Number(mapRow.y) - centerY) * localScale;
        const key = `${Math.round(projectedX * 10)}:${Math.round(projectedY * 10)}`;
        const collisionIndex = collisions.get(key) || 0;
        collisions.set(key, collisionIndex + 1);
        const angle = collisionIndex * 2.39996;
        const spread = Math.min(13, collisionIndex * 3.1);
        x = projectedX + Math.cos(angle) * spread;
        y = projectedY + Math.sin(angle) * spread;
      } else {
        const column = index % fallbackColumns;
        const row = Math.floor(index / fallbackColumns);
        x = 12 + (column / Math.max(1, fallbackColumns - 1)) * 76;
        y = 14 + (row / Math.max(1, Math.ceil(records.length / fallbackColumns) - 1)) * 72;
      }
      positions.set(record.source_id, {
        x: Math.max(6, Math.min(94, x)),
        y: Math.max(7, Math.min(93, y)),
      });
    });
    return relaxVisiblePositions(positions, records);
  }

  function relaxVisiblePositions(positions, records) {
    const ids = records.map((record) => record.source_id).filter((id) => positions.has(id));
    const activeId = state.activeId;
    const minimumX = 15;
    const minimumY = 22;
    for (let iteration = 0; iteration < 42; iteration += 1) {
      for (let leftIndex = 0; leftIndex < ids.length; leftIndex += 1) {
        for (let rightIndex = leftIndex + 1; rightIndex < ids.length; rightIndex += 1) {
          const leftId = ids[leftIndex];
          const rightId = ids[rightIndex];
          const left = positions.get(leftId);
          const right = positions.get(rightId);
          let deltaX = right.x - left.x;
          let deltaY = right.y - left.y;
          if (Math.abs(deltaX) >= minimumX || Math.abs(deltaY) >= minimumY) continue;
          if (Math.abs(deltaX) < .01 && Math.abs(deltaY) < .01) {
            const phase = ((leftIndex + 1) * 17 + (rightIndex + 1) * 31) % 360;
            deltaX = Math.cos(phase * Math.PI / 180);
            deltaY = Math.sin(phase * Math.PI / 180);
          }
          const overlapX = minimumX - Math.abs(deltaX);
          const overlapY = minimumY - Math.abs(deltaY);
          const moveLeft = leftId === activeId ? 0 : rightId === activeId ? 1 : .5;
          const moveRight = rightId === activeId ? 0 : leftId === activeId ? 1 : .5;
          if (overlapX / minimumX < overlapY / minimumY) {
            const direction = deltaX >= 0 ? 1 : -1;
            left.x -= direction * overlapX * moveLeft;
            right.x += direction * overlapX * moveRight;
          } else {
            const direction = deltaY >= 0 ? 1 : -1;
            left.y -= direction * overlapY * moveLeft;
            right.y += direction * overlapY * moveRight;
          }
          left.x = Math.max(7, Math.min(93, left.x));
          left.y = Math.max(9, Math.min(91, left.y));
          right.x = Math.max(7, Math.min(93, right.x));
          right.y = Math.max(9, Math.min(91, right.y));
        }
      }
    }
    return positions;
  }

  function svgElement(name, attributes = {}) {
    const element = document.createElementNS("http://www.w3.org/2000/svg", name);
    Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, value));
    return element;
  }

  function fieldSignal(record, mapRow) {
    const prediction = mapRow?.triage_prediction || {};
    if (state.fieldMode === "coverage") return Number(prediction.coverage_gap || 0);
    if (state.fieldMode === "evidence" || state.fieldMode === "resonance") {
      return (state.scene?.relations || []).some((relation) => (
        relationSpace(relation) === state.fieldMode &&
        (relation.source_id === record.source_id || relation.target_id === record.source_id) &&
        relation.status !== "rejected"
      )) ? 1 : 0;
    }
    return Number(prediction.information_gain || prediction.uncertainty || 0);
  }

  function renderField(positions = layout()) {
    if (!state.fieldLayer || !state.scene) return;
    state.fieldLayer.replaceChildren();
    state.root.dataset.fieldMode = state.fieldMode;
    displayRecords().forEach((record) => {
      const position = positions.get(record.source_id);
      const mapRow = mapRowFor(record.source_id);
      if (!position || !mapRow) return;
      const signal = Math.max(0, Math.min(1, fieldSignal(record, mapRow)));
      const radius = 5.5 + signal * 8.5;
      const cell = svgElement("circle", {
        cx: position.x, cy: position.y, r: radius,
        class: `mesa-field-cell is-${state.fieldMode}${signal < 0.08 ? " is-dormant" : ""}`,
        "data-field-item": record.source_id,
      });
      cell.style.setProperty("--field-strength", String(signal));
      state.fieldLayer.appendChild(cell);
    });
    renderFieldReadout();
  }

  function renderFieldReadout() {
    if (!state.fieldReadout) return;
    const mapRow = mapRowFor(state.selectedId || state.activeId);
    const prediction = mapRow?.triage_prediction || {};
    const uncertainty = Math.round(Number(prediction.uncertainty || 0) * 100);
    const coverage = Math.round(Number(prediction.coverage_gap || 0) * 100);
    const information = Math.round(Number(prediction.information_gain || 0) * 100);
    const evidenceCount = (state.scene?.relations || []).filter((row) => (
      relationSpace(row) === "evidence" && row.status !== "rejected"
    )).length;
    const resonanceCount = (state.scene?.relations || []).filter((row) => (
      relationSpace(row) === "resonance" && row.status !== "rejected"
    )).length;
    const distanceProfile = state.scene?.learning?.ordering?.field?.distance_profile || {};
    const metricLabel = distanceProfile.active === true ? "distancia adaptada" : distanceProfile.candidate_method ? "distancia base · candidato" : "distancia base";
    const metricSupport = distanceProfile.pair_support?.positive || distanceProfile.pair_support?.negative ? `${distanceProfile.pair_support?.positive || 0}/${distanceProfile.pair_support?.negative || 0}` : "sin pares";
    const renderFps = Math.round(state.visualFrame.fps || 60);
    const flowProgress = state.flowRender.total
      ? `${state.flowRender.cursor}/${state.flowRender.total}`
      : "sin datos";
    const externalPending = state.externalCandidates.filter(isPendingExternal).length;
    state.fieldReadout.innerHTML = `<span><b>${uncertainty}</b>incertidumbre</span><span><b>${coverage}</b>vacío</span><span><b>${information}</b>ganancia</span><span class="is-evidence"><b>${evidenceCount}</b>evidencia</span><span class="is-resonance"><b>${resonanceCount}</b>resonancia</span><span class="is-metric"><b>${metricSupport}</b>${metricLabel}</span><span class="is-runtime"><b>${renderFps}</b>render · ${escMesa(state.visualFrame.quality)}</span><span class="is-runtime"><b>Flow</b> canvas ${escMesa(flowProgress)}</span><span class="is-runtime"><b>${externalPending}</b>ext. pendiente</span>`;
  }

  function isPendingExternal(row) {
    const decision = String(row?.human_decision || row?.review_state || "pending").toLowerCase();
    return decision === "pending" || decision === "revise";
  }

  function externalForSource(sourceId) {
    return state.externalCandidates.filter((row) => String(row.source_id) === String(sourceId));
  }

  function updateExternalQueueCount() {
    const button = document.getElementById("mesa-external-queue");
    if (button) button.innerHTML = `evidencia externa · <b>${state.externalCandidates.filter(isPendingExternal).length}</b>`;
    renderFieldReadout();
  }

  async function loadExternalQueue() {
    try {
      const response = await fetch("/api/portfolio/external-candidates", { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      state.externalCandidates = Array.isArray(data.items) ? data.items : [];
    } catch {
      state.externalCandidates = [];
      setStatus("la cola externa no está disponible; la mesa continúa con evidencia local.");
    }
    updateExternalQueueCount();
  }

  async function openNextExternalCandidate() {
    const candidate = state.externalCandidates.find(isPendingExternal);
    if (!candidate) {
      setStatus("no quedan hipótesis externas pendientes.");
      return;
    }
    await centerRecord(candidate.source_id);
    setStatus("evidencia externa centrada; revisa la hipótesis dentro de la pieza activa.");
  }

  function resizeFlowCanvas() {
    if (!state.flowCanvas || !state.flowContext || !state.stage) return;
    const rect = state.stage.getBoundingClientRect();
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    state.flowCanvas.width = Math.max(1, Math.round(rect.width * dpr));
    state.flowCanvas.height = Math.max(1, Math.round(rect.height * dpr));
    state.flowCanvas.style.width = `${Math.max(1, rect.width)}px`;
    state.flowCanvas.style.height = `${Math.max(1, rect.height)}px`;
    state.flowContext.setTransform(dpr, 0, 0, dpr, 0, 0);
    queueFlowCanvas(true);
  }

  function queueFlowCanvas(reset = false) {
    if (!state.flowCanvas || !state.flowContext || !state.scene) return;
    if (reset) {
      state.flowRender.cursor = 0;
      state.flowRender.complete = false;
      state.flowRender.records = displayRecords();
      state.flowRender.positions = layout();
      state.flowRender.total = state.flowRender.records.length;
    }
    scheduleVisualFrame("flow-canvas", drawFlowCanvas);
  }

  function drawFlowCanvas() {
    const canvas = state.flowCanvas;
    const ctx = state.flowContext;
    if (!canvas || !ctx || !state.stage) return;
    const rect = state.stage.getBoundingClientRect();
    const width = Math.max(1, rect.width);
    const height = Math.max(1, rect.height);
    const records = state.flowRender.records;
    if (state.flowRender.cursor === 0) {
      ctx.clearRect(0, 0, width, height);
      ctx.save();
      ctx.strokeStyle = "rgba(214,185,232,.08)";
      ctx.lineWidth = 1;
      for (let x = 0; x <= width; x += 34) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke(); }
      for (let y = 0; y <= height; y += 34) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke(); }
      ctx.restore();
    }
    // Flow's mapping.html uses translate/scale around the canvas center.
    ctx.save();
    ctx.translate(width / 2 + state.camera.x, height / 2 + state.camera.y);
    ctx.scale(state.camera.zoom, state.camera.zoom);
    ctx.translate(-width / 2, -height / 2);
    const start = state.flowRender.cursor;
    const end = Math.min(records.length, start + 72);
    for (let index = start; index < end; index += 1) {
      const record = records[index];
      const position = state.flowRender.positions.get(record.source_id);
      if (!position) continue;
      const mapRow = mapRowFor(record.source_id);
      const signal = Math.max(0, Math.min(1, fieldSignal(record, mapRow)));
      const x = width * position.x / 100;
      const y = height * position.y / 100;
      ctx.beginPath();
      ctx.fillStyle = `rgba(214,185,232,${0.08 + signal * 0.20})`;
      ctx.arc(x, y, 10 + signal * 12, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.fillStyle = `rgba(183,147,111,${0.18 + signal * 0.58})`;
      ctx.arc(x, y, 1.5 + signal * 2.5, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
    state.flowRender.cursor = end;
    state.flowRender.complete = end >= records.length;
    if (state.root) state.root.dataset.flowRender = `${end}/${records.length}`;
    if (!state.flowRender.complete) scheduleVisualFrame("flow-canvas", drawFlowCanvas);
  }

  function createNode(record) {
    const node = document.createElement("button");
    node.type = "button";
    const layer = String(record.semantic_layer || "candidate").toLowerCase().replace(/[^a-z0-9_-]/g, "-");
    node.className = `mesa-node is-layer-${layer}${record.work_group ? " is-work-group" : ""}`;
    node.dataset.nodeId = record.source_id;
    node.dataset.mapConfidence = "unknown";
    node.innerHTML = `<span class="mesa-node-media">${workGroupMedia(record)}</span><span class="mesa-node-label"><b></b><small>${escMesa(record.date || "sin fecha")} · ${escMesa(record.content_type || "registro")}${escMesa(publicationSummary(record))}${escMesa(workGroupSummary(record))}</small></span><span class="mesa-node-triage" aria-hidden="true"></span>`;
    node.addEventListener("click", (event) => {
      event.stopPropagation();
      if (state.editorMode === "order") return toggleOrderSelection(record.source_id);
      selectRecord(record.source_id);
    });
    node.addEventListener("dblclick", (event) => {
      event.stopPropagation();
      state.editorMode = "relate";
      syncEditorMode();
      selectRecord(record.source_id);
    });
    return node;
  }

  function createLine(relation, positions) {
    const source = positions.get(relation.source_id);
    const target = positions.get(relation.target_id);
    if (!source || !target) return null;
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.classList.add("mesa-edge");
    line.classList.add(`is-space-${relationSpace(relation)}`);
    line.dataset.space = relationSpace(relation);
    line.setAttribute("x1", source.x);
    line.setAttribute("y1", source.y);
    line.setAttribute("x2", target.x);
    line.setAttribute("y2", target.y);
    line.setAttribute("stroke", relationColor(relation));
    line.setAttribute("aria-hidden", "true");
    return line;
  }

  function mount() {
    const app = document.getElementById("estudio-app");
    if (!app) return false;
    app.hidden = false;
    document.body.classList.add("mesa-active");
    app.innerHTML = `<div class="mesa-shell mesa-engine" data-field-mode="uncertainty"><header class="mesa-header"><div><div class="mesa-kicker">MAK · atlas vivo</div><h2>campo de orden</h2><p>La geometría permanece. Tus decisiones cambian el campo, no borran la ambigüedad.</p></div><div class="mesa-header-stats"><b id="mesa-visible-count">0</b><span>nodos</span><b id="mesa-relation-count">0</b><span>vínculos</span><span id="mesa-map-engine" class="mesa-map-engine">GTM · cargando</span><button type="button" id="mesa-external-queue" class="mesa-external-queue">evidencia externa · <b>0</b></button></div></header><div class="mesa-toolbar"><div class="mesa-mode-switch" role="toolbar" aria-label="Modo del editor"><button type="button" class="is-active" data-editor-mode="order">ordenar</button><button type="button" data-editor-mode="relate">relacionar</button><button type="button" class="mesa-seed-control" data-learning-action="next-seed" title="llevar el caso más informativo al centro">siguiente frontera</button></div><div class="mesa-field-switch" role="toolbar" aria-label="Campo visible"><button type="button" class="is-active" data-field-mode="uncertainty">incertidumbre</button><button type="button" data-field-mode="coverage">vacíos</button><button type="button" data-field-mode="evidence">evidencia</button><button type="button" data-field-mode="resonance">resonancia</button></div><div class="mesa-camera-actions"><button type="button" data-camera="reset">mapa</button><button type="button" data-camera="zoom-out">−</button><button type="button" data-camera="zoom-in">+</button><button type="button" id="mesa-audit" class="mesa-audit-button">auditoría</button></div></div><div class="mesa-lenses" role="toolbar" aria-label="Lentes de relación"><button type="button" class="is-active" data-lens="all">copiloto</button><button type="button" data-lens="date">fecha</button><button type="button" data-lens="publication">publicación</button><button type="button" data-lens="event">evento</button><button type="button" data-lens="venue">venue</button><button type="button" data-lens="artist">artista</button><button type="button" data-lens="client">cliente</button><button type="button" data-lens="text">concepto</button></div><div class="mesa-map-legend" aria-label="Lectura del campo"><span class="is-field">halo = información pendiente</span><span class="is-evidence">línea continua = evidencia</span><span class="is-resonance">línea discontinua = resonancia</span><em id="mesa-map-fit">proyección GTM</em></div><main class="mesa-main mesa-engine-main"><div class="mesa-stage" id="mesa-stage" data-flow-render="canvas-progressive" aria-label="Atlas GTM; arrastra el espacio para mover la cámara y selecciona piezas para ordenar"><canvas class="mesa-flow-canvas" id="mesa-flow-canvas" aria-hidden="true"></canvas><div class="mesa-world" id="mesa-world"><svg class="mesa-field-layer" id="mesa-field-layer" viewBox="0 0 100 100" preserveAspectRatio="none"></svg><svg class="mesa-edges" id="mesa-edges" viewBox="0 0 100 100" preserveAspectRatio="none"></svg><div class="mesa-card-layer" id="mesa-card-layer"></div></div><div class="mesa-field-readout" id="mesa-field-readout" aria-live="polite"></div><div class="mesa-order-hud" id="mesa-order-hud" aria-live="polite"></div><div class="mesa-popover" id="mesa-popover" hidden></div><div class="mesa-stage-help">click: elegir · rueda: acercar · arrastra el vacío: recorrer el atlas</div></div><nav class="mesa-timeline" id="mesa-timeline" aria-label="Nodos de esta ventana"></nav><div class="mesa-live-status" id="mesa-status" aria-live="polite"></div></main></div>`;
    state.root = app;
    state.root.dataset.editorMode = state.editorMode;
    state.root.dataset.fieldMode = state.fieldMode;
    state.stage = document.getElementById("mesa-stage");
    state.flowCanvas = document.getElementById("mesa-flow-canvas");
    state.flowContext = state.flowCanvas?.getContext("2d", { alpha: true }) || null;
    state.world = document.getElementById("mesa-world");
    state.fieldLayer = document.getElementById("mesa-field-layer");
    state.edgeLayer = document.getElementById("mesa-edges");
    state.cardLayer = document.getElementById("mesa-card-layer");
    state.popover = document.getElementById("mesa-popover");
    state.timeline = document.getElementById("mesa-timeline");
    state.status = document.getElementById("mesa-status");
    state.orderHud = document.getElementById("mesa-order-hud");
    state.fieldReadout = document.getElementById("mesa-field-readout");
    wireStaticControls();
    window.addEventListener("resize", resizeFlowCanvas, { passive: true });
    resizeFlowCanvas();
    return true;
  }

  function wireStaticControls() {
    const lensBar = state.root.querySelector(".mesa-lenses");
    const shuffleButton = document.createElement("button");
    shuffleButton.type = "button";
    shuffleButton.dataset.lens = "shuffle";
    shuffleButton.textContent = "shuffle";
    lensBar?.appendChild(shuffleButton);
    const conceptButton = state.root.querySelector('[data-lens="text"]');
    if (conceptButton) conceptButton.textContent = "concepto";
    const allButton = state.root.querySelector('[data-lens="all"]');
    if (allButton) allButton.textContent = "copiloto";
    state.root.querySelector("#mesa-external-queue")?.addEventListener("click", openNextExternalCandidate);
    state.root.querySelector("#mesa-audit")?.addEventListener("click", () => loadAuditSummary());
    state.root.querySelectorAll("[data-editor-mode]").forEach((button) => {
      button.addEventListener("click", () => setEditorMode(button.dataset.editorMode));
    });
    state.root.querySelectorAll("[data-field-mode]").forEach((button) => {
      button.addEventListener("click", () => setFieldMode(button.dataset.fieldMode));
    });
    state.root.querySelector("[data-learning-action=next-seed]")?.addEventListener(
      "click", () => loadHumanSeed({ refresh: true }));
    state.root.querySelectorAll("[data-lens]").forEach((button) => {
      button.addEventListener("click", () => {
        const mode = button.dataset.lens;
        state.lens = mode === "all" || mode === "shuffle" ? "all" : mode;
        state.suggestionMode = mode === "all" ? "copilot" : mode;
        state.root.querySelectorAll("[data-lens]").forEach((candidate) => {
          candidate.classList.toggle("is-active", candidate === button);
        });
        reloadSuggestions(mode);
      });
    });
    const visualLens = document.createElement("button");
    visualLens.type = "button";
    visualLens.dataset.lens = "visual_similarity";
    visualLens.textContent = "visual";
    lensBar?.appendChild(visualLens);
    visualLens.addEventListener("click", () => {
      state.lens = "visual_similarity";
      state.suggestionMode = "visual_similarity";
      state.root.querySelectorAll("[data-lens]").forEach((candidate) => {
        candidate.classList.toggle("is-active", candidate === visualLens);
      });
      reloadSuggestions("visual_similarity");
    });
    state.root.querySelectorAll("[data-camera]").forEach((button) => {
      button.addEventListener("click", () => {
        const action = button.dataset.camera;
        if (action === "reset") {
          state.camera = { x: 0, y: 0, zoom: 1 };
          applyCamera();
        }
        if (action === "zoom-in") zoom(.1);
        if (action === "zoom-out") zoom(-.1);
      });
    });
    state.stage.addEventListener("pointerdown", beginCameraMove);
    state.stage.addEventListener("wheel", (event) => {
      event.preventDefault();
      zoom(event.deltaY > 0 ? -.06 : .06);
    }, { passive: false });
    state.stage.addEventListener("click", (event) => {
      if (event.target === state.stage || event.target === state.world || event.target === state.edgeLayer) {
        closePopover();
      }
    });
    state.popover.addEventListener("click", handlePopoverAction);
    state.orderHud.addEventListener("click", (event) => {
      const button = event.target.closest("[data-order-action]");
      if (!button) return;
      event.stopPropagation();
      const action = button.dataset.orderAction;
      if (action === "region") {
        selectOrderRegion();
        return;
      }
      if (action === "detail") {
        const first = [...state.orderSelectedIds][0];
        if (first) {
          setEditorMode("relate");
          selectRecord(first);
        }
        return;
      }
      const records = [...state.orderSelectedIds].map(byId).filter(Boolean);
      if (action === "save-draft-all") {
        saveDraftBatch(records);
        return;
      }
      if (action === "commit-draft-all") {
        commitDraftBatch(records);
        return;
      }
      if (action === "cancel-draft-all") {
        cancelDraftBatch(records);
        return;
      }
      applyOrderDecision(action);
    });
  }

  function setFieldMode(mode) {
    if (!["uncertainty", "coverage", "evidence", "resonance"].includes(mode)) return;
    state.fieldMode = mode;
    state.root.querySelectorAll("[data-field-mode]").forEach((button) => {
      const active = button.dataset.fieldMode === mode;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    renderField();
    refreshScene();
    if (["evidence", "resonance"].includes(mode) && state.editorMode === "order") {
      setEditorMode("relate");
      return;
    }
    setStatus(`campo ${mode} activo; la posición de las piezas no cambia.`);
  }

  function setEditorMode(mode) {
    if (!['order', 'relate'].includes(mode)) return;
    state.editorMode = mode;
    if (mode === "relate") state.orderSelectedIds.clear();
    syncEditorMode();
    reloadSuggestions("copilot");
    setStatus(mode === "order"
      ? "modo ordenar: selecciona varios nodos y marca un destino común."
      : "modo relacionar: selecciona un nodo para explorar hipótesis y evidencia.");
  }

  async function loadHumanSeed(options = {}) {
    if (state.feedbackBusy.has("human-seed")) return;
    const requestId = ++state.viewRequestId;
    const excludeId = String(options.excludeId || "");
    state.feedbackBusy.add("human-seed");
    setStatus("buscando el siguiente candidato sin etiqueta…");
    try {
      const refresh = options.refresh !== false;
      let seed = state.humanSeed;
      if (refresh || !seed.length) {
        const response = await fetch("/api/portfolio/copilot/learning", { cache: "no-store" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const learning = await response.json();
        if (!learning || learning.ok === false) {
          throw new Error(learning?.error || "aprendizaje no disponible");
        }
        seed = learning.ordering?.human_seed || [];
        state.humanSeed = seed;
      }
      if (requestId !== state.viewRequestId) return false;
      if (!seed.length) throw new Error("no quedan candidatos sin etiqueta");
      const excluded = new Set(state.processedHumanSeed);
      if (excludeId) excluded.add(excludeId);
      const candidate = seed.find((row) => seedCandidateAllowed(row, excluded));
      if (!candidate) throw new Error("no quedan candidatos sin etiqueta");
      const candidateId = String(candidate.item_id);
      const scene = await fetchSceneCached(candidateId, "copilot", "order");
      if (requestId !== state.viewRequestId) return false;
      if (excludeId) state.processedHumanSeed.add(excludeId);
      state.activeId = candidateId;
      state.selectedId = candidateId;
      state.selectedRelationId = "";
      state.orderSelectedIds.clear();
      state.orderSelectedIds.add(candidateId);
      state.humanSeedActive = true;
      state.humanSeedItemId = candidateId;
      state.editorMode = "order";
      closePopover();
      state.scene = scene;
      state.camera = { x: 0, y: 0, zoom: 1 };
      rebuildScene();
      syncEditorMode();
      centerNodeInView(candidateId);
      prefetchNextHumanSeed(seed, candidateId);
      setStatus(`revisión humana: ${candidateId} · completa la ficha y pulsa siguiente`);
      return true;
    } catch (error) {
      if (requestId !== state.viewRequestId) return false;
      state.humanSeedActive = false;
      state.humanSeedItemId = "";
      state.orderSelectedIds.clear();
      syncEditorMode();
      setStatus("No se pudo abrir la semilla humana: " + error.message);
      return false;
    } finally {
      state.feedbackBusy.delete("human-seed");
    }
  }

  function syncEditorMode() {
    state.root.dataset.editorMode = state.editorMode;
    const seedReviewActive = state.editorMode === "order" && state.humanSeedActive;
    state.root.querySelectorAll("[data-editor-mode]").forEach((button) => {
      button.classList.toggle("is-active", button.dataset.editorMode === state.editorMode && !seedReviewActive);
    });
    const seedButton = state.root.querySelector("[data-learning-action=next-seed]");
    seedButton?.classList.toggle("is-active", Boolean(seedReviewActive));
    seedButton?.setAttribute("aria-pressed", String(Boolean(seedReviewActive)));
    if (state.editorMode === "order") closePopover();
    renderOrderHud();
    refreshScene();
    if (state.editorMode === "relate" && state.selectedId) showRecordPopover();
  }

  function toggleOrderSelection(id) {
    if (state.humanSeedActive && id === state.humanSeedItemId) {
      state.selectedId = id;
      state.orderSelectedIds.add(id);
      renderOrderHud();
      refreshScene();
      return;
    }
    if (state.humanSeedActive) {
      setStatus("frontera activa: no mezcles esta pieza con sus vecinos; usa detalle para completar su ficha.");
      return;
    }
    state.humanSeedActive = false;
    state.humanSeedItemId = "";
    if (state.orderSelectedIds.has(id)) state.orderSelectedIds.delete(id);
    else state.orderSelectedIds.add(id);
    state.selectedId = id;
    syncEditorMode();
  }

  function renderOrderHud() {
    if (!state.orderHud) return;
    const ids = [...state.orderSelectedIds];
    state.orderHud.hidden = state.editorMode !== "order" || !ids.length;
    if (state.orderHud.hidden) {
      state.orderHud.innerHTML = "";
      return;
    }
    const copy = state.humanSeedActive
      ? "ficha activa · la decisión no crea vínculos"
      : ids.length > 1 ? "clasificación común · no crea vínculos" : "clasificación individual";
    const pending = ids.filter((id) => draftIsPending(byId(id))).length;
    const targetSummary = ids.length <= 3
      ? ids.map((id) => escMesa(String(id))).join(" · ")
      : `${ids.slice(0, 3).map((id) => escMesa(String(id))).join(" · ")} · +${ids.length - 3}`;
    const draftActions = pending ? `<div class="mesa-order-actions"><button type="button" data-order-action="save-draft-all">guardar ${pending} borrador(es)</button><button type="button" data-order-action="commit-draft-all">efectuar ${pending} acción(es)</button><button type="button" data-order-action="cancel-draft-all">volver sin aplicar</button></div>` : "";
    state.orderHud.innerHTML = `<div class="mesa-order-compass" role="toolbar" aria-label="Destino de orden"><div class="mesa-order-hud-copy"><b>${ids.length}</b><span>${copy}${pending ? ` · ${pending} pendiente(s)` : ""}</span><small class="mesa-order-targets">objetivos: ${targetSummary}</small></div><button type="button" class="is-work" data-order-action="work" aria-label="preparar como obra">${actionGlyph("work")}<span>obra</span></button><button type="button" class="is-record" data-order-action="record" aria-label="preparar como registro">${actionGlyph("record")}<span>registro</span></button><button type="button" class="is-review" data-order-action="review" aria-label="dejar para revisar">${actionGlyph("review")}<span>revisar</span></button><button type="button" class="is-discard" data-order-action="discard" aria-label="preparar descarte; no es obra">${actionGlyph("discard")}<span>descarte</span></button><button type="button" class="is-region" data-order-action="region" aria-label="comparar región">${actionGlyph("region")}<span>${ids.length > 1 ? "una pieza" : "región"}</span></button><button type="button" class="is-detail" data-order-action="detail" aria-label="abrir detalle">${actionGlyph("detail")}<span>detalle</span></button>${draftActions}</div>`;
    positionOrderHud();
  }

  function selectOrderRegion() {
    if (state.humanSeedActive) {
      setStatus("frontera activa: la decisión pertenece a la pieza central, no a la región.");
      return;
    }
    const centerId = state.selectedId || [...state.orderSelectedIds][0];
    const center = mapRowFor(centerId);
    if (!center) return;
    if (state.orderSelectedIds.size > 1) {
      state.orderSelectedIds = new Set([centerId]);
      renderOrderHud();
      refreshScene();
      setStatus("región contraída a una pieza.");
      return;
    }
    state.humanSeedActive = false;
    state.humanSeedItemId = "";
    const candidates = displayRecords().filter((record) => (
      record.selection !== "descartar" && mapRowFor(record.source_id)
    )).map((record) => {
      const point = mapRowFor(record.source_id);
      const distance = Math.hypot(Number(point.x) - Number(center.x), Number(point.y) - Number(center.y));
      return { id: record.source_id, distance };
    }).sort((left, right) => left.distance - right.distance);
    const local = candidates.filter((row) => row.distance <= 0.24).slice(0, 6);
    const region = (local.length >= 2 ? local : candidates.slice(0, 3)).map((row) => row.id);
    state.orderSelectedIds = new Set(region);
    renderOrderHud();
    refreshScene();
    setStatus(`región comparativa: ${region.length} piezas visibles; puedes quitar cualquiera antes de decidir.`);
  }

  function positionOrderHud() {
    if (!state.orderHud || state.orderHud.hidden || !state.stage) return;
    const focusId = state.selectedId || [...state.orderSelectedIds][0];
    const node = state.nodes.get(focusId);
    if (!node) return;
    requestAnimationFrame(() => {
      if (state.orderHud.hidden) return;
      const stageRect = state.stage.getBoundingClientRect();
      const nodeRect = node.getBoundingClientRect();
      const halfWidth = Math.min(250, stageRect.width * 0.42);
      const halfHeight = Math.min(205, stageRect.height * 0.38);
      const rawLeft = nodeRect.left - stageRect.left + nodeRect.width / 2;
      const rawTop = nodeRect.top - stageRect.top + nodeRect.height / 2;
      const left = Math.max(halfWidth, Math.min(stageRect.width - halfWidth, rawLeft));
      const top = Math.max(halfHeight, Math.min(stageRect.height - halfHeight, rawTop));
      state.orderHud.style.left = `${left}px`;
      state.orderHud.style.top = `${top}px`;
    });
  }

  function applyOrderDecision(decision) {
    const itemIds = state.humanSeedActive
      ? [state.humanSeedItemId || state.activeId]
      : [...state.orderSelectedIds];
    if (!itemIds.length) return;
    let staged = 0;
    itemIds.forEach((itemId) => {
      const record = byId(itemId);
      if (!record) return;
      const draft = draftFor(record);
      const fields = { ...draft.fields, triage: decision };
      updateDraft(record, { action: decision, fields });
      staged += 1;
    });
    if (!staged) return;
    state.selectedId = itemIds.length === 1 ? itemIds[0] : state.activeId;
    rebuildScene();
    if (itemIds.length === 1) showRecordPopover();
    setStatus(`${staged} borrador(es) preparado(s) como ${decision}; revisa y efectúa la acción explícitamente.`);
  }

  function rebuildScene() {
    if (!state.scene || !state.cardLayer || !state.edgeLayer) return;
    applyWorkGroups();
    state.nodes.clear();
    state.lines.clear();
    state.cardLayer.replaceChildren();
    state.edgeLayer.replaceChildren();
    const positions = layout();
    renderField(positions);
    displayRecords().forEach((record) => {
      const node = createNode(record);
      state.nodes.set(record.source_id, node);
      state.cardLayer.appendChild(node);
    });
    visibleRelations().forEach((relation) => {
      const line = createLine(relation, positions);
      if (line) {
        state.lines.set(relation.relation_id, line);
        state.edgeLayer.appendChild(line);
      }
    });
    renderTimeline();
    refreshScene();
  }

  function refreshScene() {
    if (!state.scene) return;
    const positions = layout();
    const linkedIds = new Set();
    (state.scene.relations || []).filter((relation) => relation.status !== "rejected").forEach((relation) => {
      linkedIds.add(relation.source_id);
      linkedIds.add(relation.target_id);
    });
    state.nodes.forEach((node, id) => {
      const record = byId(id);
      const position = positions.get(id);
      if (!record || !position) return;
      const active = id === state.activeId;
      const selected = id === state.selectedId;
      const selectedForOrder = state.editorMode === "order" && state.orderSelectedIds.has(id);
      const mapRow = (state.scene.map?.items || []).find((row) => String(row.item_id) === String(id));
      const prediction = mapRow?.triage_prediction || {};
      const predictionEvidence = Number(prediction.evidence_count || 0);
      const predictionLabel = predictionEvidence ? String(prediction.recommended || "") : "";
      const uncertainty = Number(prediction.uncertainty || 0);
      const coverageGap = Number(prediction.coverage_gap || 0);
      const informationGain = Number(prediction.information_gain || 0);
      node.style.left = `${position.x}%`;
      node.style.top = `${position.y}%`;
      node.style.setProperty("--uncertainty", String(uncertainty));
      node.style.setProperty("--coverage-gap", String(coverageGap));
      node.style.setProperty("--information-gain", String(informationGain));
      node.style.setProperty("--field-alpha", String(0.08 + informationGain * 0.52));
      node.dataset.mapConfidence = mapRow?.confidence || "unknown";
      node.dataset.triage = predictionLabel || "unknown";
      node.dataset.uncertainty = uncertainty >= 0.72 ? "high" : uncertainty >= 0.42 ? "medium" : "low";
      node.classList.toggle("is-active", active);
      node.classList.toggle("is-selected", selected);
      node.classList.toggle("is-order-selected", selectedForOrder);
      node.classList.toggle("has-relation", linkedIds.has(id));
      node.classList.toggle("is-discarded", record.selection === "descartar");
      const label = node.querySelector("b");
      if (label) label.textContent = active ? "pieza central" : selected ? "pieza elegida" : record.semantic_layer === "registro" ? "registro" : "relacionada";
      const triage = node.querySelector(".mesa-node-triage");
      if (triage) {
        const probability = Number(prediction.probabilities?.[predictionLabel] || 0);
        triage.textContent = predictionLabel ? `${predictionLabel} ${Math.round(probability * 100)}%` : "";
      }
    });
    state.lines.forEach((line, relationId) => {
      const relation = (state.scene.relations || []).find((row) => row.relation_id === relationId);
      if (!relation) return;
      line.classList.toggle("is-accepted", relation.status === "accepted");
      line.classList.toggle("is-rejected", relation.status === "rejected");
      line.classList.toggle("is-candidate", relation.status === "candidate");
      line.classList.toggle("is-space-evidence", relationSpace(relation) === "evidence");
      line.classList.toggle("is-space-resonance", relationSpace(relation) === "resonance");
    });
    document.getElementById("mesa-visible-count").textContent = String(displayRecords().length);
    document.getElementById("mesa-relation-count").textContent = String(visibleRelations().length);
    const map = state.scene.map || {};
    const engine = document.getElementById("mesa-map-engine");
    const fit = document.getElementById("mesa-map-fit");
    if (engine) engine.textContent = `${map.engine === "elastic_latent_grid" ? "GTM" : "mapa"} · ${map.fit?.total || 0} datos`;
    const ordering = state.scene.learning?.ordering || {};
    const learned = Number(ordering.labeled || 0);
    const missingLabels = (ordering.missing_labels || []).join(" / ");
    const learningNote = !ordering.learning_ready ? " · falta masa crítica" : missingLabels ? ` · falta ${missingLabels}` : " · cobertura completa";
    if (fit) fit.textContent = map.fit?.sampled ? `GTM · ajuste muestreado · ${learned} decisiones${learningNote}` : `GTM · ajuste completo · ${learned} decisiones${learningNote}`;
    renderFieldReadout();
    applyCamera();
    renderOrderHud();
    if (!state.popover.hidden) placePopover();
  }

  function renderTimeline() {
    state.timeline.replaceChildren();
    displayRecords().forEach((record) => {
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.nodeRef = record.source_id;
      button.innerHTML = `<b>${escMesa(record.date || "—")}</b><span>${escMesa(record.source_id)}</span>`;
      button.addEventListener("click", () => selectRecord(record.source_id));
      state.timeline.appendChild(button);
    });
  }

  function scheduleVisualFrame(key, job) {
    state.visualFrame.jobs.set(key, job);
    if (state.visualFrame.queued) return;
    state.visualFrame.queued = true;
    requestAnimationFrame((timestamp) => {
      const frame = state.visualFrame;
      const previous = frame.lastTimestamp;
      if (previous) {
        const delta = Math.max(1, timestamp - previous);
        frame.samples.push(delta);
        if (frame.samples.length > 12) frame.samples.shift();
        const average = frame.samples.reduce((sum, value) => sum + value, 0) / frame.samples.length;
        frame.fps = Math.max(1, Math.min(120, 1000 / average));
        frame.quality = average > 32 ? "reduced" : "full";
      }
      frame.lastTimestamp = timestamp;
      const jobs = [...frame.jobs.values()];
      frame.jobs.clear();
      frame.queued = false;
      if (state.root) {
        state.root.dataset.renderQuality = frame.quality;
        state.root.dataset.renderFps = String(Math.round(frame.fps));
      }
      jobs.forEach((work) => work());
      renderFieldReadout();
    });
  }

  function applyCamera() {
    scheduleVisualFrame("camera", () => {
      if (state.world) {
        state.world.style.transform = `translate3d(${state.camera.x}px,${state.camera.y}px,0) scale(${state.camera.zoom})`;
      }
      state.timeline.querySelectorAll("[data-node-ref]").forEach((button) => {
        button.classList.toggle("is-active", button.dataset.nodeRef === state.selectedId);
      });
      if (!state.popover.hidden) placePopover();
      positionOrderHud();
    });
    queueFlowCanvas(true);
  }

  function beginCameraMove(event) {
    if (event.target.closest(".mesa-node, .mesa-popover, button")) return;
    const start = { x: event.clientX, y: event.clientY, cameraX: state.camera.x, cameraY: state.camera.y };
    const move = (moveEvent) => {
      state.camera.x = start.cameraX + moveEvent.clientX - start.x;
      state.camera.y = start.cameraY + moveEvent.clientY - start.y;
      applyCamera();
    };
    const end = () => {
      state.stage.classList.remove("is-panning");
      state.stage.removeEventListener("pointermove", move);
      state.stage.removeEventListener("pointerup", end);
      state.stage.removeEventListener("pointercancel", end);
    };
    state.stage.classList.add("is-panning");
    state.stage.setPointerCapture?.(event.pointerId);
    state.stage.addEventListener("pointermove", move);
    state.stage.addEventListener("pointerup", end);
    state.stage.addEventListener("pointercancel", end);
    event.preventDefault();
  }

  function zoom(delta) {
    state.camera.zoom = Math.max(.72, Math.min(1.55, state.camera.zoom + delta));
    applyCamera();
  }

  function centerNodeInView(id) {
    requestAnimationFrame(() => {
      const node = state.nodes.get(id);
      if (!node || !state.stage) return;
      const stageRect = state.stage.getBoundingClientRect();
      const nodeRect = node.getBoundingClientRect();
      const targetX = state.camera.x + (stageRect.left + stageRect.width / 2)
        - (nodeRect.left + nodeRect.width / 2);
      const targetY = state.camera.y + (stageRect.top + stageRect.height / 2)
        - (nodeRect.top + nodeRect.height / 2);
      const startX = state.camera.x;
      const startY = state.camera.y;
      cancelAnimationFrame(state.cameraTween);
      const started = performance.now();
      const animate = (now) => {
        const progress = Math.min(1, (now - started) / 220);
        state.camera.x = asciiMotionInterpolate(startX, targetX, progress, "ease-out");
        state.camera.y = asciiMotionInterpolate(startY, targetY, progress, "ease-out");
        applyCamera();
        if (progress < 1) state.cameraTween = requestAnimationFrame(animate);
      };
      state.cameraTween = requestAnimationFrame(animate);
    });
  }

  function setStatus(message) {
    if (state.status) state.status.textContent = message;
  }

  function acquireRecordActions(itemIds) {
    const keys = [...new Set(itemIds.map((itemId) => `record-action:${itemId}`))];
    if (keys.some((key) => state.feedbackBusy.has(key))) return null;
    keys.forEach((key) => state.feedbackBusy.add(key));
    return keys;
  }

  function releaseRecordActions(keys) {
    (keys || []).forEach((key) => state.feedbackBusy.delete(key));
  }

  function selectRecord(id) {
    if (!byId(id)) return;
    state.selectedId = id;
    state.selectedRelationId = "";
    refreshScene();
    showRecordPopover();
  }

  function positionForPopover() {
    const node = state.nodes.get(state.selectedId);
    if (!node || !state.stage || !state.popover) return;
    const stageRect = state.stage.getBoundingClientRect();
    const nodeRect = node.getBoundingClientRect();
    const popoverWidth = state.popover.offsetWidth || 310;
    const popoverHeight = state.popover.offsetHeight || 210;
    const nodeLeft = nodeRect.left - stageRect.left;
    const nodeRight = nodeRect.right - stageRect.left;
    const nodeTop = nodeRect.top - stageRect.top;
    let left = nodeRight + 16;
    if (left + popoverWidth > stageRect.width - 12) left = nodeLeft - popoverWidth - 16;
    left = Math.max(12, Math.min(left, stageRect.width - popoverWidth - 12));
    let top = nodeTop;
    if (top + popoverHeight > stageRect.height - 12) top = stageRect.height - popoverHeight - 12;
    top = Math.max(12, top);
    state.popover.style.left = `${left}px`;
    state.popover.style.top = `${top}px`;
  }

  function placePopover() {
    scheduleVisualFrame("popover", positionForPopover);
  }

  function openPopover(content) {
    state.popover.innerHTML = content;
    state.popover.hidden = false;
    placePopover();
  }

  function closePopover() {
    state.selectedRelationId = "";
    state.popover.hidden = true;
  }

  function auditMetric(label, value, note = "") {
    return `<div class="mesa-audit-metric"><b>${escMesa(value)}</b><span>${escMesa(label)}</span>${note ? `<small>${escMesa(note)}</small>` : ""}</div>`;
  }

  function auditSummaryMarkup(audit) {
    const counts = audit.counts || {};
    const current = counts.current_selection || {};
    const labels = counts.triage_labels || {};
    const feedback = counts.relation_feedback || {};
    const reviews = counts.candidate_reviews || {};
    const visual = counts.visual_feedback || {};
    const model = counts.ordering_model || {};
    const evaluation = model.evaluation || {};
    const byLabel = labels.by_label || {};
    const currentGrid = [
      auditMetric("seleccionadas ahora", current.selected || 0),
      auditMetric("deseleccionadas ahora", current.deselected || 0),
      auditMetric("descartadas ahora", current.discarded || 0),
      auditMetric("sin decisión de selección", current.pending || 0),
    ].join("");
    const labelGrid = [
      auditMetric("obra · work", byLabel.work || 0),
      auditMetric("registro · record", byLabel.record || 0),
      auditMetric("revisión · review", byLabel.review || 0),
      auditMetric("descartar · discard", byLabel.discard || 0),
    ].join("");
    const modelState = model.automation_ready ? "lista para evaluar" : "no automatizar";
    return `<div class="mesa-popover-head"><span>auditoría de solo lectura</span><button type="button" class="mesa-popover-close" data-pop-action="close" aria-label="cerrar">×</button></div><div class="mesa-popover-flow mesa-audit"><div class="mesa-audit-title"><h3>Atlas de decisiones verificable</h3><p class="mesa-popover-meta">estado actual, historial conservado y aprendizaje separados</p></div><section class="mesa-audit-section"><h4>Estado actual de selección</h4><div class="mesa-audit-grid">${currentGrid}</div><small>${escMesa(current.labeled || 0)} piezas con estado actual · ${escMesa(current.unmatched_history_rows || 0)} filas históricas sin pieza vigente</small></section><section class="mesa-audit-section"><h4>Etiquetas de aprendizaje · no son piezas activas</h4><div class="mesa-audit-grid">${labelGrid}</div><small>${escMesa(labels.total || 0)} etiquetas · origen: ${escMesa(JSON.stringify(labels.by_source || {}))}</small></section><section class="mesa-audit-section"><h4>Historial verificable</h4><div class="mesa-audit-history"><span>selecciones: <b>${escMesa(counts.selection_history?.total || 0)}</b></span><span>clasificaciones: <b>${escMesa(counts.classification_history?.total || 0)}</b></span><span>feedback: <b>${escMesa(feedback.history_total || 0)}</b> · learning ${escMesa(feedback.learning_total || 0)}</span><span>revisiones externas: <b>${escMesa(reviews.history_total || 0)}</b> · actuales ${escMesa(reviews.current_total || 0)}</span><span>feedback visual: <b>${escMesa(visual.history_total || 0)}</b></span></div></section><section class="mesa-audit-section"><h4>Estado del modelo</h4><p class="mesa-audit-status ${model.automation_ready ? "is-ready" : "is-blocked"}">${escMesa(modelState)} · accuracy ${escMesa(evaluation.accuracy ?? "sin evaluación")} · macro-recall ${escMesa(evaluation.macro_recall ?? "sin evaluación")} · promoción: ${escMesa(model.promotion || "none")}</p></section><div class="mesa-audit-actions"><button type="button" data-pop-action="audit-item" data-audit-item="${escMesa(state.selectedId)}">auditar pieza activa</button></div></div>`;
  }

  function auditItemMarkup(audit) {
    const item = audit.item || {};
    const current = item.current || {};
    const timeline = Array.isArray(item.timeline) ? item.timeline : [];
    const timelineMarkup = timeline.length
      ? timeline.map((event) => {
        const detail = event.kind === "selection"
          ? `${event.decision || "sin decisión"}`
          : event.kind === "classification"
            ? `clasificación ${JSON.stringify(event.fields || {})}`
            : event.kind === "candidate_review"
              ? `candidato ${event.decision || "sin decisión"}`
              : `${event.action || "sin acción"} · ${event.facet || "sin faceta"}`;
        return `<li><time>${escMesa(event.ts || "sin fecha")}</time><b>${escMesa(event.kind)}</b><span>${escMesa(detail)}</span></li>`;
      }).join("")
      : "<li>sin eventos registrados</li>";
    return `<div class="mesa-popover-head"><span>pieza auditada</span><button type="button" class="mesa-popover-close" data-pop-action="close" aria-label="cerrar">×</button></div><div class="mesa-popover-flow mesa-audit"><div class="mesa-audit-title"><h3>${escMesa(item.source_id || "pieza")}</h3><p class="mesa-popover-meta">${escMesa(item.date || "sin fecha")} · ${escMesa(item.content_type || "registro")}</p></div><section class="mesa-audit-section"><h4>Estado actual</h4><div class="mesa-audit-current"><span>selección: <b>${escMesa(current.selection || "pendiente")}</b></span><span>triage: <b>${escMesa(current.triage_label || "unlabeled")}</b> · ${escMesa(current.triage_source || "sin origen")}</span><span>clasificación: <b>${escMesa(JSON.stringify(current.classification || {}))}</b></span></div></section><section class="mesa-audit-section"><h4>Línea temporal · ${escMesa(item.timeline_total || 0)} eventos</h4><ol class="mesa-audit-timeline">${timelineMarkup}</ol></section><div class="mesa-audit-actions"><button type="button" data-pop-action="audit-summary">volver al resumen</button></div></div>`;
  }

  async function loadAuditSummary(sourceId = "") {
    const requested = String(sourceId || "").trim();
    setStatus(requested ? "cargando la trazabilidad de la pieza…" : "cargando el atlas verificable…");
    try {
      const query = requested ? `?source_id=${encodeURIComponent(requested)}` : "";
      const response = await fetch(`/api/portfolio/audit${query}`, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const contentType = response.headers.get("content-type") || "";
      if (!contentType.includes("application/json")) {
        throw new Error("el Hub devolvió HTML; la auditoría aún no está desplegada");
      }
      const audit = await response.json();
      if (!audit.ok) throw new Error(audit.error || "auditoría no disponible");
      openPopover(requested ? auditItemMarkup(audit) : auditSummaryMarkup(audit));
      setStatus(requested ? "trazabilidad de pieza cargada." : "atlas verificable cargado; no se modificó ninguna decisión.");
    } catch (error) {
      setStatus("No se pudo cargar la auditoría: " + error.message);
    }
  }

  function relationEvidence(relation) {
    return relationEvidenceEntries(relation).slice(0, 3).map((evidence) => (
      `<span>${escMesa(evidence.label)}: ${escMesa(evidence.value)}</span>`
    )).join("") || "<span>sin evidencia estructurada</span>";
  }

  function xioEvidenceMarkup() {
    const xio = state.scene?.xio_evidence;
    if (!xio?.available) return "";
    const atoms = (xio.evidence || []).filter((row) => row.status !== "unknown").slice(0, 5);
    const unknowns = (xio.evidence || []).filter((row) => row.status === "unknown").map((row) => row.field);
    const segments = (xio.segments || []).slice(0, 3);
    const atomMarkup = atoms.map((row) => `<span><b>${escMesa(row.field)}</b> ${escMesa(row.value)} · ${escMesa(row.status)}</span>`).join("");
    const segmentMarkup = segments.map((row) => `<span><b>${escMesa(row.timecode || "sin TC")}</b> ${escMesa(row.title || "segmento")}</span>`).join("");
    const unknownMarkup = unknowns.length ? `<small>sin declarar: ${escMesa([...new Set(unknowns)].join(", "))}</small>` : "";
    const linked = (xio.linked_source_ids || []).map(String);
    const currentLinked = linked.includes(String(state.activeId));
    const linkedMarkup = linked.length
      ? `<small>enlace humano: ${escMesa(linked.join(", "))}</small>`
      : "";
    const actionMarkup = currentLinked
      ? `<small>esta pieza ya está enlazada; no se publicó automáticamente.</small>`
      : `<button type="button" data-pop-action="xio-link" data-xio-work-id="${escMesa(xio.work?.work_id || "")}">vincular esta pieza como fuente humana</button>`;
    return `<details class="mesa-xio-evidence"><summary>XIO · evidencia separada</summary><p>Fuente disponible; el enlace requiere decisión humana explícita.</p><div class="mesa-xio-atoms">${atomMarkup || "<span>sin átomos declarados</span>"}</div><div class="mesa-xio-segments">${segmentMarkup}</div>${unknownMarkup}${linkedMarkup}<small>siguiente: ${escMesa(xio.next_action || "revisión humana")}</small><div class="mesa-xio-action">${actionMarkup}</div></details>`;
  }

  async function linkXioToRecord(workId, sourceId) {
    const busyKey = `xio-link:${workId}:${sourceId}`;
    if (!workId || !sourceId || state.feedbackBusy.has(busyKey)) return;
    state.feedbackBusy.add(busyKey);
    try {
      const response = await fetch("/api/portfolio/copilot/xio-link", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ work_id: workId, source_id: sourceId }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (!data.ok) throw new Error(data.error || "enlace XIO no guardado");
      state.scene.xio_evidence.linked_source_ids = data.linked_source_ids || [sourceId];
      state.scene.xio_evidence.linked_to_source_id = true;
      state.scene.xio_evidence.next_action = "none";
      invalidateSceneCache();
      showRecordPopover();
      setStatus(data.already_linked
        ? "el enlace XIO ya existía; se conservó el historial."
        : "enlace XIO guardado como decisión humana; no se publicó automáticamente.");
    } catch (error) {
      setStatus("no se guardó el enlace XIO: " + error.message);
    } finally {
      state.feedbackBusy.delete(busyKey);
    }
  }

  function externalReviewMarkup(record) {
    const candidates = externalForSource(record?.source_id);
    if (!candidates.length) return "";
    const cards = candidates.map((candidate) => {
      const decision = String(candidate.human_decision || candidate.review_state || "pending").toLowerCase();
      const grouping = candidate.grouping || {};
      const groupingText = grouping.is_carousel
        ? `carrusel agrupado · ${escMesa(grouping.member_count || grouping.member_ids?.length || "varios")} medios`
        : candidate.record_kind === "story_record" ? "story · registro audiovisual" : "unidad de medio";
      const actions = isPendingExternal(candidate)
        ? `<div class="mesa-external-review-actions"><button type="button" data-pop-action="external-review" data-external-ledger-id="${escMesa(candidate.ledger_id)}" data-external-decision="accept">aceptar candidato</button><button type="button" data-pop-action="external-review" data-external-ledger-id="${escMesa(candidate.ledger_id)}" data-external-decision="revise">dejar en revisión</button><button type="button" data-pop-action="external-review" data-external-ledger-id="${escMesa(candidate.ledger_id)}" data-external-decision="reject">rechazar candidato</button></div>`
        : `<small>decisión humana: ${escMesa(decision)} · historial conservado · no publicado</small>`;
      return `<article class="mesa-external-review-card"><strong>${escMesa(candidate.provider || "proveedor desconocido")} · confianza ${escMesa(candidate.confidence ?? "sin dato")}</strong><div>${escMesa(candidate.hypothesis || candidate.candidate_relations?.visual_similarity?.[0] || "hipótesis visual sin texto")}</div><small>${escMesa(groupingText)} · ${escMesa(candidate.promotion || "not_promoted")} · no es hecho canónico</small>${actions}</article>`;
    }).join("");
    const note = candidates.some(isPendingExternal)
      ? `<textarea data-external-note maxlength="1000" placeholder="nota opcional para la revisión humana…"></textarea>` : "";
    return `<details class="mesa-external-review" open><summary>evidencia externa · ${candidates.length} hipótesis · fuente aislada</summary>${cards}${note}</details>`;
  }

  async function externalDecision(ledgerId, sourceId, decision, note = "") {
    const busyKey = `external:${ledgerId}`;
    if (state.feedbackBusy.has(busyKey)) return;
    state.feedbackBusy.add(busyKey);
    try {
      const response = await fetch("/api/portfolio/external-candidates/review", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ledger_id: ledgerId, source_id: sourceId, decision, note }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (!data.ok) throw new Error(data.error || "decisión externa no guardada");
      const candidate = state.externalCandidates.find((row) => row.ledger_id === ledgerId);
      if (candidate) {
        candidate.human_decision = decision;
        candidate.review_state = decision === "revise" ? "pending" : decision;
        candidate.human_note = note;
      }
      updateExternalQueueCount();
      showRecordPopover();
      setStatus(decision === "accept"
        ? "hipótesis aceptada como evidencia candidata; no se publicó automáticamente."
        : decision === "reject" ? "hipótesis rechazada; se conserva su historial." : "hipótesis queda en revisión.");
    } catch (error) {
      setStatus("no se guardó la decisión externa: " + error.message);
    } finally {
      state.feedbackBusy.delete(busyKey);
    }
  }

  function showRecordPopover() {
    const record = byId(state.selectedId);
    if (!record) return closePopover();
    const active = record.source_id === state.activeId;
    const directRelation = relationForTarget(record.source_id);
    const usefulSuggestions = active ? pendingRelations().slice(0, 6) : [];
    const relationChoices = usefulSuggestions.map((relation) => suggestionMarkup(
      relation, byId(relationCounterpartId(relation)) || {})).join("");
    const group = record.publication_group;
    const groupNote = group?.count > 1
      ? `<div class="mesa-publication-group">una obra editorial · ${escMesa(group.count)} medios del mismo carrusel; no se separan como relaciones</div>`
      : "";
    const workGroup = record.work_group;
    const workGroupNote = workGroup?.count > 1
      ? `<div class="mesa-work-group-note">misma obra · ${escMesa(workGroup.count)} piezas agrupadas visualmente; sus relaciones ya no ocupan nodos separados.</div>`
      : "";
    const description = String(record.description || "").trim();
    const pieceContext = `${groupNote}${workGroupNote}`;
    const identityMarkup = `<div class="mesa-popover-identity"><h3>${escMesa(record.source_id)}</h3><p class="mesa-popover-meta">${escMesa(record.date || "sin fecha")} · ${escMesa(record.content_type || "registro")}${escMesa(publicationSummary(record))}${escMesa(workGroupSummary(record))}</p></div>`;
    const descriptionMarkup = description ? `<p class="mesa-popover-description">${escMesa(description)}</p>` : "";
    const xioMarkup = active ? xioEvidenceMarkup() : "";
    const externalMarkup = externalReviewMarkup(record);
    const seedNextAction = state.humanSeedActive && active
      ? actionButton("next", "siguiente") : "";
    const decisionMarkup = `${classificationMarkup(record)}<div class="mesa-popover-actions" role="toolbar" aria-label="acciones de pieza">${actionButton("center", "centro", active ? "disabled" : "")}${actionButton("relate", "relacionar", active && !usefulSuggestions.length ? "disabled" : "")}${actionButton("open", "abrir")}${actionButton("discard", "retirar")}${seedNextAction}</div>${directRelation ? `<div class="mesa-popover-note">Esta pieza tiene una hipótesis con el centro. ` + `<button type="button" data-pop-action="relation" data-relation-id="${escMesa(directRelation.relation_id)}">ver sugerencia</button></div>` : ""}`;
    const suggestionsDrawerMarkup = active && usefulSuggestions.length
      ? `<details class="mesa-suggestion-drawer" open><summary>sugerencias · ${usefulSuggestions.length}</summary><div class="mesa-suggestion-chips">${relationChoices}</div></details>`
      : "";
    openPopover(`<div class="mesa-popover-head"><span>${active ? "nodo activo" : "nodo seleccionado"}</span><button type="button" class="mesa-popover-close" data-pop-action="close" aria-label="cerrar">×</button></div><div class="mesa-popover-flow">${identityMarkup}${pieceContext}${descriptionMarkup}${xioMarkup}${externalMarkup}${decisionMarkup}${suggestionsDrawerMarkup}</div>`);
  }

  function selectRelation(relationId) {
    showRelationPopover(relationId);
  }

  function showRelationPopover(relationId) {
    const relation = (state.scene?.relations || []).find((row) => row.relation_id === relationId);
    const target = relation ? byId(relationCounterpartId(relation)) : null;
    if (!relation || !target) return showRecordPopover();
    state.selectedRelationId = relationId;
    state.selectedId = state.activeId;
    refreshScene();
    const facets = relationFacetOptions(relation, target);
    const selectedFacet = relation.feedbackFacet || relation.feedback_facet || facets[0] || "text";
    const facetChoices = facets.map((facet) => `<button type="button" class="mesa-relation-facet${facet === selectedFacet ? " is-active" : ""}" data-pop-action="facet" data-facet="${escMesa(facet)}">${escMesa(relationFacetLabels[facet])}</button>`).join("");
    const anchor = byId(relation.source_id) || byId(state.activeId);
    const relationDraft = anchor ? draftFor(anchor).relations.find((row) => (
      String(row.target_id) === String(relation.target_id)
      && String(row.relation || "") === String(relation.relation_type || "related")
    )) : null;
    const pendingRelation = Boolean(relationDraft);
    const relationUndoAvailable = !pendingRelation
      && ["accepted", "rejected"].includes(String(relation.status || ""));
    const decisions = pendingRelation
      ? `<span class="mesa-relation-pending">borrador de vínculo: ${escMesa(relationDraft.decision)} · todavía no ejecutado</span>${actionButton("save-draft", "guardar borrador")}${actionButton("commit-draft", "efectuar vínculo")}${actionButton("cancel-draft", "volver sin aplicar")}`
      : relation.status === "accepted"
        ? `<span class="mesa-relation-accepted">relación aceptada · ${escMesa(relationFacetLabels[selectedFacet] || selectedFacet)}</span>${relationUndoAvailable ? actionButton("undo-relation", "deshacer vínculo", `data-relation-id="${escMesa(relation.relation_id)}"`) : ""}`
        : relation.status === "rejected"
          ? `<span class="mesa-relation-rejected">relación rechazada · historial conservado</span>${relationUndoAvailable ? actionButton("undo-relation", "deshacer vínculo", `data-relation-id="${escMesa(relation.relation_id)}"`) : ""}`
          : `${actionButton("accept", "aceptar", `data-relation-id="${escMesa(relation.relation_id)}"`)}${actionButton("reject", "rechazar", `data-relation-id="${escMesa(relation.relation_id)}"`)}`;
    openPopover(`<div class="mesa-popover-head"><span style="color:${relationColor(relation)}">copiloto · sugerencia</span><button type="button" class="mesa-popover-close" data-pop-action="close" aria-label="cerrar">×</button></div><div class="mesa-popover-flow"><div class="mesa-relation-target"><div class="mesa-relation-target-media">${workGroupMedia(target)}</div><div><h3>${escMesa((relation.channels || []).join(" · ") || relation.relation_type)}</h3><p class="mesa-popover-meta">destino · ${escMesa(target.source_id)} · ${escMesa(target.date || "sin fecha")} · confianza ${escMesa(relation.confidence || "sin dato")}</p></div></div><div class="mesa-popover-evidence">${relationEvidence(relation)}</div><div class="mesa-relation-facets"><span>qué tipo de vínculo estás confirmando</span><div>${facetChoices}</div></div><details class="mesa-decision-note"><summary>añadir comentario opcional</summary><textarea data-pop-note maxlength="1000" placeholder="solo si necesitas dejar memoria para MAK…"></textarea></details><div class="mesa-popover-actions mesa-popover-relation-actions">${actionButton("center", "centro", `data-target-id="${escMesa(target.source_id)}"`)}${actionButton("open", "abrir", `data-target-id="${escMesa(target.source_id)}"`)}${decisions}</div></div><button type="button" class="mesa-popover-back" data-pop-action="back">volver a la pieza</button>`);
    const noteField = state.popover.querySelector("[data-pop-note]");
    if (noteField) noteField.value = relationDraft?.note || relation.note || "";
    if (relationDraft?.note || relation.note) {
      const savedNote = document.createElement("div");
      savedNote.className = "mesa-popover-saved-note";
      savedNote.textContent = "comentario guardado: " + (relationDraft?.note || relation.note);
      noteField?.parentElement?.before(savedNote);
    }
  }

  function openRecord(record) {
    if (!record?.asset_path) {
      setStatus("Esta pieza no tiene un archivo sincronizado para abrir.");
      return;
    }
    window.open(record.asset_path, "_blank", "noopener,noreferrer");
  }

  async function centerRecord(id) {
    if (!byId(id) && !state.items.some((item) => item.id === id)) return;
    if (id === state.activeId) {
      state.selectedId = id;
      showRecordPopover();
      centerNodeInView(id);
      return;
    }
    const requestId = ++state.viewRequestId;
    setStatus("cargando las relaciones de la nueva pieza…");
    try {
      const surface = state.editorMode === "order" ? "order" : "";
      const scene = await fetchSceneCached(id, state.suggestionMode, surface);
      if (requestId !== state.viewRequestId) return;
      state.scene = scene;
      state.activeId = id;
      state.selectedId = id;
      state.selectedRelationId = "";
      state.camera = { x: 0, y: 0, zoom: 1 };
      rebuildScene();
      showRecordPopover();
      centerNodeInView(id);
      setStatus("pieza centrada; sus relaciones ya están cargadas.");
    } catch (error) {
      setStatus("No se pudo centrar la pieza: " + error.message);
    }
  }

  function toggleClassification(field, value) {
    const record = byId(state.selectedId);
    if (!record) return;
    state.classificationAxis = field === "context_kind" ? "context_kind" : field;
    const draft = draftFor(record);
    const fields = { ...draft.fields };
    const clearFields = [...draft.clear_fields];
    const contextFields = { ...draft.context_fields };
    const previousContextKind = String(draft.fields.context_kind || "");
    if (field === "context_kind" && previousContextKind
        && previousContextKind !== value) {
      delete contextFields[previousContextKind];
    }
    if (fields[field] === value) {
      delete fields[field];
      if (!clearFields.includes(field)) clearFields.push(field);
      if (field === "context_kind") {
        delete fields.context_value;
        delete contextFields[value];
        if (!clearFields.includes("context_value")) clearFields.push("context_value");
      }
    } else {
      if (field === "context_kind" && fields.context_kind !== value) {
        delete fields.context_value;
        if (!clearFields.includes("context_value")) clearFields.push("context_value");
      }
      fields[field] = value;
      const clearIndex = clearFields.indexOf(field);
      if (clearIndex >= 0) clearFields.splice(clearIndex, 1);
    }
    updateDraft(record, {
      fields, clear_fields: clearFields, context_fields: contextFields,
    });
    rebuildScene();
    showRecordPopover();
    setStatus("clasificación preparada en el borrador; todavía no se ejecutó.");
  }

  function saveClassificationContext() {
    const record = byId(state.selectedId);
    state.classificationAxis = "context_kind";
    const draft = record ? draftFor(record) : null;
    const kind = draft?.fields?.context_kind
      || state.popover.querySelector('[data-class-field="context_kind"].is-active')?.dataset.classValue
      || "";
    const value = state.popover.querySelector("[data-class-context-value]")?.value.trim() || "";
    if (!record || !kind || !value) {
      setStatus("El contexto necesita tipo y nombre; no se guardó todavía.");
      return;
    }
    const fields = { ...draft.fields, context_kind: kind, context_value: value };
    const clearFields = draft.clear_fields.filter((field) => (
      field !== "context_kind" && field !== "context_value"
    ));
    const contextFields = {
      ...draft.context_fields,
      [kind]: [value],
    };
    updateDraft(record, {
      fields, clear_fields: clearFields, context_fields: contextFields,
    });
    rebuildScene();
    showRecordPopover();
    setStatus("contexto preparado en el borrador; todavía no se ejecutó.");
  }

  async function advanceSeedFromPopover() {
    const record = byId(state.selectedId);
    const draft = record ? draftFor(record) : null;
    const triage = draft?.fields?.triage || record?.classification?.triage;
    if (!record || record.source_id !== state.humanSeedItemId) return;
    if (!triage) {
      setStatus("elige obra, registro, revisar o descartar antes de seguir.");
      return;
    }
    if (draftIsPending(record)) {
      setStatus("efectúa o cancela el borrador antes de avanzar.");
      return;
    }
    if (state.feedbackBusy.has("advance-seed")) return;
    state.feedbackBusy.add("advance-seed");
    try {
      state.orderSelectedIds.clear();
      closePopover();
      await loadHumanSeed({ refresh: false, excludeId: record.source_id });
    } finally {
      state.feedbackBusy.delete("advance-seed");
    }
  }

  async function portfolioPost(path, payload) {
    const response = await fetch(path, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    let data = {};
    try { data = await response.json(); } catch { /* preserve the HTTP failure */ }
    if (!response.ok || !data.ok) {
      throw new Error(data.error || `HTTP ${response.status}`);
    }
    return data;
  }

  function syncRecordFromItem(record, item) {
    if (!record || !item) return;
    if (item.classification) record.classification = { ...item.classification };
    if (item.selection) record.selection = item.selection;
    const mirror = state.items.find((candidate) => candidate.id === record.source_id);
    if (mirror) {
      if (item.classification) mirror.classification = { ...item.classification };
      if (item.selection) mirror.selection = item.selection;
      if (item.decision_draft) mirror.decision_draft = { ...item.decision_draft };
    }
  }

  function clearDraftState(record, terminal = {}) {
    if (!record) return;
    state.drafts.delete(record.source_id);
    state.draftDirty.delete(record.source_id);
    record.decision_draft = terminal;
  }

  async function refreshActiveScene() {
    if (!state.activeId) return;
    const surface = state.editorMode === "order" ? "order" : "";
    const scene = await fetchScene(state.activeId, state.suggestionMode, surface);
    state.scene = scene;
    state.selectedId = state.activeId;
    state.selectedRelationId = "";
    rebuildScene();
  }

  async function saveDraft(record, options = {}) {
    if (!record) return false;
    const draft = draftFor(record);
    if (!draftHasContent(draft)) {
      if (!options.silent) setStatus("no hay cambios para guardar en el borrador.");
      return false;
    }
    try {
      const data = await portfolioPost("/api/portfolio/draft", {
        ...draft, status: "saved", session_id: state.sessionId,
      });
      const saved = data.draft || { ...draft, status: "saved" };
      state.drafts.set(record.source_id, saved);
      state.draftDirty.delete(record.source_id);
      record.decision_draft = saved;
      if (!options.silent) {
        rebuildScene();
        showRecordPopover();
        setStatus("borrador guardado; ninguna acción fue ejecutada.");
      }
      return true;
    } catch (error) {
      if (!options.silent) setStatus("no se guardó el borrador: " + error.message);
      return false;
    }
  }

  async function commitDraft(record, options = {}) {
    if (!record) return false;
    const draft = draftFor(record);
    if (!draftHasContent(draft)) {
      if (!options.silent) setStatus("no hay un borrador pendiente para efectuar.");
      return false;
    }
    if (!options.confirmed && !window.confirm(
      `Confirmar acción para ${record.source_id}? Se conservará el historial.`)) {
      return false;
    }
    try {
      const data = await portfolioPost("/api/portfolio/commit", {
        ...draft, confirmed: true, session_id: state.sessionId,
      });
      syncRecordFromItem(record, data.item);
      clearDraftState(record, data.draft || { status: "committed" });
      invalidateSceneCache();
      if (!options.skipRefresh && record.source_id === state.activeId
          && draft.action !== "discard") {
        await refreshActiveScene();
      } else {
        rebuildScene();
      }
      if (!options.silent) {
        showRecordPopover();
        setStatus("acción confirmada; la pieza permanece en foco y su historial puede deshacerse.");
      }
      return true;
    } catch (error) {
      if (!options.silent) setStatus("no se ejecutó la acción: " + error.message);
      return false;
    }
  }

  async function saveDraftBatch(records) {
    let saved = 0;
    for (const record of records) {
      if (await saveDraft(record, { silent: true })) saved += 1;
    }
    renderOrderHud();
    rebuildScene();
    showRecordPopover();
    setStatus(`${saved} borrador(es) guardado(s); ninguna acción fue ejecutada.`);
  }

  async function commitDraftBatch(records) {
    const pending = records.filter((record) => draftHasContent(draftFor(record)));
    if (!pending.length) return setStatus("no hay borradores pendientes para efectuar.");
    const ids = pending.map((record) => record.source_id).join(", ");
    if (!window.confirm(`Confirmar ${pending.length} acción(es) para ${ids}? Se conservará el historial.`)) return;
    let committed = 0;
    for (const record of pending) {
      if (await commitDraft(record, { confirmed: true, silent: true, skipRefresh: true })) committed += 1;
    }
    invalidateSceneCache();
    const active = pending.find((record) => record.source_id === state.activeId);
    if (active && draftFor(active).action !== "discard") {
      try { await refreshActiveScene(); } catch { rebuildScene(); }
    } else {
      rebuildScene();
    }
    renderOrderHud();
    showRecordPopover();
    setStatus(`${committed}/${pending.length} acción(es) confirmada(s); ninguna pieza fue autoavanzada.`);
  }

  async function cancelDraft(record, options = {}) {
    if (!record || !draftIsPending(record)) return false;
    const draft = draftFor(record);
    try {
      if (["saved", "partial"].includes(draft.status)) {
        await portfolioPost("/api/portfolio/draft", {
          ...draft, cancel: true, session_id: state.sessionId,
        });
      }
      clearDraftState(record, { status: "cancelled" });
      if (!options.silent) {
        rebuildScene();
        showRecordPopover();
        setStatus("borrador cancelado; el historial previo no fue alterado.");
      }
      return true;
    } catch (error) {
      if (!options.silent) setStatus("no se canceló el borrador: " + error.message);
      return false;
    }
  }

  async function cancelDraftBatch(records) {
    let cancelled = 0;
    for (const record of records) {
      if (await cancelDraft(record, { silent: true })) cancelled += 1;
    }
    renderOrderHud();
    rebuildScene();
    showRecordPopover();
    setStatus(`${cancelled} borrador(es) cancelado(s); nada fue ejecutado.`);
  }

  async function undoLastAction(record, options = {}) {
    if (!record) return false;
    if (!options.confirmed && !window.confirm(
      `Deshacer la última acción de ${record.source_id}? El historial se conservará.`)) return false;
    try {
      const data = await portfolioPost("/api/portfolio/undo", {
        item_id: record.source_id, scope: "all", confirmed: true,
        session_id: state.sessionId,
      });
      syncRecordFromItem(record, data.item);
      clearDraftState(record, data.item?.decision_draft || { status: "undone" });
      invalidateSceneCache();
      if (record.source_id === state.activeId && record.selection !== "descartar") {
        await refreshActiveScene();
      } else {
        rebuildScene();
      }
      showRecordPopover();
      setStatus("acción deshecha mediante un evento append-only; el historial permanece.");
      return true;
    } catch (error) {
      setStatus("no se deshizo la acción: " + error.message);
      return false;
    }
  }

  async function undoRelationDecision(relationId) {
    const relation = (state.scene?.relations || []).find((row) => row.relation_id === relationId);
    if (!relation) return false;
    if (!window.confirm(`Deshacer el vínculo con ${relation.target_id}? El historial se conservará.`)) return false;
    try {
      const data = await portfolioPost("/api/portfolio/undo", {
        item_id: relation.source_id, target_id: relation.target_id,
        facet: relation.feedbackFacet || relation.feedback_facet || (relation.channels || ["relation"])[0],
        relation: relation.relation_type, scope: "relation", confirmed: true,
        session_id: state.sessionId,
      });
      const anchor = byId(relation.source_id);
      syncRecordFromItem(anchor, data.item);
      clearDraftState(anchor, data.item?.decision_draft || { status: "undone" });
      invalidateSceneCache();
      await refreshActiveScene();
      showRelationPopover(relationId);
      setStatus("vínculo deshecho mediante un evento append-only; sus decisiones previas permanecen.");
      return true;
    } catch (error) {
      setStatus("no se deshizo el vínculo: " + error.message);
      return false;
    }
  }

  function discardRecord(record, note = "") {
    if (!record) return;
    const draft = draftFor(record);
    const fields = { ...draft.fields, triage: "discard" };
    const clearFields = draft.clear_fields.filter((field) => field !== "triage");
    updateDraft(record, { action: "discard", fields, clear_fields: clearFields, note });
    rebuildScene();
    showRecordPopover();
    setStatus("descarte preparado en el borrador; la pieza sigue visible y no se avanzó.");
  }

  function relationDecision(decision, relationId, note = "") {
    const relation = (state.scene?.relations || []).find((row) => row.relation_id === relationId);
    const anchor = relation ? byId(relation.source_id) : null;
    if (!relation || !anchor || !["accept", "reject"].includes(decision)) return;
    const facet = relation.feedbackFacet || relation.feedback_facet
      || (relation.channels || ["relation"])[0];
    const draft = draftFor(anchor);
    const relations = draft.relations.filter((row) => !(
      String(row.target_id) === String(relation.target_id)
      && String(row.facet || "") === String(facet || "")
      && String(row.relation || "") === String(relation.relation_type || "related")
    ));
    relations.push({
      target_id: relation.target_id, decision, facet,
      relation: relation.relation_type || "related", note,
      visual: relation.visual || {},
    });
    updateDraft(anchor, { relations });
    relation.draft_decision = decision;
    relation.feedbackFacet = facet;
    relation.note = note;
    rebuildScene();
    showRelationPopover(relationId);
    setStatus("vínculo preparado en el borrador; todavía no se ejecutó.");
  }

  function handlePopoverAction(event) {
    const button = event.target.closest("[data-pop-action]");
    if (!button) return;
    event.stopPropagation();
    const action = button.dataset.popAction;
    const record = byId(state.selectedId);
    const note = state.popover.querySelector("[data-pop-note]")?.value?.trim() || "";
    if (action === "close") return closePopover();
    if (action === "audit-summary") return loadAuditSummary();
    if (action === "audit-item") return loadAuditSummary(button.dataset.auditItem || state.selectedId);
    if (action === "back") return showRecordPopover();
    if (action === "classify-axis") {
      state.classificationAxis = button.dataset.classAxis || "lane";
      return showRecordPopover();
    }
    if (action === "classify-toggle") {
      return toggleClassification(button.dataset.classField, button.dataset.classValue);
    }
    if (action === "classify-context") return saveClassificationContext();
    if (action === "save-draft") return saveDraft(record);
    if (action === "commit-draft") return commitDraft(record);
    if (action === "cancel-draft") return cancelDraft(record);
    if (action === "undo") return undoLastAction(record);
    if (action === "undo-relation") return undoRelationDecision(button.dataset.relationId);
    if (action === "next") return advanceSeedFromPopover();
    if (action === "xio-link") {
      button.disabled = true;
      return linkXioToRecord(button.dataset.xioWorkId, record?.source_id);
    }
    if (action === "external-review") {
      const externalNote = state.popover.querySelector("[data-external-note]")?.value?.trim() || "";
      state.popover.querySelectorAll('[data-pop-action="external-review"]').forEach((candidate) => {
        candidate.disabled = true;
      });
      return externalDecision(button.dataset.externalLedgerId, record?.source_id, button.dataset.externalDecision, externalNote);
    }
    if (action === "facet") {
      state.popover.querySelectorAll("[data-pop-action=facet]").forEach((candidate) => {
        candidate.classList.toggle("is-active", candidate === button);
      });
      const relation = state.scene?.relations?.find((row) => row.relation_id === state.selectedRelationId);
      if (relation) relation.feedbackFacet = button.dataset.facet;
      return;
    }
    if (action === "relation" || action === "relate") {
      if (action === "relate" && record?.source_id === state.activeId) {
        const drawer = state.popover.querySelector(".mesa-suggestion-drawer");
        if (drawer) {
          drawer.open = true;
          drawer.scrollIntoView({ block: "nearest", behavior: "smooth" });
        }
        return;
      }
      const relation = action === "relation" ? { relation_id: button.dataset.relationId } : relationForTarget(record?.source_id);
      return relation?.relation_id ? selectRelation(relation.relation_id) : setStatus("Selecciona una sugerencia visible para relacionarla.");
    }
    if (action === "center") return centerRecord(button.dataset.targetId || record?.source_id);
    if (action === "open") return openRecord(button.dataset.targetId ? byId(button.dataset.targetId) : record);
    if (action === "discard") return discardRecord(record, note);
    if (action === "accept" || action === "reject") {
      state.popover.querySelectorAll('[data-pop-action="accept"], [data-pop-action="reject"]').forEach((candidate) => {
        candidate.disabled = true;
      });
      return relationDecision(action, button.dataset.relationId, note);
    }
  }

  function sceneCacheKey(itemId, mode, surface) {
    return [itemId, mode || "copilot", surface || ""].join("|");
  }

  function rememberScene(key, scene) {
    state.sceneCache.set(key, scene);
    while (state.sceneCache.size > 3) {
      state.sceneCache.delete(state.sceneCache.keys().next().value);
    }
    return scene;
  }

  function invalidateSceneCache() {
    state.sceneCache.clear();
    state.sceneCachePromises.clear();
    state.sceneCacheRevision += 1;
  }

  async function fetchSceneCached(itemId, mode = state.suggestionMode, surface = "") {
    const key = sceneCacheKey(itemId, mode, surface);
    const cached = state.sceneCache.get(key);
    if (cached) return cached;
    const pending = state.sceneCachePromises.get(key);
    if (pending) return pending;
    const revision = state.sceneCacheRevision;
    const request = fetchScene(itemId, mode, surface)
      .then((scene) => revision === state.sceneCacheRevision
        ? rememberScene(key, scene) : scene)
      .finally(() => {
        if (state.sceneCachePromises.get(key) === request) {
          state.sceneCachePromises.delete(key);
        }
      });
    state.sceneCachePromises.set(key, request);
    return request;
  }

  function prefetchNextHumanSeed(seed, currentId) {
    const excluded = new Set(state.processedHumanSeed);
    excluded.add(String(currentId || ""));
    const next = seed.find((row) => seedCandidateAllowed(row, excluded));
    if (!next) return;
    fetchSceneCached(String(next.item_id), "copilot", "order").catch(() => {});
  }

  async function fetchScene(itemId, mode = state.suggestionMode, surface = "") {
    const query = new URLSearchParams({ item_id: itemId, limit: "10" });
    if (mode === "shuffle") {
      query.set("mode", "shuffle");
      query.set("seed", String(Date.now()));
    } else if (mode && mode !== "copilot" && mode !== "all") {
      query.set("facet", mode);
    }
    if (surface) query.set("surface", surface);
    const response = await fetch(`/api/portfolio/copilot/scene?${query.toString()}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const scene = await response.json();
    if (!scene.ok) throw new Error(scene.error || "escena no disponible");
    return scene;
  }

  async function reloadSuggestions(mode = state.suggestionMode) {
    if (!state.activeId) return;
    const normalizedMode = mode === "all" ? "copilot" : mode;
    state.suggestionMode = normalizedMode;
    state.lens = ["all", "copilot", "shuffle"].includes(mode) ? "all" : mode;
    state.root.querySelectorAll("[data-lens]").forEach((button) => {
      button.classList.toggle("is-active", button.dataset.lens === (state.lens === "all" ? "all" : state.lens));
    });
    const requestId = ++state.viewRequestId;
    setStatus(mode === "shuffle" ? "barajando hipótesis del copiloto…" : "cambiando lente de sugerencias…");
    try {
      const surface = state.editorMode === "order" ? "order" : "";
      const scene = await fetchScene(state.activeId, normalizedMode, surface);
      if (requestId !== state.viewRequestId) return;
      state.scene = scene;
      state.selectedId = state.activeId;
      state.selectedRelationId = "";
      rebuildScene();
      if (state.editorMode === "relate") showRecordPopover();
      else closePopover();
      setStatus(mode === "shuffle" ? "nuevas hipótesis cargadas." : `lente ${mode === "all" || mode === "copilot" ? "copiloto" : mode} cargada.`);
    } catch (error) {
      if (requestId === state.viewRequestId) {
        setStatus("No se pudo cambiar la lente: " + error.message);
      }
    }
  }

  async function load() {
    if (!mount()) return;
    setStatus("cargando la mesa…");
    try {
      const inboxResponse = await fetch("/api/portfolio/inbox?surface=mesa", { cache: "no-store" });
      if (!inboxResponse.ok) throw new Error(`HTTP ${inboxResponse.status}`);
      const inbox = await inboxResponse.json();
      if (!inbox || inbox.ok === false) throw new Error(inbox?.error || "inbox no disponible");
      state.items = inbox.items || [];
      state.drafts.clear();
      state.draftDirty.clear();
      state.items.forEach((item) => {
        const draft = item?.decision_draft;
        if (draft && ["saved", "partial", "local_draft"].includes(String(draft.status || ""))) {
          state.drafts.set(String(item.id), { ...draft, item_id: String(item.id) });
        }
      });
      await loadExternalQueue();
      const first = state.items.find((item) => item.asset_available && item.selection !== "descartar");
      if (!first) throw new Error("inbox vacío");
      state.activeId = first.id;
      state.selectedId = first.id;
      state.scene = await fetchScene(first.id, "copilot", "order");
      rebuildScene();
      if (state.editorMode === "relate") showRecordPopover();
      else closePopover();
      setStatus("mapa GTM listo; selecciona un nodo para abrir su HUD y cambiar el orden.");
    } catch (error) {
      state.root.innerHTML = `<div class="mesa-empty-state">No se pudo cargar la mesa: ${escMesa(error.message)}</div>`;
    }
  }

  window.mesaMontaje = { load, state, refreshScene };
  load();
}());
