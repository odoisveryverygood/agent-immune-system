import http from "node:http";
let scenario = "normal",
  store = null,
  lastRequest = null,
  streams = 0;
const event = (seq, type, task_id = "root", parent_id = null, data = {}) => ({
  schema_version: 1,
  run_id: "http-fixture-1",
  seq,
  timestamp: "2026-10-17T20:00:00Z",
  type,
  task_id,
  parent_id,
  data,
});
const root = {
  task_id: "root",
  parent_id: null,
  role: "investigator",
  goal: "HTTP fixture investigation",
  spawn_reason: "Root investigation",
  depth: 0,
  status: "running",
  evidence_ids: [],
  child_ids: [],
};
const child = {
  ...root,
  task_id: "child",
  parent_id: "root",
  role: "attacker",
  goal: "HTTP child evidence",
  spawn_reason: "Receipt evidence: http-receipt",
  depth: 1,
  status: "queued",
};
http
  .createServer(async (req, res) => {
    const url = new URL(req.url, "http://localhost");
    let raw = "";
    for await (const chunk of req) raw += chunk;
    const json = (status, data) => {
      res.writeHead(status, { "Content-Type": "application/json" });
      res.end(JSON.stringify(data));
    };
    if (url.pathname === "/__test/reset") {
      scenario = JSON.parse(raw || "{}").scenario || "normal";
      store = null;
      streams = 0;
      return json(200, {});
    }
    if (url.pathname === "/__test/request") return json(200, lastRequest);
    if (url.pathname === "/api/runs" && req.method === "POST") {
      lastRequest = JSON.parse(raw);
      if (scenario === "missing")
        return json(503, { error_code: "missing_provider_configuration" });
      store = {
        run_id: "http-fixture-1",
        mode: lastRequest.mode,
        scenario: lastRequest.scenario || "investigation",
        status: "running",
        tasks: [structuredClone(root)],
        evidence: [],
        counters: { model_calls: 0, tool_calls: 0 },
        last_seq: 0,
        events: [],
      };
      return json(200, { run_id: store.run_id, status: "queued" });
    }
    if (url.pathname === "/api/runs/http-fixture-1/cancel") {
      store.status = "canceled";
      store.events.push(
        event(++store.last_seq, "run.canceled", "root", null, {
          reason: "All active work stopped",
        }),
      );
      return json(200, { status: "canceled" });
    }
    if (url.pathname === "/api/runs/http-fixture-1")
      return store ? json(200, store) : json(404, {});
    if (url.pathname === "/api/runs/http-fixture-1/events") {
      res.writeHead(200, {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      });
      if (scenario === "running") {
        res.write(": connected\n\n");
        const keep = setInterval(() => res.write(": keepalive\n\n"), 1000);
        res.on("close", () => clearInterval(keep));
        return;
      }
      const events = [
        event(1, "run.started", "root", null, { mode: store.mode, scenario: store.scenario }),
        event(2, "task.created", "child", "root", { ...child }),
        event(3, "task.created", "grandchild", "child", {
          role: "attacker",
          depth: 2,
          goal: "HTTP grandchild",
          spawn_reason: "Narrow http-receipt evidence",
        }),
      ];
      if (scenario === "gap") {
        res.write(`data: ${JSON.stringify(events[1])}\n\n`);
        return res.end();
      }
      const status = scenario === "timeout" ? "failed" : "blocked";
      events.push(
        event(4, `run.${status}`, "root", null, {
          error_code:
            scenario === "timeout" ? "deadline_exceeded" : "budget_exhausted",
        }),
      );
      if (scenario === "revision") {
        store.repair_attempts = [
          {attempt: 1, policy_version: "candidate-one", status: "rejected", original_replay_passed: true, legitimate_accepted: 0, legitimate_total: 2},
          {attempt: 2, policy_version: "candidate-two", status: "passed_public_checks", original_replay_passed: true, legitimate_accepted: 2, legitimate_total: 2},
        ];
        store.evidence = [
          {tool:"checkout", receipt_id:"before", case_id:"original", status:"accepted", charged_total_cents:0, minimum_allowed_total_cents:45000, policy_version:"v0"},
          {tool:"checkout", receipt_id:"first-replay", case_id:"original", status:"denied", charged_total_cents:null, policy_version:"candidate-one"},
          {tool:"checkout", receipt_id:"final-replay", case_id:"original", status:"accepted", charged_total_cents:50000, policy_version:"candidate-two"},
        ];
        events.pop();
        for (const attempt of store.repair_attempts) events.push(event(events.length + 1, "repair.checked", "root", null, attempt));
        events.push(event(events.length + 1, "run.blocked", "root", null, {error_code: "final_review_pending"}));
      }
      streams++;
      if (scenario === "disconnect" && streams === 1) events.pop();
      store.tasks = [structuredClone(root)];
      store.tasks[0].child_ids = ["child"];
      store.tasks.push(
        { ...child, child_ids: ["grandchild"] },
        {
          ...child,
          task_id: "grandchild",
          parent_id: "child",
          depth: 2,
          goal: "HTTP grandchild",
          spawn_reason: "Narrow http-receipt evidence",
        },
      );
      store.status = events.length === 3 ? "running" : status;
      store.events = events;
      store.last_seq = events.length;
      for (const e of events.filter(
        (e) => e.seq > Number(url.searchParams.get("after_seq") || 0),
      )) {
        res.write(`id: ${e.seq}\ndata: ${JSON.stringify(e)}\n\n`);
        if (e.seq === 2) res.write(`data: ${JSON.stringify(e)}\n\n`);
      }
      return res.end();
    }
    return json(404, {});
  })
  .listen(8788, "127.0.0.1");
