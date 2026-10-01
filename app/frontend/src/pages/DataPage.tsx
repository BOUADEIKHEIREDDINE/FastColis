import { useEffect, useState } from "react";
import { api } from "../api";
import { useAppState } from "../state/AppState";
import type { TableResponse } from "../types";

export function DataPage() {
  const { selected, filters, dashboard } = useAppState();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [sortBy, setSortBy] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [table, setTable] = useState<TableResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setPage(1);
  }, [selected, filters, search, pageSize]);

  useEffect(() => {
    if (!selected.length) {
      setTable(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    api
      .table({
        sources: selected,
        filters,
        page,
        page_size: pageSize,
        sort_by: sortBy,
        sort_dir: sortDir,
        search,
      })
      .then((payload) => {
        if (!cancelled) {
          setTable(payload);
          setError(null);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selected, filters, page, pageSize, sortBy, sortDir, search]);

  const onSort = (column: string) => {
    if (sortBy === column) {
      setSortDir((current) => (current === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(column);
      setSortDir("asc");
    }
  };

  return (
    <>
      <div className="context-bar">
        <div>
          <h1>Données</h1>
          <p className="meta">{table?.context || dashboard?.context || "—"}</p>
        </div>
        <div className="status-pills">
          {table ? (
            <span className="pill">
              <strong>{table.total.toLocaleString("fr-FR")}</strong> lignes
            </span>
          ) : null}
        </div>
      </div>

      <div className="table-toolbar">
        <input
          className="search"
          type="search"
          placeholder="Rechercher dans les lignes…"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <select value={pageSize} onChange={(event) => setPageSize(Number(event.target.value))}>
          {[10, 25, 50, 100].map((size) => (
            <option key={size} value={size}>
              {size} lignes
            </option>
          ))}
        </select>
        <button
          className="ghost"
          type="button"
          disabled={!selected.length}
          onClick={() => void api.exportExcel({ sources: selected, filters, search })}
        >
          Export Excel
        </button>
      </div>

      {error ? <div className="banner error">{error}</div> : null}
      {loading ? (
        <div className="loading-inline">
          <span className="spinner" />
          Chargement du tableau…
        </div>
      ) : null}

      {table ? (
        <section className="card">
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  {table.columns.map((column) => (
                    <th key={column.id} onClick={() => onSort(column.id)}>
                      {column.label}
                      {sortBy === column.id ? (sortDir === "asc" ? " ↑" : " ↓") : ""}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {table.rows.map((row, index) => (
                  <tr key={index}>
                    {table.columns.map((column) => (
                      <td key={column.id}>{formatCell(row[column.id])}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pagination">
            <span>
              {table.total.toLocaleString("fr-FR")} ligne{table.total > 1 ? "s" : ""} · page{" "}
              {table.page}/{table.pages}
            </span>
            <div className="inline-actions">
              <button
                className="ghost"
                type="button"
                disabled={table.page <= 1}
                onClick={() => setPage((current) => Math.max(1, current - 1))}
              >
                Précédent
              </button>
              <button
                className="ghost"
                type="button"
                disabled={table.page >= table.pages}
                onClick={() => setPage((current) => current + 1)}
              >
                Suivant
              </button>
            </div>
          </div>
        </section>
      ) : null}
    </>
  );
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(3);
  return String(value);
}
