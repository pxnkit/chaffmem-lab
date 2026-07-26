"use client";

import {
  useEffect,
  useMemo,
  useState,
  type KeyboardEvent,
} from "react";
import {
  attackLabels,
  defaultConfig,
  defenseLabels,
  domainLabels,
  knowledgeLabels,
  policyLabels,
  resultToCsv,
  runComparison,
  runSimulation,
  type AttackStrategy,
  type DefenseStrategy,
  type Domain,
  type ExperimentConfig,
  type KnowledgeLevel,
  type MemoryPoint,
  type MemoryPolicy,
  type MemoryStepState,
  type RetrievalQuery,
  type RunResult,
  type TraceDecision,
  type TrajectoryPoint,
} from "./simulator";

type ViewId = "map" | "trajectory" | "comparison" | "trace" | "evidence";

const viewLabels: Record<ViewId, string> = {
  map: "Memory map",
  trajectory: "Trajectory",
  comparison: "Comparison",
  trace: "Trace inspector",
  evidence: "Evidence",
};

const colorByKind: Record<MemoryPoint["kind"], string> = {
  critical: "var(--critical)",
  background: "var(--background-point)",
  chaff: "var(--chaff)",
};

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function rankLabel(rank: number | null) {
  return rank === null ? "Not stored" : `#${rank}`;
}

function download(name: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  URL.revokeObjectURL(url);
}

function SelectField<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: Record<T, string>;
  onChange: (value: T) => void;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value as T)}>
        {Object.entries(options).map(([optionValue, optionLabel]) => (
          <option key={optionValue} value={optionValue}>
            {String(optionLabel)}
          </option>
        ))}
      </select>
    </label>
  );
}

