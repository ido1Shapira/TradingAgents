interface TraceTabsProps {
  value: "events" | "llm";
  onChange: (view: "events" | "llm") => void;
}

type TabKey = "events" | "llm";

const ACCENT_MAP: Record<TabKey, { activeClass: string; dotClass: string }> = {
  events: {
    activeClass: "bg-brand-50 text-brand-700 border-brand-200 z-10",
    dotClass: "bg-brand-500",
  },
  llm: {
    activeClass: "bg-emerald-50 text-emerald-700 border-emerald-200 z-10",
    dotClass: "bg-emerald-500",
  },
};

export function TraceTabs({ value, onChange }: TraceTabsProps) {
  const tabs: Array<{ key: TabKey; label: string; shortLabel: string }> = [
    { key: "events", label: "Event Stream", shortLabel: "Events" },
    { key: "llm", label: "LLM Trace", shortLabel: "LLM" },
  ];

  return (
    <div className="flex items-center gap-0 mb-4">
      {tabs.map((tab, i) => {
        const isFirst = i === 0;
        const isLast = i === tabs.length - 1;
        const isActive = value === tab.key;
        const accent = ACCENT_MAP[tab.key];
        return (
          <button
            key={tab.key}
            onClick={() => onChange(tab.key)}
            className={`px-3 py-1.5 text-xs font-semibold border transition-all ${
              isFirst ? "rounded-l-lg" : "border-l-0"
            } ${isLast ? "rounded-r-lg" : ""} ${
              isActive
                ? accent.activeClass
                : "text-slate-500 border-brand-100 hover:text-slate-700 hover:bg-brand-50"
            }`}
          >
            <span className="flex items-center gap-1.5">
              <span className={`w-1.5 h-1.5 rounded-full ${isActive ? accent.dotClass : "bg-slate-400"}`} />
              <span className="hidden sm:inline">{tab.label}</span>
              <span className="sm:hidden">{tab.shortLabel}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}
