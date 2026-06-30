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
  | { kind: "error"; code: string; message: string; details: Record<string, unknown> };

type ViewMode = "report" | "evidence" | "pipeline";

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
      throw new ThemeResearchApiError(
        payload.error.code,
        payload.error.message,
        payload.error.details,
      );
    }
    throw new ThemeResearchApiError("internal_error", `Request failed with ${response.status}`);
  }

  return response.json();
}

class ThemeResearchApiError extends Error {
  code: string;
  details: Record<string, unknown>;

  constructor(code: string, message: string, details: Record<string, unknown> = {}) {
    super(message);
    this.code = code;
    this.details = details;
  }
}

export function App() {
  const [health, setHealth] = useState<HealthState>({ kind: "loading" });
  const [theme, setTheme] = useState("低空经济");
  const [maxResults, setMaxResults] = useState(5);
  const [includeReport, setIncludeReport] = useState(true);
  const [research, setResearch] = useState<ResearchState>({ kind: "idle" });
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("report");

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

  const selectedCandidate = useMemo(() => {
    if (research.kind !== "ready") {
      return null;
    }
    return (
      research.response.result.pool.find((candidate) => candidate.symbol === selectedSymbol) ??
      research.response.result.pool[0] ??
      null
    );
  }, [research, selectedSymbol]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setResearch({ kind: "loading" });

    runThemeResearch({
      theme,
      max_results: maxResults,
      include_report: includeReport,
    })
      .then((response) => {
        setSelectedSymbol(response.result.pool[0]?.symbol ?? null);
        setViewMode(response.result.report ? "report" : "evidence");
        setResearch({ kind: "ready", response });
      })
      .catch((error: unknown) => {
        if (error instanceof ThemeResearchApiError) {
          setResearch({
            kind: "error",
            code: error.code,
            message: error.message,
            details: error.details,
          });
          return;
        }
        const message = error instanceof Error ? error.message : "Unknown request error";
        setResearch({ kind: "error", code: "internal_error", message, details: {} });
      });
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <p className="eyebrow">Adaptive Strategy Research Agent</p>
          <h1>ASTRA</h1>
        </div>
        <div className="system-strip">
          <HealthBadge health={health} />
          <span className="mode-chip">AKShare live</span>
          <span className="mode-chip">Fake model</span>
        </div>
      </header>

      <section className="workspace" aria-labelledby="theme-form-title">
        <aside className="control-panel">
          <form className="query-form" onSubmit={handleSubmit}>
            <div className="section-heading compact">
              <p>Research Run</p>
              <h2 id="theme-form-title">主题研究</h2>
            </div>
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

          <RunStatus research={research} />
        </aside>

        <section className="research-surface" aria-live="polite">
          {research.kind === "idle" ? <EmptyState /> : null}
          {research.kind === "loading" ? <LoadingState /> : null}
          {research.kind === "error" ? (
            <ErrorState
              code={research.code}
              message={research.message}
              details={research.details}
            />
          ) : null}
          {research.kind === "ready" ? (
            <ResearchResultView
              response={research.response}
              evidenceCount={visibleEvidenceCount}
              selectedCandidate={selectedCandidate}
              selectedSymbol={selectedSymbol}
              onSelectCandidate={setSelectedSymbol}
              viewMode={viewMode}
              onChangeViewMode={setViewMode}
            />
          ) : null}
        </section>
      </section>
    </main>
  );
}

function HealthBadge({ health }: { health: HealthState }) {
  return (
    <div className="health-row" aria-live="polite">
      <span className="health-label">Backend</span>
      {health.kind === "loading" ? <span className="health-value muted">checking</span> : null}
      {health.kind === "ready" ? <span className="health-value ok">{health.status}</span> : null}
      {health.kind === "error" ? <span className="health-value error">error</span> : null}
    </div>
  );
}

function RunStatus({ research }: { research: ResearchState }) {
  const label =
    research.kind === "ready"
      ? "完成"
      : research.kind === "loading"
        ? "运行中"
        : research.kind === "error"
          ? "错误"
          : "待运行";
  return (
    <div className={`run-status ${research.kind}`}>
      <span className="status-light" />
      <div>
        <strong>{label}</strong>
        <p>
          {research.kind === "ready"
            ? "研究结果已生成"
            : research.kind === "error"
              ? research.code
              : "Phase 1 research funnel"}
        </p>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="empty-state">
      <div className="empty-plate">
        <span className="empty-mark">ASTRA</span>
        <strong>等待研究请求</strong>
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="loading-state">
      <div className="skeleton-line wide" />
      <div className="skeleton-grid">
        <div className="skeleton-tile" />
        <div className="skeleton-tile" />
        <div className="skeleton-tile" />
      </div>
      <div className="skeleton-table" />
    </div>
  );
}