function NumberField({
  label,
  value,
  min,
  max,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}

function Metric({
  label,
  value,
  note,
  tone = "default",
}: {
  label: string;
  value: string;
  note: string;
  tone?: "default" | "good" | "warn";
}) {
  return (
    <article className={`metric metric-${tone}`}>
      <p>{label}</p>
      <strong>{value}</strong>
      <span>{note}</span>
    </article>
  );
}

function MemoryMap({
  points,
  visibleStep,
  stepState,
  query,
  selectedId,
  onSelect,
}: {
  points: MemoryPoint[];
  visibleStep: number;
  stepState: MemoryStepState;
  query: RetrievalQuery;
  selectedId: string | null;
  onSelect: (point: MemoryPoint) => void;
}) {
  const retainedIds = new Set(stepState.retainedIds);
  const pointRank = (point: MemoryPoint) => stepState.ranks[point.id] ?? null;
  const visible = points.filter(
    (point) => point.createdAt <= visibleStep || point.kind === "critical",
  );
  const selected = visible.find((point) => point.id === selectedId) ?? visible[0];

  return (
    <div className="memory-layout">
      <section className="memory-canvas" aria-label="Two-dimensional toy retrieval space">
        <div className="axis-label axis-x">Retrieval feature 1</div>
        <div className="axis-label axis-y">Retrieval feature 2</div>
        <div className="projection-note">
          Toy distance space used directly for ranking
        </div>
        {visible.map((point) => (
          <button
            key={point.id}
            type="button"
            className={`memory-point ${retainedIds.has(point.id) ? "" : "memory-point-evicted"} ${
              selected?.id === point.id ? "memory-point-selected" : ""
            }`}
            style={{
              left: `${point.x}%`,
              top: `${100 - point.y}%`,
              width: "24px",
              height: "24px",
              border: 0,
              background: `radial-gradient(circle, ${colorByKind[point.kind]} 0 5px, var(--surface) 6px 7px, transparent 8px)`,
            }}
            aria-label={`${point.kind} record ${point.id}, rank ${rankLabel(pointRank(point))}`}
            title={`${point.id}: ${point.content}`}
            onClick={() => onSelect(point)}
          />
        ))}
        <div
          className="target-ring"
          style={{ left: `${query.x}%`, top: `${100 - query.y}%` }}
          role="img"
          aria-label={`Retrieval query marker: ${query.text}`}
          title={`Retrieval query: ${query.text}`}
        />
      </section>

      <aside className="point-detail" aria-live="polite">
        {selected ? (
          <>
            <div className="eyebrow">Selected record</div>
            <h3>{selected.id}</h3>
            <p>{selected.content}</p>
            <dl className="detail-grid">
              <div>
                <dt>Type</dt>
                <dd>{selected.kind}</dd>
              </div>
              <div>
                <dt>Origin</dt>
                <dd>{selected.origin}</dd>
              </div>
              <div>
                <dt>Cell</dt>
                <dd>{selected.cell}</dd>
              </div>
              <div>
                <dt>Rank</dt>
                <dd>{rankLabel(pointRank(selected))}</dd>
              </div>
              <div>
                <dt>Importance</dt>
                <dd>{selected.importance.toFixed(2)}</dd>
              </div>
              <div>
                <dt>Store state</dt>
                <dd>{retainedIds.has(selected.id) ? "Retained" : "Evicted"}</dd>
              </div>
            </dl>
          </>
        ) : null}
        <div className="legend" aria-label="Memory point legend">
          <span><i className="dot dot-critical" /> Critical target</span>
          <span><i className="dot dot-chaff" /> Benign chaff</span>
          <span><i className="dot dot-background" /> Background</span>
          <span><i className="dot dot-evicted" /> Evicted</span>
          <span>◎ Retrieval query</span>
        </div>
        <details className="memory-table-wrap">
          <summary>Open precise table ({visible.length})</summary>
          <div>
            <table>
              <caption>Records visible at write {visibleStep}</caption>
              <thead>
                <tr>
                  <th scope="col">Record</th>
                  <th scope="col">Type</th>
                  <th scope="col">Rank</th>
                  <th scope="col">State</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((point) => (
                  <tr key={point.id}>
                    <th scope="row">{point.id}</th>
                    <td>{point.kind}</td>
                    <td>{rankLabel(pointRank(point))}</td>
                    <td>{retainedIds.has(point.id) ? "Retained" : "Evicted"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </aside>
    </div>
  );
}

function linePoints(
  trajectory: TrajectoryPoint[],
  getter: (point: TrajectoryPoint) => number,
) {
  const maxStep = Math.max(1, trajectory[trajectory.length - 1]?.step ?? 1);
  return trajectory
    .map((point) => {
      const x = 46 + (point.step / maxStep) * 674;
      const y = 24 + (1 - getter(point)) * 226;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
}

function TrajectoryChart({ trajectory }: { trajectory: TrajectoryPoint[] }) {
  const last = trajectory[trajectory.length - 1];
  return (
    <div className="chart-wrap">
      <div className="chart-summary">
        <div>
          <span>Current write</span>
          <strong>{last?.step ?? 0}</strong>
        </div>
        <div>
          <span>Critical recall</span>
          <strong>{last ? percent(last.recall) : "0%"}</strong>
        </div>
        <div>
          <span>Heuristic alert score</span>
          <strong>{last ? percent(last.alertScore) : "0%"}</strong>
        </div>
      </div>
      <svg
        className="trajectory-chart"
        viewBox="0 0 760 292"
        role="img"
        aria-labelledby="trajectory-title trajectory-description"
      >
        <title id="trajectory-title">Availability over attack writes</title>
        <desc id="trajectory-description">
          Critical recall and a heuristic crowding score from zero to the current write
        </desc>
        {[0, 0.25, 0.5, 0.75, 1].map((tick) => {
          const y = 24 + (1 - tick) * 226;
          return (
            <g key={tick}>
              <line x1="46" x2="720" y1={y} y2={y} className="grid-line" />
              <text x="36" y={y + 4} textAnchor="end" className="axis-tick">
                {Math.round(tick * 100)}
              </text>
            </g>
          );
        })}
        <line x1="46" x2="720" y1="250" y2="250" className="axis-line" />
        <line x1="46" x2="46" y1="24" y2="250" className="axis-line" />
        <polyline
          points={linePoints(trajectory, (point) => point.recall)}
          className="chart-line chart-recall"
        />
        <polyline
          points={linePoints(trajectory, (point) => point.alertScore)}
          className="chart-line chart-alert"
        />
        <text x="383" y="280" textAnchor="middle" className="axis-title">
          Accepted and rejected writes
        </text>
        <text x="8" y="140" textAnchor="middle" className="axis-title axis-title-y">
          Percent
        </text>
      </svg>
      <div className="chart-legend">
        <span><i className="line-key line-key-recall" /> Critical Recall@k</span>
        <span><i className="line-key line-key-alert" /> Heuristic crowding alert</span>
      </div>
    </div>
  );
}

function ComparisonView({
  arms,
}: {
  arms: ReturnType<typeof runComparison>;
}) {
  const bestRecall = Math.max(...arms.map((arm) => arm.metrics.criticalRecall));
  return (
    <div className="comparison-grid">
      {arms.map((arm) => (
        <article className="comparison-card" key={arm.id}>
          <div className="comparison-head">
            <div>
              <span>{arm.description}</span>
              <h3>{arm.label}</h3>
            </div>
            {arm.metrics.criticalRecall === bestRecall ? (
              <span className="best-badge">Highest observed</span>
            ) : null}
          </div>
          <div className="comparison-score">
            <strong>{percent(arm.metrics.criticalRecall)}</strong>
            <span>trajectory recall</span>
          </div>
          <dl className="comparison-details">
            <div>
              <dt>Final rank</dt>
              <dd>{rankLabel(arm.metrics.finalTargetRank)}</dd>
            </div>
            <div>
              <dt>Failure write</dt>
              <dd>{arm.metrics.writesToFailure ?? "None"}</dd>
            </div>
            <div>
              <dt>Physical</dt>
              <dd>{percent(arm.metrics.physicalAvailability)}</dd>
            </div>
            <div>
              <dt>Rejected</dt>
              <dd>{arm.metrics.rejectedWrites}</dd>
            </div>
          </dl>
          <div className="mini-trajectory" aria-hidden="true">
            {arm.trajectory.map((point) => (
              <i
                key={point.step}
                style={{
                  height: `${Math.max(8, point.recall * 100)}%`,
                  opacity: 0.28 + point.alertScore * 0.62,
                }}
              />
            ))}
          </div>
        </article>
      ))}
      <div className="comparison-note">
        <strong>Controlled comparison</strong>
        <p>
          Every arm reuses the same pre-generated candidate traffic, query budget,
          policy, and purpose-keyed random draws. Storage controls are labeled
          separately and are not retrieval upper bounds.
        </p>
      </div>
    </div>
  );
}

function TraceInspector({
  trace,
  selected,
  onSelect,
}: {
  trace: TraceDecision[];
  selected: TraceDecision | null;
  onSelect: (decision: TraceDecision) => void;
}) {
  return (
    <div className="trace-layout">
      <div className="trace-list" role="list" aria-label="Experiment decisions">
        {trace.map((event) => (
          <div role="listitem" key={event.id}>
            <button
            type="button"
            className={`trace-row ${selected?.id === event.id ? "trace-row-active" : ""}`}
            onClick={() => onSelect(event)}
          >
            <span className={`trace-kind trace-kind-${event.kind}`}>{event.kind}</span>
            <span className="trace-main">
              <strong>{event.title}</strong>
              <small>Write {event.step} · {event.recordId ?? "query result"}</small>
            </span>
            <code>{event.hash}</code>
            </button>
          </div>
        ))}
      </div>
      <aside className="trace-detail">
        {selected ? (
          <>
            <div className="eyebrow">Decision {selected.id}</div>
            <h3>{selected.title}</h3>
            <p>{selected.reason}</p>
            <dl className="detail-grid">
              <div>
                <dt>Step</dt>
                <dd>{selected.step}</dd>
              </div>
              <div>
                <dt>Candidate set</dt>
                <dd>{selected.candidateCount}</dd>
              </div>
              <div>
                <dt>Target rank</dt>
                <dd>{rankLabel(selected.targetRank)}</dd>
              </div>
              <div>
                <dt>Record</dt>
                <dd>{selected.recordId ?? "None"}</dd>
              </div>
            </dl>
            <div className="hash-chain">
              <span>Previous hash</span>
              <code>{selected.previousHash}</code>
              <span>Event hash</span>
              <code>{selected.hash}</code>
            </div>
          </>
        ) : null}
      </aside>
    </div>
  );
}

function EvidenceView({ result }: { result: RunResult }) {
  const claims = [
    {
      status: "Observed",
      title: "This configuration has a measurable availability trajectory",
      detail: `${result.config.budget} deterministic writes produced ${percent(
        result.metrics.criticalRecall,
      )} critical Recall@k in the toy distance engine`,
    },
    {
      status: "Implemented",
      title: "Retrieval and physical availability are separated",
      detail:
        "The run records whether the target exists, where it ranks, and whether it enters a fixed three-record downstream read window",
    },
    {
      status: "Implemented",
      title: "Every decision is checksum chained",
      detail: `The final deterministic trace checksum is ${result.digest}`,
    },
    {
      status: "Untested",
      title: "No cross-model or production-system conclusion",
      detail:
        "The live demo is a deterministic research model. Full statistical claims require the repository benchmark suite",
    },
  ];

  return (
    <div className="evidence-layout">
      <section>
        <div className="section-kicker">Claim registry</div>
        <h3>Evidence before conclusion</h3>
        <p className="section-copy">
          The interface labels implemented behavior, observed outputs, and untested
          hypotheses separately. A visual result is not treated as a paper claim.
        </p>
        <div className="claim-list">
          {claims.map((claim) => (
            <article key={claim.title}>
              <span className={`claim-status claim-${claim.status.toLowerCase()}`}>
                {claim.status}
              </span>
              <div>
                <h4>{claim.title}</h4>
                <p>{claim.detail}</p>
              </div>
            </article>
          ))}
        </div>
      </section>
      <aside className="evidence-aside">
        <div className="eyebrow">Safety boundary</div>
        <h3>Local, benign, auditable</h3>
        <ul>
          <li>No hosted assistant or third-party target</li>
          <li>No prompt injection or executable payload</li>
          <li>No paid model or external API dependency</li>
          <li>Fixed write budget and deterministic seed</li>
          <li>Gold-target storage controls are labeled explicitly</li>
        </ul>
        <div className="manifest-card">
          <span>Run manifest</span>
          <code>{result.runId}</code>
          <small>Schema v1 · seed {result.config.seed} · checksum {result.digest}</small>
        </div>
      </aside>
    </div>
  );
}

export default function Explorer() {
  const [config, setConfig] = useState<ExperimentConfig>(defaultConfig);
  const [result, setResult] = useState<RunResult>(() =>
    runSimulation(defaultConfig),
  );
  const [visibleStep, setVisibleStep] = useState(defaultConfig.budget);
  const [playing, setPlaying] = useState(false);
  const [activeView, setActiveView] = useState<ViewId>("map");
  const [selectedPointId, setSelectedPointId] = useState<string | null>(
    "critical-target",
  );
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);

  const comparison = useMemo(
    () => (activeView === "comparison" ? runComparison(result.config) : []),
    [activeView, result.config],
  );
  const visibleTrajectory = result.trajectory.filter(
    (point) => point.step <= visibleStep,
  );
  const visibleTrace = result.trace.filter((event) => event.step <= visibleStep);
  const selectedTrace =
    visibleTrace.find((event) => event.id === selectedTraceId) ??
    visibleTrace[visibleTrace.length - 1] ??
    null;
  const current =
    visibleTrajectory[visibleTrajectory.length - 1] ?? result.trajectory[0];
  const currentMemoryState =
    result.states.find((state) => state.step === current.step) ??
    result.states[0];

  useEffect(() => {
    if (!playing || visibleStep >= result.config.budget) return;
    const timer = window.setTimeout(() => {
      const nextStep = Math.min(result.config.budget, visibleStep + 1);
      setVisibleStep(nextStep);
      if (nextStep >= result.config.budget) setPlaying(false);
    }, 85);
    return () => window.clearTimeout(timer);
  }, [playing, result.config.budget, visibleStep]);

  function updateConfig<K extends keyof ExperimentConfig>(
    key: K,
    value: ExperimentConfig[K],
  ) {
    setConfig((currentConfig) => ({ ...currentConfig, [key]: value }));
  }

  function runExperiment() {
    const nextResult = runSimulation(config);
    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    setResult(nextResult);
    setSelectedPointId("critical-target");
    setSelectedTraceId(null);
    setVisibleStep(reduceMotion ? nextResult.config.budget : 0);
    setPlaying(!reduceMotion && nextResult.config.budget > 0);
  }

  function togglePlayback() {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setVisibleStep(result.config.budget);
      setPlaying(false);
      return;
    }
    setPlaying((value) => !value);
  }

  function handleTabKeyDown(
    event: KeyboardEvent<HTMLButtonElement>,
    view: ViewId,
  ) {
    const views = Object.keys(viewLabels) as ViewId[];
    const currentIndex = views.indexOf(view);
    let nextIndex: number | null = null;
    if (event.key === "ArrowRight") {
      nextIndex = (currentIndex + 1) % views.length;
    } else if (event.key === "ArrowLeft") {
      nextIndex = (currentIndex - 1 + views.length) % views.length;
    } else if (event.key === "Home") {
      nextIndex = 0;
    } else if (event.key === "End") {
      nextIndex = views.length - 1;
    }
    if (nextIndex === null) return;
    event.preventDefault();
    const nextView = views[nextIndex];
    setActiveView(nextView);
    window.requestAnimationFrame(() => {
      document.getElementById(`view-tab-${nextView}`)?.focus();
    });
  }

  const availabilityTone =
    current.recall === 1 ? "good" : current.physical === 1 ? "warn" : "warn";

  return (
    <main>
      <header className="site-header">
        <a className="brand" href="#top" aria-label="ChaffMem Lab home">
          <span className="brand-mark">CM</span>
          <span>
            <strong>ChaffMem Lab</strong>
            <small>Memory availability research</small>
          </span>
        </a>
        <nav aria-label="Primary navigation">
          <a href="#experiment">Experiment</a>
          <a href="#method">Method</a>
          <a href="#status">Research status</a>
        </nav>
        <a className="header-action" href="https://github.com/pxnkit/chaffmem-lab">
          View source
        </a>
      </header>

      <section className="hero" id="top">
        <div className="hero-copy">
          <div className="eyebrow">Research instrument 01 · deterministic reference model</div>
          <h1>
            Measure when agent memory
            <span>stops being available</span>
          </h1>
          <p>
            ChaffMem Lab tests whether one important, true memory remains stored,
            retrievable, and available to a bounded downstream reader while a
            bounded memory receives harmless but targeted records.
          </p>
          <div className="hero-actions">
            <a href="#experiment" className="button button-primary">
              Configure an experiment
            </a>
            <button
              type="button"
              className="button button-quiet"
              onClick={() => {
                setActiveView("evidence");
                document.getElementById("results")?.scrollIntoView({ behavior: "smooth" });
              }}
            >
              Inspect evidence boundary
            </button>
          </div>
          <div className="hero-badges">
            <span>CPU only</span>
            <span>No external APIs</span>
            <span>Checksum-chained traces</span>
            <span>Benign fixtures</span>
          </div>
        </div>
        <div className="hero-instrument" aria-label="Example availability monitor">
          <div className="instrument-top">
            <div>
              <span>Reference episode</span>
              <strong>{result.runId}</strong>
            </div>
            <span className={`live-state ${playing ? "live-state-running" : ""}`}>
              {playing ? "Running" : "Ready"}
            </span>
          </div>
          <div className="instrument-orbit">
            <div className="orbit orbit-one" />
            <div className="orbit orbit-two" />
            <div className="orbit orbit-three" />
            <i className="orb orb-target" />
            <i className="orb orb-a" />
            <i className="orb orb-b" />
            <i className="orb orb-c" />
            <div className="instrument-readout">
              <span>Critical Recall@{result.config.topK}</span>
              <strong>{percent(current.recall)}</strong>
              <small>write {current.step} of {result.config.budget}</small>
            </div>
          </div>
          <div className="instrument-bottom">
            <div>
              <span>Target rank</span>
              <strong>{rankLabel(current.rank)}</strong>
            </div>
            <div>
              <span>Crowding score</span>
              <strong>{percent(current.alertScore)}</strong>
            </div>
            <div>
              <span>Capacity</span>
              <strong>{percent(Math.min(1, current.occupancy))}</strong>
            </div>
          </div>
        </div>
      </section>

      <section className="experiment-shell" id="experiment">
        <aside className="builder">
          <div className="builder-heading">
            <div>
              <span>Experiment builder</span>
              <h2>Bound the system</h2>
            </div>
            <button
              type="button"
              className="reset-button"
              onClick={() => setConfig(defaultConfig)}
            >
              Reset
            </button>
          </div>

          <div className="field-grid">
            <SelectField<MemoryPolicy>
              label="Memory policy"
              value={config.policy}
              options={policyLabels}
              onChange={(value) => updateConfig("policy", value)}
            />
            <SelectField<AttackStrategy>
              label="Traffic strategy"
              value={config.attack}
              options={attackLabels}
              onChange={(value) => updateConfig("attack", value)}
            />
            <SelectField<DefenseStrategy>
              label="Defense"
              value={config.defense}
              options={defenseLabels}
              onChange={(value) => updateConfig("defense", value)}
            />
            <SelectField<KnowledgeLevel>
              label="Attacker knowledge"
              value={config.knowledge}
              options={knowledgeLabels}
              onChange={(value) => updateConfig("knowledge", value)}
            />
            <SelectField<Domain>
              label="Benchmark domain"
              value={config.domain}
              options={domainLabels}
              onChange={(value) => updateConfig("domain", value)}
            />
            <NumberField
              label="Random seed"
              value={config.seed}
              min={0}
              max={99999}
              onChange={(value) => updateConfig("seed", value)}
            />
          </div>

          <div className="range-stack">
            <label>
              <span>
                Capacity <strong>{config.capacity} records</strong>
              </span>
              <input
                type="range"
                min="8"
                max="80"
                value={config.capacity}
                onChange={(event) => updateConfig("capacity", Number(event.target.value))}
              />
            </label>
            <label>
              <span>
                Retrieval budget <strong>top {config.topK}</strong>
              </span>
              <input
                type="range"
                min="1"
                max="12"
                value={config.topK}
                onChange={(event) => updateConfig("topK", Number(event.target.value))}
              />
            </label>
            <label>
              <span>
                Write budget <strong>{config.budget} writes</strong>
              </span>
              <input
                type="range"
                min="0"
                max="80"
                value={config.budget}
                onChange={(event) => updateConfig("budget", Number(event.target.value))}
              />
            </label>
          </div>

          <button
            className="run-button"
            type="button"
            onClick={runExperiment}
            disabled={playing}
          >
            <span>{playing ? "Experiment running" : "Run controlled experiment"}</span>
            <b aria-hidden="true">→</b>
          </button>
          <p className="builder-note">
            The live engine is deterministic. Knowledge changes targeting precision
            for targeted strategies; matched and random streams ignore it. Repeating
            a configuration and seed produces the same trace checksum.
          </p>
        </aside>

        <section className="results" id="results">
          <div className="results-head">
            <div>
              <span className="section-kicker">Live episode</span>
              <h2>Availability monitor</h2>
            </div>
            <div className="run-controls">
              <button
                type="button"
                onClick={togglePlayback}
                disabled={visibleStep >= result.config.budget}
              >
                {playing ? "Pause" : "Resume"}
              </button>
              <button
                type="button"
                onClick={() =>
                  download(
                    `${result.runId}.json`,
                    JSON.stringify(result, null, 2),
                    "application/json",
                  )
                }
              >
                Export trace
              </button>
              <button
                type="button"
                onClick={() =>
                  download(
                    `${result.runId}-metrics.csv`,
                    resultToCsv(result),
                    "text/csv",
                  )
                }
              >
                Export CSV
              </button>
            </div>
          </div>

          <div className="metrics-row">
            <Metric
              label="Critical Recall@k"
              value={percent(current.recall)}
              note={`Target ${rankLabel(current.rank).toLowerCase()}`}
              tone={availabilityTone}
            />
            <Metric
              label="Physical availability"
              value={percent(current.physical)}
              note={current.physical ? "Record remains stored" : "Record was evicted"}
              tone={current.physical ? "good" : "warn"}
            />
            <Metric
              label="Heuristic crowding score"
              value={percent(current.alertScore)}
              note={current.alertScore >= 0.58 ? "Intervention threshold crossed" : "Below heuristic threshold"}
              tone={current.alertScore >= 0.58 ? "warn" : "default"}
            />
            <Metric
              label="Write accounting"
              value={`${current.step - current.rejectedWrites}/${current.step}`}
              note={`${current.rejectedWrites} rejected through this write`}
            />
          </div>

          <div className="view-tabs" role="tablist" aria-label="Experiment views">
            {(Object.keys(viewLabels) as ViewId[]).map((view) => (
              <button
                key={view}
                id={`view-tab-${view}`}
                type="button"
                role="tab"
                aria-selected={activeView === view}
                aria-controls="experiment-view-panel"
                tabIndex={activeView === view ? 0 : -1}
                onClick={() => setActiveView(view)}
                onKeyDown={(event) => handleTabKeyDown(event, view)}
              >
                {viewLabels[view]}
              </button>
            ))}
          </div>

          <div
            className="view-panel"
            id="experiment-view-panel"
            role="tabpanel"
            aria-labelledby={`view-tab-${activeView}`}
          >
            {activeView === "map" ? (
              <MemoryMap
                points={result.points}
                visibleStep={visibleStep}
                stepState={currentMemoryState}
                query={result.query}
                selectedId={selectedPointId}
                onSelect={(point) => setSelectedPointId(point.id)}
              />
            ) : null}
            {activeView === "trajectory" ? (
              <TrajectoryChart trajectory={visibleTrajectory} />
            ) : null}
            {activeView === "comparison" ? (
              <ComparisonView arms={comparison} />
            ) : null}
            {activeView === "trace" ? (
              <TraceInspector
                trace={visibleTrace}
                selected={selectedTrace}
                onSelect={(decision) => setSelectedTraceId(decision.id)}
              />
            ) : null}
            {activeView === "evidence" ? <EvidenceView result={result} /> : null}
          </div>
        </section>
      </section>

      <section className="method" id="method">
        <div className="method-heading">
          <span className="section-kicker">Research design</span>
          <h2>One failure, measured four ways</h2>
          <p>
            ChaffMem Lab keeps storage, retrieval, a fixed downstream read window,
            and time separate so a full store is not mistaken for usable memory.
          </p>
        </div>
        <div className="method-grid">
          {[
            ["01", "Physical", "Does the verified record still exist after bounded eviction"],
            ["02", "Retrieval", "Does the record appear inside the fixed top-k budget"],
            ["03", "Read window", "Does the record reach a fixed three-record downstream reader"],
            ["04", "Temporal", "How long does availability survive along the write trajectory"],
          ].map(([index, title, copy]) => (
            <article key={title}>
              <span>{index}</span>
              <h3>{title}</h3>
              <p>{copy}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="status-section" id="status">
        <div>
          <span className="section-kicker">Current research status</span>
          <h2>A working instrument, not a finished claim</h2>
        </div>
        <div className="status-grid">
          <article>
            <span className="status-icon status-done">✓</span>
            <div>
              <h3>Implemented</h3>
              <p>
                Deterministic policies, bounded benign traffic, defenses, heuristic
                crowding monitoring, replayable traces, comparison arms, exports, and
                a local API are included in the repository.
              </p>
            </div>
          </article>
          <article>
            <span className="status-icon status-pending">○</span>
            <div>
              <h3>Requires full study</h3>
              <p>
                Cross-domain effect sizes, transfer across learned embeddings, large-scale
                concurrency, and any security conclusion remain untested until the full
                benchmark is executed.
              </p>
            </div>
          </article>
        </div>
      </section>

      <footer>
        <div className="brand footer-brand">
          <span className="brand-mark">CM</span>
          <span>
            <strong>ChaffMem Lab</strong>
            <small>Open research prototype</small>
          </span>
        </div>
        <p>
          Defensive research for local agent-memory implementations. No commercial
          system is evaluated or named.
        </p>
        <a href="#top">Back to top ↑</a>
      </footer>
    </main>
  );
}
