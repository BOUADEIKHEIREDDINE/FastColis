import { useAppState } from "../state/AppState";

const labels = {
  dashboard: "Dashboard",
  data: "Données",
  assistant: "Assistant",
  quality: "Qualité",
} as const;

export function Layout({ children }: { children: React.ReactNode }) {
  const { page, setPage } = useAppState();
  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark" aria-hidden>
            FC
          </div>
          <div className="brand-copy">
            <strong>FastColis</strong>
            <span>Analyse intelligente des données</span>
          </div>
        </div>
        <nav className="nav" aria-label="Navigation principale">
          {(Object.keys(labels) as Array<keyof typeof labels>).map((id) => (
            <button
              key={id}
              className={page === id ? "active" : ""}
              type="button"
              onClick={() => setPage(id)}
            >
              {labels[id]}
            </button>
          ))}
        </nav>
        <div className="profile-chip">Analyste</div>
      </header>
      {children}
    </div>
  );
}
