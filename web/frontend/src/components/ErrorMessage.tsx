import { useState } from "react";
import { AlertCircle, ChevronDown, ChevronRight, Wifi, Bot, HelpCircle } from "lucide-react";

type ErrorType = "network" | "llm" | "tool" | "stream" | "unknown";

interface ErrorMessageProps {
  type: ErrorType;
  message: string;
  details?: string;
  suggestion?: string;
}

const TYPE_CONFIG: Record<ErrorType, { icon: typeof AlertCircle; label: string; iconClass: string }> = {
  network: { icon: Wifi, label: "Connection Error", iconClass: "text-red-400" },
  llm: { icon: Bot, label: "AI Model Error", iconClass: "text-red-400" },
  tool: { icon: AlertCircle, label: "Tool Error", iconClass: "text-red-400" },
  stream: { icon: AlertCircle, label: "Response Error", iconClass: "text-red-400" },
  unknown: { icon: HelpCircle, label: "Error", iconClass: "text-red-400" },
};

export function ErrorMessage({ type, message, details, suggestion }: ErrorMessageProps) {
  const [expanded, setExpanded] = useState(false);
  const config = TYPE_CONFIG[type];
  const Icon = config.icon;

  return (
    <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm">
      <div className="flex items-start gap-2">
        <Icon className={`h-4 w-4 mt-0.5 shrink-0 ${config.iconClass}`} />
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-red-300 text-xs uppercase tracking-wider mb-0.5">
            {config.label}
          </div>
          <div className="text-red-200">{message}</div>
          {suggestion && (
            <div className="text-red-300/70 text-xs mt-1">{suggestion}</div>
          )}
        </div>
      </div>
      {details && (
        <div className="mt-2 border-t border-red-500/20 pt-2">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs text-red-400 hover:text-red-300 transition-colors"
          >
            {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
            {expanded ? "Hide details" : "Show details"}
          </button>
          {expanded && (
            <pre className="mt-2 text-xs text-red-300/60 bg-red-900/20 rounded p-2 overflow-x-auto whitespace-pre-wrap break-all">
              {details}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}