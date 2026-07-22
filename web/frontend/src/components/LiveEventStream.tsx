import { useState, useEffect, useRef, useMemo } from "react";
import { MessageSquare, AlertTriangle, Wrench, Play } from "lucide-react";
import { useFocusedRunEvents } from "../hooks/useFocusedRunEvents";
import { formatDuration } from "../lib/format";
import type { WsEvent } from "../lib/events";

const colorForType: Record<string, string> = {
  analyst_started: "bg-brand-50 text-brand-600 border-l-brand-500",
  analyst_thinking: "bg-brand-50/60 text-brand-600/80 border-l-brand-500/50",
  analyst_completed: "bg-brand-50 text-brand-600 border-l-brand-500",
  tool_call: "bg-brand-50 text-slate-600 border-l-slate-400",
  tool_result: "bg-brand-50 text-slate-600 border-l-slate-400",
  debate_message: "bg-amber-50 text-amber-700 border-l-amber-500",
  risk_message: "bg-amber-50 text-amber-700 border-l-amber-500",
  decision: "bg-emerald-50 text-emerald-700 border-l-emerald-500",
  run_failed: "bg-red-50 text-red-700 border-l-red-500",
  run_finished: "bg-emerald-50 text-emerald-700/80 border-l-emerald-500",
  server_notice: "bg-brand-50 text-slate-600 border-l-slate-400",
};

type EventData = Record<string, unknown>;
type Formatter = (data: EventData) => string;

function formatRunFailed(data: EventData): string {
  const reason = String(data.reason ?? "unknown");
  const cls = data.exception_class ? String(data.exception_class) : null;
  const msg = data.message ? String(data.message) : null;
  if (cls && msg) return `failed: ${reason} (${cls}: ${msg})`;
  if (cls) return `failed: ${reason} (${cls})`;
  if (msg) return `failed: ${reason}: ${msg}`;
  return `failed: ${reason}`;
}

const formatBubble: Record<string, Formatter> = {
  analyst_started: (d) =>
    `analyst_started: ${d.node ?? d.stage ?? "(unknown node)"}`,
  analyst_thinking: (d) => String(d.node ?? d.stage ?? "thinking"),
  analyst_completed: (d) =>
    `analyst_completed: ${d.stage ?? d.node ?? "(unknown stage)"}` +
    (d.summary ? ` — ${String(d.summary)}` : ""),
  debate_message: (d) => {
    const side = String(d.side ?? "debate");
    const text = String(d.text ?? "");
    const turn = d.turn != null ? ` [#${d.turn}]` : "";
    return `${side}${turn}: ${text.slice(0, 120)}`;
  },
  risk_message: (d) => {
    const side = String(d.side ?? "risk");
    const text = String(d.text ?? "");
    return `${side}: ${text.slice(0, 120)}`;
  },
  decision: (d) => {
    const action = d.action ?? "(none)";
    const target = d.target;
    return target == null ? `DECISION: ${action}` : `DECISION: ${action} @ ${target}`;
  },
  tool_call: (d) => `tool: ${d.tool}${d.description ? ` — ${d.description}` : ""}`,
  tool_result: (d) => `result: ${String(d.summary ?? "").slice(0, 60)}${d.error ? ` ⚠ ${d.error}` : ""}`,
  tool_call_warning: (d) => `warning: ${d.message ?? "(no message)"}`,
  run_failed: formatRunFailed,
};

const TYPE_ICON: Record<string, JSX.Element | undefined> = {
  debate_message: <MessageSquare className="w-3 h-3 inline mr-1 -mt-0.5 text-amber-700" />,
  risk_message: <AlertTriangle className="w-3 h-3 inline mr-1 -mt-0.5 text-red-700" />,
  tool_call: <Wrench className="w-3 h-3 inline mr-1 -mt-0.5 text-slate-600" />,
  tool_result: <Wrench className="w-3 h-3 inline mr-1 -mt-0.5 text-slate-600" />,
  decision: <Play className="w-3 h-3 inline mr-1 -mt-0.5 text-emerald-700" />,
  analyst_started: <Play className="w-3 h-3 inline mr-1 -mt-0.5 text-brand-600" />,
};

