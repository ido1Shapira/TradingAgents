import { useState } from "react";
import { GripVertical, X, Bell } from "lucide-react";
import { useUi } from "../store/ui";

interface Props {
  ticker: string;
  companyName: string;
  lastDecision: string | null;
  sparkline: number[];
  status: "idle" | "queued" | "running" | "done" | "errored";
  price?: number;
  changePct?: number | null;
  stale?: boolean;
  onRemove?: (ticker: string) => void | Promise<void>;
  onAddAlert?: (ticker: string) => void;
  group?: string | null;
  groupColor?: string;
  onGroupChange?: (ticker: string, group: string | null) => void;
  onDrop?: (e: React.DragEvent) => void;
  dragHandleProps?: {
    draggable: boolean;
    onDragStart: (e: React.DragEvent) => void;
    onDragOver?: (e: React.DragEvent) => void;
    onDragEnd?: (e: React.DragEvent) => void;
  };
}

const dotColor: Record<Props["status"], string> = {
  idle: "bg-slate-400",
  queued: "bg-amber-500 shadow-sm",
  running: "bg-brand-500 animate-pulse shadow-sm",
  done: "bg-emerald-500 shadow-sm",
  errored: "bg-red-500 shadow-sm",
};

const GROUP_COLORS = ["#38bdf8", "#fb923c", "#a78bfa", "#34d399", "#f472b6", "#fbbf24", "#f87171", "#2dd4bf"];

export function TickerRow({ ticker, companyName, lastDecision, sparkline, status, price, changePct, stale, onRemove, onAddAlert, group, groupColor, onGroupChange, onDrop, dragHandleProps }: Props) {
  const focused = useUi((s) => s.focusedTicker);
  const setFocused = useUi((s) => s.setFocusedTicker);
  const isFocused = focused === ticker;
  const [pending, setPending] = useState(false);
  const [isDragOver, setDragOver] = useState(false);

  const sparkPath = sparkline.length > 1
    ? sparkline.map((v, i) => `${i === 0 ? "M" : "L"} ${i * 4} ${20 - v}`).join(" ")
    : "";

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      setFocused(ticker);
    }
  };

  const showChange = changePct != null && !isNaN(changePct);
  const changeColor = showChange ? (changePct >= 0 ? "text-emerald-600" : "text-rose-600") : "text-slate-400";

  const gc = groupColor ?? GROUP_COLORS[0];

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };
  const handleDragLeave = (e: React.DragEvent) => {
    // Only hide when actually leaving this element (not entering a child)
    if (e.currentTarget === e.target || !e.currentTarget.contains(e.relatedTarget as Node)) {
      setDragOver(false);
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => setFocused(ticker)}
      onKeyDown={handleKeyDown}
      data-focused={isFocused}
      draggable={dragHandleProps?.draggable ?? false}
      onDragStart={dragHandleProps?.onDragStart}
      onDragOver={(e) => {
        e.preventDefault();
        dragHandleProps?.onDragOver?.(e);
        setDragOver(true);
      }}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDrop={(e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragOver(false);
        onDrop?.(e);
      }}
      onDragEnd={(e) => {
        setDragOver(false);
        dragHandleProps?.onDragEnd?.(e);
      }}
      className={`relative group w-full text-left px-3 py-2.5 rounded-xl flex items-center gap-2 transition-colors duration-150 cursor-pointer ${
        isFocused
          ? "bg-brand-50 ring-1 ring-brand-200"
          : isDragOver
            ? "bg-brand-50/50"
            : "hover:bg-brand-50"
      } ${dragHandleProps?.draggable ? "opacity-100" : ""} ${isDragOver ? "shadow-[inset_0_2px_0_0_rgba(37,99,235,0.2)]" : ""}`}
    >
      {/* Drag handle */}
      <span
        className="shrink-0 flex flex-col gap-0.5 cursor-grab active:cursor-grabbing opacity-30 md:group-hover:opacity-70 hover:opacity-100 transition-opacity px-0.5"
        onMouseDown={(e) => e.stopPropagation()}
        aria-label={`Drag ${ticker} to reorder`}
      >
        <GripVertical className="w-3.5 h-5 text-slate-500" />
      </span>
      <span className={`h-2 w-2 rounded-full shrink-0 ${dotColor[status]}`} />
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-1.5">
          <span className="text-sm font-semibold text-slate-900">{ticker}</span>
          {stale ? (
            <span
              data-testid={`ticker-row-${ticker}-unavailable`}
              className="text-[10px] uppercase tracking-wider font-medium text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-1.5 py-0.5"
            >
              unavailable
            </span>
          ) : price != null && !isNaN(price) ? (
            <span className="text-xs data-text text-slate-600">
              ${price.toFixed(2)}
            </span>
          ) : null}
        </div>
        <div className="flex items-baseline gap-1.5">
          <span className="text-xs text-slate-400 truncate">
            {stale ? "Price data unavailable" : companyName || lastDecision || "—"}
          </span>
          {!stale && showChange ? (
            <span className={`text-xs data-text font-medium ${changeColor}`}>
              {changePct >= 0 ? "+" : ""}{changePct.toFixed(2)}%
            </span>
          ) : !stale ? (
            <span className="text-xs data-text font-medium text-slate-500">N/A</span>
          ) : null}
        </div>
      </div>
      <svg width="40" height="20" className="opacity-40 shrink-0" aria-hidden="true">
        {sparkPath && <path d={sparkPath} stroke={isFocused ? "#2563eb" : "#94a3b8"} strokeWidth="1.5" fill="none" />}
      </svg>
      {!pending ? (
        <>
          {onAddAlert && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onAddAlert(ticker);
              }}
              className="md:opacity-0 md:group-hover:opacity-100 text-slate-500 hover:text-brand-600 p-2 shrink-0 transition-opacity rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-200"
              title="Add price alert"
            >
              <Bell className="w-3 h-3" />
            </button>
          )}
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); setPending(true); }}
            aria-label={`Remove ${ticker} from watchlist`}
            className="md:opacity-0 md:group-hover:opacity-100 text-slate-500 hover:text-red-600 p-2 shrink-0 transition-opacity rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-200"
          >
            <X className="w-3 h-3" />
          </button>
        </>
      ) : (
        <span className="flex items-center gap-1 text-xs shrink-0" onClick={(e) => e.stopPropagation()}>
          <button
            type="button"
            onClick={async (e) => { e.stopPropagation(); await onRemove?.(ticker); }}
            className="text-red-600 hover:text-red-700 hover:underline"
          >Remove</button>
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); setPending(false); }}
            className="text-slate-500 hover:text-slate-600 hover:underline"
          >Cancel</button>
        </span>
      )}
    </div>
  );
}