function ErrorState({
  code,
  message,
  details,
}: {
  code: string;
  message: string;
  details: Record<string, unknown>;
}) {
  const detailEntries = Object.entries(details).filter(([, value]) => {
    if (value === null || value === undefined || value === "") {
      return false;
    }
    return !Array.isArray(value) || value.length > 0;
  });

  return (
    <div className="error-state" role="alert">
      <span className="error-code">{code}</span>
      <strong>{message}</strong>
      {detailEntries.length > 0 ? (
        <dl className="error-details">
          {detailEntries.slice(0, 6).map(([key, value]) => (
            <div key={key}>
              <dt>{key}</dt>
              <dd>{formatDetailValue(value)}</dd>
            </div>
          ))}
        </dl>
      ) : null}
    </div>
  );
}

function formatDetailValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.slice(0, 4).map(formatDetailValue).join(" | ");
  }
  if (typeof value === "object" && value !== null) {
    return JSON.stringify(value);
  }
  return String(value);
}

function ResearchResultView({
  response,
  evidenceCount,
  selectedCandidate,
  selectedSymbol,
  onSelectCandidate,
  viewMode,
  onChangeViewMode,
}: {
  response: ThemeResearchResponse;
  evidenceCount: number;
  selectedCandidate: CandidateStock | null;
  selectedSymbol: string | null;
  onSelectCandidate: (symbol: string) => void;
  viewMode: ViewMode;
  onChangeViewMode: (mode: ViewMode) => void;
}) {
  const { result } = response;
  const topCandidate = result.pool[0] ?? null;
  const averageScore =
    result.pool.length > 0
      ? result.pool.reduce((total, candidate) => total + candidate.scores.final_score, 0) /
        result.pool.length
      : 0;

  return (
    <div className="result-workbench">
      <section className="summary-band" aria-label="研究摘要">
        <div className="section-heading">
          <p>Theme</p>
          <h2>{response.request.normalized_query}</h2>
        </div>
        <div className="summary-metrics">
          <Metric label="As of" value={result.as_of} />
          <Metric label="股票池" value={String(result.pool.length)} />
          <Metric label="证据" value={String(evidenceCount)} />
          <Metric label="均分" value={averageScore.toFixed(1)} />
        </div>
        {topCandidate ? (
          <div className="top-pick">
            <span>Top ranked</span>
            <strong>
              {topCandidate.name} · {topCandidate.symbol}
            </strong>
          </div>
        ) : null}
      </section>

      <section className="pool-band" aria-labelledby="pool-title">
        <div className="section-heading inline">
          <div>
            <p>Ranked Pool</p>
            <h2 id="pool-title">股票池</h2>
          </div>
          <span className="data-badge">cn_a</span>
        </div>
        <StockPoolTable
          candidates={result.pool}
          selectedSymbol={selectedSymbol}
          onSelectCandidate={onSelectCandidate}
        />
      </section>

      <div className="detail-layout">
        <section className="detail-band" aria-label="重点公司">
          <div className="section-heading">
            <p>Focused Company</p>
            <h2>{selectedCandidate?.name ?? "重点公司"}</h2>
          </div>
          {selectedCandidate ? <CandidateDetail candidate={selectedCandidate} /> : null}
        </section>

        <section className="report-band" aria-label="研究详情">
          <SegmentedControl value={viewMode} onChange={onChangeViewMode} />
          {viewMode === "report" ? (
            result.report ? <ReportView report={result.report} /> : <ReportOmitted />
          ) : null}
          {viewMode === "evidence" ? (
            <EvidenceBoundaryView
              candidate={selectedCandidate}
              warnings={result.warnings}
              dataBoundary={result.data_boundary}
            />
          ) : null}
          {viewMode === "pipeline" ? <PipelineView stages={result.pipeline} /> : null}
        </section>
      </div>
    </div>
  );
}

