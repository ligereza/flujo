export type ApiState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
  source: 'api' | 'demo';
};

export type Ping = {
  status?: string;
  version?: string;
  root?: string;
  connected?: boolean;
  mode?: string;
  note?: string;
};

export type DashboardSummary = {
  total_items?: number;
  total_svg?: number;
  total_jobs?: number;
  [key: string]: unknown;
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
  ],
  count: 2,
  source: 'demo',
};

export const flujoApi = {
  isFileMode,
  async ping(): Promise<Ping> {
    if (isFileMode()) return { status: 'demo', version: 'offline', connected: false, mode: 'file' };
    return request<Ping>('/api/ping');
  },
  async dashboardSummary(): Promise<DashboardSummary> {
    if (isFileMode()) return { total_items: 0, total_jobs: demoJobs.count };
    return request<DashboardSummary>('/api/dashboard-summary');
  },
  async jobs(): Promise<JobsResponse> {
    if (isFileMode()) return demoJobs;
    try {
      return await request<JobsResponse>('/api/list-jobs');
    } catch (error) {
      return { ...demoJobs, error: error instanceof Error ? error.message : String(error) };
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
