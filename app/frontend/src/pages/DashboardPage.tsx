import { BarSeries, LineSeries } from "../charts/Charts";
import { useAppState } from "../state/AppState";

export function DashboardPage() {
  const { dashboard, filters, setFilters, selected, loading } = useAppState();

  if (!dashboard && loading) {
    return (
      <>
        <div className="loading-inline">
          <span className="spinner" />
          Mise à jour du dashboard…
        </div>
        <div className="skeleton-grid">
          {Array.from({ length: 5 }).map((_, index) => (
            <div key={index} className="skeleton" />
          ))}
        </div>
      </>
    );
  }

  if (!dashboard) {
    return <p className="meta">Aucune donnée à afficher. Sélectionnez au moins une source.</p>;
  }

  const charts = dashboard.charts;
  const toggleCountry = (label: string) => {
    const current = filters.chart_pays;
    const next = current.includes(label)
      ? current.filter((item) => item !== label)
      : [...current, label];
    setFilters({ ...filters, chart_pays: next });
  };

  return (
    <>
      <div className="context-bar">
        <div>
          <h1>Dashboard</h1>
          <p className="meta">{dashboard.context}</p>
        </div>
        <div className="status-pills">
          <span className="pill">
            <strong>{selected.length}</strong> source{selected.length > 1 ? "s" : ""}
          </span>
          <span className="pill">
            <strong>{dashboard.row_count.toLocaleString("fr-FR")}</strong> lignes
          </span>
          <span className={dashboard.active_filters ? "pill accent" : "pill"}>
            <strong>{dashboard.active_filters}</strong> filtre
            {dashboard.active_filters > 1 ? "s" : ""}
          </span>
          {loading ? (
            <span className="pill">
              <span className="spinner" /> maj…
            </span>
          ) : null}
        </div>
      </div>

      {dashboard.missing?.length ? (
        <div className="banner warn">{dashboard.missing.join(" · ")}</div>
      ) : null}

      <div className="kpi-grid">
        {dashboard.kpis.map((kpi) => (
          <div key={kpi.id} className={kpi.available ? "kpi" : "kpi disabled"}>
            <div className="label">{kpi.label}</div>
            <div className="value">{kpi.value ?? "—"}</div>
            <div className="hint">{kpi.hint}</div>
          </div>
        ))}
      </div>

      <div className="chart-grid">
        {dashboard.has_satisfaction ? (
          <>
            <BarSeries
              title="Satisfaction par pays"
              data={charts.satisfaction_by_country || []}
              onSelect={toggleCountry}
              selected={filters.chart_pays}
            />
            <BarSeries
              title="Satisfaction par produit"
              data={charts.satisfaction_by_product || []}
              layout="horizontal"
            />
            <LineSeries title="Évolution temporelle" data={charts.satisfaction_over_time || []} />
            <BarSeries title="Distribution des scores" data={charts.score_distribution || []} />
          </>
        ) : null}

        {dashboard.has_claims ? (
          <>
            <BarSeries title="Réclamations par catégorie" data={charts.claims_by_category || []} />
            <BarSeries title="Réclamations par pays" data={charts.claims_by_country || []} />
            <LineSeries title="Volume de réclamations" data={charts.claims_over_time || []} />
            <BarSeries title="Réclamations par statut" data={charts.claims_by_status || []} />
          </>
        ) : null}
      </div>

      {filters.chart_pays.length ? (
        <div className="banner ok" style={{ marginTop: 12, marginBottom: 0 }}>
          Filtre croisé graphique : {filters.chart_pays.join(", ")}.{" "}
          <button
            className="linkish"
            type="button"
            onClick={() => setFilters({ ...filters, chart_pays: [] })}
          >
            Effacer
          </button>
        </div>
      ) : null}
    </>
  );
}
