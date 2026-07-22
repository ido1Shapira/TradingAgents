import { useMemo } from "react";
import type { WsEvent } from "../lib/events";

interface DagNode {
  name: string;
  status: "pending" | "running" | "completed" | "errored";
  stage: string;
}

const AGENTS = [
  { name: "Market Analyst", stage: "market" },
  { name: "Sentiment Analyst", stage: "sentiment" },
  { name: "News Analyst", stage: "news" },
  { name: "Fundamentals Analyst", stage: "fundamentals" },
  { name: "Bull Researcher", stage: "research" },
  { name: "Bear Researcher", stage: "research" },
  { name: "Research Manager", stage: "research" },
  { name: "Trader", stage: "trader" },
  { name: "Aggressive Analyst", stage: "risk" },
  { name: "Conservative Analyst", stage: "risk" },
  { name: "Neutral Analyst", stage: "risk" },
  { name: "Portfolio Manager", stage: "risk" },
];

function statusForAgent(name: string, events: WsEvent[]): DagNode["status"] {
  const completed = events.some(e => e.type === "analyst_completed" && (e.data as any)?.node === name);
  const failed = events.some(e => e.type === "run_failed");
  const started = events.some(e => e.type === "analyst_started" && (e.data as any)?.node === name);
  if (completed) return "completed";
  if (failed) return "errored";
  if (started) return "running";
  return "pending";
}

const STATUS_STYLES: Record<DagNode["status"], { dot: string; bg: string; border: string }> = {
  completed: { dot: "bg-emerald-500", bg: "bg-emerald-50", border: "border-emerald-200" },
  running: { dot: "bg-brand-500 animate-pulse", bg: "bg-brand-50", border: "border-brand-200" },
  pending: { dot: "bg-slate-400", bg: "bg-white", border: "border-slate-200" },
  errored: { dot: "bg-red-500", bg: "bg-red-50", border: "border-red-200" },
};

export function ObservatoryDag({ events, onNodeClick }: { events: WsEvent[]; onNodeClick: (name: string) => void }) {
  const nodes = useMemo(() => AGENTS.map(a => ({ ...a, status: statusForAgent(a.name, events) })), [events]);

  return (
    <div className="glass-panel p-3 space-y-3" data-testid="observatory-dag">
      <span className="section-header">Agent Flow</span>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2">
        {nodes.map(n => {
          const s = STATUS_STYLES[n.status];
          return (
            <button key={n.name} data-testid={`dag-node-${n.name}`}
              onClick={() => onNodeClick(n.name)}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-left text-xs transition-all hover:brightness-125 ${s.bg} ${s.border}`}>
              <span className={`w-2 h-2 rounded-full shrink-0 ${s.dot}`} />
              <div className="min-w-0">
                <div className="text-slate-700 truncate font-medium">{n.name}</div>
                <div className="text-slate-400 capitalize text-[10px]">{n.status}</div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
