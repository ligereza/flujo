import { useEffect, useMemo, useState } from 'react';
import {
  LayoutDashboard, Boxes, ClipboardList, Calculator,
  TerminalSquare, Map, Shapes, Zap, Activity,
  CheckCircle2, Clock, AlertCircle, ArrowRight, Camera, Radio, Layers,
  Loader2,
} from 'lucide-react';
import type { AppView } from './AppShell';
import { flujoApi, type Ping, type HubStatus, type JobsResponse, type ProjectLearningSummary, type ProjectProbeResponse, type ProjectReviewQueueResponse, type ArchivePortfolioViewResponse, type ArchiveOrientationResponse, type OperationsReadOnlyMapResponse, type RdReadOnlyContextResponse, type CulturaResearchReadOnlyContextResponse, type PortfolioVizzReadOnlyContextResponse, type LearningReadOnlyContextResponse, type PortfolioReviewContextResponse, type PortfolioRelationEvidencePlanResponse, type OperationReceiptResponse, type VizzMeasurementStatusResponse, type VizzLineageStatusResponse, type StructuralDeltaStatusResponse, type PortfolioDirectionContextResponse, type PortfolioWorkPacketResponse, type PortfolioWorkPreviewResponse, type ResearchJob, type ResearchJobsResponse, type ResearchContinuationResponse, type ResearchJobDetail, type ResearchHumanConfirmationResponse, type ResearchNormalizeReadinessResponse, type ResearchNormalizePlanResponse, type ResearchNormalizeDryRunResponse, type ResearchLicenseReviewResponse, type ResearchLicenseSourceReviewResponse, type ResearchLicenseCompatibilityPlanResponse } from '../api/flujoApi';

interface Props {
  onNavigate: (v: AppView) => void;
}

