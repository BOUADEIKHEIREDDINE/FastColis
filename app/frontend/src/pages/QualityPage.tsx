import { useEffect, useState } from "react";
import { api } from "../api";
import type { QualityResponse } from "../types";

export function QualityPage() {
  const [quality, setQuality] = useState<QualityResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .quality()
      .then((payload) => {
        setQuality(payload);
        setError(null);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="meta">Chargement des indicateurs de qualité…</p>;
  if (error) return <div className="banner error">{error}</div>;
  if (!quality) return <p className="meta">Aucun rapport disponible.</p>;

  return (
    <>
      <div className="context-bar">
        <div>
          <h1>Qualité des données</h1>
          <p className="meta">
            Profils des fichiers consommés par le dashboard, plus les rapports raw de la pipeline
            existante.
          </p>
        </div>
      </div>

      {quality.error ? <div className="banner warn">{quality.error}</div> : null}

      <div className="quality-grid">
        {quality.normalized.map((row) => (
          <section key={String(row.source)} className="card">
            <h2>{String(row.source)}</h2>
            {row.available ? (
              <>
                <p className="meta">
                  {Number(row.rows).toLocaleString("fr-FR")} lignes · {String(row.columns)} colonnes
                </p>
                <p className="meta">Doublons : {String(row.duplicate_rows)}</p>
                <p className="meta">
                  Manquants : {String(row.total_missing)} ({String(row.missing_rate_pct)} %)
                </p>
              </>
            ) : (
              <div className="banner error">{String(row.error || "Indisponible")}</div>
            )}
          </section>
        ))}
      </div>

      {quality.notes?.length ? (
        <section className="card" style={{ marginTop: 12 }}>
          <h2>Notes</h2>
          <ul className="meta">
            {quality.notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {quality.raw_available ? (
        <>
          <section className="card" style={{ marginTop: 12 }}>
            <h2>Structure (raw)</h2>
            <PreviewTable rows={quality.structure} />
          </section>
          <section className="card" style={{ marginTop: 12 }}>
            <h2>Valeurs manquantes (raw)</h2>
            <PreviewTable rows={quality.missing} />
          </section>
          <section className="card" style={{ marginTop: 12 }}>
            <h2>Outliers (raw)</h2>
            <PreviewTable rows={quality.outliers} />
          </section>
          <section className="card" style={{ marginTop: 12 }}>
            <h2>Faibles corrélations (candidats &lt; 0.2)</h2>
            <PreviewTable rows={quality.low_correlation_removed_candidates} />
          </section>
        </>
      ) : null}
    </>
  );
}

function PreviewTable({ rows }: { rows: Array<Record<string, unknown>> }) {
  if (!rows.length) return <p className="meta">Aucune ligne.</p>;
  const columns = Object.keys(rows[0]).slice(0, 8);
  return (
    <div className="table-wrap">
      <table className="data">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 40).map((row, index) => (
            <tr key={index}>
              {columns.map((column) => (
                <td key={column}>{String(row[column] ?? "—")}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
