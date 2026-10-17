import { describe, expect, it } from "vitest";
import {
  applyEvent,
  emptyRun,
  evaluationVerdict,
  parseEvent,
  parseSnapshot,
} from "./model";
import { fixtureEvents, fixtureRun } from "./fixture";
describe("event integrity", () => {
  it("preserves real fixture lineage and root counters", () => {
    const run = fixtureRun();
    expect(run.tasks.map((t) => [t.task_id, t.parent_id, t.depth])).toEqual([
      ["root", null, 0],
      ["attack-1", "root", 1],
      ["attack-1a", "attack-1", 2],
    ]);
    expect(run.tasks[1].child_ids).toEqual(["attack-1a"]);
    expect(run.counters.model_calls).toBe(0);
  });
  it("deduplicates events without changing state", () => {
    const run = fixtureRun();
    expect(applyEvent(run, fixtureEvents[4])).toBe(run);
  });
  it("rejects cross-run data and missing sequences", () => {
    const run = emptyRun("fixture-run-1");
    expect(() => applyEvent(run, fixtureEvents[1])).toThrow(
      "Missing event sequence",
    );
    expect(() => applyEvent(emptyRun("other"), fixtureEvents[0])).toThrow(
      "different run",
    );
  });
  it("rejects malformed envelopes and snapshots", () => {
    expect(() => parseEvent({ seq: 1 })).toThrow();
    expect(() =>
      parseSnapshot({ run_id: "r", status: "running" }, "r"),
    ).toThrow();
  });
  it.each(["blocked", "failed", "canceled"])(
    "retains %s status and error data",
    (status) => {
      const run = applyEvent(emptyRun("fixture-run-1"), fixtureEvents[0]);
      const next = applyEvent(run, {
        ...fixtureEvents[1],
        type: `run.${status}`,
        data: { error_code: "budget_exhausted" },
      });
      expect(next.status).toBe(status);
      expect(next.events[1].data.error_code).toBe("budget_exhausted");
    },
  );
});
describe("verification fails closed", () => {
  const complete = {
    evaluation_status: "passed",
    repair_verified: true,
    original_replay_passed: true,
    heldout: { total: 8, blocked: 8, violations: 0, errors: 0 },
    legitimate: { total: 2, accepted: 2, errors: 0 },
  };
  it("never verifies a completed fixture", () =>
    expect(evaluationVerdict(fixtureRun().evaluation).label).toBe(
      "Incomplete",
    ));
  it("requires complete positive case counts", () => {
    expect(evaluationVerdict(complete).label).toBe("Verified");
    expect(
      evaluationVerdict({
        ...complete,
        heldout: { total: 0, blocked: 0, violations: 0, errors: 0 },
      }).label,
    ).toBe("Incomplete");
    expect(
      evaluationVerdict({
        ...complete,
        legitimate: { total: 1, accepted: 1, errors: 0 },
      }).label,
    ).toBe("Incomplete");
  });
  it("rejects errors, inconsistent totals and violations", () => {
    expect(
      evaluationVerdict({
        ...complete,
        heldout: { total: 8, blocked: 7, violations: 0, errors: 1 },
      }).label,
    ).toBe("Incomplete");
    expect(
      evaluationVerdict({
        ...complete,
        heldout: { total: 8, blocked: 8, violations: 1, errors: 0 },
      }).label,
    ).toBe("Failed");
    expect(
      evaluationVerdict({ ...complete, original_replay_passed: false }).label,
    ).toBe("Incomplete");
  });
});

it("appending receipt evidence does not mutate a prior snapshot", () => {
  const before = fixtureEvents
    .slice(0, 5)
    .reduce(applyEvent, emptyRun("fixture-run-1"));
  const after = applyEvent(before, fixtureEvents[5]);
  expect(
    before.tasks.find((t) => t.task_id === "attack-1a")?.evidence_ids,
  ).toEqual([]);
  expect(
    after.tasks.find((t) => t.task_id === "attack-1a")?.evidence_ids,
  ).toEqual(["fixture-receipt-01"]);
});
