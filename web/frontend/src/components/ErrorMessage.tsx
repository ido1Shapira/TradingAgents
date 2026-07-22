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
  network: { icon: Wifi, label: "Connection Error", iconClass: "text-red-700" },
  llm: { icon: Bot, label: "AI Model Error", iconClass: "text-red-700" },
  tool: { icon: AlertCircle, label: "Tool Error", iconClass: "text-red-700" },
  stream: { icon: AlertCircle, label: "Response Error", iconClass: "text-red-700" },
  unknown: { icon: HelpCircle, label: "Error", iconClass: "text-red-700" },
};

export function ErrorMessage({ type, message, details, suggestion }: ErrorMessageProps) {
  const [expanded, setExpanded] = useState(false);
  const config = TYPE_CONFIG[type] ?? TYPE_CONFIG.unknown;
  const Icon = config.icon;

  return (
    <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm">
      <div className="flex items-start gap-2">
        <Icon className={`h-4 w-4 mt-0.5 shrink-0 ${config.iconClass}`} />
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-red-700 text-xs uppercase tracking-wider mb-0.5">
            {config.label}
          </div>
          <div className="text-red-700">{message}</div>
          {suggestion && (
            <div className="text-red-700/70 text-xs mt-1">{suggestion}</div>
          )}
        </div>
      </div>
      {details && (
        <div className="mt-2 border-t border-red-200 pt-2">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs text-red-700 hover:text-red-800 transition-colors"
          >
            {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
            {expanded ? "Hide details" : "Show details"}
          </button>
          {expanded && (
            <pre className="mt-2 text-xs text-red-700/60 bg-red-50 rounded p-2 overflow-x-auto whitespace-pre-wrap break-all">
              {details}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}