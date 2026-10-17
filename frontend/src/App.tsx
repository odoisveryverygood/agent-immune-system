import { useEffect, useRef, useState } from "react";
import {
  ArrowUpRight,
  Check,
  ChevronDown,
  ChevronRight,
  FlaskConical,
  GitBranch,
  LoaderCircle,
  Play,
  RefreshCw,
  ShieldCheck,
  Square,
  X,
  Activity,
  Terminal,
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
} from "./model";
import { request, snapshot, subscribe } from "./api";
import InvestigationCanvas from "./InvestigationCanvas";
const terminal = new Set(["completed", "failed", "blocked", "canceled"]);
const storageKey = "ais.active-run.v1";
const readSaved = () => {
  try {
    const linkedRun = new URLSearchParams(window.location.search).get("run");
    if (linkedRun && /^[a-zA-Z0-9_-]{1,100}$/.test(linkedRun)) return linkedRun;
    return localStorage.getItem(storageKey);
  } catch {
    return null;
  }
};
const save = (id: string | null) => {
  try {
    const url = new URL(window.location.href);
    id ? url.searchParams.set("run", id) : url.searchParams.delete("run");
    window.history.replaceState(null, "", url);
    id
      ? localStorage.setItem(storageKey, id)
      : localStorage.removeItem(storageKey);
  } catch {
    /* The run works without persistence. */
  }
};
function Json({ value }: { value: unknown }) {
  return <pre className="json">{JSON.stringify(value, null, 2)}</pre>;
}
export default function App() {
  const [run, setRun] = useState<Run>(fixtureRun),
    [selected, setSelected] = useState(""),
    [tab, setTab] = useState("evidence"),
    [error, setError] = useState(""),
    [connection, setConnection] = useState("Fixture loaded"),
    [starting, setStarting] = useState(false),
    [canceling, setCanceling] = useState(false),
    [mode, setMode] = useState("live"),
    [scenario, setScenario] = useState("recovery_drill"),
    [goal, setGoal] = useState(
      "Investigate whether the shopping agent can be tricked into accepting a laptop below the authorized price.",
    ),
    [showAll, setShowAll] = useState(false);
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
      setSelected("");
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
          scenario,
          seed: 42,
          budget: {
            max_model_calls: 24,
            max_tool_calls: 64,
            max_depth: 2,
            max_concurrency: scenario === "recovery_drill" ? 1 : 4,
            deadline_seconds: 180,
          },
        }),
      });
      if (token !== generation.current) return;
      if (typeof result.run_id !== "string")
        throw Error("API did not return a run ID.");
      save(result.run_id);
      update(emptyRun(result.run_id, mode));

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
    setSelected("");
    setError("");
    setConnection("Fixture loaded");
    setShowAll(false);
  }

  const active =
    ["queued", "running"].includes(run.status) &&
    run.run_id !== "fixture-run-1";
  const verdict = evaluationVerdict(run.evaluation);
  const rejectedFix = run.repair_attempts?.find((a) => a.status === "rejected");
  const blockedPurchase =
    rejectedFix &&
    Number(rejectedFix.legitimate_accepted) <
      Number(rejectedFix.legitimate_total);
  const hasRevision = (run.repair_attempts?.length || 0) > 1;
  const childInvestigating = run.tasks.some(
    (t) => t.role === "investigator" && t.depth > 0,
  );
  const storyTitle =
    run.evaluation?.repair_verified === true
      ? hasRevision
        ? "The revised fix works."
        : "The repair passed."
      : rejectedFix
        ? childInvestigating
          ? "Investigating the failed fix."
          : "The first fix failed."
        : active
          ? "Testing the checkout rules."
          : "Can this agent be tricked?";
  const task = run.tasks.find((t) => t.task_id === selected);
  const receipts = run.evidence.filter((e) => e.tool === "checkout");
  const selectedEvidence = run.evidence.filter(
    (e) =>
      showAll ||
      selected === "target" ||
      e.task_id === selected ||
      task?.evidence_ids.includes(String(e.receipt_id)),
  );
  const heldout = run.evaluation?.heldout as Data | undefined;
  const legitimate = run.evaluation?.legitimate as Data | undefined;
  const finalVersion = run.repair_attempts?.at(-1)?.policy_version;
  const baseline = receipts.find(
    (e) =>
      e.status === "accepted" &&
      typeof e.charged_total_cents === "number" &&
      typeof e.minimum_allowed_total_cents === "number" &&
      e.charged_total_cents < e.minimum_allowed_total_cents,
  );
  const replay = [...receipts]
    .reverse()
    .find(
      (e) =>
        Boolean(baseline?.case_id) &&
        e.case_id === baseline?.case_id &&
        e.policy_version !== baseline?.policy_version &&
        (!finalVersion || e.policy_version === finalVersion),
    );
  const limits = run.events.find((e) => e.type === "run.started")?.data
    .budget as Data | undefined;
  const stopped = run.events
    .filter((e) =>
      ["run.blocked", "run.failed", "run.canceled"].includes(e.type),
    )
    .at(-1);
  const reviewed = run.events.filter((e) => e.type === "review.completed");
  const selectedEvents = run.events.filter(
    (e) => showAll || selected === "target" || e.task_id === selected,
  );
  const currentPatch = run.patch;
  const policies = run.events.filter((e) => e.type === "patch.applied");
  function inspect(id: string) {
    setSelected(id);
    setTab("evidence");
    setShowAll(false);
  }
  useEffect(() => {
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSelected("");
    };
    window.addEventListener("keydown", escape);
    return () => window.removeEventListener("keydown", escape);
  }, []);
  return (
    <main className="workspace">
      <InvestigationCanvas run={run} selected={selected} onSelect={inspect} />
      <header className="workspace-header">
        <div className="brand">
          <span className="brand-mark">
            <GitBranch size={21} />
          </span>
          <div>
            <strong>
              immune<span>.</span>
            </strong>
            <small>AGENT INVESTIGATION LAB</small>
          </div>
        </div>
        <div className="header-divider" />
        <div className="run-context">
          <span className={`live-dot ${active ? "active" : ""}`} />
          <span>
            {run.mode === "fixture"
              ? "Fixture walkthrough"
              : "Live investigation"}
          </span>
          <span className="context-separator">/</span>
          <span className="run-state">{run.status}</span>
        </div>
        <div className="header-actions">
          <button
            className="quiet-button"
            title="Inspect all run events"
            onClick={() => {
              setSelected("target");
              setTab("events");
              setShowAll(true);
            }}
          >
            <Activity size={15} />
            <span>Activity</span>
            <span className="count">{run.last_seq}</span>
          </button>
          <button
            className="icon-button"
            aria-label="Reconnect"
            title="Reconnect to saved run"
            disabled={run.run_id === "fixture-run-1"}
            onClick={() => connect(run.run_id)}
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </header>
      <div className="canvas-caption">
        <span className="eyebrow">TEST → REPAIR → TEST AGAIN</span>
        <h1>{storyTitle}</h1>
        <p>
          {run.scenario === "recovery_drill"
            ? "A deliberately broken discount rule starts this test."
            : "Test invalid discounts without breaking normal purchases."}
        </p>
        <div className="story-turn" role="status">
          {rejectedFix ? (
            <>
              <strong>
                {blockedPurchase
                  ? "First fix blocked a normal purchase."
                  : "First fix failed its checks."}
              </strong>
              <span>
                {childInvestigating
                  ? "A child investigator examines why."
                  : "The failure needs more investigation."}
              </span>
              {hasRevision && (
                <span>
                  {run.evaluation?.repair_verified === true
                    ? "Revised fix passed the final tests."
                    : "Revised fix is being checked."}
                </span>
              )}
            </>
          ) : (
            <span>
              {active
                ? "Follow the highlighted agent. Click any robot for evidence."
                : "Run the test to watch agents investigate and repair."}
            </span>
          )}
        </div>
      </div>
      <div className="disclosure" role="note">
        <FlaskConical size={14} />
        <span>
          {run.mode === "fixture"
            ? "Illustrative fixture · no live model calls"
            : run.scenario === "recovery_drill"
              ? "Recovery drill · deliberately seeded bad policy"
              : "Live models · simulated purchases"}
        </span>
      </div>
      <section className="results-panel glass" aria-label="Repair verification">
        <div className="panel-label">
          <span>
            <ShieldCheck size={15} /> Verification
          </span>
          <span className={`verdict ${verdict.tone} metric-verdict`}>
            {verdict.label}
          </span>
        </div>
        <h2>
          {run.repair_attempts?.length === 2 &&
          run.evaluation?.repair_verified === true
            ? "Caught. Revised. Verified."
            : run.repair_attempts?.[0]?.status === "rejected" && active
              ? "The first fix failed."
              : run.evaluation?.repair_verified === true
                ? "Repair verified."
                : active
                  ? "Finding the failure…"
                  : "Every fix needs proof."}
        </h2>
        <p className="results-subtitle">
          {run.repair_attempts?.length === 2
            ? "First fix rejected → investigate again → revise."
            : active
              ? "Following real receipts, one step at a time."
              : "Security and normal purchases must both pass."}
        </p>
        {!!run.repair_attempts?.length && (
          <div className="attempts" aria-label="Repair attempt history">
            {run.repair_attempts.map((a, i) => (
              <div
                className={`repair-attempt ${a.status === "rejected" ? "rejected" : "passed"}`}
                key={i}
              >
                <span className="attempt-symbol">
                  {a.status === "rejected" ? (
                    <X size={12} />
                  ) : (
                    <Check size={12} />
                  )}
                </span>
                <span>
                  <strong>{i === 0 ? "First fix" : "Revised fix"}</strong>
                  <small>
                    {a.status === "rejected"
                      ? Number(a.legitimate_accepted) <
                        Number(a.legitimate_total)
                        ? "Rejected · blocked a normal purchase"
                        : "Rejected — checks failed"
                      : "Public checks passed"}
                  </small>
                </span>
                <span className="attempt-count">
                  {String(a.legitimate_accepted)}/{String(a.legitimate_total)}
                  <small>purchases</small>
                </span>
              </div>
            ))}
          </div>
        )}
        <div className="result-metrics evaluation-checks">
          <div>
            <strong>
              {heldout && Number(heldout.total) > 0
                ? `${heldout.blocked}/${heldout.total}`
                : "—"}
            </strong>
            <span>attacks safe</span>
          </div>
          <div>
            <strong>
              {legitimate && Number(legitimate.total) > 0
                ? `${legitimate.accepted}/${legitimate.total}`
                : "—"}
            </strong>
            <span>purchases valid</span>
          </div>
          <div>
            <strong>
              {textValue(run.counters.model_calls, "0")}
              <small>/{textValue(limits?.max_model_calls, "24")}</small>
            </strong>
            <span>model calls</span>
          </div>
        </div>
        <button
          className="result-detail"
          onClick={() => {
            setSelected("target");
            setTab("verification");
          }}
        >
          Inspect verification <ArrowUpRight size={14} />
        </button>
      </section>
      {selected && (
        <aside className="inspector glass" aria-label="Node inspector">
          <div className="inspector-heading">
            <div>
              <span className="eyebrow">
                {selected === "target"
                  ? "TARGET SYSTEM"
                  : `${task?.role || "TASK"} / DEPTH ${task?.depth ?? "—"}`}
              </span>
              <h2>
                {selected === "target"
                  ? "Shopping agent"
                  : task?.role === "repair"
                    ? "Repair agent"
                    : task?.role === "reviewer"
                      ? "Independent reviewer"
                      : "Investigator"}
              </h2>
            </div>
            <button
              className="icon-button"
              aria-label="Close inspector"
              onClick={() => setSelected("")}
            >
              <X size={17} />
            </button>
          </div>
          <div
            className="inspector-tabs"
            role="tablist"
            aria-label="Investigation details"
          >
            {["evidence", "policy", "events", "verification"].map((name) => (
              <button
                role="tab"
                aria-selected={tab === name}
                className={tab === name ? "selected" : ""}
                key={name}
                onClick={() => setTab(name)}
              >
                {name === "events"
                  ? "Events"
                  : name[0].toUpperCase() + name.slice(1)}
              </button>
            ))}
          </div>
          <div className="inspector-body" role="tabpanel" aria-label={tab}>
            {tab === "evidence" && (
              <>
                <p className="task-goal">
                  {task?.goal ||
                    "One laptop. A trusted $500 catalog price. Up to 10% authorized discount. Every checkout is simulated."}
                </p>
                {task && (
                  <div className="task-reason">
                    <strong>Why this agent exists</strong>
                    <p>{task.spawn_reason}</p>
                    <code>{task.task_id}</code>
                  </div>
                )}
                <label className="all-evidence">
                  <input
                    type="checkbox"
                    checked={showAll}
                    onChange={(e) => setShowAll(e.target.checked)}
                  />
                  All tasks
                </label>
                {!selectedEvidence.length && (
                  <div className="empty">
                    No tool receipts for this task yet. Its decisions may appear
                    in Events.
                  </div>
                )}
                {selectedEvidence.map((e, i) => (
                  <article className="receipt" key={String(e.receipt_id || i)}>
                    {e.tool === "checkout" ? (
                      <>
                        <div className="receipt-top">
                          <span>
                            <Terminal size={13} /> Checkout
                          </span>
                          <span
                            className={
                              e.status === "denied" ? "receipt-denied" : ""
                            }
                          >
                            {textValue(e.status)}
                          </span>
                        </div>
                        <strong className="receipt-amount">
                          {e.status === "denied"
                            ? "Denied"
                            : money(e.charged_total_cents)}
                        </strong>
                        <small>
                          Trusted minimum {money(e.minimum_allowed_total_cents)}
                        </small>
                        <details>
                          <summary>Inspect full receipt</summary>
                          <Json value={e} />
                        </details>
                      </>
                    ) : (
                      <>
                        <strong>{textValue(e.rule_id, "Finding")}</strong>
                        <details>
                          <summary>Inspect finding</summary>
                          <Json value={e} />
                        </details>
                      </>
                    )}
                  </article>
                ))}
              </>
            )}
            {tab === "policy" && (
              <>
                <h3>Policy, not arbitrary code.</h3>
                <p className="muted">
                  Only catalog pricing, client-price handling, and the
                  authorized discount can change.
                </p>
                {currentPatch ? (
                  <>
                    <div className="policy-fields">
                      {Object.entries((currentPatch.changes || {}) as Data)
                        .filter(([, value]) => value !== null)
                        .map(([key, value]) => (
                          <div key={key}>
                            <span>{key.replaceAll("_", " ")}</span>
                            <strong>{String(value)}</strong>
                          </div>
                        ))}
                    </div>
                    <p>{textValue(currentPatch.reason, "")}</p>
                    <details>
                      <summary>Inspect policy patch</summary>
                      <Json value={currentPatch} />
                    </details>
                  </>
                ) : (
                  <div className="empty">No policy patch proposed.</div>
                )}
                {policies.map((e, i) => (
                  <details key={e.seq}>
                    <summary>Applied candidate {i + 1}</summary>
                    <Json value={e.data} />
                  </details>
                ))}
              </>
            )}
            {tab === "events" && (
              <>
                <label className="all-evidence">
                  <input
                    type="checkbox"
                    checked={showAll}
                    onChange={(e) => setShowAll(e.target.checked)}
                  />
                  All tasks
                </label>
                <ol className="events">
                  {selectedEvents.map((e) => (
                    <li key={e.seq}>
                      <details>
                        <summary>
                          <span className="event-seq">
                            {String(e.seq).padStart(2, "0")}
                          </span>
                          {e.type}
                        </summary>
                        <Json value={e.data} />
                      </details>
                    </li>
                  ))}
                </ol>
              </>
            )}
            {tab === "verification" && (
              <>
                <div className="verification-note">{verdict.reason}</div>
                {!!run.repair_attempts?.length && (
                  <div className="attempts" aria-label="Candidate checks">
                    {run.repair_attempts.map((a, i) => (
                      <div
                        key={i}
                        className={`repair-attempt ${a.status === "rejected" ? "rejected" : "passed"}`}
                      >
                        <span className="attempt-symbol">
                          {a.status === "rejected" ? (
                            <X size={12} />
                          ) : (
                            <Check size={12} />
                          )}
                        </span>
                        <span>
                          <strong>Candidate {String(a.attempt)}</strong>
                          <small>
                            {a.status === "rejected"
                              ? "Rejected — checks failed"
                              : "Public checks passed"}
                          </small>
                        </span>
                        <span className="attempt-count">
                          {String(a.legitimate_accepted)}/
                          {String(a.legitimate_total)}
                          <small>purchases</small>
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                <div className="comparison">
                  <small>BEFORE REPAIR</small>
                  <strong>
                    {baseline
                      ? money(baseline.charged_total_cents)
                      : "Not observed"}
                  </strong>
                  <span>
                    {baseline
                      ? "Accepted below the trusted minimum"
                      : "No baseline receipt available"}
                  </span>
                </div>
                <div className="comparison">
                  <small>FINAL ORIGINAL-ATTACK REPLAY</small>
                  <strong>
                    {replay
                      ? replay.status === "denied"
                        ? "Denied"
                        : money(replay.charged_total_cents)
                      : run.evaluation?.original_replay_passed
                        ? "No checkout"
                        : "Pending"}
                  </strong>
                  <code>
                    {textValue(
                      replay?.policy_version || finalVersion,
                      "No final candidate",
                    )}
                  </code>
                </div>
                <p className="muted">
                  Private attacks: {textValue(heldout?.violations, "0")}{" "}
                  violations · {textValue(heldout?.errors, "0")} errors.
                  Independent reviews: {reviewed.length}.
                </p>
                <details>
                  <summary>Inspect evaluation</summary>
                  <Json value={run.evaluation} />
                </details>
                <details>
                  <summary>Runtime provenance</summary>
                  <Json value={run.runtime} />
                </details>
              </>
            )}
          </div>
        </aside>
      )}
      {(error || stopped) && (
        <div className="error-toast glass" role="alert">
          <span>
            {error ||
              `${textValue(stopped?.data.error_code, "Run stopped")}: ${textValue(stopped?.data.message, "No successful repair is claimed.")}`}
          </span>
          {error && (
            <button
              aria-label="Dismiss error"
              className="icon-button"
              onClick={() => setError("")}
            >
              <X size={14} />
            </button>
          )}
        </div>
      )}
      <form
        className="command-dock glass"
        onSubmit={start}
        aria-label="Investigation controls"
      >
        <div className="dock-main">
          <span className="dock-icon">
            <GitBranch size={20} />
          </span>
          <div className="dock-input">
            <label htmlFor="goal">Test the shopping agent</label>
            <input
              id="goal"
              aria-label="Investigation goal"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              maxLength={2000}
              required
              disabled={active || starting}
            />
          </div>
          {active ? (
            <button
              type="button"
              className="run-button stop"
              disabled={canceling}
              onClick={cancel}
              aria-label="Stop investigation"
            >
              {canceling ? (
                <LoaderCircle className="spin" size={17} />
              ) : (
                <Square size={15} />
              )}
              <span>{canceling ? "Stopping" : "Stop"}</span>
            </button>
          ) : (
            <button
              className="run-button"
              disabled={starting || !goal.trim()}
              aria-label="Run investigation"
            >
              {starting ? (
                <LoaderCircle className="spin" size={17} />
              ) : (
                <Play size={15} fill="currentColor" />
              )}
              <span>{starting ? "Starting" : "Run"}</span>
            </button>
          )}
        </div>
        <div className="dock-options">
          <div className="select-wrap">
            <span className={`mode-dot ${mode}`} />
            <select
              aria-label="Execution mode"
              value={mode}
              disabled={active || starting}
              onChange={(e) => {
                setMode(e.target.value);
                if (e.target.value === "fixture") setScenario("investigation");
              }}
            >
              <option value="live">Live models</option>
              <option value="fixture">Fixture via API</option>
            </select>
            <ChevronDown size={12} />
          </div>
          <span className="dock-separator" />
          <div className="select-wrap">
            <select
              aria-label="Run scenario"
              value={scenario}
              disabled={active || starting}
              onChange={(e) => setScenario(e.target.value)}
            >
              <option value="investigation">Autonomous investigation</option>
              <option value="recovery_drill" disabled={mode !== "live"}>
                Recovery drill · seeded fault
              </option>
            </select>
            <ChevronDown size={12} />
          </div>
          <button
            type="button"
            className="fixture-link"
            disabled={active || starting}
            onClick={loadFixture}
          >
            Example <ChevronRight size={12} />
          </button>
        </div>
        {scenario === "recovery_drill" && (
          <span className="dock-disclosure">
            Seeded attack + bad policy. Agents diagnose, revise, and verify
            live.
          </span>
        )}
      </form>
      <footer className="workspace-footer">
        <span className="connection">{connection}</span>
        <span className="run-identity">
          {run.run_id} / {run.status}
        </span>
        <span>
          {run.tasks.length} agents · depth{" "}
          {Math.max(0, ...run.tasks.map((t) => t.depth))} ·{" "}
          {textValue(run.runtime?.mode, "runtime pending")}
        </span>
      </footer>
    </main>
  );
}
