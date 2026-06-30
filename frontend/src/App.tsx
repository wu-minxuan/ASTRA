import { FormEvent, useEffect, useMemo, useState } from "react";

type HealthState =
  | { kind: "loading" }
  | { kind: "ready"; status: string; service: string }
  | { kind: "error"; message: string };

type PipelineStage = {
  stage: string;
  input_count: number;
  output_count: number;
  notes: string[];
};

type EvidenceItem = {
  id: string;
  kind: string;
  stance: string;
  summary: string;
  source_name: string;
  source_type: string;
  confidence: string;
};

type CandidateStock = {
  symbol: string;
  name: string;
  exchange: string;
  industry: string;
  concepts: string[];
  recall_sources: string[];
  evidence: EvidenceItem[];
  scores: {
    recall_score: number;
    coarse_score: number;
    final_score: number;
  };
  rank: number | null;
  selection_reason: string;
  key_risks: string[];
};

type FocusCompany = {
  symbol: string;
  name: string;
  reason: string;
  supporting_evidence_ids: string[];
  risks: string[];
};

type ResearchReport = {
  title: string;
  summary: string;
  theme_overview: string;
  pool_summary: string;
  focus_companies: FocusCompany[];
  risks: string[];
  data_boundary: string;
  not_investment_advice: string;
};

type ThemeResearchResponse = {
  contract_version: "phase1.v1";
  request: {
    theme: string;
    normalized_query: string;
    market: "cn_a";
    max_results: number;
    include_report: boolean;
  };
  result: {
    as_of: string;
    pool: CandidateStock[];
    report: ResearchReport | null;
    pipeline: PipelineStage[];
    data_boundary: string[];
    warnings: string[];
  };
};

type ThemeResearchErrorResponse = {
  contract_version: "phase1.v1";
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  };
};

type ResearchState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ready"; response: ThemeResearchResponse }
  | { kind: "error"; code: string; message: string };

async function fetchHealth(): Promise<{ status: string; service: string }> {
  const response = await fetch("/api/health");
  if (!response.ok) {
    throw new Error(`Health check failed with ${response.status}`);
  }
  return response.json();
}

async function runThemeResearch(request: {
  theme: string;
  max_results: number;
  include_report: boolean;
}): Promise<ThemeResearchResponse> {
  const response = await fetch("/api/theme-research", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      theme: request.theme,
      market: "cn_a",
      max_results: request.max_results,
      include_report: request.include_report,
    }),
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as
      | ThemeResearchErrorResponse
      | null;
    if (payload?.error) {
      throw new ThemeResearchApiError(payload.error.code, payload.error.message);
    }
    throw new ThemeResearchApiError("internal_error", `Request failed with ${response.status}`);
  }

  return response.json();
}

class ThemeResearchApiError extends Error {
  code: string;

  constructor(code: string, message: string) {
    super(message);
    this.code = code;
  }
}

export function App() {
  const [health, setHealth] = useState<HealthState>({ kind: "loading" });
  const [theme, setTheme] = useState("低空经济");
  const [maxResults, setMaxResults] = useState(5);
  const [includeReport, setIncludeReport] = useState(true);
  const [research, setResearch] = useState<ResearchState>({ kind: "idle" });

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

  const visibleEvidenceCount = useMemo(() => {
    if (research.kind !== "ready") {
      return 0;
    }
    return research.response.result.pool.reduce(
      (total, candidate) => total + candidate.evidence.length,
      0,
    );
  }, [research]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setResearch({ kind: "loading" });

    runThemeResearch({
      theme,
      max_results: maxResults,
      include_report: includeReport,
    })
      .then((response) => {
        setResearch({ kind: "ready", response });
      })
      .catch((error: unknown) => {
        if (error instanceof ThemeResearchApiError) {
          setResearch({ kind: "error", code: error.code, message: error.message });
          return;
        }
        const message = error instanceof Error ? error.message : "Unknown request error";
        setResearch({ kind: "error", code: "internal_error", message });
      });
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Adaptive Strategy Research Agent</p>
          <h1>ASTRA</h1>
        </div>
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
          {health.kind === "ready" ? (
            <span className="health-detail">Service: {health.service}</span>
          ) : null}
        </div>
      </header>

      <section className="workbench" aria-labelledby="theme-form-title">
        <form className="query-panel" onSubmit={handleSubmit}>
          <h2 id="theme-form-title">主题研究</h2>
          <label className="field">
            <span>主题</span>
            <input
              value={theme}
              onChange={(event) => setTheme(event.target.value)}
              maxLength={40}
              autoComplete="off"
            />
          </label>
          <div className="form-row">
            <label className="field">
              <span>结果数</span>
              <input
                type="number"
                value={maxResults}
                min={1}
                max={10}
                onChange={(event) => setMaxResults(Number(event.target.value))}
              />
            </label>
            <label className="toggle-row">
              <input
                type="checkbox"
                checked={includeReport}
                onChange={(event) => setIncludeReport(event.target.checked)}
              />
              <span>研究报告</span>
            </label>
          </div>
          <button className="primary-action" type="submit" disabled={research.kind === "loading"}>
            {research.kind === "loading" ? "运行中" : "运行研究"}
          </button>
        </form>

        <section className="result-panel" aria-live="polite">
          {research.kind === "idle" ? <EmptyState /> : null}
          {research.kind === "loading" ? <LoadingState /> : null}
          {research.kind === "error" ? (
            <ErrorState code={research.code} message={research.message} />
          ) : null}
          {research.kind === "ready" ? (
            <ResearchResultView response={research.response} evidenceCount={visibleEvidenceCount} />
          ) : null}
        </section>
      </section>
    </main>
  );
}

