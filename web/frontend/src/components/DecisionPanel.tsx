import { TrendingUp, TrendingDown } from "lucide-react";
import type { RunDetail } from "../lib/api";

interface Props {
  action: "BUY" | "SELL" | "HOLD" | string;
  target: number | null;
  confidence: number;
  rationale: string;
  degraded?: boolean;
  run?: RunDetail | null;
}

export function DecisionPanel({ action, target, confidence, rationale, degraded }: Props) {
  const isBuy = action === "BUY";
  const isSell = action === "SELL";
  const actionColor = isBuy ? "text-emerald-700" : isSell ? "text-red-700" : "text-slate-600";
  const actionBg = isBuy ? "bg-emerald-50 border-emerald-200" : isSell ? "bg-red-50 border-red-200" : "bg-brand-50 border-brand-100";
  const accentBorder = isBuy ? "border-l-emerald-500" : isSell ? "border-l-red-500" : "border-l-slate-500";
  const pct = Math.max(0, Math.min(1, confidence)) * 100;
  return (
    <div
      className={`glass-panel mt-4 border-l-2 ${accentBorder} ${degraded ? "opacity-80" : ""}`}
      role="region"
      aria-label={`Decision: ${action}${target != null ? ` at $${target}` : ""}`}
    >
      <div className="flex items-center gap-3 mb-3">
        <span className={`tag ${actionBg} text-sm font-semibold ${actionColor}`} role="status" aria-label={`Action: ${action}`}>
          {isBuy && <TrendingUp className="w-3.5 h-3.5 mr-1" />}
          {isSell && <TrendingDown className="w-3.5 h-3.5 mr-1" />}
          <span className="inline-flex items-center gap-1">{action}</span>
        </span>
        {target != null && <span className="text-lg data-text text-slate-700">@ ${target.toFixed(2)}</span>}
        <div className="flex-1" />
        {degraded && <span className="text-[10px] font-medium text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-md">degraded</span>}
      </div>
      <div className="flex items-center justify-between text-xs text-slate-500 mb-1.5">
        <span id="confidence-label">Confidence</span>
        <span className="data-text font-semibold text-slate-700" aria-labelledby="confidence-label">{pct.toFixed(0)}%</span>
      </div>
      <div className="progress-bar" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: isBuy ? "linear-gradient(90deg, #10b981, #34d399)" : isSell ? "linear-gradient(90deg, #ef4444, #f87171)" : "linear-gradient(90deg, #64748b, #94a3b8)" }} />
      </div>
      <p className="text-sm text-slate-600 mt-3 whitespace-pre-wrap leading-relaxed">{rationale}</p>
    </div>
  );
}
