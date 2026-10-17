import { useEffect, useMemo, useRef, useState } from "react";
import {
  Crosshair,
  Minus,
  Plus,
  ScanSearch,
  ShoppingBag,
  ShieldCheck,
  Wrench,
  GitBranch,
} from "lucide-react";
import type { Run, Task } from "./model";
import "./canvas-graph.css";
import AgentRobot from "./AgentRobot";
type Point = { x: number; y: number };
export interface InvestigationCanvasProps {
  run: Run;
  selected: string;
  onSelect: (id: string) => void;
}
const roleName = (t: Task) =>
  t.role === "repair"
    ? "Repair agent"
    : t.role === "reviewer"
      ? "Independent reviewer"
      : t.role === "attacker"
        ? "Attack investigator"
        : t.depth > 0
          ? "Child investigator"
          : "Lead investigator";
export default function InvestigationCanvas({
  run,
  selected,
  onSelect,
}: InvestigationCanvasProps) {
  const area = useRef<HTMLDivElement>(null),
    drag = useRef<{ x: number; y: number; origin: Point } | null>(null);
  const [size, setSize] = useState({ width: 1000, height: 700 }),
    [zoom, setZoom] = useState(1),
    [pan, setPan] = useState<Point>({ x: 0, y: 0 });
  useEffect(() => {
    if (!area.current) return;
    const o = new ResizeObserver(([e]) =>
      setSize({ width: e.contentRect.width, height: e.contentRect.height }),
    );
    o.observe(area.current);
    return () => o.disconnect();
  }, []);
  useEffect(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, [run.run_id]);
  const compact = size.width < 750;
  const positions = useMemo(() => {
    const p = new Map<string, Point>();
    if (compact) {
      const rows = Math.ceil(run.tasks.length / 2);
      run.tasks.forEach((task, index) =>
        p.set(task.task_id, {
          x: index % 2 === 0 ? -210 : 210,
          y: (Math.floor(index / 2) - (rows - 1) / 2) * 170,
        }),
      );
      return p;
    }
    const inner = run.tasks.filter((t) => t.depth <= 1),
      count = Math.max(inner.length, 5);
    inner.forEach((t, i) => {
      const a = ((-150 + (i * 360) / count) * Math.PI) / 180;
      p.set(t.task_id, { x: Math.cos(a) * 320, y: Math.sin(a) * 230 });
    });
    run.tasks
      .filter((t) => t.depth > 1)
      .forEach((t) => {
        const parent = p.get(t.parent_id || "") || { x: 320, y: 0 };
        const siblings = run.tasks.filter((s) => s.parent_id === t.parent_id);
        const siblingOffset =
          (siblings.findIndex((s) => s.task_id === t.task_id) -
            (siblings.length - 1) / 2) *
          190;
        p.set(t.task_id, {
          x: parent.x + (parent.x >= 0 ? 310 : -310),
          y: parent.y + (parent.y >= 0 ? 90 : -90) + siblingOffset,
        });
      });
    return p;
  }, [run.tasks, compact]);
  const bounds = [...positions.values()],
    maxX = Math.max(
      compact ? 320 : 420,
      ...bounds.map((p) => Math.abs(p.x) + 110),
    ),
    maxY = Math.max(
      compact ? 110 : 285,
      ...bounds.map((p) => Math.abs(p.y) + 65),
    ),
    fit = Math.min(
      1,
      Math.max(0.25, (size.width - 40) / (maxX * 2)),
      Math.max(0.25, (size.height - 45) / (maxY * 2)),
    ),
    scale = fit * zoom,
    root = run.tasks.find((t) => t.parent_id === null);
  return (
    <section
      className={`ig-canvas ${compact ? "ig-compact" : ""}`}
      aria-label="Live investigation canvas"
    >
      <div
        className="ig-map-area"
        ref={area}
        onPointerDown={(e) => {
          if ((e.target as HTMLElement).closest("button")) return;
          drag.current = { x: e.clientX, y: e.clientY, origin: pan };
          e.currentTarget.setPointerCapture(e.pointerId);
        }}
        onPointerMove={(e) => {
          if (drag.current)
            setPan({
              x: drag.current.origin.x + e.clientX - drag.current.x,
              y: drag.current.origin.y + e.clientY - drag.current.y,
            });
        }}
        onPointerUp={() => {
          drag.current = null;
        }}
        onPointerCancel={() => {
          drag.current = null;
        }}
      >
        <div
          className="ig-world"
          style={{
            transform: `translate(${size.width / 2 + pan.x}px,${size.height / 2 + pan.y}px) scale(${scale})`,
          }}
        >
          <svg
            className="ig-connections"
            width="2000"
            height="1400"
            viewBox="-1000 -700 2000 1400"
            aria-hidden="true"
          >
            {root && positions.get(root.task_id) && (
              <path
                className="ig-target-link"
                d={`M 0 0 L ${positions.get(root.task_id)!.x} ${positions.get(root.task_id)!.y}`}
              />
            )}
            {run.tasks.map((t) => {
              const s = positions.get(t.parent_id || ""),
                d = positions.get(t.task_id);
              if (!s || !d) return null;
              const x = (s.x + d.x) / 2,
                y = (s.y + d.y) / 2,
                l = Math.hypot(x, y) || 1;
              return (
                <path
                  key={t.task_id}
                  className={`ig-edge ${t.status === "running" ? "ig-edge-active" : ""} ${selected === t.task_id ? "ig-edge-selected" : ""}`}
                  d={`M ${s.x} ${s.y} Q ${x + (x / l) * 80} ${y + (y / l) * 80} ${d.x} ${d.y}`}
                />
              );
            })}
          </svg>
          <button
            type="button"
            className={`ig-target ${selected === "target" ? "ig-selected" : ""}`}
            onClick={() => onSelect("target")}
            aria-pressed={selected === "target"}
          >
            <span className="ig-target-robot">
              <AgentRobot role="shopping" status={run.status} />
            </span>
            <span className="ig-target-eyebrow">SYSTEM UNDER TEST</span>
            <strong>Shopping agent</strong>
            <span className="ig-target-caption">
              Simulated checkout environment
            </span>
            <span className="ig-target-foot">
              <span className="ig-blue-dot" />
              {run.mode === "fixture" ? "Fixture mode" : "Live model mode"}
            </span>
          </button>
          {run.tasks.map((t) => {
            const p = positions.get(t.task_id);
            if (!p) return null;
            const repairIndex = run.tasks
              .filter((task) => task.role === "repair")
              .findIndex((task) => task.task_id === t.task_id);
            const attempt =
              repairIndex >= 0 ? run.repair_attempts?.[repairIndex] : undefined;
            const checkStatus =
              attempt?.status === "rejected"
                ? "Checks failed"
                : attempt?.status === "passed_public_checks"
                  ? "Public checks passed"
                  : undefined;
            const finding =
              t.status === "failed"
                ? "Task could not finish"
                : attempt?.status === "rejected"
                  ? Number(attempt.legitimate_accepted) <
                    Number(attempt.legitimate_total)
                    ? "Blocked a normal purchase"
                    : "First fix failed checks"
                  : attempt?.status === "passed_public_checks"
                    ? "Revised rules passed checks"
                    : t.role === "repair"
                      ? "Repairing checkout rules"
                      : t.role === "reviewer"
                        ? t.status === "completed"
                          ? "Evidence reviewed"
                          : "Checking the evidence"
                        : t.depth > 0
                          ? "Why did the fix fail?"
                          : "Can discounts be abused?";
            return (
              <button
                type="button"
                key={t.task_id}
                className={`ig-task ig-status-${t.status} ${checkStatus === "Checks failed" ? "ig-check-rejected" : checkStatus ? "ig-check-passed" : ""} ${selected === t.task_id ? "ig-selected" : ""}`}
                style={{ left: p.x, top: p.y }}
                onClick={() => onSelect(t.task_id)}
                aria-label={`${roleName(t)}, ${t.status}: ${t.goal}`}
                aria-pressed={selected === t.task_id}
              >
                <span className="ig-task-robot">
                  <AgentRobot
                    role={t.role}
                    status={t.status}
                    rejected={checkStatus === "Checks failed"}
                  />
                </span>
                <span className="ig-task-top">
                  <span className="ig-task-role">{finding}</span>
                  <span className="ig-status-dot" title={t.status} />
                </span>
                <span className="ig-task-goal">{roleName(t)}</span>
                <span className="ig-task-meta">
                  <span title={`Task ${t.status}`}>
                    {checkStatus || t.status}
                  </span>
                </span>
              </button>
            );
          })}
        </div>
        {!run.tasks.length && (
          <div className="ig-empty-caption">
            Start an investigation to watch the agents build their task tree.
          </div>
        )}
      </div>
      <div className="ig-map-controls" aria-label="Canvas navigation">
        <button
          type="button"
          aria-label="Zoom out"
          disabled={zoom <= 0.55}
          onClick={() => setZoom((v) => Math.max(0.55, v - 0.15))}
        >
          <Minus size={15} />
        </button>
        <span>{Math.round(scale * 100)}%</span>
        <button
          type="button"
          aria-label="Zoom in"
          disabled={zoom >= 2}
          onClick={() => setZoom((v) => Math.min(2, v + 0.15))}
        >
          <Plus size={15} />
        </button>
        <span className="ig-control-divider" />
        <button
          type="button"
          aria-label="Fit investigation to view"
          onClick={() => {
            setZoom(1);
            setPan({ x: 0, y: 0 });
          }}
        >
          <Crosshair size={16} />
        </button>
      </div>
      <div className="ig-map-legend">
        <span className="ig-blue-dot" />
        Actual task lineage<span>·</span>Drag to explore
      </div>
    </section>
  );
}
