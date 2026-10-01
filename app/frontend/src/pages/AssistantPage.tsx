import { useEffect, useRef, useState } from "react";
import { useAppState } from "../state/AppState";

const COLLAPSE_AT = 720;

function CollapsibleAnswer({ content }: { content: string }) {
  const [expanded, setExpanded] = useState(false);
  const long = content.length > COLLAPSE_AT;
  const shown = !long || expanded ? content : `${content.slice(0, COLLAPSE_AT).trimEnd()}…`;

  return (
    <>
      <div className={long && !expanded ? "answer clamped" : "answer"}>{shown}</div>
      {long ? (
        <button className="linkish" type="button" onClick={() => setExpanded((value) => !value)}>
          {expanded ? "Réduire" : "Voir plus"}
        </button>
      ) : null}
    </>
  );
}

export function AssistantPage() {
  const { messages, asking, selected, sources, dashboard, clearMessages } = useAppState();
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, asking]);

  const scope = selected
    .map((id) => sources.find((source) => source.id === id)?.label || id)
    .join(" · ");

  return (
    <>
      <div className="context-bar">
        <div>
          <h1>Assistant</h1>
          <p className="meta">
            Les chiffres viennent de Python. Le modèle reformule uniquement à partir du périmètre actif.
          </p>
        </div>
        <div className="status-pills">
          <span className="pill accent">{scope || "Aucune source"}</span>
          {dashboard?.active_filters ? (
            <span className="pill">{dashboard.active_filters} filtre(s)</span>
          ) : null}
          {messages.length ? (
            <button className="ghost" type="button" onClick={clearMessages}>
              Effacer le fil
            </button>
          ) : null}
        </div>
      </div>

      {!messages.length ? (
        <section className="card chat-empty">
          <h2>Commencez une analyse</h2>
          <p className="meta">
            Posez une question dans la barre du haut. Les suggestions accélèrent les cas les plus
            fréquents. Les réponses longues se replient automatiquement.
          </p>
          <div className="suggestion-row" style={{ marginTop: 12 }}>
            <span className="pill">Moyennes & comparaisons</span>
            <span className="pill">Produits faibles</span>
            <span className="pill">Réclamations</span>
            <span className="pill">Isolation de pays</span>
          </div>
        </section>
      ) : null}

      <div className="chat-thread">
        {messages.map((message, index) => (
          <article key={index} className={`msg ${message.role}`}>
            <div className="msg-label">{message.role === "user" ? "Vous" : "FastColis"}</div>
            <div className="msg-bubble">
              {message.role === "assistant" ? (
                <CollapsibleAnswer content={message.content} />
              ) : (
                <div className="answer">{message.content}</div>
              )}

              {message.meta?.fallback ? (
                <div className="banner warn" style={{ marginTop: 10, marginBottom: 0 }}>
                  Réponse calculée en Python (Ollama indisponible ou trop lent).
                </div>
              ) : null}
              {message.meta?.scope?.conflict && message.meta.scope.warning ? (
                <div className="banner warn" style={{ marginTop: 10, marginBottom: 0 }}>
                  {message.meta.scope.warning}
                </div>
              ) : null}

              {message.meta?.sources?.length ? (
                <div className="msg-footer">
                  <span className="pill accent">{message.meta.sources.join(" · ")}</span>
                  {message.meta.row_count != null ? (
                    <span className="pill">
                      <strong>{message.meta.row_count.toLocaleString("fr-FR")}</strong> lignes
                    </span>
                  ) : null}
                  {message.meta.model ? <span className="pill">{message.meta.model}</span> : null}
                </div>
              ) : null}

              {message.meta?.facts || message.meta?.evidence?.length ? (
                <div className="msg-tools">
                  {message.meta.facts ? (
                    <details>
                      <summary>Faits Python</summary>
                      <pre>{JSON.stringify(message.meta.facts, null, 2)}</pre>
                    </details>
                  ) : null}
                  {message.meta.evidence?.length ? (
                    <details>
                      <summary>Échantillon ({message.meta.evidence.length})</summary>
                      <div className="evidence">
                        {message.meta.evidence.map((row, rowIndex) => (
                          <pre key={rowIndex}>{JSON.stringify(row, null, 2)}</pre>
                        ))}
                      </div>
                    </details>
                  ) : null}
                </div>
              ) : null}
            </div>
          </article>
        ))}

        {asking ? (
          <div className="msg assistant">
            <div className="msg-label">FastColis</div>
            <div className="typing" aria-label="Analyse en cours">
              <span />
              <span />
              <span />
            </div>
          </div>
        ) : null}
        <div ref={endRef} />
      </div>
    </>
  );
}
