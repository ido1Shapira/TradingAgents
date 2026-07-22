import type { Verdict } from "../verdicts";
import { actionColor } from "../verdicts";
import { fmtPct, fmtPrice, fmtTime } from "../lib/format";

export interface RunListItemProps {
  run: {
    id: string;
    started_at: string | null;
    decision_action: string | null;
    decision_target: number | null;
    start_price: number | null;
  };
  verdict: Verdict;
  selected: boolean;
  scale: "m" | "h" | "d";
  onClick: () => void;
}

function verdictBadge(v: Verdict): { glyph: string; tone: string; subtext: string; color: string } {
  if (v.status === "right") {
    return { glyph: "✓", tone: "text-emerald-700", subtext: v.reason === "within_threshold" ? "within" : "hit", color: "#10b981" };
  }
  if (v.status === "wrong") {
    return { glyph: "✗", tone: "text-red-700", subtext: v.reason === "threshold_exceeded" ? "exceeded" : "miss", color: "#ef4444" };
  }
  if (v.reason === "incomplete_window") return { glyph: "?", tone: "text-slate-400", subtext: "pending", color: "#64748b" };
  if (v.reason === "no_data") return { glyph: "?", tone: "text-slate-400", subtext: "no data", color: "#64748b" };
  if (v.reason === "tie") return { glyph: "?", tone: "text-slate-400", subtext: "tie", color: "#64748b" };
  if (v.reason === "no_start_price") return { glyph: "?", tone: "text-slate-400", subtext: "no start price", color: "#64748b" };
  if (v.reason === "unknown_action") return { glyph: "?", tone: "text-slate-400", subtext: "unknown action", color: "#64748b" };
  return { glyph: "?", tone: "text-slate-400", subtext: "unknown", color: "#64748b" };
}

export function RunListItem({ run, verdict, selected, scale, onClick }: RunListItemProps) {
  const t = run.started_at ? new Date(run.started_at).getTime() : null;
  const badge = verdictBadge(verdict);
  const pct = verdict.pctMove;
  const ac = run.decision_action ? actionColor(run.decision_action) : "#64748b";
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={`Run from ${run.started_at ? new Date(run.started_at).toLocaleString() : 'unknown time'} - ${verdict.status}`}
      data-testid={`run-row-${run.id}`}
      className={`w-full text-left px-3 py-2.5 border-b border-slate-200 hover:bg-slate-50 transition-colors ${
        selected ? "bg-brand-50 border-l-2 border-l-brand-500" : "border-l-2 border-l-transparent"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xs font-mono text-slate-400 w-20 shrink-0">
            {t != null ? fmtTime(t, scale) : "—"}
          </span>
          <span
            className="text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded-md"
            style={{ color: ac, backgroundColor: `${ac}15`, border: `1px solid ${ac}30` }}
          >
            {run.decision_action ?? "—"}
          </span>
          {run.start_price != null && (
            <span className="text-xs data-text text-slate-400">${fmtPrice(run.start_price)}</span>
          )}
          {run.decision_target != null && run.decision_action !== "HOLD" && (
            <>
              <span className="text-xs text-slate-400">→</span>
              <span className="text-xs data-text text-slate-400">${fmtPrice(run.decision_target)}</span>
            </>
          )}
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {pct != null && (
            <span className={`text-xs data-text font-medium ${pct >= 0 ? "text-emerald-700" : "text-red-700"}`}>
              {fmtPct(pct)}
            </span>
          )}
          <span className={`text-sm ${badge.tone}`} title={badge.subtext}>
            {badge.glyph}
          </span>
        </div>
      </div>
    </button>
  );
}
