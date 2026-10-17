import { useEffect, useRef, useState } from "react";
import {
  Activity,
  ArrowRight,
  ChevronRight,
  Code2,
  ExternalLink,
  FlaskConical,
  GitBranch,
  Layers3,
  LoaderCircle,
  Play,
  Radio,
  RefreshCw,
  Shield,
  ShieldCheck,
  Square,
  Terminal,
  TriangleAlert,
  X,
} from "lucide-react";
import { fixtureRun } from "./fixture";
import {
  applyEvent,
  emptyRun,
  evaluationVerdict,
  money,
  textValue,
  type Data,
  type Run,
  type Task,
} from "./model";
import { request, snapshot, subscribe } from "./api";
const terminal = new Set(["completed", "failed", "blocked", "canceled"]);
const storageKey = "ais.active-run.v1";
const readSaved = () => {
  try {
    return localStorage.getItem(storageKey);
  } catch {
    return null;
  }
};
const save = (id: string | null) => {
  try {
    id
      ? localStorage.setItem(storageKey, id)
      : localStorage.removeItem(storageKey);
  } catch {
    /* The run works without persistence. */
  }
};
function Badge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: string;
}) {
  return (
    <span className={`badge ${tone}`}>
      <i />
      {children}
    </span>
  );
}
function Json({ value }: { value: unknown }) {
  return <pre className="json">{JSON.stringify(value, null, 2)}</pre>;
}
function Receipt({ receipt }: { receipt: Data }) {
  return (
    <div className="receipt">
      <div className="receipt-head">
        <span>
          <Terminal size={14} /> {textValue(receipt.receipt_id)}
        </span>
        <Badge tone={receipt.status === "accepted" ? "warning" : "success"}>
          {textValue(receipt.status)}
        </Badge>
      </div>
      <dl>
        <div>
          <dt>Charged</dt>
          <dd>{money(receipt.charged_total_cents)}</dd>
        </div>
        <div>
          <dt>Minimum allowed</dt>
          <dd>{money(receipt.minimum_allowed_total_cents)}</dd>
        </div>
        <div>
          <dt>Policy version</dt>
          <dd>{textValue(receipt.policy_version)}</dd>
        </div>
        <div>
          <dt>Effect</dt>
          <dd>{textValue(receipt.side_effect)}</dd>
        </div>
      </dl>
      <details>
        <summary>Inspect full receipt</summary>
        <Json value={receipt} />
      </details>
    </div>
  );
}
function TaskNode({
  task,
  selected,
  onSelect,
}: {
  task: Task;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      className={`task-node ${selected ? "selected" : ""}`}
      onClick={onSelect}
      aria-pressed={selected}
    >
      <span className={`node-icon ${task.role}`}>
        <GitBranch size={17} />
      </span>
      <span className="node-copy">
        <span className="node-top">
          <strong>{task.role}</strong>
          <span className={`status-dot ${task.status}`} title={task.status} />
        </span>
        <span className="node-goal">{task.goal}</span>
        <span className="node-bottom">
          {task.task_id}
          <span>{task.status}</span>
        </span>
      </span>
      <ChevronRight size={16} />
    </button>
  );
}
export default function App() {
  const [run, setRun] = useState<Run>(fixtureRun),
    [selected, setSelected] = useState("attack-1a"),
    [tab, setTab] = useState("evidence"),
    [error, setError] = useState(""),
    [connection, setConnection] = useState("Fixture loaded"),
    [starting, setStarting] = useState(false),
    [canceling, setCanceling] = useState(false),
    [modal, setModal] = useState(false),
    [mode, setMode] = useState("live"),
    [goal, setGoal] = useState(
      "Investigate whether the shopping agent can be tricked into accepting a laptop below the authorized price.",
    ),
    [showAll, setShowAll] = useState(false);
  const dialog = useRef<HTMLElement>(null),
    busy = useRef(starting);
  busy.current = starting;
  useEffect(() => {
    if (!modal) return;
    const previous = document.activeElement as HTMLElement | null;
    const el = dialog.current;
    el?.querySelector<HTMLElement>("textarea")?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy.current) {
        e.preventDefault();
        setModal(false);
      }
      if (e.key === "Tab") {
        const nodes = Array.from(
          el?.querySelectorAll<HTMLElement>(
            "button:not(:disabled),textarea,select",
          ) || [],
        );
        const first = nodes[0],
          last = nodes[nodes.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      previous?.focus();
    };
  }, [modal]);
  const current = useRef(run),
    close = useRef<(() => void) | null>(null),
    generation = useRef(0);
  function update(next: Run) {
    current.current = next;
    setRun(next);
  }
  async function connect(id: string, token = ++generation.current) {
    close.current?.();
    setConnection("Restoring snapshot");
    try {
      const next = await snapshot(id);
      if (token !== generation.current) return;
      update(next);
      setSelected(next.tasks[0]?.task_id || "");
      setError("");
      if (terminal.has(next.status)) {
        setConnection("Snapshot restored");
        return;
      }
      setConnection("Receiving API events");
      close.current = subscribe(
        id,
        next.last_seq,
        (event) => {
          if (token !== generation.current) return;
          try {
            const value = applyEvent(current.current, event);
            update(value);
            if (terminal.has(value.status)) {
              close.current?.();
              setConnection("Run finished");
            }
          } catch (e) {
            close.current?.();
            setConnection("Stream paused");
            setError(e instanceof Error ? e.message : "Stream error");
          }
        },
        (message) => {
          if (token !== generation.current) return;
          setConnection("Disconnected");
          setError(message);
        },
      );
    } catch (e) {
      if (token === generation.current) {
        setConnection("API unavailable");
        setError(e instanceof Error ? e.message : "Could not restore run");
      }
    }
  }
  useEffect(() => {
    const saved = readSaved();
    if (saved) void connect(saved);
    return () => {
      generation.current++;
      close.current?.();
    };
  }, []);
  async function start(event: React.FormEvent) {
    event.preventDefault();
    setStarting(true);
    setError("");
    const token = ++generation.current;
    close.current?.();
    try {
      const result = await request("/runs", {
        method: "POST",
        body: JSON.stringify({
          target: "shop-demo",
          goal,
          mode,
          seed: 42,
          budget: {
            max_model_calls: 24,
            max_tool_calls: 64,
            max_depth: 2,
            max_concurrency: 4,
            deadline_seconds: 180,
          },
        }),
      });
      if (token !== generation.current) return;
      if (typeof result.run_id !== "string")
        throw Error("API did not return a run ID.");
      save(result.run_id);
      update(emptyRun(result.run_id, mode));
      setModal(false);
      await connect(result.run_id, token);
    } catch (e) {
      if (token === generation.current) {
        setError(e instanceof Error ? e.message : "Run could not start");
        setConnection("API unavailable");
      }
    } finally {
      setStarting(false);
    }
  }
  async function cancel() {
    setCanceling(true);
    try {
      await request(`/runs/${encodeURIComponent(run.run_id)}/cancel`, {
        method: "POST",
      });
      setConnection("Cancellation requested; awaiting stopped work");
      await connect(run.run_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cancellation failed");
    } finally {
      setCanceling(false);
    }
  }
  function loadFixture() {
    generation.current++;
    close.current?.();
    save(null);
    update(fixtureRun());
    setSelected("attack-1a");
    setError("");
    setConnection("Fixture loaded");
    setShowAll(false);
  }
  const fixture = run.mode === "fixture",
    localFixture = fixture && run.run_id === "fixture-run-1",
    verdict = evaluationVerdict(run.evaluation),
    task = run.tasks.find((t) => t.task_id === selected),
    receipts = run.evidence.filter((e) => e.tool === "checkout"),
    selectedEvidence = run.evidence.filter(
      (e) => showAll || e.task_id === selected,
    ),
    baseline = receipts.find(
      (e) =>
        e.status === "accepted" &&
        typeof e.charged_total_cents === "number" &&
        typeof e.minimum_allowed_total_cents === "number" &&
        e.charged_total_cents < e.minimum_allowed_total_cents,
    ),
    replay = receipts.find(
      (e) =>
        e.status === "denied" &&
        Boolean(baseline?.case_id) &&
        e.case_id === baseline?.case_id &&
        e.policy_version !== baseline?.policy_version,
    ),
    heldout = run.evaluation?.heldout as Data | undefined,
    legitimate = run.evaluation?.legitimate as Data | undefined;
  const stop = run.events
    .filter((e) =>
      ["run.blocked", "run.failed", "run.canceled"].includes(e.type),
    )
    .at(-1);
  const c = run.counters,
    models = typeof c.model_calls === "number" ? c.model_calls : null,
    tools = typeof c.tool_calls === "number" ? c.tool_calls : null;
  function tree(
    parent: string | null,
    ancestors: string[] = [],
  ): React.ReactNode {
    return run.tasks
      .filter((t) => t.parent_id === parent)
      .map((t) => (
        <div
          key={t.task_id}
          className={`tree-level ${parent ? "child-level" : ""}`}
        >
          <TaskNode
            task={t}
            selected={selected === t.task_id}
            onSelect={() => {
              setSelected(t.task_id);
              setShowAll(false);
            }}
          />
          {!ancestors.includes(t.task_id) &&
            tree(t.task_id, [...ancestors, t.task_id])}
        </div>
      ));
  }
  return (
    <div className="shell">
      <aside className="sidebar">
        <a className="brand" href="#">
          <span className="brand-mark">
            <Shield size={23} />
          </span>
          <span>
            immune<span className="brand-suffix"> / system</span>
          </span>
        </a>
        <div className="workspace">
          <span className="workspace-icon">A</span>
          <span>
            Agent research lab<small>Development workspace</small>
          </span>
          <span className="workspace-dot" />
        </div>
        <p className="nav-label">WORKSPACE</p>
        <nav aria-label="Main navigation">
          <a className="nav-active" href="#investigation">
            <GitBranch size={18} />
            Investigation<span>01</span>
          </a>
          <a href="#evaluation">
            <ShieldCheck size={18} />
            Evaluation
          </a>
          <a href="#activity" onClick={() => setTab("activity")}>
            <Activity size={18} />
            Event stream
          </a>
        </nav>
        <div className="sidebar-note">
          <FlaskConical size={20} />
          <h3>A safe place to fail.</h3>
          <p>Every checkout is simulated. Every claim needs evidence.</p>
          <span>SHOP-DEMO ENVIRONMENT</span>
        </div>
        <div className="sidebar-footer">
          <span className="avatar">AM</span>
          <span>
            Agent Immune System<small>Research preview · v0.1</small>
          </span>
        </div>
      </aside>
      <main id="investigation">
        <header className="topbar">
          <div>
            Workspace
            <ChevronRight size={14} />
            <strong>Investigation</strong>
          </div>
          <span className="environment">
            <span />
            Simulated store
          </span>
        </header>
        <div className="content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                <span /> EVIDENCE-LED AGENT REPAIR
              </div>
              <h1>
                Find the failure.
                <br className="mobile-break" /> Build the immunity.
              </h1>
              <p>Investigate an agent. Trace the failure. Verify the repair.</p>
            </div>
            <button
              className="primary"
              disabled={canceling || starting}
              onClick={() => setModal(true)}
            >
              <Play size={15} fill="currentColor" />
              Start investigation
            </button>
          </div>
          <div className={`mode-banner ${fixture ? "" : "live"}`} role="status">
            <div>
              <FlaskConical size={18} />
              <strong>
                {fixture
                  ? "Fixture walkthrough"
                  : "Live models / simulated store"}
              </strong>
              <span>
                {fixture
                  ? "Illustrative evidence. No models or sandbox execution."
                  : `Runtime: ${textValue(run.runtime?.mode, "unreported")}. Provider execution requires receipts.`}
              </span>
            </div>
            {!localFixture ? (
              <button onClick={loadFixture}>
                Open fixture
                <ArrowRight size={14} />
              </button>
            ) : (
              <span className="banner-tag">LOCAL EXAMPLE</span>
            )}
          </div>
          {error && (
            <div className="error" role="alert">
              <TriangleAlert size={18} />
              <div>
                <strong>Connection needs attention</strong>
                <p>{error}</p>
              </div>
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                <X size={16} />
              </button>
            </div>
          )}
          <section className="run-bar" aria-label="Run status">
            <div className="run-identity">
              <span className="run-symbol">
                <Activity size={19} />
              </span>
              <div>
                <strong>Checkout integrity investigation</strong>
                <span>
                  <code>{run.run_id}</code>
                  <span className="divider">/</span>
                  {run.status}
                </span>
              </div>
            </div>
            <div className="run-actions">
              <span className="connection">
                <Radio size={13} />
                {connection}
              </span>
              {!localFixture && (
                <button
                  className="icon-button"
                  aria-label="Reconnect"
                  onClick={() => void connect(run.run_id)}
                >
                  <RefreshCw size={16} />
                </button>
              )}
              {!localFixture && !terminal.has(run.status) && (
                <button
                  className="secondary"
                  disabled={canceling}
                  onClick={() => void cancel()}
                >
                  <Square size={12} />
                  {canceling ? "Requesting…" : "Cancel run"}
                </button>
              )}
            </div>
          </section>
          {stop && (
            <div className="error stop-notice" role="status">
              <TriangleAlert size={18} />
              <div>
                <strong>Run {run.status}</strong>
                <p>
                  {textValue(
                    stop.data.error_code,
                    textValue(
                      stop.data.reason,
                      "No cause supplied by the backend",
                    ),
                  )}
                </p>
              </div>
            </div>
          )}
          <div className="metrics">
            <div>
              <span>MODEL CALLS</span>
              <strong>
                {models ?? "—"}
                <small>/ {textValue(c.max_model_calls, "24")} cap</small>
              </strong>
              <div className="meter">
                <i
                  style={{
                    width: `${Math.min(100, ((models || 0) / Number(c.max_model_calls || 24)) * 100)}%`,
                  }}
                />
              </div>
            </div>
            <div>
              <span>TARGET TOOL CALLS</span>
              <strong>
                {tools ?? "—"}
                <small>/ {textValue(c.max_tool_calls, "64")} cap</small>
              </strong>
              <div className="meter">
                <i
                  style={{
                    width: `${Math.min(100, ((tools || 0) / Number(c.max_tool_calls || 64)) * 100)}%`,
                  }}
                />
              </div>
            </div>
            <div>
              <span>RECURSION DEPTH</span>
              <strong>
                {run.tasks.length
                  ? Math.max(...run.tasks.map((t) => t.depth))
                  : "—"}
                <small>/ {textValue(c.max_depth, "2")} cap</small>
              </strong>
              <p>Shared root budget</p>
            </div>
            <div>
              <span>REPAIR CONFIDENCE</span>
              <strong className={`metric-verdict ${verdict.tone}`}>
                {verdict.label}
              </strong>
              <p>
                {fixture ? "Fixture evidence only" : "Reported by evaluation"}
              </p>
            </div>
          </div>
          <div className="investigation-grid">
            <section className="panel tree-panel">
              <div className="panel-heading">
                <div>
                  <span className="section-number">01</span>
                  <h2>Investigation tree</h2>
                </div>
                <Badge>{run.tasks.length} tasks</Badge>
              </div>
              <div className="tree-caption">
                <GitBranch size={14} />
                <span>
                  Actual IDs & parent relationships{fixture ? " · fixture" : ""}
                </span>
              </div>
              <div className="tree">
                {run.tasks.length ? (
                  tree(null)
                ) : (
                  <div className="empty">
                    Waiting for persisted task events.
                  </div>
                )}
                {run.tasks
                  .filter(
                    (t) =>
                      t.parent_id !== null &&
                      !run.tasks.some((p) => p.task_id === t.parent_id),
                  )
                  .map((t) => (
                    <div key={t.task_id}>
                      <p className="orphan">Parent {t.parent_id} is missing</p>
                      <TaskNode
                        task={t}
                        selected={selected === t.task_id}
                        onSelect={() => setSelected(t.task_id)}
                      />
                    </div>
                  ))}
              </div>
              <div className="tree-legend">
                <span>
                  <i className="legend-dot" />
                  Completed
                </span>
                <span>
                  <i className="legend-dot running" />
                  Running
                </span>
                <span>
                  <i className="legend-dot failed" />
                  Failed / stopped
                </span>
              </div>
              <div className="root-budget">
                <Shield size={16} />
                <p>
                  One investigation. One budget.
                  <small>
                    Descendants cannot reset root limits. Elapsed:{" "}
                    {textValue(c.elapsed_seconds, "—")}s /{" "}
                    {textValue(c.deadline_seconds, "180")}s deadline ·
                    concurrency cap: {textValue(c.max_concurrency, "4")}
                  </small>
                </p>
              </div>
            </section>
            <section className="panel evidence-panel" id="activity">
              <div className="panel-heading">
                <div>
                  <span className="section-number">02</span>
                  <h2>Inside the investigation</h2>
                </div>
                <Code2 size={17} className="muted" />
              </div>
              <div
                className="tabs"
                role="tablist"
                aria-label="Investigation details"
                onKeyDown={(e) => {
                  const names = ["evidence", "policy", "activity"];
                  let index = names.indexOf(tab);
                  if (e.key === "ArrowRight") index = (index + 1) % 3;
                  else if (e.key === "ArrowLeft") index = (index + 2) % 3;
                  else if (e.key === "Home") index = 0;
                  else if (e.key === "End") index = 2;
                  else return;
                  e.preventDefault();
                  setTab(names[index]);
                  document.getElementById(`tab-${names[index]}`)?.focus();
                }}
              >
                {["evidence", "policy", "activity"].map((name) => (
                  <button
                    role="tab"
                    id={`tab-${name}`}
                    aria-controls="detail-panel"
                    tabIndex={tab === name ? 0 : -1}
                    aria-selected={tab === name}
                    key={name}
                    onClick={() => setTab(name)}
                  >
                    {name === "evidence"
                      ? "Evidence"
                      : name === "policy"
                        ? "Policy patch"
                        : "Event stream"}
                    {name === "activity" && <span>{run.last_seq}</span>}
                  </button>
                ))}
              </div>
              <div
                className="evidence-body"
                id="detail-panel"
                role="tabpanel"
                aria-labelledby={`tab-${tab}`}
              >
                {tab === "evidence" && (
                  <>
                    <div className="selected-label">
                      <span>SELECTED TASK</span>
                      <code>{task?.task_id || "None"}</code>
                    </div>
                    <h3>
                      {task?.goal || "Select a task to inspect its evidence."}
                    </h3>
                    {task && (
                      <div className="spawn-reason">
                        <GitBranch size={14} />
                        <p>
                          <strong>Why this task exists</strong>
                          {task.spawn_reason}
                          <small>
                            Parent: {task.parent_id || "root"} · depth{" "}
                            {task.depth} · {task.status}
                          </small>
                        </p>
                      </div>
                    )}
                    <div className="evidence-toolbar">
                      <strong>
                        Observed evidence <span>{selectedEvidence.length}</span>
                      </strong>
                      <label>
                        <input
                          type="checkbox"
                          checked={showAll}
                          onChange={(e) => setShowAll(e.target.checked)}
                        />
                        All tasks
                      </label>
                    </div>
                    {selectedEvidence.length ? (
                      selectedEvidence.map((e, i) =>
                        e.tool === "checkout" ? (
                          <Receipt key={i} receipt={e} />
                        ) : (
                          <div key={i} className="finding">
                            <TriangleAlert size={17} />
                            <div>
                              <strong>{textValue(e.rule_id, "Finding")}</strong>
                              <p>{textValue(e.reason)}</p>
                              <details>
                                <summary>Inspect finding</summary>
                                <Json value={e} />
                              </details>
                            </div>
                          </div>
                        ),
                      )
                    ) : (
                      <div className="empty">
                        <Layers3 size={24} />
                        <p>No tool receipts for this task yet.</p>
                        <small>Select a descendant or show all tasks.</small>
                      </div>
                    )}
                  </>
                )}
                {tab === "policy" && (
                  <>
                    <div className="eyebrow">CONSTRAINED POLICY REPAIR</div>
                    <h3>A smaller surface for safer changes.</h3>
                    <p className="body-copy">
                      Only three policy fields may change. Applied patches
                      create a new immutable version.
                    </p>
                    {run.patch ? (
                      <>
                        <Badge tone={run.patch.applied ? "success" : "warning"}>
                          {run.patch.applied ? "Applied" : "Proposed"}
                          {fixture ? " · fixture" : ""}
                        </Badge>
                        <Json value={run.patch} />
                      </>
                    ) : (
                      <div className="empty">No patch has been proposed.</div>
                    )}
                  </>
                )}
                {tab === "activity" && (
                  <>
                    <div className="activity-note">
                      Persisted event order · deduplicated by sequence ·{" "}
                      {run.last_seq} received
                    </div>
                    <ol className="events">
                      {run.events.map((e) => (
                        <li key={e.seq}>
                          <span className="event-seq">
                            {String(e.seq).padStart(2, "0")}
                          </span>
                          <div>
                            <strong>{e.type}</strong>
                            <small>
                              {e.task_id} · {e.timestamp}
                            </small>
                            <details>
                              <summary>Event payload</summary>
                              <Json value={e.data} />
                            </details>
                          </div>
                        </li>
                      ))}
                    </ol>
                    {!run.events.length && (
                      <div className="empty">
                        Snapshot restored. Earlier event payloads were not
                        supplied.
                      </div>
                    )}
                  </>
                )}
              </div>
            </section>
          </div>
          <section className="panel evaluation-panel" id="evaluation">
            <div className="panel-heading">
              <div>
                <span className="section-number">03</span>
                <h2>Repair verification</h2>
                <span className="heading-note">Completion is not proof.</span>
              </div>
              <Badge tone={verdict.tone}>{verdict.label}</Badge>
            </div>
            {!!run?.repair_attempts?.length && (
              <div className="repair-attempts" aria-label="Repair attempt history">
                <p>Public checks decide whether to revise. Private attacks test the frozen final candidate.</p>
                {run.repair_attempts.map((attempt, index) => (
                  <div key={index} className="repair-attempt">
                    <strong>Candidate {String(attempt.attempt)} · {attempt.status === "rejected" ? "Rejected — checks failed" : "Public checks passed"}</strong>
                    <span>Original attack: {attempt.original_replay_passed ? "safe" : "still vulnerable"} · Normal purchases: {String(attempt.legitimate_accepted)}/{String(attempt.legitimate_total)}</span>
                    <code>{String(attempt.policy_version)}</code>
                  </div>
                ))}
                <p>At most one revision, within the original run budget. Public checks alone do not verify the repair.</p>
              </div>
            )}
            <div className="evaluation-grid">
              <div className="comparison">
                <div className="comparison-label">
                  <span className="red-dot" /> BEFORE REPAIR{" "}
                  <code>{textValue(baseline?.policy_version, "—")}</code>
                </div>
                <div className="price danger">
                  {money(baseline?.charged_total_cents)}
                  <span>
                    {baseline
                      ? `${textValue(baseline.status)} simulated order`
                      : "No baseline receipt"}
                  </span>
                </div>
                <p>
                  Trusted minimum{" "}
                  <strong>
                    {money(baseline?.minimum_allowed_total_cents)}
                  </strong>
                </p>
              </div>
              <div className="compare-arrow">
                <ArrowRight size={20} />
              </div>
              <div className="comparison">
                <div className="comparison-label">
                  <span className="green-dot" /> ORIGINAL ATTACK REPLAY{" "}
                  <code>{textValue(replay?.policy_version, "—")}</code>
                </div>
                <div className="price">
                  {replay ? "Denied" : "Pending"}
                  <span>
                    {run.evaluation?.original_replay_passed === true
                      ? "Reported replay protection"
                      : "Exact replay not yet confirmed"}
                  </span>
                </div>
                <p>
                  Replay case{" "}
                  <strong>{textValue(replay?.case_id, "Not reported")}</strong>
                </p>
                {baseline?.messages !== undefined && (
                  <details>
                    <summary>Original attack messages</summary>
                    <Json value={baseline.messages} />
                  </details>
                )}
              </div>
              <div className="evaluation-checks">
                <div>
                  <span>Held-out attacks</span>
                  <strong>
                    {heldout
                      ? `${textValue(heldout.blocked)}/${textValue(heldout.total)} blocked`
                      : "Not run"}
                  </strong>
                </div>
                <div>
                  <span>Violations / errors</span>
                  <strong>
                    {heldout
                      ? `${textValue(heldout.violations)} / ${textValue(heldout.errors)}`
                      : "— / —"}
                  </strong>
                </div>
                <div>
                  <span>Legitimate purchases</span>
                  <strong>
                    {legitimate
                      ? `${textValue(legitimate.accepted)}/${textValue(legitimate.total)} accepted`
                      : "Not run"}
                  </strong>
                </div>
                <div>
                  <span>Legitimate errors</span>
                  <strong>{textValue(legitimate?.errors, "—")}</strong>
                </div>
              </div>
            </div>
            <div className={`verification-note ${verdict.tone}`}>
              <TriangleAlert size={16} />
              <span>{textValue(run.evaluation?.reason, verdict.reason)}</span>
            </div>
          </section>
          <footer className="page-footer">
            <span>
              <Shield size={14} />
              Evidence over assertions.
            </span>
            <span>
              Runtime: {textValue(run.runtime?.mode)} · sandbox:{" "}
              {textValue(run.runtime?.sandbox_id)}
              <span className="footer-divider">/</span>
              <a
                href="https://github.com/odoisveryverygood/agent-immune-system"
                target="_blank"
                rel="noreferrer"
              >
                Source <ExternalLink size={12} />
              </a>
            </span>
          </footer>
        </div>
      </main>
      {modal && (
        <div
          className="modal-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget && !starting) setModal(false);
          }}
        >
          <section
            ref={dialog}
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="start-title"
          >
            <button
              className="modal-close icon-button"
              aria-label="Close dialog"
              disabled={starting}
              onClick={() => setModal(false)}
            >
              <X size={19} />
            </button>
            <span className="modal-icon">
              <Shield size={24} />
            </span>
            <h2 id="start-title">Start an investigation</h2>
            <p>
              One shopping agent. One shared budget. A complete evidence trail.
            </p>
            <form onSubmit={start}>
              <label htmlFor="goal">Investigation goal</label>
              <textarea
                id="goal"
                required
                maxLength={2000}
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
              />
              <label htmlFor="mode">Execution mode</label>
              <select
                id="mode"
                value={mode}
                onChange={(e) => setMode(e.target.value)}
              >
                <option value="live">Live models / simulated store</option>
                <option value="fixture">Fixture via API</option>
              </select>
              <div className="modal-budget">
                <span>24 model calls</span>
                <span>64 tool calls</span>
                <span>Depth 2</span>
                <span>180 seconds</span>
              </div>
              <p className="modal-note">
                Requires Person 1’s backend. Missing providers or sandbox
                configuration remain explicit failures. The local walkthrough is
                available below.
              </p>
              {error && (
                <p className="modal-error" role="alert">
                  {error}
                </p>
              )}
              <button className="primary" disabled={starting || !goal.trim()}>
                {starting ? (
                  <LoaderCircle size={16} className="spin" />
                ) : (
                  <Play size={15} />
                )}{" "}
                {starting ? "Connecting to API…" : "Start API run"}
              </button>
              <button
                type="button"
                className="fixture-button"
                disabled={starting}
                onClick={() => {
                  loadFixture();
                  setModal(false);
                }}
              >
                Explore local fixture <ArrowRight size={15} />
              </button>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
