import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchRunDetail, type RunDetail } from "../lib/api";
import type { RunLike } from "../verdicts";

interface Props {
  runs: RunLike[];
  onClose: () => void;
}

/* ─── helpers ────────────────────────────────────────── */

const STAGE_DOTS = [
  { key: "market", label: "Mkt" },
  { key: "sentiment", label: "Snt" },
  { key: "news", label: "Nws" },
  { key: "fundamentals", label: "Fnd" },
  { key: "research", label: "Rsh" },
  { key: "trader", label: "Trd" },
  { key: "risk", label: "Rsk" },
] as const;

function completedStages(events: RunDetail["events"]): Set<string> {
  const done = new Set<string>();
  for (const e of events) {
    if (e.type === "analyst_completed") {
      const stage = (e.data as Record<string, unknown>)?.stage as
        | string
        | undefined;
      if (stage) done.add(stage);
    }
  }
  return done;
}

function lastReportExcerpt(
  events: RunDetail["events"],
): { stage: string; text: string } | null {
  for (let i = events.length - 1; i >= 0; i--) {
    const e = events[i];
    if (e.type === "analyst_completed") {
      const d = e.data as Record<string, unknown>;
      const stage = (d.stage as string) ?? "";
      const excerpt = d.report_excerpt as string | undefined;
      const text = d.report_text as string | undefined;
      const content = excerpt ?? (text ? text.slice(0, 300) : null);
      if (content) return { stage, text: content };
    }
  }
  return null;
}

function fmtShortDate(iso: string): string {
  const d = new Date(iso);
  const mo = d.toLocaleDateString(undefined, { month: "short" });
  const day = d.getDate();
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${mo} ${day}, ${hh}:${mm}`;
}

/* ─── Mini Pipeline (stage dots) ─────────────────────── */

function MiniPipeline({ events }: { events: RunDetail["events"] }) {
  const done = useMemo(() => completedStages(events), [events]);
  return (
    <div className="flex items-center gap-1 flex-wrap">
      {STAGE_DOTS.map((s) => {
        const isDone = done.has(s.key);
        return (
          <span
            key={s.key}
            className={`inline-flex items-center justify-center rounded text-[9px] font-semibold px-1.5 py-0.5 transition-colors ${
              isDone
                ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                : "bg-white text-slate-400 border border-slate-200"
            }`}
            title={s.key}
          >
            {isDone ? "✓" : s.label}
          </span>
        );
      })}
    </div>
  );
}

/* ─── Single-run comparison panel ────────────────────── */

function RunPanel({ runId }: { runId: string }) {
  const {
    data: detail,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["run-comparison-detail", runId],
    queryFn: () => fetchRunDetail(runId),
    enabled: !!runId,
  });

  const report = useMemo(
    () => (detail ? lastReportExcerpt(detail.events ?? []) : null),
    [detail],
  );
  const events = detail?.events ?? [];

  /* ── loading state ── */
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="w-8 h-8 rounded-full border-2 border-brand-200 border-t-brand-600 animate-spin" />
      </div>
    );
  }

  /* ── error state ── */
  if (error || !detail) {
    return (
      <div className="py-8 px-2 text-xs text-slate-600 text-center">
        <p>
          Failed to load:{" "}
          <span className="font-mono text-red-700">
            {error instanceof Error ? error.message : "Unknown error"}
          </span>
        </p>
      </div>
    );
  }

  const action = detail.decision_action;
  const isBuy = action === "BUY";
  const isSell = action === "SELL";
  const actionColorClass = isBuy
    ? "text-emerald-700 bg-emerald-50 border-emerald-200"
    : isSell
      ? "text-red-700 bg-red-50 border-red-200"
      : "text-slate-600 bg-slate-100 border-slate-200";
  const confidence = detail.decision_confidence ?? 0;
  const pct = Math.max(0, Math.min(1, confidence)) * 100;

  return (
    <div className="space-y-3">
      {/* ── header: ticker + action badge + date ── */}
      <div>
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-sm font-semibold text-slate-900">
            {detail.ticker}
          </span>
          <span
            className={`text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded-md border ${actionColorClass}`}
          >
            {action ?? "—"}
          </span>
        </div>
        <div className="text-[10px] text-slate-400 font-mono">
          {detail.started_at ? fmtShortDate(detail.started_at) : "—"}
        </div>
      </div>

      {/* ── confidence bar ── */}
      <div>
        <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
          <span>Confidence</span>
          <span className="data-text text-slate-700 text-xs">
            {pct.toFixed(0)}%
          </span>
        </div>
        <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              isBuy
                ? "bg-emerald-500"
                : isSell
                  ? "bg-red-500"
                  : "bg-slate-500"
            }`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* ── mini pipeline flow ── */}
      <div>
        <div className="section-header mb-1.5">Pipeline</div>
        <MiniPipeline events={events} />
      </div>

      {/* ── decision summary ── */}
      <div>
        <div className="section-header mb-1.5">Decision</div>
        <div className="text-xs space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-slate-400">Action:</span>
            <span
              className={`font-semibold ${
                isBuy
                  ? "text-emerald-700"
                  : isSell
                    ? "text-red-700"
                    : "text-slate-600"
              }`}
            >
              {action ?? "—"}
            </span>
            {detail.decision_target != null && (
              <>
                <span className="text-slate-400">→</span>
                <span className="data-text text-slate-700">
                  ${Number(detail.decision_target).toFixed(2)}
                </span>
              </>
            )}
          </div>
          {detail.decision_rationale && (
            <p className="text-slate-600 leading-relaxed">
              {detail.decision_rationale.length > 250
                ? detail.decision_rationale.slice(0, 250) + "…"
                : detail.decision_rationale}
            </p>
          )}
        </div>
      </div>

      {/* ── report excerpt ── */}
      {report && (
        <div>
          <div className="section-header mb-1.5">
            Report ({report.stage})
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            {report.text.length > 280
              ? report.text.slice(0, 280) + "…"
              : report.text}
          </p>
        </div>
      )}
    </div>
  );
}

