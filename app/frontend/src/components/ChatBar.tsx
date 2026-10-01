import { useEffect, useRef, useState } from "react";
import { useAppState } from "../state/AppState";

const SUGGESTIONS = [
  "Quelle est la satisfaction moyenne ?",
  "Compare la France et le Maroc",
  "Quel produit a la satisfaction la plus faible ?",
  "Quelles sont les principales réclamations ?",
];

export function ChatBar() {
  const { ask, asking, model, setModel, selected, sources, dashboard, page } = useAppState();
  const [question, setQuestion] = useState("");
  const areaRef = useRef<HTMLTextAreaElement>(null);

  const scopeLabel = selected
    .map((id) => sources.find((source) => source.id === id)?.label || id)
    .join(" · ");

  useEffect(() => {
    const node = areaRef.current;
    if (!node) return;
    node.style.height = "0px";
    node.style.height = `${Math.min(node.scrollHeight, 96)}px`;
  }, [question]);

  const submit = (value = question) => {
    const trimmed = value.trim();
    if (!trimmed || asking) return;
    void ask(trimmed);
    setQuestion("");
  };

  return (
    <div className="chat-wrap">
      <div className="chat-inner">
        <div className="chat-meta-row">
          <div className="scope-chip" title={scopeLabel || "Aucune source"}>
            <span className="dot" />
            <span>
              {selected.length
                ? `${selected.length} source${selected.length > 1 ? "s" : ""} · ${scopeLabel}`
                : "Aucune source sélectionnée"}
              {dashboard?.active_filters
                ? ` · ${dashboard.active_filters} filtre${dashboard.active_filters > 1 ? "s" : ""}`
                : ""}
            </span>
          </div>
          <span className="meta">Entrée pour envoyer · Maj+Entrée pour une nouvelle ligne</span>
        </div>

        <form
          className="chat-bar"
          onSubmit={(event) => {
            event.preventDefault();
            submit();
          }}
        >
          <textarea
            ref={areaRef}
            rows={1}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                submit();
              }
            }}
            placeholder="Posez une question sur vos données…"
            aria-label="Question à FastColis"
          />
          <div className="chat-actions">
            <select value={model} onChange={(event) => setModel(event.target.value)} aria-label="Modèle">
              <option value="mistral:latest">mistral</option>
              <option value="qwen3.5:2b">qwen 2b</option>
            </select>
            <button className="send" type="submit" disabled={asking || !question.trim()} aria-label="Envoyer">
              ↑
            </button>
          </div>
        </form>

        {page !== "assistant" || !question ? (
          <div className="suggestion-row">
            {SUGGESTIONS.map((item) => (
              <button key={item} className="suggestion" type="button" disabled={asking} onClick={() => submit(item)}>
                {item}
              </button>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