function EmptyState() {
  return (
    <div className="empty-state">
      <span className="status-dot" />
      <p>等待研究请求</p>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="loading-state">
      <div className="loading-bar" />
      <div className="loading-bar short" />
      <div className="loading-bar" />
    </div>
  );
}

function ErrorState({ code, message }: { code: string; message: string }) {
  return (
    <div className="error-state" role="alert">
      <strong>{code}</strong>
      <p>{message}</p>
    </div>
  );
}

function ResearchResultView({
  response,
  evidenceCount,
}: {
  response: ThemeResearchResponse;
  evidenceCount: number;
}) {
  const { result } = response;

  return (
    <div className="result-grid">
      <div className="metric-row">
        <Metric label="As of" value={result.as_of} />
        <Metric label="Pool" value={String(result.pool.length)} />
        <Metric label="Evidence" value={String(evidenceCount)} />
      </div>

      <section className="stock-section" aria-labelledby="pool-title">
        <h2 id="pool-title">股票池</h2>
        <div className="stock-list">
          {result.pool.map((candidate) => (
            <article className="stock-card" key={candidate.symbol}>
              <div className="stock-card-header">
                <span className="rank">#{candidate.rank}</span>
                <div>
                  <h3>{candidate.name}</h3>
                  <p>
                    {candidate.symbol} · {candidate.exchange}
                  </p>
                </div>
                <span className="score">{candidate.scores.final_score.toFixed(1)}</span>
              </div>
              <p className="selection-reason">{candidate.selection_reason}</p>
              <div className="tag-row">
                <span>{candidate.industry}</span>
                {candidate.concepts.slice(0, 3).map((concept) => (
                  <span key={`${candidate.symbol}-${concept}`}>{concept}</span>
                ))}
              </div>
              <dl className="score-grid">
                <div>
                  <dt>Recall</dt>
                  <dd>{candidate.scores.recall_score.toFixed(0)}</dd>
                </div>
                <div>
                  <dt>Coarse</dt>
                  <dd>{candidate.scores.coarse_score.toFixed(0)}</dd>
                </div>
                <div>
                  <dt>Evidence</dt>
                  <dd>{candidate.evidence.length}</dd>
                </div>
              </dl>
              <p className="risk-line">{candidate.key_risks[0]}</p>
            </article>
          ))}
        </div>
      </section>

      {result.report ? <ReportView report={result.report} /> : <ReportOmitted />}

      <section className="pipeline-section" aria-labelledby="pipeline-title">
        <h2 id="pipeline-title">Pipeline</h2>
        <div className="pipeline-list">
          {result.pipeline.map((stage) => (
            <div className="pipeline-item" key={stage.stage}>
              <span>{stage.stage}</span>
              <strong>
                {stage.input_count} → {stage.output_count}
              </strong>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ReportView({ report }: { report: ResearchReport }) {
  return (
    <section className="report-section" aria-labelledby="report-title">
      <h2 id="report-title">{report.title}</h2>
      <p className="report-summary">{report.summary}</p>
      <div className="report-columns">
        <section>
          <h3>主题概述</h3>
          <p>{report.theme_overview}</p>
        </section>
        <section>
          <h3>股票池摘要</h3>
          <p>{report.pool_summary}</p>
        </section>
      </div>
      <div className="focus-list">
        {report.focus_companies.map((company) => (
          <article className="focus-item" key={company.symbol}>
            <h3>
              {company.name} <span>{company.symbol}</span>
            </h3>
            <p>{company.reason}</p>
            <small>{company.risks[0]}</small>
          </article>
        ))}
      </div>
      <div className="boundary-block">
        <strong>数据边界</strong>
        <p>{report.data_boundary}</p>
      </div>
      <p className="advice-note">{report.not_investment_advice}</p>
    </section>
  );
}

function ReportOmitted() {
  return (
    <section className="report-section" aria-labelledby="report-omitted-title">
      <h2 id="report-omitted-title">研究报告</h2>
      <p className="report-summary">未请求报告生成。</p>
    </section>
  );
}