function StockPoolTable({
  candidates,
  selectedSymbol,
  onSelectCandidate,
}: {
  candidates: CandidateStock[];
  selectedSymbol: string | null;
  onSelectCandidate: (symbol: string) => void;
}) {
  return (
    <div className="table-wrap">
      <table className="pool-table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>股票</th>
            <th>行业/概念</th>
            <th>Final</th>
            <th>Coarse</th>
            <th>风险</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {candidates.map((candidate) => (
            <tr
              className={candidate.symbol === selectedSymbol ? "selected" : ""}
              key={candidate.symbol}
            >
              <td>
                <span className="rank-pill">#{candidate.rank}</span>
              </td>
              <td>
                <strong>{candidate.name}</strong>
                <span>
                  {candidate.symbol} · {candidate.exchange}
                </span>
              </td>
              <td>
                <span className="industry-text">{candidate.industry}</span>
                <div className="tag-row">
                  {candidate.concepts.slice(0, 3).map((concept) => (
                    <span key={`${candidate.symbol}-${concept}`}>{concept}</span>
                  ))}
                </div>
              </td>
              <td>
                <ScoreMeter value={candidate.scores.final_score} />
              </td>
              <td>{candidate.scores.coarse_score.toFixed(0)}</td>
              <td className="risk-cell">{candidate.key_risks[0]}</td>
              <td>
                <button
                  className="row-action"
                  type="button"
                  onClick={() => onSelectCandidate(candidate.symbol)}
                >
                  查看
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CandidateDetail({ candidate }: { candidate: CandidateStock }) {
  return (
    <div className="candidate-detail">
      <div className="candidate-title-row">
        <div>
          <strong>{candidate.symbol}</strong>
          <span>{candidate.exchange}</span>
        </div>
        <span className="score-chip">{candidate.scores.final_score.toFixed(1)}</span>
      </div>
      <p className="selection-reason">{candidate.selection_reason}</p>
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
      <div className="risk-list">
        {candidate.key_risks.map((risk) => (
          <p key={risk}>{risk}</p>
        ))}
      </div>
    </div>
  );
}

function ReportView({ report }: { report: ResearchReport }) {
  return (
    <div className="report-view">
      <div className="section-heading">
        <p>Research Brief</p>
        <h2>{report.title}</h2>
      </div>
      <p className="report-summary">{report.summary}</p>
      <div className="brief-grid">
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
      <p className="advice-note">{report.not_investment_advice}</p>
    </div>
  );
}

function ReportOmitted() {
  return (
    <div className="report-view">
      <div className="section-heading">
        <p>Research Brief</p>
        <h2>研究报告</h2>
      </div>
      <p className="report-summary">未请求报告生成。</p>
    </div>
  );
}

function EvidenceBoundaryView({
  candidate,
  warnings,
  dataBoundary,
}: {
  candidate: CandidateStock | null;
  warnings: string[];
  dataBoundary: string[];
}) {
  return (
    <div className="evidence-view">
      <div className="section-heading">
        <p>Evidence</p>
        <h2>证据与边界</h2>
      </div>
      <div className="evidence-list">
        {(candidate?.evidence ?? []).slice(0, 6).map((item) => (
          <article className="evidence-item" key={item.id}>
            <div>
              <strong>{item.kind}</strong>
              <span>{item.source_name}</span>
            </div>
            <p>{item.summary}</p>
          </article>
        ))}
      </div>
      <BoundaryList title="数据边界" items={dataBoundary} />
      <BoundaryList title="Warnings" items={warnings} />
    </div>
  );
}

function PipelineView({ stages }: { stages: PipelineStage[] }) {
  return (
    <div className="pipeline-view">
      <div className="section-heading">
        <p>Trace</p>
        <h2>Pipeline</h2>
      </div>
      <div className="pipeline-list">
        {stages.map((stage, index) => (
          <article className="pipeline-item" key={stage.stage}>
            <span className="stage-index">{String(index + 1).padStart(2, "0")}</span>
            <div>
              <strong>{stage.stage}</strong>
              <p>
                {stage.input_count} → {stage.output_count}
              </p>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function BoundaryList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) {
    return null;
  }
  return (
    <section className="boundary-list">
      <h3>{title}</h3>
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

function SegmentedControl({
  value,
  onChange,
}: {
  value: ViewMode;
  onChange: (mode: ViewMode) => void;
}) {
  const options: { label: string; value: ViewMode }[] = [
    { label: "报告", value: "report" },
    { label: "证据", value: "evidence" },
    { label: "流程", value: "pipeline" },
  ];
  return (
    <div className="segmented-control" role="tablist" aria-label="研究详情视图">
      {options.map((option) => (
        <button
          aria-selected={value === option.value}
          className={value === option.value ? "active" : ""}
          key={option.value}
          onClick={() => onChange(option.value)}
          role="tab"
          type="button"
        >
          {option.label}
        </button>
      ))}
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

function ScoreMeter({ value }: { value: number }) {
  const width = `${Math.max(0, Math.min(100, value))}%`;
  return (
    <div className="score-meter">
      <span>{value.toFixed(1)}</span>
      <div>
        <i style={{ width }} />
      </div>
    </div>
  );
}