/* ─── main component ──────────────────────────────────── */

export function RunComparison({ runs, onClose }: Props) {
  const sorted = useMemo(
    () =>
      [...runs].sort(
        (a, b) =>
          new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime(),
      ),
    [runs],
  );

  const [leftId, setLeftId] = useState(sorted[0]?.id ?? "");
  const [rightId, setRightId] = useState(
    sorted[1]?.id ?? sorted[0]?.id ?? "",
  );

  /* ── empty state ── */
  if (runs.length === 0) {
    return (
      <div className="glass-panel p-6 text-center">
        <p className="text-sm text-slate-400">No runs to compare.</p>
        <button
          onClick={onClose}
          className="mt-3 text-xs text-brand-600 hover:text-brand-700 transition-colors"
        >
          Close
        </button>
      </div>
    );
  }

  return (
    <div className="glass-panel">
      {/* ── toolbar: selectors + close ── */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
              Left
            </label>
            <select
              value={leftId}
              onChange={(e) => setLeftId(e.target.value)}
              className="text-xs bg-white border border-slate-200 rounded-lg px-2 py-1.5 text-slate-700 focus:outline-none focus:ring-2 focus:ring-brand-200 max-w-[180px]"
            >
              {sorted.map((r) => (
                <option key={r.id} value={r.id}>
                  {fmtShortDate(r.startedAt)} — {r.decisionAction ?? "—"}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
              Right
            </label>
            <select
              value={rightId}
              onChange={(e) => setRightId(e.target.value)}
              className="text-xs bg-white border border-slate-200 rounded-lg px-2 py-1.5 text-slate-700 focus:outline-none focus:ring-2 focus:ring-brand-200 max-w-[180px]"
            >
              {sorted.map((r) => (
                <option key={r.id} value={r.id}>
                  {fmtShortDate(r.startedAt)} — {r.decisionAction ?? "—"}
                </option>
              ))}
            </select>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-xs text-slate-400 hover:text-slate-700 transition-colors"
        >
          Close
        </button>
      </div>

      {/* ── side-by-side panels ── */}
      <div className="grid grid-cols-2 gap-0">
        <div className="p-4 border-r border-slate-200">
          {leftId && <RunPanel runId={leftId} />}
        </div>
        <div className="p-4">
          {rightId && <RunPanel runId={rightId} />}
        </div>
      </div>
    </div>
  );
}