export function LiveEventStream() {
  const events = useFocusedRunEvents();
  const ref = useRef<HTMLDivElement>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [initialLoading, setInitialLoading] = useState(true);

  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
    if (events.length > 0) setInitialLoading(false);
  }, [events.length]);

  const toggleExpand = (key: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const stats = useMemo(() => {
    const startedNodes = new Set<string>();
    const completedNodes = new Set<string>();
    let toolCalls = 0;
    let llmCalls = 0;
    let firstTs: number | null = null;
    let lastTs: number | null = null;

    for (const e of events) {
      const ts = new Date(e.ts).getTime();
      if (firstTs === null || ts < firstTs) firstTs = ts;
      if (lastTs === null || ts > lastTs) lastTs = ts;

      const data = e.data as EventData;
      if (e.type === "analyst_started") {
        const node = String(data.node ?? "");
        if (node) startedNodes.add(node);
      } else if (e.type === "analyst_completed") {
        const node = String(data.node ?? "");
        if (node) completedNodes.add(node);
      } else if (e.type === "tool_call") {
        toolCalls++;
      } else if (e.type === "analyst_thinking") {
        llmCalls++;
      }
    }

    const elapsed =
      firstTs != null && lastTs != null
        ? formatDuration(lastTs - firstTs)
        : "--";

    return {
      agentsDone: completedNodes.size,
      agentsTotal: startedNodes.size,
      llmCalls,
      toolCalls,
      elapsed,
      hasRun: firstTs != null,
    };
  }, [events]);

  return (
    <div className="glass-panel" data-testid="live-event-stream">
      <div className="flex items-center justify-between px-3 py-2 border-b border-brand-100">
        <span className="section-header flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-brand-500 shadow-sm animate-pulse" />
          Event Stream
        </span>
        <span className="text-[10px] font-mono text-slate-400">{events.length} events</span>
      </div>
      <div ref={ref} className="h-48 md:h-72 overflow-y-auto p-2 space-y-1">
      {events.length === 0 && initialLoading ? (
        <div className="space-y-2 px-3 py-6">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex items-center gap-2 animate-pulse">
              <div className="w-1.5 h-1.5 rounded-full bg-brand-100" />
              <div className="h-3 bg-brand-50 rounded w-full" style={{ width: `${60 + Math.random() * 30}%` }} />
            </div>
          ))}
        </div>
      ) : events.length === 0 ? (
        <p className="text-sm text-slate-400 text-center py-8">No events yet. Click &quot;Run analysis&quot; to start.</p>
      ) : null}
      {events.map((e) => {
        const key = (e.id ?? "") + ":" + (e.ts ?? 0);
        const data = e.data as EventData;
        const hasReport = !!data.report_text;
        const hasText = !!(data.text || data.summary || data.message);
        const canExpand = hasReport || hasText || e.type === "debate_message" || e.type === "risk_message";
        return (
          <Bubble
            key={key}
            event={e}
            expanded={expanded.has(key)}
            onToggle={canExpand ? () => toggleExpand(key) : undefined}
          />
        );
      })}
      </div>
      {stats.hasRun && (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 px-3 py-1.5 border-t border-brand-100 bg-brand-50 text-[10px] font-mono text-slate-500">
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            <span className="text-emerald-700 font-semibold">{stats.agentsDone}</span>
            <span className="text-slate-400">/</span>
            <span className="text-slate-600">{stats.agentsTotal}</span>
            <span className="text-slate-400">agents</span>
          </span>
          <span className="w-px h-3 bg-brand-100" />
          <span className="text-slate-400">LLM</span>
          <span className="text-brand-600">{stats.llmCalls}</span>
          <span className="w-px h-3 bg-brand-100" />
          <span className="text-slate-400">tools</span>
          <span className="text-amber-700">{stats.toolCalls}</span>
          <span className="w-px h-3 bg-brand-100" />
          <span className="text-slate-400">elapsed</span>
          <span className="text-slate-700">{stats.elapsed}</span>
        </div>
      )}
    </div>
  );
}

function Bubble({ event, expanded, onToggle }: { event: WsEvent; expanded: boolean; onToggle?: () => void }) {
  const data = event.data as EventData;
  const formatter = formatBubble[event.type];
  const text = formatter ? formatter(data) : event.type;
  const reportText = data.report_text as string | undefined;
  const fullText = data.text as string | undefined;
  const fullSummary = data.summary as string | undefined;
  const fullMessage = data.message as string | undefined;
  const toolArgs = data.args as string | undefined;
  const canExpand = !!onToggle;
  const icon = TYPE_ICON[event.type];

  let expandContent: React.ReactNode = null;
  if (expanded) {
    if (reportText) {
      expandContent = (
        <pre className="mt-2 whitespace-pre-wrap text-xs text-slate-700 bg-brand-50 rounded-lg p-3 border border-brand-100 max-h-96 overflow-y-auto">
          {reportText}
        </pre>
      );
    } else if (fullText) {
      expandContent = (
        <pre className="mt-2 whitespace-pre-wrap text-xs text-slate-700 bg-brand-50 rounded-lg p-3 border border-brand-100 max-h-96 overflow-y-auto">
          {fullText}
        </pre>
      );
    } else if (event.type === "tool_call" && toolArgs) {
      expandContent = (
        <div className="mt-2 text-xs text-slate-700 bg-brand-50 rounded-lg p-3 border border-brand-100 max-h-96 overflow-y-auto font-mono whitespace-pre-wrap">
          {typeof toolArgs === "string" ? toolArgs : JSON.stringify(toolArgs, null, 2)}
        </div>
      );
    } else if (fullSummary) {
      expandContent = (
        <div className="mt-2 text-xs text-slate-600 bg-brand-50 rounded-lg p-2 border border-brand-100">
          {fullSummary}
        </div>
      );
    } else if (fullMessage) {
      expandContent = (
        <div className="mt-2 text-xs text-slate-600 bg-brand-50 rounded-lg p-2 border border-brand-100">
          {fullMessage}
        </div>
      );
    }
  }

  return (
    <div
      data-testid={`event-${event.id ?? ""}`}
      className={`text-xs px-3 py-1.5 rounded-md border-l-2 ${
        colorForType[event.type] ?? "bg-brand-50 text-slate-600 border-l-slate-400"
      } ${canExpand ? "cursor-pointer select-none hover:brightness-125" : ""} transition-all`}
      onClick={canExpand ? onToggle : undefined}
    >
      <span className="text-slate-400 mr-2 font-mono text-[10px]">{new Date(event.ts).toLocaleTimeString()}</span>
      {icon}
      <span className="font-medium">{text}</span>
      {expandContent}
    </div>
  );
}

export function useStageReports(events: WsEvent[]): { stage: string; text: string }[] {
  const seen = new Set<string>();
  const reports: { stage: string; text: string }[] = [];
  for (let i = events.length - 1; i >= 0; i--) {
    const e = events[i];
    if (e.type !== "analyst_completed") continue;
    const data = e.data as EventData;
    const stage = data.stage as string | undefined;
    const text = data.report_text as string | undefined;
    if (stage && text && !seen.has(stage)) {
      seen.add(stage);
      reports.push({ stage, text });
    }
  }
  return reports.reverse();
}
