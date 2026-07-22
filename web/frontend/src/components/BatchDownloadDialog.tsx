import { useState, useEffect, useRef } from "react";
import { X } from "lucide-react";
import { downloadTickers } from "../lib/api";

interface Props {
  tickers: string[];
  onClose: () => void;
}

type Format = "zip" | "csv" | "json";

const formats: { value: Format; label: string }[] = [
  { value: "zip", label: "ZIP" },
  { value: "csv", label: "CSV" },
  { value: "json", label: "JSON" },
];

export default function BatchDownloadDialog({ tickers, onClose }: Props) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [format, setFormat] = useState<Format>("zip");
  const [loading, setLoading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);

  const allSelected = tickers.length > 0 && selected.size === tickers.length;
  const someSelected = selected.size > 0 && selected.size < tickers.length;

  const toggleAll = () => {
    if (allSelected) {
      setSelected(new Set());
    } else {
      setSelected(new Set(tickers));
    }
  };

  const toggleTicker = (ticker: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(ticker)) {
        next.delete(ticker);
      } else {
        next.add(ticker);
      }
      return next;
    });
  };

  const handleDownload = async () => {
    if (selected.size === 0) return;
    setLoading(true);
    try {
      await downloadTickers(Array.from(selected), format);
      onClose();
    } catch (err) {
      setDownloadError("Download failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-400/30 backdrop-blur-sm">
      <div
        ref={modalRef}
        className="bg-white border border-brand-100 rounded-xl shadow-sm max-w-md w-full mx-4 max-h-[80vh] flex flex-col"
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-brand-100">
          <h2 className="text-sm font-semibold text-slate-900">Download Ticker Data</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 p-1 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-200">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="px-4 py-2 border-b border-brand-100">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={allSelected}
              ref={(el) => {
                if (el) el.indeterminate = someSelected;
              }}
              onChange={toggleAll}
              className="accent-brand-600 shrink-0"
            />
            <span className="text-sm text-slate-700 font-medium">Select all ({tickers.length})</span>
          </label>
        </div>

        <div className="overflow-y-auto flex-1 px-2 py-2 space-y-1 min-h-[120px] max-h-[200px]">
          {tickers.length === 0 && (
            <div className="text-sm text-slate-400 text-center py-8">No tickers available</div>
          )}
          {tickers.map((ticker) => (
            <label
              key={ticker}
              className="flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer hover:bg-brand-50 transition-colors"
            >
              <input
                type="checkbox"
                checked={selected.has(ticker)}
                onChange={() => toggleTicker(ticker)}
                className="accent-brand-600 shrink-0"
              />
              <span className="text-sm text-slate-700">{ticker}</span>
            </label>
          ))}
        </div>

        <div className="px-4 py-2 border-t border-brand-100">
          <div className="text-xs text-slate-400 mb-1.5 font-medium">Format</div>
          <div className="flex gap-3">
            {formats.map((f) => (
              <label
                key={f.value}
                className={`flex items-center gap-1.5 px-2 py-1 rounded-md cursor-pointer border text-xs transition-colors ${
                  format === f.value
                    ? "bg-brand-50 border-brand-200 text-brand-700"
                    : "border-transparent text-slate-600 hover:bg-brand-50"
                }`}
              >
                <input
                  type="radio"
                  name="format"
                  value={f.value}
                  checked={format === f.value}
                  onChange={() => setFormat(f.value)}
                  className="accent-brand-600 shrink-0"
                />
                {f.label}
              </label>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between px-4 py-3 border-t border-brand-100">
          <div className="flex items-center gap-3">
            {downloadError && <span className="text-xs text-red-700" role="alert">{downloadError}</span>}
            <span className="text-xs text-slate-400">{selected.size} selected</span>
          </div>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-3 py-1.5 text-sm bg-brand-50 text-slate-700 rounded-lg hover:bg-brand-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-200"
            >
              Cancel
            </button>
            <button
              onClick={handleDownload}
              disabled={selected.size === 0 || loading}
              className="px-3 py-1.5 text-sm bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-200"
            >
              {loading ? "Preparing…" : `Download ${format.toUpperCase()} (${selected.size})`}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}