export default function HubDashboard({ onNavigate }: Props) {
  const [ping, setPing] = useState<Ping | null>(null);
  const [jobs, setJobs] = useState<JobsResponse | null>(null);
  const [learning, setLearning] = useState<ProjectLearningSummary | null>(null);
  const [systemStatus, setSystemStatus] = useState<HubStatus | null>(null);
  const [operationsMap, setOperationsMap] = useState<OperationsReadOnlyMapResponse | null>(null);
  const [rdContext, setRdContext] = useState<RdReadOnlyContextResponse | null>(null);
  const [culturaResearchContext, setCulturaResearchContext] = useState<CulturaResearchReadOnlyContextResponse | null>(null);
  const [portfolioVizzContext, setPortfolioVizzContext] = useState<PortfolioVizzReadOnlyContextResponse | null>(null);
  const [learningContext, setLearningContext] = useState<LearningReadOnlyContextResponse | null>(null);
  const [reviewQueue, setReviewQueue] = useState<ProjectReviewQueueResponse | null>(null);
  const [researchJobs, setResearchJobs] = useState<ResearchJobsResponse | null>(null);
  const [researchJobDetail, setResearchJobDetail] = useState<ResearchJobDetail | null>(null);
  const [researchJobBusy, setResearchJobBusy] = useState(false);
  const [researchActor, setResearchActor] = useState('');
  const [researchConfirmation, setResearchConfirmation] = useState<ResearchHumanConfirmationResponse | null>(null);
  const [researchConfirmationBusy, setResearchConfirmationBusy] = useState(false);
  const [researchNormalizeReadiness, setResearchNormalizeReadiness] = useState<ResearchNormalizeReadinessResponse | null>(null);
  const [researchNormalizePlan, setResearchNormalizePlan] = useState<ResearchNormalizePlanResponse | null>(null);
  const [researchNormalizeDryRun, setResearchNormalizeDryRun] = useState<ResearchNormalizeDryRunResponse | null>(null);
  const [researchLicenseReview, setResearchLicenseReview] = useState<ResearchLicenseReviewResponse | null>(null);
  const [researchLicenseSourceReview, setResearchLicenseSourceReview] = useState<ResearchLicenseSourceReviewResponse | null>(null);
  const [researchLicenseCompatibilityPlan, setResearchLicenseCompatibilityPlan] = useState<ResearchLicenseCompatibilityPlanResponse | null>(null);
  const [researchResume, setResearchResume] = useState<ResearchContinuationResponse | null>(null);
  const [researchResumeBusy, setResearchResumeBusy] = useState(false);
  const [selectedReviewProjectId, setSelectedReviewProjectId] = useState('');
  const [archiveView, setArchiveView] = useState<ArchivePortfolioViewResponse | null>(null);
  const [archiveOrientation, setArchiveOrientation] = useState<ArchiveOrientationResponse | null>(null);
  const [portfolioReviewContext, setPortfolioReviewContext] = useState<PortfolioReviewContextResponse | null>(null);
  const [portfolioRelationEvidencePlan, setPortfolioRelationEvidencePlan] = useState<PortfolioRelationEvidencePlanResponse | null>(null);
  const [portfolioDirectionContext, setPortfolioDirectionContext] = useState<PortfolioDirectionContextResponse | null>(null);
  const [portfolioWorkPacket, setPortfolioWorkPacket] = useState<PortfolioWorkPacketResponse | null>(null);
  const [portfolioWorkPreview, setPortfolioWorkPreview] = useState<PortfolioWorkPreviewResponse | null>(null);
  const [operationReceipt, setOperationReceipt] = useState<OperationReceiptResponse | null>(null);
  const [vizzMeasurementStatus, setVizzMeasurementStatus] = useState<VizzMeasurementStatusResponse | null>(null);
  const [vizzLineageStatus, setVizzLineageStatus] = useState<VizzLineageStatusResponse | null>(null);
  const [structuralDeltaStatus, setStructuralDeltaStatus] = useState<StructuralDeltaStatusResponse | null>(null);
  const [probeOpen, setProbeOpen] = useState(false);
  const [probeText, setProbeText] = useState('');
  const [probeResult, setProbeResult] = useState<ProjectProbeResponse | null>(null);
  const [probeBusy, setProbeBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    flujoApi.ping().then(d => alive && setPing(d));
    flujoApi.jobs().then(d => alive && setJobs(d));
    flujoApi.status().then(d => {
      if (!alive) return;
      setSystemStatus(d);
      setLearning(d.operational?.learning || null);
    });
    flujoApi.operationsReadOnlyMap().then(d => alive && setOperationsMap(d));
    flujoApi.rdReadOnlyContext().then(d => alive && setRdContext(d));
    flujoApi.culturaResearchReadOnlyContext().then(d => alive && setCulturaResearchContext(d));
    flujoApi.portfolioVizzReadOnlyContext().then(d => alive && setPortfolioVizzContext(d));
    flujoApi.learningReadOnlyContext().then(d => alive && setLearningContext(d));
    flujoApi.projectReviewQueue().then(d => {
      if (!alive) return;
      setReviewQueue(d);
    });
    flujoApi.researchJobs().then(d => alive && setResearchJobs(d));
    flujoApi.archivePortfolioView().then(d => alive && setArchiveView(d));
    // archiveOrientation() keeps declared-works, documented-record,
    // observed-field and practice-context separate for the read-only view.
    flujoApi.archiveOrientation().then(d => alive && setArchiveOrientation(d));
    flujoApi.operationReceipt().then(d => alive && setOperationReceipt(d));
    flujoApi.vizzMeasurementStatus().then(d => alive && setVizzMeasurementStatus(d));
    flujoApi.vizzLineageStatus().then(d => alive && setVizzLineageStatus(d));
    flujoApi.structuralDeltaStatus().then(d => alive && setStructuralDeltaStatus(d));
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    let alive = true;
    // portfolioDirectionContext() remains read-only; the selected project is
    // only a query parameter for the contextual view.
    flujoApi.portfolioReviewContext(selectedReviewProjectId || undefined).then(d => {
      if (alive) {
        setPortfolioReviewContext(d);
        setPortfolioDirectionContext(null);
      }
    });
    flujoApi.portfolioRelationEvidencePlan(selectedReviewProjectId || undefined).then(d => {
      // portfolioRelationEvidencePlan() remains read-only and relation-unbound.
      if (alive) setPortfolioRelationEvidencePlan(d);
    });
    flujoApi.portfolioDirectionContext(selectedReviewProjectId || undefined).then(d => {
      if (alive) setPortfolioDirectionContext(d);
    });
    // portfolioWorkPacket() is a read-only task list; it never executes a task.
    flujoApi.portfolioWorkPacket(selectedReviewProjectId || undefined).then(d => {
      if (alive) setPortfolioWorkPacket(d);
    });
    setPortfolioWorkPreview(null);
    return () => { alive = false; };
  }, [selectedReviewProjectId]);

  const openJobs = jobs?.jobs.filter(j => !String(j.estado || '').toLowerCase().includes('entregado')).length ?? 0;
  const recent = useMemo(() => (jobs?.jobs || []).slice(0, 5), [jobs]);
  const projectCount = Object.values(learning?.projects || {}).reduce((sum, count) => sum + count, 0);
  const episodeCount = Object.values(learning?.episodes || {}).reduce((sum, count) => sum + count, 0);
  const promotedRules = learning?.rules?.promoted || 0;
  const contractCount = Object.values(learning?.contracts?.counts || {}).reduce((sum, count) => sum + count, 0);
  const auditedCount = Object.values(learning?.audits?.statuses || {}).reduce((sum, count) => sum + count, 0);
  const auditAttention = learning?.audits?.attention || [];
  const latestAbstain = learning?.latest_abstain;
  const operational = systemStatus?.operational;
  const operationalStatus = String(operational?.status || 'unknown');
  const operationalStatusLabel = {
    ready: 'Listo',
    attention: 'Requiere atención',
    blocked: 'Bloqueado',
    unknown: 'No disponible',
  }[operationalStatus] || operationalStatus;
  const operationalStatusClass = operationalStatus === 'ready'
    ? 'border-emerald-800/60 bg-emerald-950/20 text-emerald-300'
    : operationalStatus === 'blocked'
      ? 'border-rose-800/60 bg-rose-950/20 text-rose-300'
      : operationalStatus === 'attention'
        ? 'border-amber-800/60 bg-amber-950/20 text-amber-300'
        : 'border-zinc-700 bg-zinc-900/60 text-zinc-400';

  const runProbe = async () => {
    setProbeBusy(true);
    setProbeResult(null);
    try {
      const parsed = JSON.parse(probeText);
      setProbeResult(await flujoApi.projectProbe(parsed));
    } catch (error) {
      setProbeResult({ ok: false, error: error instanceof Error ? error.message : String(error) });
    } finally {
      setProbeBusy(false);
    }
  };

  const resumeResearch = async (job: ResearchJob) => {
    if (researchResumeBusy || job.next_process !== 'extract') return;
    setResearchResumeBusy(true);
    try {
      const requestId = `hub-job-${job.id}-${job.next_process}`;
      setResearchResume(await flujoApi.resumeResearchJob(job.id, job.next_process || '', requestId));
      setResearchJobs(await flujoApi.researchJobs());
    } finally {
      setResearchResumeBusy(false);
    }
  };

  const inspectResearchJob = async (jobId: number) => {
    setResearchJobBusy(true);
    try {
      const result = await flujoApi.researchJob(jobId);
      setResearchJobDetail(result.job || null);
      setResearchNormalizeReadiness(await flujoApi.researchNormalizeReadiness(jobId));
      setResearchNormalizePlan(await flujoApi.researchNormalizePlan(jobId));
      setResearchNormalizeDryRun(await flujoApi.researchNormalizeDryRun(jobId));
      setResearchLicenseReview(await flujoApi.researchLicenseReview(jobId));
      setResearchLicenseSourceReview(await flujoApi.researchLicenseSourceReview(jobId));
      setResearchLicenseCompatibilityPlan(await flujoApi.researchLicenseCompatibilityPlan(jobId));
    } finally {
      setResearchJobBusy(false);
    }
  };

  const confirmResearchExtraction = async () => {
    const jobId = researchJobDetail?.id;
    const inputSha256 = researchJobDetail?.extract_input_sha256 || researchResume?.input_sha256 || '';
    const actor = researchActor.trim();
    if (!jobId || !inputSha256 || !actor || researchConfirmationBusy) return;
    setResearchConfirmationBusy(true);
    try {
      const requestId = `hub-confirm-extract-${jobId}-${inputSha256.slice(0, 12)}`;
      setResearchConfirmation(await flujoApi.confirmResearchExtraction(jobId, actor, inputSha256, requestId));
    } finally {
      setResearchConfirmationBusy(false);
    }
  };

  const previewPortfolioTask = async (taskId: string) => {
    if (!taskId) return;
    // portfolioWorkPreview() is a query-only scope check.
    setPortfolioWorkPreview(await flujoApi.portfolioWorkPreview(taskId, selectedReviewProjectId || undefined));
  };

  // Editables primero (producen trabajo dentro de la app); consulta y
  // generadores de comandos copy/paste al final.
  const actions = [
    { view: 'plano' as const, icon: Map, title: 'Plano / Rider', desc: 'Dibujá el plano del evento y sacá su rider para el recinto', color: 'from-emerald-500 to-teal-600', badge: 'editable' },
    { view: 'visualizer' as const, icon: Shapes, title: 'SVG Studio', desc: 'Revisá las piezas de diseño y ajustá textos y alineación', color: 'from-violet-500 to-purple-600', badge: 'editable' },
    { view: 'quote' as const, icon: Calculator, title: 'Cotización', desc: 'Armá el presupuesto y exportalo en PDF', color: 'from-pink-500 to-rose-600', badge: 'editable' },
    { view: 'intake' as const, icon: ClipboardList, title: 'Pegar Pedido', desc: 'Pegá el correo del cliente y queda anotado como trabajo', color: 'from-blue-500 to-cyan-600', badge: 'editable' },
    { view: 'jobs' as const, icon: Boxes, title: 'Ver trabajos', desc: 'En qué va cada trabajo, con lo que hay en disco', color: 'from-yellow-500 to-amber-600' },
    { view: 'events' as const, icon: Camera, title: 'Eventos / IG', desc: 'Prepara el flyer de un evento desde su publicación de Instagram', color: 'from-fuchsia-500 to-violet-600', badge: 'Studio' },
    { view: 'resolume' as const, icon: Radio, title: 'Resolume / Chataigne', desc: 'Arma el comando SMPTE/OSC pre-flight para shows', color: 'from-indigo-500 to-blue-600', badge: 'SMPTE' },
    { view: 'commands' as const, icon: TerminalSquare, title: 'Comandos', desc: 'Copiar checks y build', color: 'from-zinc-400 to-zinc-600' },
    { view: 'cultura' as const, icon: Layers, title: 'Cultura', desc: 'Arte-investigacion: tapiz, tilde, psicosis, precursor', color: 'from-amber-500 to-orange-700', badge: 'Cultura' },
  ];

  const statusColor = (s?: string) => {
    const v = String(s || '').toLowerCase();
    if (v.includes('entregado')) return 'text-emerald-400 bg-emerald-500/10';
    if (v.includes('revision') || v.includes('revis')) return 'text-blue-400 bg-blue-500/10';
    if (v.includes('diseno') || v.includes('dise')) return 'text-purple-400 bg-purple-500/10';
    if (v.includes('pendiente')) return 'text-yellow-400 bg-yellow-500/10';
    return 'text-zinc-400 bg-zinc-800';
  };

  return (
    <div className="space-y-8">
      {/* Hero header */}
      <div className="relative overflow-hidden rounded-2xl border border-zinc-800/70 bg-gradient-to-br from-zinc-900 via-zinc-900 to-zinc-800 p-6 md:p-8">
        <div className="absolute right-0 top-0 h-64 w-64 bg-gradient-to-bl from-emerald-500/5 to-transparent" />
        <div className="relative">
          <div className="flex items-center gap-3 mb-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 shadow-lg shadow-emerald-500/20">
              <Zap className="h-5 w-5 text-white" />
            </div>
            <div>
              <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider
                ${ping?.connected !== false ? 'border-emerald-800 bg-emerald-950/50 text-emerald-400' : 'border-zinc-700 bg-zinc-800/50 text-zinc-400'}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${ping?.connected !== false ? 'bg-emerald-400 animate-pulse' : 'bg-zinc-500'}`} />
                {ping?.connected !== false ? 'todo local, sin nube' : 'modo demostración'}
              </span>
            </div>
          </div>
          <h1 className="text-2xl font-black tracking-tight md:text-3xl">Panel de trabajo</h1>
          <p className="mt-2 max-w-xl text-sm text-zinc-400 leading-relaxed">
            Desde acá se atiende el día: se reciben los pedidos, se arman los planos y riders de cada evento, se cotiza y se revisan las piezas de diseño antes de entregarlas.
          </p>
        </div>

        {/* Stats row */}
        <div className="relative mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
          {[
            { label: 'Trabajos abiertos', value: openJobs, icon: Activity, color: 'text-amber-400' },
            { label: 'Trabajos en total', value: jobs?.count ?? 0, icon: Boxes, color: 'text-blue-400' },
            { label: 'Versión', value: ping?.version || '—', icon: LayoutDashboard, color: 'text-emerald-400' },
            { label: 'Estado', value: ping?.connected !== false ? 'Conectado' : 'Demo', icon: ping?.connected !== false ? CheckCircle2 : AlertCircle, color: ping?.connected !== false ? 'text-emerald-400' : 'text-zinc-400' },
          ].map(stat => {
            const Icon = stat.icon;
            return (
              <div key={stat.label} className="rounded-xl border border-zinc-800/60 bg-black/30 p-3">
                <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-zinc-500">
                  <Icon className={`h-3.5 w-3.5 ${stat.color}`} />
                  {stat.label}
                </div>
                <div className="mt-1 text-lg font-bold">{stat.value}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Unified operational state: one source for the CLI and the Hub. */}
      <div className={`rounded-2xl border p-5 md:p-6 ${operationalStatusClass}`}>
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <div className="flex items-center gap-2">
              {operationalStatus === 'ready' ? <CheckCircle2 className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
              <h2 className="text-lg font-bold">Estado de la casa</h2>
              <span className="rounded-full border border-current/30 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider">
                {operationalStatusLabel}
              </span>
            </div>
            <p className="mt-1 max-w-2xl text-xs leading-relaxed text-zinc-500">
              El Hub, el comando local y el ledger leen el mismo estado. Las abstenciones se conservan como decisiones seguras; no se convierten en falsos éxitos.
            </p>
          </div>
          <div className="shrink-0 text-right text-[10px] text-zinc-600">
            <div>{operational?.read_only === false ? 'con escritura' : 'solo lectura'}</div>
            <div>{operational?.counts?.attention || 0} atención · {operational?.counts?.blocked || 0} bloqueo</div>
          </div>
        </div>
        {operational?.attention && operational.attention.length > 0 ? (
          <div className="mt-4 grid gap-2 md:grid-cols-2">
            {operational.attention.filter(item => item.severity !== 'info').slice(0, 6).map(item => (
              <div key={item.id} className="rounded-xl border border-current/20 bg-black/20 p-3">
                <div className="text-[10px] font-bold uppercase tracking-wider text-current">{item.kind || 'estado'} · {item.status || 'unknown'}</div>
                <div className="mt-1 text-xs text-zinc-400">{item.reason || item.id}</div>
                {item.next_action && <div className="mt-2 text-[10px] text-zinc-500">Siguiente: {item.next_action}</div>}
              </div>
            ))}
          </div>
        ) : (
          <div className="mt-4 text-xs text-zinc-500">No hay excepciones operativas registradas.</div>
        )}
        {operational?.next_actions && operational.next_actions.length > 0 && (
          <div className="mt-4 border-t border-current/15 pt-3 text-[10px] text-zinc-500">
            Próximo: {operational.next_actions[0]}
          </div>
        )}
      </div>

      {operationsMap?.available && (
        <div className="rounded-2xl border border-emerald-900/40 bg-gradient-to-br from-emerald-950/15 via-zinc-900/60 to-zinc-900/40 p-5 md:p-6">
          <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
            <div><div className="flex items-center gap-2"><Layers className="h-4 w-4 text-emerald-300" /><h2 className="text-lg font-bold">Índice de operaciones observables</h2><span className="rounded-full border border-emerald-800/60 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-emerald-300">GET · contrato</span></div><p className="mt-1 max-w-2xl text-xs leading-relaxed text-zinc-500">Conecta cada área con su ruta y evidencia actual. El índice no ejecuta, no decide y no convierte métricas en conocimiento.</p></div>
            <div className="text-right text-[10px] text-zinc-600">{operationsMap.entries?.length ?? 0} superficies · external_calls=false</div>
          </div>
          <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {(operationsMap.entries || []).map(entry => <div key={entry.endpoint} className="rounded-xl border border-zinc-800/70 bg-black/25 p-3"><div className="flex items-center justify-between gap-2"><span className="text-[10px] font-bold uppercase tracking-wider text-emerald-200">{entry.domain || '—'}</span><span className="text-[9px] text-zinc-500">{entry.observed_status || '—'}</span></div><code className="mt-2 block truncate text-[10px] text-zinc-400">{entry.endpoint || '—'}</code><div className="mt-2 text-[10px] text-zinc-600">{entry.surface_kind || 'surface'} · {entry.source_schema || 'unknown schema'}</div></div>)}
          </div>
          <div className="mt-3 text-[10px] text-zinc-600">Siguiente: <code className="text-zinc-500">{operationsMap.next_action || 'human_review_operations_map_then_choose_one_bounded_area_experiment'}</code> · semantic_claim=false · learning_demonstrated=unknown · ejecución=false · promoción=none.</div>
        </div>
      )}

      {rdContext?.available && (
        <div className="rounded-2xl border border-amber-900/40 bg-gradient-to-br from-amber-950/15 via-zinc-900/60 to-zinc-900/40 p-5 md:p-6">
          <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between"><div><div className="flex items-center gap-2"><Shapes className="h-4 w-4 text-amber-300" /><h2 className="text-lg font-bold">Contexto RD</h2><span className="rounded-full border border-amber-800/60 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-amber-300">read-only</span></div><p className="mt-1 max-w-2xl text-xs leading-relaxed text-zinc-500">Proyección, temas y cruces candidatos en una sola lectura; ningún cruce se transforma en relación confirmada.</p></div><div className="text-right text-[10px] text-zinc-600">{rdContext.topics?.canonical_rows ?? 0} filas canónicas · {rdContext.topics?.runtime_rows ?? 0} runtime</div></div>
          <div className="mt-4 grid gap-2 sm:grid-cols-3"><div className="rounded-xl border border-zinc-800/70 bg-black/25 p-3"><div className="text-[10px] font-bold uppercase tracking-wider text-amber-200">Temas</div><div className="mt-1 text-lg font-bold">{rdContext.topics?.topic_count ?? 0}</div><div className="text-[10px] text-zinc-600">mutation={rdContext.topics?.mutation || '—'}</div></div><div className="rounded-xl border border-zinc-800/70 bg-black/25 p-3"><div className="text-[10px] font-bold uppercase tracking-wider text-amber-200">Crosswalk</div><div className="mt-1 text-sm font-bold">{rdContext.crosswalk?.status || '—'}</div><div className="text-[10px] text-zinc-600">{rdContext.crosswalk?.entity_count ?? 0} entidades · {rdContext.crosswalk?.identity_join || '—'}</div></div><div className="rounded-xl border border-zinc-800/70 bg-black/25 p-3"><div className="text-[10px] font-bold uppercase tracking-wider text-amber-200">RD · Cultura</div><div className="mt-1 text-sm font-bold">{rdContext.relations?.status || '—'}</div><div className="text-[10px] text-zinc-600">{rdContext.relations?.relation_count ?? 0} candidatos · mutation={rdContext.relations?.mutation || '—'}</div></div></div>
          <div className="mt-3 text-[10px] text-zinc-600">Siguiente: <code className="text-zinc-500">{rdContext.next_action || 'human_review_rd_projection_and_candidate_joins_before_any_crosswalk_or_relation_decision'}</code> · explicit_provenance_only · semantic_claim=false · ejecución=false.</div>
        </div>
      )}

      {culturaResearchContext?.available && (
        <div className="rounded-2xl border border-fuchsia-900/40 bg-gradient-to-br from-fuchsia-950/15 via-zinc-900/60 to-zinc-900/40 p-5 md:p-6">
          <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between"><div><div className="flex items-center gap-2"><Radio className="h-4 w-4 text-fuchsia-300" /><h2 className="text-lg font-bold">Cultura · Research</h2><span className="rounded-full border border-fuchsia-800/60 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-fuchsia-300">offline-first</span></div><p className="mt-1 max-w-2xl text-xs leading-relaxed text-zinc-500">Fuentes, capacidades y jobs en contexto; scraping y propuestas siguen requiriendo sus gates explícitos.</p></div><div className="text-right text-[10px] text-zinc-600">{culturaResearchContext.cultura?.entry_count ?? 0} fuentes · {culturaResearchContext.research?.observed_job_count ?? 0} jobs</div></div>
          <div className="mt-4 grid gap-2 sm:grid-cols-3"><div className="rounded-xl border border-zinc-800/70 bg-black/25 p-3"><div className="text-[10px] font-bold uppercase tracking-wider text-fuchsia-200">Fuentes</div><div className="mt-1 text-lg font-bold">{culturaResearchContext.cultura?.entry_count ?? 0}</div><div className="text-[10px] text-zinc-600">{culturaResearchContext.cultura?.root_count ?? 0} raíces · truncado={culturaResearchContext.cultura?.truncated ? 'true' : 'false'}</div></div><div className="rounded-xl border border-zinc-800/70 bg-black/25 p-3"><div className="text-[10px] font-bold uppercase tracking-wider text-fuchsia-200">Policy</div><div className="mt-1 text-sm font-bold">{culturaResearchContext.cultura?.opportunity_mode || '—'}</div><div className="text-[10px] text-zinc-600">scrape=explicit · proposal=draft</div></div><div className="rounded-xl border border-zinc-800/70 bg-black/25 p-3"><div className="text-[10px] font-bold uppercase tracking-wider text-fuchsia-200">Jobs</div><div className="mt-1 text-lg font-bold">{culturaResearchContext.research?.observed_job_count ?? 0}</div><div className="text-[10px] text-zinc-600">{Object.entries(culturaResearchContext.research?.job_status_counts || {}).map(([key, value]) => `${key}=${value}`).join(' · ') || 'sin estados'}</div></div></div>
          <div className="mt-3 text-[10px] text-zinc-600">Siguiente: <code className="text-zinc-500">{culturaResearchContext.next_action || 'human_review_cultura_source_and_research_job_before_any_explicit_scrape_or_proposal_gate'}</code> · semantic_claim=false · learning_demonstrated=unknown · network=false · ejecución=false.</div>
        </div>
      )}

      {portfolioVizzContext?.available && (
        <div className="rounded-2xl border border-sky-900/40 bg-gradient-to-br from-sky-950/15 via-zinc-900/60 to-zinc-900/40 p-5 md:p-6">
          <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between"><div><div className="flex items-center gap-2"><Layers className="h-4 w-4 text-sky-300" /><h2 className="text-lg font-bold">VIZZ · contexto de instrumento</h2><span className="rounded-full border border-sky-800/60 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-sky-300">fail-closed</span></div><p className="mt-1 max-w-2xl text-xs leading-relaxed text-zinc-500">Medición, lineage, delta y preview en una lectura trazable; la calibración física sigue siendo requisito.</p></div><div className="text-right text-[10px] text-zinc-600">{portfolioVizzContext.measurement?.status || '—'} · preview={portfolioVizzContext.preview?.task_id || '—'}</div></div>
          <div className="mt-4 grid gap-2 sm:grid-cols-4"><div className="rounded-xl border border-zinc-800/70 bg-black/25 p-3"><div className="text-[10px] font-bold uppercase tracking-wider text-sky-200">Medición</div><div className="mt-1 text-[11px] font-bold">{portfolioVizzContext.measurement?.calibration_status || '—'}</div><div className="text-[10px] text-zinc-600">triangulación=false · depth=false</div></div><div className="rounded-xl border border-zinc-800/70 bg-black/25 p-3"><div className="text-[10px] font-bold uppercase tracking-wider text-sky-200">Lineage</div><div className="mt-1 text-[11px] font-bold">{portfolioVizzContext.lineage?.status || '—'}</div><div className="text-[10px] text-zinc-600">replace={portfolioVizzContext.lineage?.current_state_replaced ? 'true' : 'false'}</div></div><div className="rounded-xl border border-zinc-800/70 bg-black/25 p-3"><div className="text-[10px] font-bold uppercase tracking-wider text-sky-200">Delta</div><div className="mt-1 text-[11px] font-bold">{portfolioVizzContext.delta?.status || '—'}</div><div className="text-[10px] text-zinc-600">shared={portfolioVizzContext.delta?.shared_keys ?? 0} · residue={portfolioVizzContext.delta?.residue_keys ?? 0}</div></div><div className="rounded-xl border border-zinc-800/70 bg-black/25 p-3"><div className="text-[10px] font-bold uppercase tracking-wider text-sky-200">Preview</div><div className="mt-1 text-[11px] font-bold">{portfolioVizzContext.preview?.human_gate || '—'}</div><div className="text-[10px] text-zinc-600">execution={portfolioVizzContext.preview?.execution_allowed ? 'true' : 'false'}</div></div></div>
          <div className="mt-3 text-[10px] text-zinc-600">Siguiente: <code className="text-zinc-500">{portfolioVizzContext.next_action || 'provide_physical_calibration_evidence_before_metric_measurement'}</code> · semantic_claim=false · learning_demonstrated=false · publication=false.</div>
        </div>
      )}

      {learningContext?.available && (
        <div className="rounded-2xl border border-cyan-900/40 bg-gradient-to-br from-cyan-950/15 via-zinc-900/60 to-zinc-900/40 p-5 md:p-6">
          <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between"><div><div className="flex items-center gap-2"><Activity className="h-4 w-4 text-cyan-300" /><h2 className="text-lg font-bold">Aprendizaje · evidencia separada</h2><span className="rounded-full border border-cyan-800/60 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-cyan-300">candidate</span></div><p className="mt-1 max-w-2xl text-xs leading-relaxed text-zinc-500">Muestra evaluación y registro sin llamarlos conocimiento aprendido ni promoción.</p></div><div className="text-right text-[10px] text-zinc-600">{learningContext.policy?.eligible_examples ?? 0} elegibles · {learningContext.policy?.status || '—'}</div></div>
          <div className="mt-4 grid gap-2 sm:grid-cols-4"><div className="rounded-xl border border-zinc-800/70 bg-black/25 p-3"><div className="text-[10px] font-bold uppercase tracking-wider text-cyan-200">Evaluación</div><div className="mt-1 text-lg font-bold">{learningContext.policy?.holdout_accuracy ?? '—'}</div><div className="text-[10px] text-zinc-600">baseline={learningContext.policy?.holdout_baseline ?? '—'}</div></div><div className="rounded-xl border border-zinc-800/70 bg-black/25 p-3"><div className="text-[10px] font-bold uppercase tracking-wider text-cyan-200">Partición</div><div className="mt-1 text-sm font-bold">{learningContext.policy?.train_count ?? 0} train · {learningContext.policy?.holdout_count ?? 0} holdout</div><div className="text-[10px] text-zinc-600">reason={learningContext.policy?.reason || '—'}</div></div><div className="rounded-xl border border-zinc-800/70 bg-black/25 p-3"><div className="text-[10px] font-bold uppercase tracking-wider text-cyan-200">Ledger</div><div className="mt-1 text-sm font-bold">{learningContext.ledger?.projects?.review_required ?? 0} en revisión</div><div className="text-[10px] text-zinc-600">{learningContext.ledger?.episodes_open?.needs_evidence ?? 0} necesitan evidencia</div></div><div className="rounded-xl border border-zinc-800/70 bg-black/25 p-3"><div className="text-[10px] font-bold uppercase tracking-wider text-cyan-200">Control</div><div className="mt-1 text-sm font-bold">promoción=none</div><div className="text-[10px] text-zinc-600">recordable={learningContext.policy?.recordable ? 'true' : 'false'} · ejecución=false</div></div></div>
          <div className="mt-3 text-[10px] text-zinc-600">Siguiente: <code className="text-zinc-500">{learningContext.next_action || 'keep_candidate_policy_separate_from_verified_knowledge_and_require_human_review'}</code> · semantic_claim=false · learning_demonstrated=false.</div>
        </div>
      )}

      {/* Learning ledger: bounded visibility, no automatic execution. */}
      <div className="rounded-2xl border border-cyan-900/40 bg-gradient-to-br from-cyan-950/20 via-zinc-900/60 to-zinc-900/40 p-5 md:p-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-cyan-400" />
              <h2 className="text-lg font-bold">Memoria operativa</h2>
              <span className="rounded-full border border-cyan-800/60 bg-cyan-950/40 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-cyan-300">
                ledger
              </span>
            </div>
            <p className="mt-1 max-w-2xl text-xs leading-relaxed text-zinc-500">
              Registra proyectos, pruebas y abstenciones. Una abstención es una decisión segura: falta evidencia, no es un error del Hub.
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap justify-end gap-2">
            <button
              onClick={() => onNavigate('intake')}
              className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-900/60 px-3 py-2 text-xs font-bold text-zinc-300 transition-colors hover:bg-zinc-800"
            >
              Abrir intake <ArrowRight className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => setProbeOpen(value => !value)}
              className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-cyan-800/60 bg-cyan-950/30 px-3 py-2 text-xs font-bold text-cyan-300 transition-colors hover:bg-cyan-900/40"
            >
              Probe read-only
            </button>
          </div>
        </div>
        <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-6">
          {[
            { label: 'Proyectos', value: learning?.available ? projectCount : '—', note: learning?.projects?.review_required ? `${learning.projects.review_required} en revisión` : 'ledger local', color: 'text-cyan-300' },
            { label: 'Episodios', value: learning?.available ? episodeCount : '—', note: learning?.episodes?.needs_evidence ? `${learning.episodes.needs_evidence} requieren evidencia` : 'sin pruebas pendientes', color: 'text-amber-300' },
            { label: 'Reglas promovidas', value: learning?.available ? promotedRules : '—', note: 'sin autoejecución', color: 'text-violet-300' },
            { label: 'Contratos', value: learning?.contracts?.available ? contractCount : '—', note: learning?.contracts?.available ? 'formatos + consumidores' : learning?.contracts?.reason || 'pendiente de materializar', color: 'text-emerald-300' },
            { label: 'Auditoría', value: learning?.audits?.available ? auditedCount : '—', note: learning?.audits?.available ? `${learning.audits.statuses?.verified || 0} verificados · ${learning.audits.statuses?.needs_evidence || 0} evidencia · ${learning.audits.statuses?.unavailable || 0} no disponibles` : learning?.audits?.reason || 'pendiente de auditar', color: 'text-sky-300' },
            { label: 'Último abstain', value: latestAbstain ? 'registrado' : learning?.available ? 'ninguno' : '—', note: latestAbstain?.phase || learning?.reason || 'criterio de seguridad', color: 'text-rose-300' },
          ].map(stat => (
            <div key={stat.label} className="rounded-xl border border-zinc-800/70 bg-black/25 p-3">
              <div className="text-[10px] font-bold uppercase tracking-widest text-zinc-600">{stat.label}</div>
              <div className={`mt-1 text-lg font-bold ${stat.color}`}>{stat.value}</div>
              <div className="mt-1 truncate text-[10px] text-zinc-600" title={stat.note}>{stat.note}</div>
          </div>
        ))}
        </div>
        {reviewQueue?.available && (reviewQueue.items?.length ?? 0) > 0 && (
          <div className="mt-4 rounded-xl border border-amber-900/50 bg-amber-950/10 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-sm font-bold text-amber-200">Cola de revisión humana</div>
                <div className="mt-1 text-[11px] text-zinc-500">
                  {reviewQueue.summary?.pending ?? reviewQueue.items?.length ?? 0} proyectos pendientes · lectura ordenada por evidencia
                </div>
              </div>
              <span className="rounded-full border border-amber-800/60 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-amber-300">
                sin promoción automática
              </span>
            </div>
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              {(reviewQueue.items || []).map(item => (
                <button
                  key={item.project_id}
                  type="button"
                  onClick={() => setSelectedReviewProjectId(item.project_id)}
                  className={`rounded-lg border p-3 text-left transition-colors ${selectedReviewProjectId === item.project_id ? 'border-amber-700/70 bg-amber-950/20' : 'border-zinc-800/70 bg-black/20 hover:border-zinc-700'}`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="truncate text-xs font-bold text-zinc-200">{item.title}</div>
                      <div className="mt-1 truncate font-mono text-[9px] text-zinc-600">{item.project_id}</div>
                    </div>
                    <span className="shrink-0 rounded border border-amber-800/60 px-1.5 py-0.5 text-[9px] text-amber-300">{item.state}</span>
                  </div>
                  <div className="mt-2 text-[10px] text-zinc-500">
                    {item.unknowns.length} unknowns · {item.evidence.length} evidencias · {item.decisions_available.length} salidas posibles
                  </div>
                  {item.unknowns[0] && <div className="mt-1 truncate text-[10px] text-zinc-600" title={item.unknowns[0]}>Falta: {item.unknowns[0]}</div>}
                </button>
              ))}
            </div>
            <div className="mt-3 text-[10px] text-zinc-600">
              Fuente: {reviewQueue.provenance?.source || 'project_records'} · cualquier transición requiere actor humano y evidencia explícita.
            </div>
          </div>
        )}
        {researchJobs?.available && (
          <div className="mt-4 rounded-xl border border-cyan-900/50 bg-cyan-950/10 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-sm font-bold text-cyan-200">Investigación · jobs reanudables</div>
                <div className="mt-1 text-[11px] text-zinc-500">
                  Cada avance ejecuta un solo proceso persistido y deja checkpoint; la carga no se reanuda al abrir el panel.
                </div>
              </div>
              <span className="rounded-full border border-cyan-800/60 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-cyan-300">
                acción explícita · sin auto-run
              </span>
            </div>
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              {(researchJobs.jobs || []).map(item => (
                <div key={item.id} className="rounded-lg border border-zinc-800/70 bg-black/20 p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="truncate text-xs font-bold text-zinc-200">#{item.id} · {item.question}</div>
                      <div className="mt-1 text-[10px] text-zinc-600">{item.status || '—'} · {item.done_steps ?? 0}/{item.steps ?? 0} pasos · próximo: {item.next_process || '—'}</div>
                    </div>
                    {item.next_process === 'extract' ? (
                      <div className="flex shrink-0 flex-col gap-1">
                        <button
                          type="button"
                          onClick={() => resumeResearch(item)}
                          disabled={researchResumeBusy}
                          className="rounded-lg border border-cyan-800/60 bg-cyan-950/30 px-2.5 py-1.5 text-[10px] font-bold text-cyan-300 transition-colors hover:bg-cyan-900/40 disabled:cursor-wait disabled:opacity-50"
                        >
                          {researchResumeBusy ? 'ejecutando…' : 'reanudar extract'}
                        </button>
                        <button
                          type="button"
                          onClick={() => inspectResearchJob(item.id)}
                          disabled={researchJobBusy}
                          className="rounded border border-zinc-800 px-2 py-1 text-[9px] text-zinc-500 hover:border-zinc-700 hover:text-zinc-300 disabled:opacity-50"
                        >
                          ver evidencia
                        </button>
                      </div>
                    ) : (
                      <div className="flex shrink-0 flex-col items-end gap-1">
                        <span className="rounded border border-zinc-800 px-1.5 py-0.5 text-[9px] text-zinc-600">requiere siguiente adaptador</span>
                        <button
                          type="button"
                          onClick={() => inspectResearchJob(item.id)}
                          disabled={researchJobBusy}
                          className="rounded border border-zinc-800 px-2 py-1 text-[9px] text-zinc-500 hover:border-zinc-700 hover:text-zinc-300 disabled:opacity-50"
                        >
                          ver evidencia
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
            {researchJobDetail && (
              <div className="mt-3 rounded-lg border border-zinc-800/70 bg-black/20 p-3">
                <div className="text-[10px] font-bold uppercase tracking-wider text-zinc-400">
                  Evidencia capturada · job #{researchJobDetail.id}
                </div>
                <div className="mt-1 text-[11px] text-zinc-500">{researchJobDetail.sources?.length || 0} fuentes · hashes visibles · confirmar antes de normalize</div>
                {researchNormalizeReadiness && (
                  <div className="mt-2 rounded border border-zinc-800/70 bg-black/20 p-2 text-[10px] text-zinc-500">
                    Preparación normalize: <strong className="text-zinc-300">{researchNormalizeReadiness.human_attestation?.present ? 'atestación presente' : 'esperando atestación humana'}</strong> · hash coincide={researchNormalizeReadiness.human_attestation?.matches_input_sha256 ? 'true' : 'false'} · normalization_allowed={researchNormalizeReadiness.normalization_allowed ? 'true' : 'false'}
                    <div className="mt-1 text-zinc-600">Próximo: <code>{researchNormalizeReadiness.next_action || '—'}</code> · read-only · state_advance={researchNormalizeReadiness.control?.state_advance ? 'true' : 'false'}</div>
                  </div>
                )}
                {researchNormalizePlan?.available && (
                  <div className="mt-2 rounded border border-violet-900/40 bg-violet-950/10 p-2 text-[10px] text-zinc-500">
                    Plan normalize (solo lectura): <strong className="text-zinc-300">{researchNormalizePlan.plan?.record_count ?? 0} registros</strong> · execution_allowed={researchNormalizePlan.execution_allowed ? 'true' : 'false'} · semantic_claims_created={researchNormalizePlan.plan?.semantic_claims_created ? 'true' : 'false'}
                    <div className="mt-1 text-zinc-600">Operaciones: {(researchNormalizePlan.plan?.operations || []).join(' · ') || '—'} · próximo: <code>{researchNormalizePlan.next_action || '—'}</code></div>
                  </div>
                )}
                {researchNormalizeDryRun?.available && (
                  <div className="mt-2 rounded border border-emerald-900/40 bg-emerald-950/10 p-2 text-[10px] text-zinc-500">
                    Dry-run normalize: <strong className="text-zinc-300">{researchNormalizeDryRun.dry_run?.records ?? 0} registros</strong> · transform={researchNormalizeDryRun.dry_run?.semantic_transform_performed ? 'true' : 'false'} · database_rows_created={researchNormalizeDryRun.dry_run?.database_rows_created ?? 0}
                    <div className="mt-1 text-zinc-600">attempted={researchNormalizeDryRun.execution?.attempted ? 'true' : 'false'} · normalize_execution={researchNormalizeDryRun.execution?.normalize_execution ? 'true' : 'false'} · read-only · state_advance={researchNormalizeDryRun.control?.state_advance ? 'true' : 'false'}</div>
                  </div>
                )}
                {researchLicenseReview?.available && (
                  <div className="mt-2 rounded border border-amber-900/40 bg-amber-950/10 p-2 text-[10px] text-zinc-500">
                    Revisión de licencias: <strong className="text-zinc-300">{researchLicenseReview.sources?.length ?? 0} fuentes</strong> · ready_for_attestation={researchLicenseReview.ready_for_attestation ? 'true' : 'false'} · read-only
                    <div className="mt-1 text-zinc-600">Estados: {Object.entries(researchLicenseReview.counts || {}).map(([state, count]) => `${state}=${count}`).join(' · ') || '—'} · próximo: <code>{researchLicenseReview.next_action || '—'}</code></div>
                  </div>
                )}
                {researchLicenseSourceReview?.available && (
                  <div className="mt-2 rounded border border-rose-900/40 bg-rose-950/10 p-2 text-[10px] text-zinc-500">
                    Fuente oficial de licencias: <strong className="text-zinc-300">{researchLicenseSourceReview.findings?.length ?? 0} hallazgos</strong> · conflictos={researchLicenseSourceReview.conflicts ?? 0} · unknown/pending={researchLicenseSourceReview.unknown_or_pending ?? 0} · ready_for_attestation={researchLicenseSourceReview.ready_for_attestation ? 'true' : 'false'}
                    <div className="mt-1 text-zinc-600">La evidencia externa está fijada por hash ({researchLicenseSourceReview.source_review_sha256?.slice(0, 16) || '—'}…); no cambia los estados del registry. Próximo: <code>{researchLicenseSourceReview.next_action || '—'}</code></div>
                    <div className="mt-2 grid gap-1 md:grid-cols-2">
                      {(researchLicenseSourceReview.findings || []).map((finding, index) => (
                        <div key={`${finding.source_ref || 'source'}-${index}`} className="rounded border border-zinc-800/70 bg-black/20 p-2">
                          <div className="truncate font-mono text-[9px] text-zinc-600">{finding.source_ref || 'source_ref ausente'}</div>
                          <div className="mt-1 text-zinc-300">{finding.official_license || 'licencia no concluyente'} · {finding.license_state || 'unknown'}</div>
                          <div className="mt-1 text-zinc-600">Acción: {finding.action || 'revisión humana'}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {researchLicenseCompatibilityPlan?.available && (
                  <div className="mt-2 rounded border border-sky-900/40 bg-sky-950/10 p-2 text-[10px] text-zinc-500">
                    Compatibilidad (plan de revisión): <strong className="text-zinc-300">{researchLicenseCompatibilityPlan.candidate_count ?? 0} candidatos · {researchLicenseCompatibilityPlan.blocked_count ?? 0} bloqueados</strong> · legal_conclusion={researchLicenseCompatibilityPlan.legal_conclusion ? 'true' : 'false'} · ready_for_attestation={researchLicenseCompatibilityPlan.ready_for_attestation ? 'true' : 'false'}
                    <div className="mt-1 text-zinc-600">No es permiso legal ni selección editorial; próximo: <code>{researchLicenseCompatibilityPlan.next_action || '—'}</code></div>
                    <div className="mt-2 grid gap-1 md:grid-cols-2">
                      {(researchLicenseCompatibilityPlan.items || []).map((item, index) => (
                        <div key={`${item.source_ref || 'source'}-compat-${index}`} className="rounded border border-zinc-800/70 bg-black/20 p-2">
                          <div className="truncate font-mono text-[9px] text-zinc-600">{item.source_ref || 'source_ref ausente'}</div>
                          <div className="mt-1 text-zinc-300">{item.compatibility_action || 'revisión pendiente'}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <div className="mt-2 grid gap-2 md:grid-cols-2">
                  {(researchJobDetail.sources || []).map(source => (
                    <div key={source.id} className="rounded border border-zinc-800/70 p-2 text-[10px] text-zinc-500">
                      <div className="truncate text-zinc-300" title={source.title || source.url}>{source.title || source.url || `fuente ${source.id}`}</div>
                      <div className="mt-1">{source.capture_status || '—'} · HTTP {source.http_status ?? '—'} · licencia {source.license_state || '—'}</div>
                      <div className="mt-1 truncate font-mono text-[9px] text-zinc-700" title={source.text_sha256 || source.raw_sha256}>text_sha256={source.text_sha256 || '—'}</div>
                    </div>
                  ))}
                </div>
                <div className="mt-3 rounded border border-amber-900/50 bg-amber-950/10 p-2">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-amber-200">Confirmación humana explícita</div>
                  <div className="mt-1 text-[10px] text-zinc-500">Confirma solo que estos registros corresponden al extract; no habilita normalize.</div>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <input
                      value={researchActor}
                      onChange={event => setResearchActor(event.target.value)}
                      placeholder="actor humano"
                      className="min-w-[12rem] flex-1 rounded border border-zinc-800 bg-black/40 px-2 py-1.5 text-[10px] text-zinc-300 outline-none focus:border-amber-800"
                    />
                    <button
                      type="button"
                      onClick={confirmResearchExtraction}
                      disabled={researchConfirmationBusy || !researchActor.trim() || !(researchJobDetail.extract_input_sha256 || researchResume?.input_sha256)}
                      className="rounded border border-amber-800/60 bg-amber-950/30 px-2.5 py-1.5 text-[10px] font-bold text-amber-300 hover:bg-amber-900/40 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {researchConfirmationBusy ? 'guardando…' : 'confirmar extract'}
                    </button>
                  </div>
                  <div className="mt-1 truncate font-mono text-[9px] text-zinc-700" title={researchJobDetail.extract_input_sha256 || researchResume?.input_sha256}>
                    input_sha256={researchJobDetail.extract_input_sha256 || researchResume?.input_sha256 || 'no disponible'}
                  </div>
                  {researchConfirmation?.status && (
                    <div className="mt-2 text-[10px] text-emerald-300">{researchConfirmation.status} · actor_id={researchConfirmation.actor_id || '—'} · actor_kind={researchConfirmation.actor_kind || '—'} · process_advanced={researchConfirmation.execution?.process_advanced ? 'true' : 'false'} · decision_write={researchConfirmation.control?.decision_write ? 'true' : 'false'}</div>
                  )}
                </div>
                <div className="mt-2 text-[10px] text-amber-300/80">La revisión humana debe confirmar estos registros; esta vista no cambia el job ni abre la siguiente etapa. endpoint=confirm-extraction</div>
              </div>
            )}
            {researchResume?.status && (
              <div className="mt-3 rounded-lg border border-cyan-900/40 bg-black/20 p-2 text-[10px] text-zinc-500">
                Última continuación: <strong className="text-zinc-300">{researchResume.status}</strong> · job {researchResume.job_id ?? '—'} · próximo {researchResume.next_process || '—'} · idempotent_replay={researchResume.idempotent_replay ? 'true' : 'false'} · {researchResume.output_ref || 'sin output_ref'}
              </div>
            )}
            {researchResume?.error && (
              <div className="mt-3 text-[10px] text-rose-300">No ejecutado: {researchResume.error} · {researchResume.detail || ''}</div>
            )}
            <div className="mt-2 text-[10px] text-zinc-600">
              Control: database_write=true solo para checkpoint · decision_write=false · promotion=none · publication=false.
            </div>
          </div>
        )}
        {archiveView?.status === 'draft_only' && (
          <div className="mt-4 rounded-xl border border-violet-900/50 bg-violet-950/10 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-sm font-bold text-violet-200">Portafolio / archivo</div>
                <div className="mt-1 text-[11px] text-zinc-500">
                  Visión acotada de cultura y computación; cada registro conserva su origen y estado epistémico.
                </div>
              </div>
              <span className="rounded-full border border-violet-800/60 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-violet-300">
                draft only
              </span>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-5">
              {[
                ['Obras declaradas', archiveView.selection?.declared_work_count ?? 0],
                ['Registros documentados', archiveView.selection?.documented_record_count ?? 0],
                ['Campo observado', archiveView.selection?.observed_field_count ?? 0],
                ['Contexto de práctica', archiveView.selection?.practice_context_count ?? 0],
                ['Visible', archiveView.selection?.selected_item_count ?? 0],
              ].map(([label, value]) => (
                <div key={String(label)} className="rounded-lg border border-zinc-800/70 bg-black/20 p-2">
                  <div className="text-[9px] font-bold uppercase tracking-wider text-zinc-600">{label}</div>
                  <div className="mt-1 text-sm font-bold text-violet-300">{value}</div>
                </div>
              ))}
            </div>
            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-zinc-500">
              <span>Resultado interno (no aprobación): <strong className="text-zinc-300">{archiveView.contracurator?.status || '—'}</strong></span>
              <span>Promociones de verdad: <strong className="text-zinc-300">{archiveView.reconciliation?.truth_promotions ?? 0}</strong></span>
              <span>Promoción: <strong className="text-zinc-300">{archiveView.control?.promotion || 'none'}</strong></span>
              <span>Decisión editorial: <strong className="text-zinc-300">no automatizada · requiere actor humano</strong></span>
              <span>Publicación: <strong className="text-zinc-300">{archiveView.control?.publication ? 'habilitada' : 'cerrada'}</strong></span>
            </div>
            <div className="mt-2 text-[10px] text-zinc-600">
              Fuente: <code className="text-zinc-500">{archiveView.source?.path_hint || 'iskvw/datos/archivo.json'}</code>
              {' · '}
              {archiveView.reconciliation?.omitted_piece_count ?? 0} piezas quedan fuera de esta selección acotada.
            </div>
            {archiveView.source?.input_hash && (
              <div className="mt-1 truncate font-mono text-[9px] text-zinc-700" title={archiveView.source.input_hash}>
                input_hash: {archiveView.source.input_hash}
              </div>
            )}
            {(archiveView.gaps?.length ?? 0) > 0 && (
              <div className="mt-3 text-[10px] text-zinc-600">
                Límites conservados: {(archiveView.gaps || []).join(' · ')}
              </div>
            )}
            {archiveView.contracurator?.result?.selected_thesis_id && (
              <details className="mt-3 rounded-lg border border-zinc-800/70 bg-black/20 p-2" open>
                <summary className="cursor-pointer text-[10px] font-bold uppercase tracking-wider text-zinc-400">
                  Visión interna · no aprobación
                </summary>
                <div className="mt-2 text-[11px] leading-relaxed text-zinc-400">
                  Hipótesis seleccionada para lectura: <code className="text-violet-300">{archiveView.contracurator.result.selected_thesis_id}</code>
                  {archiveView.contracurator.result.exhibition?.title && (
                    <span> · {archiveView.contracurator.result.exhibition.title}</span>
                  )}
                </div>
                <div className="mt-2 grid gap-2 md:grid-cols-3">
                  {(archiveView.contracurator.theses || []).map((thesis, index) => (
                    <div key={thesis.thesis_id || index} className="rounded-lg border border-zinc-800/70 bg-black/20 p-2">
                      <div className="text-[9px] font-bold uppercase tracking-wider text-sky-300">
                        {thesis.assessment?.status === 'survives' ? 'hipótesis que sobrevive al test interno' : 'hipótesis derrotada'}
                      </div>
                      <div className="mt-1 text-[10px] leading-relaxed text-zinc-500">{thesis.position || thesis.thesis_id}</div>
                    </div>
                  ))}
                </div>
                <details className="mt-2 rounded-lg border border-zinc-800/70 bg-black/20 p-2">
                  <summary className="cursor-pointer text-[10px] font-bold uppercase tracking-wider text-zinc-500">
                    Contraevidencia conservada ({(archiveView.contracurator.theses || []).reduce((total, thesis) => total + (thesis.counterevidence?.length || 0), 0)})
                  </summary>
                  <ul className="mt-2 space-y-2 text-[10px] text-zinc-500">
                    {(archiveView.contracurator.theses || []).map(thesis => (
                      (thesis.counterevidence || []).map((counter, index) => (
                        <li key={`${thesis.thesis_id || 'thesis'}-counter-${index}`} className="border-l border-zinc-700 pl-2">
                          <div>{counter.statement || 'Contraevidencia sin statement legible.'}</div>
                          {counter.reason && <div className="mt-1 text-zinc-600">Razón: {counter.reason}</div>}
                          {counter.source_refs && <div className="mt-1 text-zinc-700">Referencias de evidencia: {counter.source_refs.length}</div>}
                        </li>
                      ))
                    ))}
                  </ul>
                </details>
                <div className="mt-2 text-[10px] text-zinc-600">
                  Entradas incluidas: {archiveView.contracurator.result.exhibition?.why_in?.length || 0} · excluidas: {archiveView.contracurator.result.exhibition?.why_out?.length || 0}
                </div>
                {(archiveView.contracurator.result.limits?.length ?? 0) > 0 && (
                  <ul className="mt-2 space-y-1 pl-4 text-[10px] text-zinc-600">
                    {(archiveView.contracurator.result.limits || []).map(limit => (
                      <li key={limit} className="list-disc">{limit}</li>
                    ))}
                  </ul>
                )}
              </details>
            )}
          </div>
        )}
        {portfolioRelationEvidencePlan?.available && (
          <div className="mt-4 rounded-xl border border-sky-900/50 bg-sky-950/10 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-sm font-bold text-sky-200">Relación · plan de evidencia</div>
                <div className="mt-1 text-[11px] text-zinc-500">Expone qué falta demostrar para relacionar proyecto y archivo; no crea la relación.</div>
              </div>
              <span className="rounded-full border border-sky-800/60 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-sky-300">{portfolioRelationEvidencePlan.relation?.status || 'needs_evidence'}</span>
            </div>
            <div className="mt-3 grid gap-2 md:grid-cols-3">
              <div className="rounded-lg border border-zinc-800/70 bg-black/20 p-2 text-[10px] text-zinc-500">Unknowns: <strong className="text-zinc-300">{portfolioRelationEvidencePlan.project?.unknown_count ?? 0}</strong></div>
              <div className="rounded-lg border border-zinc-800/70 bg-black/20 p-2 text-[10px] text-zinc-500">Evidencia observada: <strong className="text-zinc-300">{portfolioRelationEvidencePlan.project?.observed_evidence_count ?? 0}</strong></div>
              <div className="rounded-lg border border-zinc-800/70 bg-black/20 p-2 text-[10px] text-zinc-500">Sin resolver: <strong className="text-zinc-300">{portfolioRelationEvidencePlan.unresolved_count ?? 0}</strong></div>
            </div>
            <div className="mt-3 grid gap-1 md:grid-cols-2">
              {(portfolioRelationEvidencePlan.requirements || []).map(item => (
                <div key={item.requirement_id} className="rounded border border-zinc-800/60 bg-black/20 px-2 py-1 text-[10px] text-zinc-600">{item.requirement_id}: {item.expected_evidence_kind} · {item.status}</div>
              ))}
            </div>
            <div className="mt-3 rounded-lg border border-zinc-800/60 bg-black/20 p-2">
              <div className="text-[9px] font-bold uppercase tracking-wider text-sky-300">Evidencia observada</div>
              {(portfolioRelationEvidencePlan.observed_evidence || []).map((item, index) => (
                <div key={`${item.kind || 'evidence'}-${index}`} className="mt-1 text-[10px] text-zinc-600">{item.kind || '—'} · {item.status || '—'} · reference_present={item.reference_present ? 'true' : 'false'} · class={item.reference_class || 'unbound_evidence'}</div>
              ))}
            </div>
            <div className="mt-2 text-[10px] text-zinc-700">typed_relation_present={portfolioRelationEvidencePlan.relation?.typed_relation_present ? 'true' : 'false'} · selection_effect={portfolioRelationEvidencePlan.relation?.selection_effect || 'none'} · promoción=none · publicación=false.</div>
          </div>
        )}
        {archiveOrientation?.available && (
          <div className="mt-4 rounded-xl border border-violet-900/50 bg-violet-950/10 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-sm font-bold text-violet-200">Orientación del archivo · 4 capas</div>
                <div className="mt-1 text-[11px] text-zinc-500">La matriz ordena el origen de cada registro; no convierte observación en autoría ni selección.</div>
              </div>
              <span className="rounded-full border border-violet-800/60 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-violet-300">read-only</span>
            </div>
            <div className="mt-3 grid gap-2 md:grid-cols-4">
              {(archiveOrientation.axes || []).map(axis => (
                <div key={axis.format_id} className="rounded-lg border border-zinc-800/70 bg-black/20 p-2">
                  <div className="text-[9px] font-bold uppercase tracking-wider text-violet-300">{axis.format_id || '—'}</div>
                  <div className="mt-1 text-[10px] text-zinc-300">{axis.item_count ?? 0} visibles</div>
                  <div className="mt-1 text-[9px] text-zinc-600">{axis.role || '—'} · omitidos {axis.omitted_count ?? 0}</div>
                </div>
              ))}
            </div>
            <div className="mt-2 text-[10px] text-zinc-700">Fuente: <code className="text-zinc-500">{archiveOrientation.source?.path_hint || '—'}</code> · source_piece_count={archiveOrientation.source?.source_piece_count ?? 0} · source_link_count={archiveOrientation.source?.source_link_count ?? 0} · projected_link_count={archiveOrientation.source?.projected_link_count ?? 0} · semantic_claim={archiveOrientation.boundary?.semantic_claim ? 'true' : 'false'} · promoción=none · publicación=false.</div>
          </div>
        )}
        {portfolioReviewContext?.available && (
          <div className="mt-4 rounded-xl border border-sky-900/50 bg-sky-950/10 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-sm font-bold text-sky-200">Puente Portafolio ↔ revisión</div>
                <div className="mt-1 text-[11px] text-zinc-500">
                  Comparte evidencia medida sin fabricar una relación entre archivo y proyecto.
                </div>
              </div>
              <span className="rounded-full border border-sky-800/60 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-sky-300">
                {portfolioReviewContext.relation?.status || 'unbound'}
              </span>
            </div>
            <div className="mt-3 grid gap-2 md:grid-cols-3">
              <div className="rounded-lg border border-zinc-800/70 bg-black/20 p-2 text-[10px] text-zinc-500">
                Relación tipada: <strong className="text-zinc-300">{portfolioReviewContext.relation?.typed_relation_present ? 'sí' : 'no'}</strong>
              </div>
              <div className="rounded-lg border border-zinc-800/70 bg-black/20 p-2 text-[10px] text-zinc-500">
                Efecto de selección: <strong className="text-zinc-300">{portfolioReviewContext.relation?.selection_effect || 'none'}</strong>
              </div>
              <div className="rounded-lg border border-zinc-800/70 bg-black/20 p-2 text-[10px] text-zinc-500">
                Proyecto seleccionado: <strong className="text-zinc-300">{portfolioReviewContext.project?.title || portfolioReviewContext.project?.project_id || 'ninguno'}</strong>
              </div>
            </div>
            {portfolioReviewContext.project?.project_id && (
              <div className="mt-3 grid gap-2 md:grid-cols-2">
                <details className="rounded-lg border border-zinc-800/70 bg-black/20 p-2" open>
                  <summary className="cursor-pointer text-[10px] font-bold uppercase tracking-wider text-zinc-400">
                    Faltantes concretos ({portfolioReviewContext.project.unknowns?.length || 0})
                  </summary>
                  <ul className="mt-2 space-y-1 pl-4 text-[10px] text-zinc-500">
                    {(portfolioReviewContext.project.unknowns || []).map(unknown => (
                      <li key={unknown} className="list-disc">{unknown}</li>
                    ))}
                  </ul>
                </details>
                <details className="rounded-lg border border-zinc-800/70 bg-black/20 p-2" open>
                  <summary className="cursor-pointer text-[10px] font-bold uppercase tracking-wider text-zinc-400">
                    Evidencias observadas ({portfolioReviewContext.project.evidence?.length || 0})
                  </summary>
                  <ul className="mt-2 space-y-1 text-[10px] text-zinc-500">
                    {(portfolioReviewContext.project.evidence || []).map((evidence, index) => (
                      <li key={`${String(evidence.kind || 'evidence')}-${index}`} className="truncate" title={String(evidence.kind || 'evidence')}>
                        {String(evidence.kind || 'evidence')} · {String(evidence.status || 'observed')}
                        {evidence.source_ref ? ' · referencia local' : ''}
                      </li>
                    ))}
                  </ul>
                </details>
              </div>
            )}
            <div className="mt-2 text-[10px] text-zinc-600">
              {portfolioReviewContext.relation?.reason || 'Sin inferencia de relación.'} · {portfolioReviewContext.project?.unknowns?.length || 0} unknowns · {portfolioReviewContext.project?.evidence?.length || 0} evidencias · decisiones requieren actor humano.
            </div>
            {portfolioReviewContext.project?.project_id && (
              <div className="mt-1 text-[10px] text-zinc-600">
                Siguiente acción: <code className="text-zinc-500">{portfolioReviewContext.project.next_action || 'provide_typed_archive_project_relation_with_source_refs'}</code>
              </div>
            )}
          </div>
        )}
        {portfolioDirectionContext?.available && (
          <div className="mt-4 rounded-xl border border-amber-900/50 bg-amber-950/10 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-sm font-bold text-amber-200">Marco de trabajo · visión / orden / cultura-computación</div>
                <div className="mt-1 text-[11px] text-zinc-500">
                  Ordena lo observado para decidir qué investigar después; no fabrica autoría, significado ni permiso.
                </div>
              </div>
              <span className="rounded-full border border-amber-800/60 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-amber-300">
                read-only
              </span>
            </div>
            <div className="mt-3 grid gap-2 md:grid-cols-3">
              {[
                ['Visión', portfolioDirectionContext.frame?.vision?.state || '—', `${portfolioDirectionContext.frame?.vision?.visible_item_count ?? 0} observaciones acotadas`],
                ['Orden', portfolioDirectionContext.frame?.order?.state || '—', `${portfolioDirectionContext.frame?.order?.expanded_count ?? 0} expansiones estructurales`],
                ['Cultura-computación', portfolioDirectionContext.frame?.culture_computation?.state || '—', `${portfolioDirectionContext.frame?.culture_computation?.practice_context_count ?? 0} contextos de práctica`],
              ].map(([label, state, detail]) => (
                <div key={String(label)} className="rounded-lg border border-zinc-800/70 bg-black/20 p-2">
                  <div className="text-[9px] font-bold uppercase tracking-wider text-amber-300">{label}</div>
                  <div className="mt-1 text-[10px] text-zinc-300">{state}</div>
                  <div className="mt-1 text-[10px] text-zinc-600">{detail}</div>
                </div>
              ))}
            </div>
            <div className="mt-3 text-[10px] text-zinc-600">
              Instrumento VIZZ: {portfolioDirectionContext.frame?.instrument?.measurement_status || '—'} · lineage {portfolioDirectionContext.frame?.instrument?.lineage_status || '—'} · measurement_claim_allowed={portfolioDirectionContext.frame?.instrument?.measurement_claim_allowed ? 'true' : 'false'}.
            </div>
            <div className="mt-1 text-[10px] text-zinc-700">
              purpose=vision_order_culture_computation_read_only_frame · Siguiente acción: <code className="text-zinc-500">{portfolioDirectionContext.next_action || '—'}</code> · selección=none · promoción=none · publicación=false · aprendizaje demostrado=false.
            </div>
          </div>
        )}
        {portfolioWorkPacket?.available && (
          <div className="mt-4 rounded-xl border border-cyan-900/50 bg-cyan-950/10 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-sm font-bold text-cyan-200">Paquete de trabajo · Portafolio</div>
                <div className="mt-1 text-[11px] text-zinc-500">Cuatro tareas posibles ordenadas por evidencia; ninguna se ejecuta desde esta vista.</div>
              </div>
              <span className="rounded-full border border-cyan-800/60 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-cyan-300">{portfolioWorkPacket.execution?.executed_task_count ?? 0}/{portfolioWorkPacket.execution?.task_count ?? 0} ejecutadas</span>
            </div>
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              {(portfolioWorkPacket.tasks || []).map(task => (
                <div key={task.id} className="rounded-lg border border-zinc-800/70 bg-black/20 p-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-300">{task.area || task.id}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-[9px] text-zinc-600">execution_allowed={task.execution_allowed ? 'true' : 'false'}</span>
                      <button type="button" onClick={() => previewPortfolioTask(task.id || '')} className="rounded border border-cyan-900/60 px-1.5 py-0.5 text-[9px] text-cyan-400 hover:border-cyan-700">previsualizar</button>
                    </div>
                  </div>
                  <div className="mt-1 text-[10px] text-zinc-300">{task.action || 'revisión pendiente'}</div>
                  <div className="mt-1 text-[9px] text-zinc-600">{task.evidence || '—'} · gate={task.human_gate || 'human'}</div>
                </div>
              ))}
            </div>
            {portfolioWorkPreview?.available && (
              <div className="mt-3 rounded-lg border border-cyan-800/50 bg-black/30 p-2 text-[10px] text-zinc-500">
                Preview: <strong className="text-cyan-300">{portfolioWorkPreview.task?.id || '—'}</strong> · proyecto={portfolioWorkPreview.source?.project_id || 'sin project_id'} · relación={portfolioWorkPreview.source?.relation_status || '—'} · área={portfolioWorkPreview.task?.area || '—'} · gate={portfolioWorkPreview.task?.human_gate || 'human'} · execution_allowed={portfolioWorkPreview.task?.execution_allowed ? 'true' : 'false'} · selection_effect={portfolioWorkPreview.control?.selection_effect || 'context_only'} · normalize_execution={portfolioWorkPreview.control?.normalize_execution ? 'true' : 'false'} · measurement_execution={portfolioWorkPreview.control?.measurement_execution ? 'true' : 'false'}
                <div className="mt-1 text-zinc-700">{portfolioWorkPreview.task?.action || '—'} · siguiente: <code className="text-zinc-500">{portfolioWorkPreview.next_action || 'human_review_selected_work_preview_before_execution'}</code></div>
              </div>
            )}
            <div className="mt-2 text-[10px] text-zinc-700">Siguiente acción: <code className="text-zinc-500">{portfolioWorkPacket.next_action || 'human_review_portfolio_work_packet_and_choose_one_task'}</code> · database_write=false · decision_write=false · normalize_execution={portfolioWorkPacket.control?.normalize_execution ? 'true' : 'false'} · measurement_execution={portfolioWorkPacket.control?.measurement_execution ? 'true' : 'false'} · promoción=none · publicación=false.</div>
          </div>
        )}
        {operationReceipt?.available && (
          <div className="mt-4 rounded-xl border border-emerald-900/50 bg-emerald-950/10 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-sm font-bold text-emerald-200">Recibo de operación</div>
                <div className="mt-1 text-[11px] text-zinc-500">
                  Ejecución estructural demostrada; visible para ordenar el trabajo, no para declarar verdad artística.
                </div>
              </div>
              <span className="rounded-full border border-emerald-800/60 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-emerald-300">
                {operationReceipt.status || 'executed_structural_only'}
              </span>
            </div>
            <div className="mt-3 grid gap-2 md:grid-cols-4">
              <div className="rounded-lg border border-zinc-800/70 bg-black/20 p-2 text-[10px] text-zinc-500">
                Operación: <strong className="text-zinc-300">{operationReceipt.operation?.name || 'expand_library_program'}</strong>
              </div>
              <div className="rounded-lg border border-zinc-800/70 bg-black/20 p-2 text-[10px] text-zinc-500">
                Dialecto: <strong className="text-zinc-300">{operationReceipt.operation?.dialect || '—'}</strong>
              </div>
              <div className="rounded-lg border border-zinc-800/70 bg-black/20 p-2 text-[10px] text-zinc-500">
                Expansión exacta: <strong className="text-zinc-300">{operationReceipt.operation?.expanded_count ?? 0} claves</strong>
              </div>
              <div className="rounded-lg border border-zinc-800/70 bg-black/20 p-2 text-[10px] text-zinc-500">
                Efecto: <strong className="text-zinc-300">{operationReceipt.control?.selection_effect || 'none'}</strong>
              </div>
            </div>
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              <div className="rounded-lg border border-zinc-800/70 bg-black/20 p-2 text-[10px] text-zinc-500">
                Rechazos conservados: {(operationReceipt.rejected_attempts || []).map(attempt => `${attempt.kind}:${attempt.reason}`).join(' · ') || '—'}
              </div>
              <div className="rounded-lg border border-zinc-800/70 bg-black/20 p-2 text-[10px] text-zinc-500">
                Controles: read-only · database_write=false · decision_write=false · promotion={operationReceipt.control?.promotion || 'none'} · publication={operationReceipt.control?.publication === false ? 'false' : '—'}
              </div>
            </div>
            <div className="mt-2 text-[10px] text-zinc-600">
              Provenance: {operationReceipt.provenance?.library_source_ref || '—'} ↔ {operationReceipt.provenance?.evaluation_source_ref || '—'} · equivalencia semántica autorizada: {operationReceipt.control?.semantic_equivalence_authorized === false ? 'no' : '—'}.
            </div>
          </div>
        )}
        {vizzMeasurementStatus?.available && (
          <div className="mt-4 rounded-xl border border-rose-900/50 bg-rose-950/10 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-sm font-bold text-rose-200">VIZZ · estado de medición</div>
                <div className="mt-1 text-[11px] text-zinc-500">
                  El UNKNOWN vuelve al operador con su razón y próximo paso; no se convierte en profundidad.
                </div>
              </div>
              <span className="rounded-full border border-rose-800/60 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-rose-300">
                {vizzMeasurementStatus.status || 'unknown_measurement_refused'}
              </span>
            </div>
            <div className="mt-3 grid gap-2 md:grid-cols-4">
              <div className="rounded-lg border border-zinc-800/70 bg-black/20 p-2 text-[10px] text-zinc-500">
                Medición: <strong className="text-zinc-300">{vizzMeasurementStatus.measurement?.status || '—'}</strong>
              </div>
              <div className="rounded-lg border border-zinc-800/70 bg-black/20 p-2 text-[10px] text-zinc-500">
                Calibración: <strong className="text-zinc-300">{vizzMeasurementStatus.measurement?.calibration_status || '—'}</strong>
              </div>
              <div className="rounded-lg border border-zinc-800/70 bg-black/20 p-2 text-[10px] text-zinc-500">
                Triangulación: <strong className="text-zinc-300">{vizzMeasurementStatus.measurement?.triangulation_attempted ? 'intentada' : 'no ejecutada'}</strong>
              </div>
              <div className="rounded-lg border border-zinc-800/70 bg-black/20 p-2 text-[10px] text-zinc-500">
                Profundidad: <strong className="text-zinc-300">{vizzMeasurementStatus.measurement?.depth_result_present ? 'presente' : 'no emitida'}</strong>
              </div>
            </div>
            <div className="mt-3 text-[10px] text-zinc-500">
              Razón: <span className="text-zinc-300">{vizzMeasurementStatus.reason || 'calibración física pendiente'}</span>
            </div>
            <div className="mt-1 text-[10px] text-zinc-600">
              Siguiente acción: <code className="text-zinc-500">{vizzMeasurementStatus.next_action || 'provide_physical_calibration_evidence_before_metric_measurement'}</code> · read-only · selection_effect={vizzMeasurementStatus.control?.selection_effect || 'none'} · promotion={vizzMeasurementStatus.control?.promotion || 'none'} · publication={vizzMeasurementStatus.control?.publication === false ? 'false' : '—'}
            </div>
            <div className="mt-1 text-[10px] text-zinc-700">
              Provenance: {vizzMeasurementStatus.provenance?.ref || '—'} · source_schema={vizzMeasurementStatus.provenance?.source_schema || '—'} · calibration_audit_sha256={vizzMeasurementStatus.provenance?.calibration_audit_sha256 || '—'} · calibration_provenance_ref={vizzMeasurementStatus.provenance?.calibration_provenance_ref || 'none'}
            </div>
          </div>
        )}
        {vizzLineageStatus?.available && (
          <div className="mt-4 rounded-xl border border-fuchsia-900/50 bg-fuchsia-950/10 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-sm font-bold text-fuchsia-200">Lineage VIZZ · contexto</div>
                <div className="mt-1 text-[11px] text-zinc-500">
                  La revisión se puede auditar sin reemplazar el UNKNOWN vigente.
                </div>
              </div>
              <span className="rounded-full border border-fuchsia-800/60 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-fuchsia-300">
                {vizzLineageStatus.status || 'revision_context_only'}
              </span>
            </div>
            <div className="mt-3 grid gap-2 md:grid-cols-3">
              <div className="rounded-lg border border-zinc-800/70 bg-black/20 p-2 text-[10px] text-zinc-500">
                Vigente: <strong className="text-zinc-300">{vizzLineageStatus.current?.status || '—'}</strong>
              </div>
              <div className="rounded-lg border border-zinc-800/70 bg-black/20 p-2 text-[10px] text-zinc-500">
                Revisión: <strong className="text-zinc-300">{vizzLineageStatus.revision?.revision_id || '—'}</strong>
              </div>
              <div className="rounded-lg border border-zinc-800/70 bg-black/20 p-2 text-[10px] text-zinc-500">
                Estado: <strong className="text-zinc-300">{vizzLineageStatus.revision?.status || '—'}</strong>
              </div>
            </div>
            <div className="mt-2 text-[10px] text-zinc-600">
              previous={vizzLineageStatus.revision?.previous_artifact_sha256?.slice(0, 16) || '—'}… · current={vizzLineageStatus.revision?.current_artifact_sha256?.slice(0, 16) || '—'}… · current_state_replaced={vizzLineageStatus.control?.current_state_replaced === false ? 'false' : '—'} · read-only · promotion={vizzLineageStatus.control?.promotion || 'none'} · publication={vizzLineageStatus.control?.publication === false ? 'false' : '—'}
            </div>
          </div>
        )}
        {structuralDeltaStatus?.available && (
          <div className="mt-4 rounded-xl border border-orange-900/50 bg-orange-950/10 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-sm font-bold text-orange-200">Delta estructural · revisión-only</div>
                <div className="mt-1 text-[11px] text-zinc-500">
                  La pérdida y los residuos quedan visibles para ordenar el trabajo; no son aprendizaje ni selección.
                </div>
              </div>
              <span className="rounded-full border border-orange-800/60 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-orange-300">
                {structuralDeltaStatus.status || 'revision_only_delta'}
              </span>
            </div>
            <div className="mt-3 grid gap-2 md:grid-cols-4">
              <div className="rounded-lg border border-zinc-800/70 bg-black/20 p-2 text-[10px] text-zinc-500">
                Evaluadas: <strong className="text-zinc-300">{structuralDeltaStatus.delta?.evaluated_keys ?? 0}</strong>
              </div>
              <div className="rounded-lg border border-zinc-800/70 bg-black/20 p-2 text-[10px] text-zinc-500">
                Compartidas: <strong className="text-zinc-300">{structuralDeltaStatus.delta?.shared_keys ?? 0}</strong>
              </div>
              <div className="rounded-lg border border-zinc-800/70 bg-black/20 p-2 text-[10px] text-zinc-500">
                Residuos nuevos: <strong className="text-zinc-300">{structuralDeltaStatus.delta?.residue_keys ?? 0}</strong>
              </div>
              <div className="rounded-lg border border-zinc-800/70 bg-black/20 p-2 text-[10px] text-zinc-500">
                Costo serializado: <strong className="text-zinc-300">{structuralDeltaStatus.delta?.serialized_savings_bytes ?? 0} bytes</strong>
              </div>
            </div>
            <div className="mt-2 text-[10px] text-zinc-600">
              Clave nueva: <code className="text-zinc-500">{structuralDeltaStatus.delta?.revision_only_key || '—'}</code> · library_pin={structuralDeltaStatus.provenance?.library_pin || '—'} · evaluation_pin={structuralDeltaStatus.provenance?.evaluation_pin || '—'} · learning_demonstrated={structuralDeltaStatus.control?.learning_demonstrated === false ? 'false' : '—'} · selection_effect={structuralDeltaStatus.control?.selection_effect || 'none'} · promotion={structuralDeltaStatus.control?.promotion || 'none'} · publication={structuralDeltaStatus.control?.publication === false ? 'false' : '—'}
            </div>
          </div>
        )}
        {latestAbstain && (
          <div className="mt-3 rounded-xl border border-rose-950/60 bg-rose-950/10 px-3 py-2 text-[11px] text-zinc-500">
            <span className="font-bold text-rose-300">{latestAbstain.episode_id}</span>
            <span className="mx-1.5 text-zinc-700">·</span>
            {latestAbstain.objective || 'Episodio sin objetivo legible'}
          </div>
        )}
        {auditAttention.length > 0 && (
          <div className="mt-3 rounded-xl border border-amber-900/50 bg-amber-950/10 px-3 py-2 text-[11px] text-zinc-500">
            <span className="font-bold text-amber-300">Atención de auditoría:</span>{' '}
            {auditAttention.map(item => `${item.contract_id || 'contract'}=${item.status || 'unknown'}${item.missing?.length ? ` (${item.missing.join(', ')})` : ''}`).join(' · ')}
          </div>
        )}
        {probeOpen && (
          <div className="mt-4 rounded-xl border border-cyan-900/50 bg-black/25 p-3">
            <div className="mb-2 text-[10px] font-bold uppercase tracking-widest text-cyan-400">Evaluar Project IR sin ejecutar herramientas</div>
            <textarea
              value={probeText}
              onChange={event => setProbeText(event.target.value)}
              rows={5}
              placeholder="Pega aquí un objeto Project IR en JSON"
              className="w-full rounded-lg border border-zinc-800 bg-black/40 px-3 py-2 font-mono text-[10px] leading-5 text-zinc-300 outline-none focus:border-cyan-800"
            />
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <button
                onClick={runProbe}
                disabled={probeBusy || !probeText.trim()}
                className="inline-flex items-center gap-1.5 rounded-lg bg-cyan-500 px-3 py-2 text-xs font-bold text-black hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {probeBusy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                Evaluar
              </button>
              <span className="text-[10px] text-zinc-600">No registra episodios y no inicia Blender, Research ni mutadores.</span>
            </div>
            {probeResult && (
              <pre className="mt-3 max-h-60 overflow-auto rounded-lg bg-black/40 p-3 text-[10px] leading-5 text-zinc-400">
                {JSON.stringify(probeResult, null, 2)}
              </pre>
            )}
          </div>
        )}
      </div>

      {/* Quick actions grid */}
      <div>
        <div className="mb-4 flex items-center gap-2">
          <h2 className="text-lg font-bold">Acciones rápidas</h2>
          <span className="text-xs text-zinc-500">operación diaria</span>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {actions.map(item => {
            const Icon = item.icon;
            return (
              <button
                key={item.view}
                onClick={() => onNavigate(item.view)}
                className="group relative overflow-hidden rounded-xl border border-zinc-800/60 bg-zinc-900/50 p-5 text-left transition-all hover:border-zinc-700 hover:bg-zinc-800/50 hover:shadow-lg"
              >
                <div className={`absolute inset-0 bg-gradient-to-br ${item.color} opacity-0 transition-opacity group-hover:opacity-[0.03]`} />
                <div className="relative">
                  <div className="flex items-start justify-between">
                    <div className={`flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br ${item.color} shadow-lg`}>
                      <Icon className="h-5 w-5 text-white" />
                    </div>
                    {'badge' in item && item.badge && (
                      <span className="rounded-full bg-violet-500/20 px-2 py-0.5 text-[10px] font-bold text-violet-300">
                        {item.badge}
                      </span>
                    )}
                  </div>
                  <h3 className="mt-3 text-sm font-bold">{item.title}</h3>
                  <p className="mt-1 text-xs text-zinc-500">{item.desc}</p>
                  <div className="mt-3 flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-zinc-600 group-hover:text-zinc-400">
                    Abrir <ArrowRight className="h-3 w-3" />
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Recent jobs */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold">Jobs recientes</h2>
          <button onClick={() => onNavigate('jobs')} className="text-xs text-zinc-500 hover:text-zinc-300 flex items-center gap-1">
            Ver todos <ArrowRight className="h-3 w-3" />
          </button>
        </div>
        <div className="space-y-2">
          {recent.length ? recent.map(job => (
            <div key={job.path || job.name} className="flex items-center gap-4 rounded-xl border border-zinc-800/50 bg-zinc-900/30 p-3 transition-colors hover:bg-zinc-800/30">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-zinc-800">
                <Boxes className="h-4 w-4 text-zinc-500" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium truncate">{job.name}</div>
                <div className="text-[10px] text-zinc-600 truncate">{job.tipo_pieza || 'pieza'} · {job.proyecto || '—'}</div>
              </div>
              <span className={`shrink-0 rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider ${statusColor(job.estado)}`}>
                {job.estado || 'sin estado'}
              </span>
              <Clock className="h-3.5 w-3.5 text-zinc-700" />
            </div>
          )) : (
            <div className="rounded-xl border border-dashed border-zinc-800 p-8 text-center text-sm text-zinc-600">
              Sin jobs reales todavía. Usa <strong>Intake</strong> para crear uno.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
