import { Bot, Cpu, Timer, Wrench } from "lucide-react";

interface PipelineStatsProps {
  agentsDone: number;
  agentsTotal: number;
  llmCalls: number;
  toolCalls: number;
  elapsedSec: number;
}

export function PipelineStats({ agentsDone, agentsTotal, llmCalls, toolCalls, elapsedSec }: PipelineStatsProps) {
  const fmt = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  };

  return (
    <div className="flex items-center gap-3 mt-2.5 pt-2 border-t border-brand-100 text-[10px] font-mono text-slate-500">
      <span className="flex items-center gap-1">
        <Bot className="w-3 h-3" style={{ color: agentsDone === agentsTotal ? "#34d399" : "#38bdf8" }} />
        <span className="font-semibold tabular-nums" style={{ color: agentsDone === agentsTotal ? "#34d399" : "#94a3b8" }}>
          {agentsDone}
        </span>
        <span className="text-slate-400">/</span>
        <span className="text-slate-600">{stats.agentsTotal}</span>
        <span className="text-slate-400">agents</span>
      </span>
      <span className="w-px h-3 bg-brand-100" />
      <Cpu className="w-3 h-3 text-brand-600" />
      <span className="text-brand-600 tabular-nums">{llmCalls}</span>
      <span className="w-px h-3 bg-brand-100" />
      <Wrench className="w-3 h-3 text-amber-700" />
      <span className="text-amber-700 tabular-nums">{toolCalls}</span>
      <span className="w-px h-3 bg-brand-100" />
      <Timer className="w-3 h-3 text-slate-500" />
      <span className="text-slate-700 tabular-nums">{fmt(elapsedSec)}</span>
    </div>
  );
}
