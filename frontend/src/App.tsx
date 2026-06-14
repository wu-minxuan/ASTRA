import { useEffect, useState } from "react";

type HealthState =
  | { kind: "loading" }
  | { kind: "ready"; status: string; service: string }
  | { kind: "error"; message: string };

async function fetchHealth(): Promise<{ status: string; service: string }> {
  const response = await fetch("/api/health");
  if (!response.ok) {
    throw new Error(`Health check failed with ${response.status}`);
  }
  return response.json();
}

export function App() {
  const [health, setHealth] = useState<HealthState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;

    fetchHealth()
      .then((payload) => {
        if (!cancelled) {
          setHealth({ kind: "ready", ...payload });
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "Unknown health check error";
          setHealth({ kind: "error", message });
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="app-shell">
      <section className="status-panel" aria-labelledby="app-title">
        <p className="eyebrow">Adaptive Strategy Research Agent</p>
        <h1 id="app-title">ASTRA</h1>
        <div className="health-row" aria-live="polite">
          <span className="health-label">Backend</span>
          {health.kind === "loading" ? (
            <span className="health-value muted">checking</span>
          ) : null}
          {health.kind === "ready" ? (
            <span className="health-value ok">{health.status}</span>
          ) : null}
          {health.kind === "error" ? (
            <span className="health-value error">error</span>
          ) : null}
        </div>
        {health.kind === "ready" ? (
          <p className="health-detail">Service: {health.service}</p>
        ) : null}
        {health.kind === "error" ? <p className="health-detail">{health.message}</p> : null}
      </section>
    </main>
  );
}

