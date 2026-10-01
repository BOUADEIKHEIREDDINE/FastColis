import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "../api";
import { emptyFilters, type AskResponse, type DashboardResponse, type Filters, type SourceInfo } from "../types";

type PageId = "dashboard" | "data" | "assistant" | "quality";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  meta?: AskResponse;
};

type AppStateValue = {
  page: PageId;
  setPage: (page: PageId) => void;
  sources: SourceInfo[];
  selected: string[];
  setSelected: (ids: string[]) => void;
  filters: Filters;
  setFilters: (filters: Filters | ((current: Filters) => Filters)) => void;
  resetFilters: () => void;
  dashboard: DashboardResponse | null;
  loading: boolean;
  error: string | null;
  model: string;
  setModel: (model: string) => void;
  messages: ChatMessage[];
  asking: boolean;
  ask: (question: string) => Promise<void>;
  clearMessages: () => void;
};

const AppStateContext = createContext<AppStateValue | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [page, setPage] = useState<PageId>("dashboard");
  const [sources, setSources] = useState<SourceInfo[]>([]);
  const [selected, setSelected] = useState<string[]>(["france", "espagne", "maroc", "allemagne", "canada"]);
  const [filters, setFilters] = useState<Filters>(emptyFilters());
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [model, setModel] = useState("mistral:latest");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [asking, setAsking] = useState(false);

  useEffect(() => {
    api.sources()
      .then((payload) => setSources(payload.sources as SourceInfo[]))
      .catch((err: Error) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!selected.length) {
      setDashboard(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    api.dashboard({ sources: selected, filters })
      .then((payload) => {
        if (!cancelled) {
          setDashboard(payload);
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
  }, [selected, filters]);

  const ask = async (question: string) => {
    const trimmed = question.trim();
    if (!trimmed) return;
    setAsking(true);
    setPage("assistant");
    setMessages((current) => [...current, { role: "user", content: trimmed }]);
    try {
      const response = await api.ask({
        question: trimmed,
        sources: selected,
        filters,
        model,
      });
      setMessages((current) => [
        ...current,
        { role: "assistant", content: response.answer || response.error || "Réponse indisponible.", meta: response },
      ]);
    } catch (err) {
      setMessages((current) => [
        ...current,
        { role: "assistant", content: err instanceof Error ? err.message : "Erreur LLM." },
      ]);
    } finally {
      setAsking(false);
    }
  };

  const value = useMemo<AppStateValue>(
    () => ({
      page,
      setPage,
      sources,
      selected,
      setSelected,
      filters,
      setFilters,
      resetFilters: () => setFilters(emptyFilters()),
      dashboard,
      loading,
      error,
      model,
      setModel,
      messages,
      asking,
      ask,
      clearMessages: () => setMessages([]),
    }),
    [page, sources, selected, filters, dashboard, loading, error, model, messages, asking],
  );

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState() {
  const value = useContext(AppStateContext);
  if (!value) throw new Error("AppState missing");
  return value;
}
