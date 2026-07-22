import { useEffect, useRef, useState } from "react";
import { Terminal, X, Trash2, Search } from "lucide-react";
import { useLogStore } from "../store/logs";
import { useLogStream } from "../hooks/useLogStream";

  const LEVEL_COLORS: Record<string, string> = {
  DEBUG: "text-gray-600",
  INFO: "text-blue-700",
  WARNING: "text-amber-700",
  ERROR: "text-red-700",
};

const LEVEL_BG: Record<string, string> = {
  DEBUG: "bg-gray-50 hover:bg-gray-100",
  INFO: "bg-blue-50 hover:bg-blue-100",
  WARNING: "bg-amber-50 hover:bg-amber-100",
  ERROR: "bg-red-50 hover:bg-red-100",
};

const SOURCE_ACCENT: Record<string, string> = {
  server: "border-l-2 border-l-brand-500",
  client: "border-l-2 border-l-emerald-500",
};

export function LogPanel() {
  const { status } = useLogStream();
  const entries = useLogStore((s) => s.entries);
  const clear = useLogStore((s) => s.clear);
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState("");
  const [levelFilter, setLevelFilter] = useState<Set<string>>(new Set(["DEBUG", "INFO", "WARNING", "ERROR"]));
  const [autoScroll, setAutoScroll] = useState(true);
  const [confirmClear, setConfirmClear] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const filtered = entries.filter((e) => {
    if (!levelFilter.has(e.level)) return false;
    if (filter && !e.message.toLowerCase().includes(filter.toLowerCase())) return false;
    return true;
  });

  useEffect(() => {
    if (!autoScroll) return;
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries, autoScroll]);

  const handleScroll = () => {
    const el = listRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 50;
    setAutoScroll(atBottom);
  };

  const toggleLevel = (l: string) => {
    setLevelFilter((prev) => {
      const next = new Set(prev);
      next.has(l) ? next.delete(l) : next.add(l);
      return next;
    });
  };

  const handleClear = () => {
    if (confirmClear) {
      clear();
      setConfirmClear(false);
    } else {
      setConfirmClear(true);
      setTimeout(() => setConfirmClear(false), 2000);
    }
  };

  const allLevels: Array<"DEBUG" | "INFO" | "WARNING" | "ERROR"> = ["DEBUG", "INFO", "WARNING", "ERROR"];

  return (
    <>
      {/* Toggle button */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="fixed bottom-4 right-4 z-50 flex items-center gap-2 rounded-full bg-white px-3 py-2 text-sm text-slate-700 shadow-sm hover:bg-brand-50 border border-brand-100 transition-all duration-200"
        title={open ? "Close logs" : "Open logs"}
      >
        <Terminal size={16} />
        {status === "open" && <span className="h-2 w-2 rounded-full bg-emerald-500 shadow-sm" />}
        {status === "connecting" && <span className="h-2 w-2 animate-pulse rounded-full bg-amber-500" />}
      </button>

      {/* Panel */}
      {open && (
        <div className="fixed bottom-16 right-4 z-50 flex h-[40vh] w-[600px] max-w-[calc(100vw-2rem)] flex-col rounded-xl bg-white shadow-sm backdrop-blur-md border border-brand-100 animate-slide-up">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-brand-100 px-4 py-2.5 shrink-0">
            <span className="text-sm font-medium text-slate-700">
              Logs
              <span className="ml-1.5 text-xs text-slate-400">({entries.length})</span>
            </span>
            <div className="flex items-center gap-1.5">
              <div className="flex items-center gap-0.5 bg-white rounded-lg p-0.5">
                {allLevels.map((l) => {
                  const active = levelFilter.has(l);
                  return (
                    <button
                      key={l}
                      onClick={() => toggleLevel(l)}
                      className={`text-[10px] font-medium px-1.5 py-0.5 rounded-md transition-all ${
                        active
                          ? `${LEVEL_COLORS[l]} bg-brand-100 shadow-sm`
                          : "text-slate-400 hover:text-slate-600"
                      }`}
                    >
                      {l}
                    </button>
                  );
                })}
              </div>
              <div className="relative">
                <Search className="absolute left-1.5 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-400 pointer-events-none" />
                <input
                  type="text"
                  placeholder="Search..."
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                  className="w-28 rounded-lg bg-white pl-6 pr-2 py-1 text-xs text-slate-700 placeholder-slate-400 border border-brand-100 focus:outline-none focus:border-brand-200 transition-colors"
                />
              </div>
              <button
                onClick={handleClear}
                className={`rounded-lg p-1.5 transition-all ${
                  confirmClear
                    ? "bg-red-50 text-red-700"
                    : "hover:bg-brand-50 text-slate-400 hover:text-slate-700"
                }`}
                title={confirmClear ? "Click again to clear" : "Clear logs"}
              >
                <Trash2 size={14} />
              </button>
              <button
                onClick={() => setOpen(false)}
                className="rounded-lg p-1.5 hover:bg-brand-50 text-slate-400 hover:text-slate-700 transition-colors"
                title="Close"
              >
                <X size={14} />
              </button>
            </div>
          </div>

          {/* Log list */}
          <div ref={listRef} className="flex-1 overflow-y-auto font-mono text-xs" onScroll={handleScroll}>
            {filtered.length === 0 && (
              <div className="flex h-full items-center justify-center text-slate-400 text-sm">
                {entries.length === 0 ? "No logs yet" : "No matching logs"}
              </div>
            )}
            {filtered.map((e) => (
              <div
                key={e.id}
                className={`flex gap-2 px-3 py-0.5 border-b border-brand-50 hover:bg-brand-50 transition-colors ${SOURCE_ACCENT[e.source] ?? ""}`}
              >
                <span className="w-16 shrink-0 text-slate-400">{e.ts?.split("T")[1]?.slice(0, 8) ?? ""}</span>
                <span className={`w-16 shrink-0 ${LEVEL_COLORS[e.level] ?? "text-slate-600"}`}>{e.level}</span>
                <span className="w-20 shrink-0 truncate text-slate-400">{e.logger}</span>
                <span className={`flex-1 break-all ${LEVEL_COLORS[e.level] ?? "text-slate-700"}`}>{e.message}</span>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        </div>
      )}
    </>
  );
}
