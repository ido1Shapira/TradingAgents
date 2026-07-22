import { useRef, useEffect } from "react";
import { Shield, Scale, AlertTriangle } from "lucide-react";
import type { WsEvent } from "../lib/events";

const SIDE_LABELS: Record<string, string> = {
  "Bull Researcher": "Bull",
  "Bear Researcher": "Bear",
  "Aggressive Analyst": "Aggressive",
  "Conservative Analyst": "Conservative",
  "Neutral Analyst": "Neutral",
};

const SIDE_STYLES: Record<string, { bg: string; border: string; text: string }> = {
  "Bull Researcher": { bg: "bg-emerald-50", border: "border-emerald-200", text: "text-emerald-700" },
  "Bear Researcher": { bg: "bg-red-50", border: "border-red-200", text: "text-red-700" },
  "Aggressive Analyst": { bg: "bg-orange-50", border: "border-orange-200", text: "text-orange-700" },
  "Conservative Analyst": { bg: "bg-blue-50", border: "border-blue-200", text: "text-blue-700" },
  "Neutral Analyst": { bg: "bg-slate-100", border: "border-slate-200", text: "text-slate-700" },
};

function SideIcon({ side }: { side: string }) {
  if (side.startsWith("Bull")) return <span className="text-emerald-700 text-xs">📈</span>;
  if (side.startsWith("Bear")) return <span className="text-red-700 text-xs">📉</span>;
  if (side.startsWith("Aggressive")) return <AlertTriangle className="w-3 h-3 text-orange-700" />;
  if (side.startsWith("Conservative")) return <Shield className="w-3 h-3 text-blue-700" />;
  return <Scale className="w-3 h-3 text-slate-600" />;
}

interface DebateFlowProps {
  events: WsEvent[];
  type: "debate" | "risk";
}

export function DebateFlow({ events, type }: DebateFlowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const msgType = type === "debate" ? "debate_message" : "risk_message";
  const messages = events.filter(e => e.type === msgType);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  if (messages.length === 0) {
    return <div className="text-xs text-slate-400 italic py-4 text-center">No {type} messages yet.</div>;
  }

  return (
    <div className="space-y-2 max-h-96 overflow-y-auto" data-testid="debate-flow">
      {messages.map((e, i) => {
        const d = e.data as any;
        const side = d.side || "unknown";
        const style = SIDE_STYLES[side] || SIDE_STYLES["Neutral Analyst"];
        const isLeft = side.startsWith("Bull") || side.startsWith("Aggressive");
        return (
          <div key={e.id ?? i} className={`flex ${isLeft ? "justify-start" : "justify-end"}`}>
            <div className={`max-w-[80%] rounded-xl px-3 py-2 border ${style.bg} ${style.border}`}>
              <div className={`text-[10px] font-semibold mb-1 ${style.text} flex items-center gap-1`}>
                <SideIcon side={side} />
                {SIDE_LABELS[side] || side} {d.turn ? `[Round ${d.turn}]` : ""}
              </div>
              <div className="text-xs text-slate-700 whitespace-pre-wrap">{d.text}</div>
            </div>
          </div>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
}
