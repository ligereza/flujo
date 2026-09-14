export interface PortfolioProject {
  id: string;
  nombre: string;
  linea: string;
  estado: string;
  descripcion: string;
  tags: string[];
  ruta?: string;
  url?: string;
}

export interface PortfolioCatalog {
  titulo?: string;
  proyectos: PortfolioProject[];
  contrato?: {
    name?: string;
    version?: number;
    source?: string;
    visual_works_source?: string;
  };
  prototipo_generado?: boolean;
  prototipo_ruta?: string;
}

export class PortfolioCatalogError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'PortfolioCatalogError';
  }
}

function text(value: unknown, field: string, index: number): string {
  if (typeof value !== 'string' || !value.trim()) {
    throw new PortfolioCatalogError(`project[${index}] missing ${field}`);
  }
  return value;
}

export function parsePortfolioCatalog(payload: unknown): PortfolioCatalog {
  if (!payload || typeof payload !== 'object') {
    throw new PortfolioCatalogError('catalogue response is not an object');
  }
  const candidate = payload as Record<string, unknown>;
  if (!Array.isArray(candidate.proyectos)) {
    throw new PortfolioCatalogError('catalogue response has no proyectos list');
  }

  const ids = new Set<string>();
  const proyectos = candidate.proyectos.map((raw, index): PortfolioProject => {
    if (!raw || typeof raw !== 'object') {
      throw new PortfolioCatalogError(`project[${index}] is not an object`);
    }
    const item = raw as Record<string, unknown>;
    const id = text(item.id, 'id', index);
    if (ids.has(id)) throw new PortfolioCatalogError(`duplicate project id: ${id}`);
    ids.add(id);
    const tags = item.tags ?? [];
    if (!Array.isArray(tags) || !tags.every(tag => typeof tag === 'string')) {
      throw new PortfolioCatalogError(`project[${index}] tags are invalid`);
    }
    return {
      id,
      nombre: text(item.nombre, 'nombre', index),
      linea: text(item.linea, 'linea', index),
      estado: text(item.estado, 'estado', index),
      descripcion: text(item.descripcion, 'descripcion', index),
      tags,
      ...(typeof item.ruta === 'string' ? { ruta: item.ruta } : {}),
      ...(typeof item.url === 'string' ? { url: item.url } : {}),
    };
  });

  return {
    ...(typeof candidate.titulo === 'string' ? { titulo: candidate.titulo } : {}),
    proyectos,
    ...(candidate.contrato && typeof candidate.contrato === 'object'
      ? { contrato: candidate.contrato as PortfolioCatalog['contrato'] }
      : {}),
    ...(typeof candidate.prototipo_generado === 'boolean'
      ? { prototipo_generado: candidate.prototipo_generado }
      : {}),
    ...(typeof candidate.prototipo_ruta === 'string'
      ? { prototipo_ruta: candidate.prototipo_ruta }
      : {}),
  };
}

export async function fetchPortfolioCatalog(): Promise<PortfolioCatalog> {
  const response = await fetch('/api/portafolio');
  const payload: unknown = await response.json();
  if (!response.ok) throw new PortfolioCatalogError(`HTTP ${response.status}`);
  if (payload && typeof payload === 'object' && 'error' in payload) {
    const error = (payload as { error?: unknown }).error;
    if (typeof error === 'string' && error) throw new PortfolioCatalogError(error);
  }
  return parsePortfolioCatalog(payload);
}
