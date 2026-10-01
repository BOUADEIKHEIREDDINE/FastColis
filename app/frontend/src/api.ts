import type { AskResponse, DashboardResponse, QualityResponse, TableResponse } from "./types";

async function parseError(response: Response): Promise<string> {
  try {
    const payload = await response.json();
    if (typeof payload?.detail === "string") return payload.detail;
    if (payload?.error) return payload.error;
    return JSON.stringify(payload);
  } catch {
    return response.statusText;
  }
}

export async function postJson<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return response.json() as Promise<T>;
}

export async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return response.json() as Promise<T>;
}

export const api = {
  sources: () => getJson<{ sources: Array<Record<string, unknown>> }>("/api/sources"),
  dashboard: (body: unknown) => postJson<DashboardResponse>("/api/dashboard", body),
  table: (body: unknown) => postJson<TableResponse>("/api/table", body),
  async ask(body: unknown): Promise<AskResponse> {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    try {
      return (await response.json()) as AskResponse;
    } catch {
      throw new Error(response.statusText || "Erreur LLM");
    }
  },
  quality: () => getJson<QualityResponse>("/api/quality"),
  async exportExcel(body: unknown) {
    const response = await fetch("/api/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      throw new Error(await parseError(response));
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "fastcolis_export.xlsx";
    anchor.click();
    URL.revokeObjectURL(url);
  },
};
