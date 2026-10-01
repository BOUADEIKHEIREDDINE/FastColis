import { Layout } from "./components/Layout";
import { ChatBar } from "./components/ChatBar";
import { Sidebar } from "./components/Sidebar";
import { AppStateProvider, useAppState } from "./state/AppState";
import { DashboardPage } from "./pages/DashboardPage";
import { DataPage } from "./pages/DataPage";
import { AssistantPage } from "./pages/AssistantPage";
import { QualityPage } from "./pages/QualityPage";

function Workspace() {
  const { page, error, loading, selected } = useAppState();

  return (
    <div className="workspace">
      <Sidebar />
      <main className="main">
        <div className="main-inner">
          {error ? <div className="banner error">{error}</div> : null}
          {!selected.length ? (
            <div className="banner warn">Sélectionnez au moins une source dans la barre latérale.</div>
          ) : null}
          {loading && page !== "dashboard" ? (
            <div className="loading-inline">
              <span className="spinner" />
              Mise à jour…
            </div>
          ) : null}
          {page === "dashboard" ? <DashboardPage /> : null}
          {page === "data" ? <DataPage /> : null}
          {page === "assistant" ? <AssistantPage /> : null}
          {page === "quality" ? <QualityPage /> : null}
        </div>
      </main>
    </div>
  );
}

export function App() {
  return (
    <AppStateProvider>
      <Layout>
        <ChatBar />
        <Workspace />
      </Layout>
    </AppStateProvider>
  );
}
