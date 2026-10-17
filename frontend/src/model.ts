export type Data = Record<string, unknown>;
export interface RunEvent {
  schema_version: 1;
  run_id: string;
  seq: number;
  timestamp: string;
  type: string;
  task_id: string;
  parent_id: string | null;
  data: Data;
}
export interface Task {
  task_id: string;
  parent_id: string | null;
  role: string;
  goal: string;
  spawn_reason: string;
  depth: number;
  status: string;
  evidence_ids: string[];
  child_ids: string[];
}
export interface Run {
  run_id: string;
  status: string;
  mode: string;
  tasks: Task[];
  events: RunEvent[];
  counters: Data;
  evidence: Data[];
  patch?: Data;
  evaluation?: Data;
  repair_attempts?: Data[];
  scenario?: string;
  last_seq: number;
  runtime?: Data;
}
export const emptyRun = (id: string, mode = "live"): Run => ({
  run_id: id,
  status: "queued",
  mode,
  tasks: [],
  events: [],
  counters: {},
  evidence: [],
  last_seq: 0,
});
export function parseEvent(raw: unknown): RunEvent {
  const e = raw as RunEvent;
  if (
    !e ||
    e.schema_version !== 1 ||
    typeof e.run_id !== "string" ||
    !Number.isSafeInteger(e.seq) ||
    e.seq < 1 ||
    typeof e.type !== "string" ||
    typeof e.task_id !== "string" ||
    !(e.parent_id === null || typeof e.parent_id === "string") ||
    typeof e.timestamp !== "string" ||
    !e.data ||
    typeof e.data !== "object" ||
    Array.isArray(e.data)
  )
    throw Error(
      "Invalid event envelope. Stream paused; evidence has not been accepted.",
    );
  return e;
}
export function applyEvent(run: Run, event: RunEvent): Run {
  if (event.run_id !== run.run_id)
    throw Error("Event belongs to a different run.");
  if (event.seq <= run.last_seq) return run;
  if (event.seq !== run.last_seq + 1)
    throw Error(
      `Missing event sequence ${run.last_seq + 1}; restore the snapshot before continuing.`,
    );
  const next: Run = {
    ...run,
    events: [...run.events, event],
    tasks: run.tasks.map((t) => ({
      ...t,
      child_ids: [...t.child_ids],
      evidence_ids: [...t.evidence_ids],
    })),
    evidence: [...run.evidence],
    last_seq: event.seq,
  };
  const d = event.data;
  if (event.type === "run.started") {
    next.status = "running";
    next.mode = String(d.mode || run.mode);
    if (!next.tasks.some((t) => t.task_id === event.task_id))
      next.tasks.push({
        task_id: event.task_id,
        parent_id: null,
        role: "investigator",
        goal: String(d.goal || "Investigate checkout price integrity"),
        spawn_reason: "Root investigation",
        depth: 0,
        status: "running",
        evidence_ids: [],
        child_ids: [],
      });
  }
  if (event.type === "task.created") {
    const existing = next.tasks.find((t) => t.task_id === event.task_id);
    if (event.parent_id === null) {
      if (
        Number(d.depth) !== 0 ||
        next.tasks.some((t) => t.parent_id === null && t.task_id !== event.task_id) ||
        (existing && existing.parent_id !== null)
      )
        throw Error("Invalid task lineage: root task does not match the run.");
      const root: Task = {
        task_id: event.task_id,
        parent_id: null,
        role: String(d.role || "investigator"),
        goal: String(d.goal || ""),
        spawn_reason: String(d.spawn_reason || "No spawn reason supplied"),
        depth: Number(d.depth || 0),
        status: existing?.status || "queued",
        evidence_ids: Array.isArray(d.evidence_ids)
          ? d.evidence_ids.map(String)
          : [],
        child_ids: existing?.child_ids || [],
      };
      if (existing) Object.assign(existing, root);
      else next.tasks.push(root);
    } else {
      const parent = next.tasks.find((t) => t.task_id === event.parent_id);
      if (
        existing ||
        !parent ||
        event.task_id === event.parent_id ||
        Number(d.depth) !== parent.depth + 1
      )
        throw Error(
          "Invalid task lineage: parent or depth does not match the persisted tree.",
        );
      next.tasks.push({
        task_id: event.task_id,
        parent_id: event.parent_id,
        role: String(d.role || "investigator"),
        goal: String(d.goal || ""),
        spawn_reason: String(d.spawn_reason || "No spawn reason supplied"),
        depth: Number(d.depth || 0),
        status: "queued",
        evidence_ids: Array.isArray(d.evidence_ids)
          ? d.evidence_ids.map(String)
          : [],
        child_ids: [],
      });
      if (!parent.child_ids.includes(event.task_id))
        parent.child_ids.push(event.task_id);
    }
  }
  const task = next.tasks.find((t) => t.task_id === event.task_id);
  if (task && /^task\.(started|completed|failed)$/.test(event.type))
    task.status =
      event.type === "task.started" ? "running" : event.type.slice(5);
  if (event.type === "tool.observed" || event.type === "violation.found") {
    const receipt =
      event.type === "tool.observed" &&
      d.receipt &&
      typeof d.receipt === "object" &&
      !Array.isArray(d.receipt)
        ? (d.receipt as Data)
        : d;
    next.evidence.push({
      ...receipt,
      ...(typeof d.case_id === "string" && typeof receipt.case_id !== "string"
        ? { case_id: d.case_id }
        : {}),
      task_id: event.task_id,
      event_seq: event.seq,
      event_type: event.type,
    });
    if (
      task &&
      typeof receipt.receipt_id === "string" &&
      !task.evidence_ids.includes(receipt.receipt_id)
    )
      task.evidence_ids.push(receipt.receipt_id);
  }
  if (d.counters && typeof d.counters === "object")
    next.counters = { ...next.counters, ...(d.counters as Data) };
  if (d.runtime && typeof d.runtime === "object" && ((d.runtime as Data).mode !== "not_executed" || !next.runtime))
    next.runtime = d.runtime as Data;
  if (event.type === "patch.proposed" || event.type === "patch.applied")
    next.patch = {
      ...next.patch,
      ...d,
      applied: event.type === "patch.applied",
    };
  if (event.type === "run.started" && typeof d.scenario === "string") next.scenario = d.scenario;
  if (event.type === "repair.checked") next.repair_attempts = [...(next.repair_attempts || []), d];
  if (event.type === "evaluation.completed") next.evaluation = d;
  if (/^run\.(completed|blocked|failed|canceled)$/.test(event.type))
    next.status = event.type.slice(4);
  return next;
}
export function parseSnapshot(raw: unknown, id: string): Run {
  const s = raw as Partial<Run>;
  if (
    !s ||
    s.run_id !== id ||
    ![
      "queued",
      "running",
      "completed",
      "blocked",
      "failed",
      "canceled",
    ].includes(s.status || "") ||
    !["fixture", "live"].includes(s.mode || "") ||
    !Array.isArray(s.tasks) ||
    !Array.isArray(s.evidence) ||
    !s.counters ||
    typeof s.counters !== "object" ||
    Array.isArray(s.counters) ||
    !Number.isSafeInteger(s.last_seq) ||
    s.last_seq! < 0
  )
    throw Error(
      "Snapshot is incompatible: expected tasks, evidence, counters and last_seq. See frontend/README.md.",
    );
  if (
    s.tasks.some(
      (t) =>
        !t ||
        typeof t.goal !== "string" ||
        typeof t.spawn_reason !== "string" ||
        typeof t.role !== "string" ||
        !Number.isSafeInteger(t.depth) ||
        t.depth < 0 ||
        typeof t.status !== "string" ||
        typeof t.task_id !== "string" ||
        !(t.parent_id === null || typeof t.parent_id === "string") ||
        !Array.isArray(t.child_ids) ||
        !Array.isArray(t.evidence_ids),
    )
  )
    throw Error("Snapshot contains an invalid task.");
  const ids = new Set(s.tasks.map((t) => t.task_id));
  if (
    ids.size !== s.tasks.length ||
    s.evidence.some((e) => !e || typeof e !== "object" || Array.isArray(e))
  )
    throw Error("Snapshot contains duplicate tasks or invalid evidence.");
  for (const task of s.tasks) {
    const visited = new Set<string>();
    let cursor: Task | undefined = task;
    while (cursor) {
      if (visited.has(cursor.task_id))
        throw Error("Snapshot task lineage contains a cycle.");
      visited.add(cursor.task_id);
      if (cursor.parent_id === null) {
        if (cursor.depth !== 0) throw Error("Invalid root depth.");
        break;
      }
      const parent = s.tasks.find((t) => t.task_id === cursor!.parent_id);
      if (!parent || parent.depth + 1 !== cursor.depth)
        throw Error("Snapshot parent or depth is invalid.");
      cursor = parent;
    }
  }
  const events = (s.events || []).map(parseEvent);
  if (events.some((e) => e.run_id !== id || e.seq > Number(s.last_seq)))
    throw Error("Snapshot events are inconsistent.");
  return { ...emptyRun(id), ...s, events } as Run;
}
export function evaluationVerdict(e?: Data): {
  label: string;
  tone: string;
  reason: string;
} {
  if (!e)
    return {
      label: "Not evaluated",
      tone: "neutral",
      reason: "Replay, held-out attacks and legitimate purchases are required.",
    };
  const h = e.heldout as Data | undefined,
    l = e.legitimate as Data | undefined;
  if (
    e.evaluation_status === "failed" ||
    (typeof h?.violations === "number" && h.violations > 0)
  )
    return {
      label: "Failed",
      tone: "danger",
      reason: "A check failed. The repair is not verified.",
    };
  const complete =
    e.evaluation_status === "passed" &&
    e.repair_verified === true &&
    e.original_replay_passed === true &&
    h &&
    Number.isInteger(h.total) &&
    Number(h.total) > 0 &&
    h.errors === 0 &&
    h.violations === 0 &&
    h.blocked === h.total &&
    l &&
    Number.isInteger(l.total) &&
    Number(l.total) >= 2 &&
    l.accepted === l.total &&
    l.errors === 0;
  return complete
    ? {
        label: "Verified",
        tone: "success",
        reason:
          "Backend reports a verified repair with complete evaluation counts. Inspect receipts and review evidence.",
      }
    : {
        label: "Incomplete",
        tone: "warning",
        reason:
          "Missing checks, errors or inconsistent totals prevent verification.",
      };
}
export const textValue = (v: unknown, fallback = "Not reported") =>
  v === undefined || v === null ? fallback : String(v);
export const money = (v: unknown) =>
  typeof v === "number"
    ? new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
      }).format(v / 100)
    : "—";
