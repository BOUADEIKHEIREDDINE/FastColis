export type SourceInfo = {
  id: string;
  label: string;
  kind: "satisfaction" | "reclamations" | string;
  available: boolean;
  error: string | None;
  rows: number;
  columns: string[];
};

type None = null;

export type Filters = {
  pays: string[];
  produit_global: string[];
  taille_colis: string[];
  statut_colis: string[];
  categorie_reclamation: string[];
  statut_reclamation: string[];
  priorite_traitement: string[];
  satisfaction_min: number | null;
  satisfaction_max: number | null;
  date_start: string | null;
  date_end: string | null;
  chart_pays: string[];
};

export type FilterOptions = {
  pays: string[];
  produit_global: string[];
  taille_colis: string[];
  statut_colis: string[];
  categorie_reclamation: string[];
  statut_reclamation: string[];
  priorite_traitement: string[];
  canal_reclamation: string[];
  date_min: string | null;
  date_max: string | null;
  columns: string[];
};

export type Kpi = {
  id: string;
  label: string;
  value: string | null;
  hint: string;
  available: boolean;
};

export type ChartPoint = {
  label: string;
  value: number;
  count?: number;
};

export type DashboardResponse = {
  context: string;
  source_ids: string[];
  row_count: number;
  satisfaction_rows: number;
  claims_rows: number;
  active_filters: number;
  kpis: Kpi[];
  charts: Record<string, ChartPoint[]>;
  has_satisfaction: boolean;
  has_claims: boolean;
  missing: string[];
  options: FilterOptions;
};

export type TableResponse = {
  columns: { id: string; label: string }[];
  rows: Record<string, unknown>[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  missing: string[];
  context: string;
};

export type AskResponse = {
  ok: boolean;
  answer?: string;
  error?: string;
  sources?: string[];
  source_ids?: string[];
  scope?: {
    mode: string;
    conflict: boolean;
    warning: string | null;
    selected: string[];
    mentioned: string[];
    effective: string[];
  };
  facts?: Record<string, unknown>;
  fallback?: boolean;
  evidence?: Record<string, unknown>[];
  row_count?: number;
  missing_files?: string[];
  context?: string;
  model?: string;
};

export type QualityResponse = {
  normalized: Array<Record<string, unknown>>;
  raw_available: boolean;
  error?: string | null;
  structure: Array<Record<string, unknown>>;
  missing: Array<Record<string, unknown>>;
  correlations: Array<Record<string, unknown>>;
  low_correlation_removed_candidates: Array<Record<string, unknown>>;
  outliers: Array<Record<string, unknown>>;
  notes?: string[];
};

export const emptyFilters = (): Filters => ({
  pays: [],
  produit_global: [],
  taille_colis: [],
  statut_colis: [],
  categorie_reclamation: [],
  statut_reclamation: [],
  priorite_traitement: [],
  satisfaction_min: null,
  satisfaction_max: null,
  date_start: null,
  date_end: null,
  chart_pays: [],
});
