import { useAppState } from "../state/AppState";

function toggle(list: string[], value: string) {
  return list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
}

function ChipMulti({
  values,
  selected,
  onChange,
}: {
  values: string[];
  selected: string[];
  onChange: (next: string[]) => void;
}) {
  return (
    <div className="chip-list">
      {values.map((item) => {
        const active = selected.includes(item);
        return (
          <button
            key={item}
            type="button"
            className={active ? "chip active" : "chip"}
            onClick={() => onChange(toggle(selected, item))}
          >
            {item}
          </button>
        );
      })}
    </div>
  );
}

export function Sidebar() {
  const { sources, selected, setSelected, filters, setFilters, resetFilters, dashboard } = useAppState();
  const options = dashboard?.options;
  const hasClaims = selected.includes("reclamations");
  const hasSatisfaction = selected.some((id) => id !== "reclamations");
  const activeFilters = dashboard?.active_filters ?? 0;

  return (
    <aside className="sidebar">
      <div className="sidebar-block">
        <div className="section-title">
          <span>Sources</span>
          <span className="meta">{selected.length}/{sources.length}</span>
        </div>
        <div className="inline-actions">
          <button
            type="button"
            onClick={() => setSelected(sources.filter((item) => item.available).map((item) => item.id))}
          >
            Tout
          </button>
          <button type="button" onClick={() => setSelected([])}>
            Aucun
          </button>
        </div>
        <div className="source-list">
          {sources.map((source) => (
            <label key={source.id} className="check-row">
              <input
                type="checkbox"
                checked={selected.includes(source.id)}
                disabled={!source.available}
                onChange={() => setSelected(toggle(selected, source.id))}
              />
              <span>{source.label}</span>
              <span className="source-meta">
                {!source.available ? "off" : source.rows.toLocaleString("fr-FR")}
              </span>
            </label>
          ))}
        </div>
      </div>

      <div className="sidebar-block">
        <div className="section-title">
          <span>Filtres</span>
          {activeFilters ? (
            <button className="linkish" type="button" onClick={resetFilters}>
              Réinitialiser ({activeFilters})
            </button>
          ) : (
            <button className="linkish" type="button" onClick={resetFilters}>
              Réinitialiser
            </button>
          )}
        </div>

        {options?.pays?.length ? (
          <div className="filter-group">
            <span className="section-title">Pays</span>
            <ChipMulti
              values={options.pays}
              selected={filters.pays}
              onChange={(pays) => setFilters({ ...filters, pays })}
            />
          </div>
        ) : null}

        {hasSatisfaction && options?.produit_global?.length ? (
          <div className="filter-group" style={{ marginTop: 12 }}>
            <span className="section-title">Produit</span>
            <ChipMulti
              values={options.produit_global}
              selected={filters.produit_global}
              onChange={(produit_global) => setFilters({ ...filters, produit_global })}
            />
          </div>
        ) : null}

        {hasSatisfaction ? (
          <div className="filter-group" style={{ marginTop: 12 }}>
            <span className="section-title">Satisfaction</span>
            <div className="inline-actions">
              <input
                className="field"
                type="number"
                min={1}
                max={5}
                step={0.1}
                placeholder="Min"
                value={filters.satisfaction_min ?? ""}
                onChange={(event) =>
                  setFilters({
                    ...filters,
                    satisfaction_min: event.target.value === "" ? null : Number(event.target.value),
                  })
                }
              />
              <input
                className="field"
                type="number"
                min={1}
                max={5}
                step={0.1}
                placeholder="Max"
                value={filters.satisfaction_max ?? ""}
                onChange={(event) =>
                  setFilters({
                    ...filters,
                    satisfaction_max: event.target.value === "" ? null : Number(event.target.value),
                  })
                }
              />
            </div>
          </div>
        ) : null}

        <div className="filter-group" style={{ marginTop: 12 }}>
          <span className="section-title">Période</span>
          <input
            type="date"
            value={filters.date_start ?? ""}
            min={options?.date_min ?? undefined}
            max={options?.date_max ?? undefined}
            onChange={(event) => setFilters({ ...filters, date_start: event.target.value || null })}
          />
          <input
            type="date"
            value={filters.date_end ?? ""}
            min={options?.date_min ?? undefined}
            max={options?.date_max ?? undefined}
            onChange={(event) => setFilters({ ...filters, date_end: event.target.value || null })}
          />
        </div>

        {hasClaims && options?.categorie_reclamation?.length ? (
          <div className="filter-group" style={{ marginTop: 12 }}>
            <span className="section-title">Catégorie</span>
            <ChipMulti
              values={options.categorie_reclamation}
              selected={filters.categorie_reclamation}
              onChange={(categorie_reclamation) => setFilters({ ...filters, categorie_reclamation })}
            />
          </div>
        ) : null}

        {hasClaims && options?.statut_reclamation?.length ? (
          <div className="filter-group" style={{ marginTop: 12 }}>
            <span className="section-title">Statut</span>
            <ChipMulti
              values={options.statut_reclamation}
              selected={filters.statut_reclamation}
              onChange={(statut_reclamation) => setFilters({ ...filters, statut_reclamation })}
            />
          </div>
        ) : null}
      </div>
    </aside>
  );
}
