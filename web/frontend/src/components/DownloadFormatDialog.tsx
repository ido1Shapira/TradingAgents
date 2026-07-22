import { useState } from "react";
import { X } from "lucide-react";
import { downloadSingleTicker } from "../lib/api";

interface Props {
  ticker: string;
  onClose: () => void;
}

type Format = "zip" | "csv" | "json";

const formats: { value: Format; label: string; desc: string }[] = [
  { value: "zip", label: "ZIP", desc: "All data bundled with raw files + summary" },
  { value: "csv", label: "CSV", desc: "Tabular run data — ideal for spreadsheets" },
  { value: "json", label: "JSON", desc: "Full structured data — ideal for analysis" },
];

export default function DownloadFormatDialog({ ticker, onClose }: Props) {
  const [selected, setSelected] = useState<Format>("zip");
  const [loading, setLoading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const handleDownload = async () => {
    setLoading(true);
    try {
      await downloadSingleTicker(ticker, selected);
      onClose();
    } catch (err) {
      setDownloadError("Download failed. Please try again.");
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-400/30 backdrop-blur-sm">
      <div className="bg-white border border-brand-100 rounded-xl shadow-sm w-full mx-4 max-w-sm">
        <div className="flex items-center justify-between px-4 py-3 border-b border-brand-100">
          <h2 className="text-sm font-semibold text-slate-900">Download {ticker} Data</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 p-1 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-200">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="px-4 py-3 space-y-2">
          {formats.map((f) => (
            <label
              key={f.value}
                className={`flex items-start gap-3 px-3 py-2.5 rounded-lg cursor-pointer border transition-colors ${
                  selected === f.value
                    ? "bg-brand-50 border-brand-200"
                    : "border-transparent hover:bg-brand-50"
                }`}
            >
              <input
                type="radio"
                name="format"
                value={f.value}
                checked={selected === f.value}
                onChange={() => setSelected(f.value)}
                className="accent-brand-600 shrink-0 mt-0.5"
              />
              <div>
                <div className="text-sm font-medium text-slate-900">{f.label}</div>
                <div className="text-xs text-slate-400 mt-0.5">{f.desc}</div>
              </div>
            </label>
          ))}
        </div>

        <div className="flex items-center justify-between gap-2 px-4 py-3 border-t border-brand-100">
          {downloadError ? (
            <span className="text-xs text-red-700" role="alert">{downloadError}</span>
          ) : <span />}
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-3 py-1.5 text-sm bg-brand-50 text-slate-700 rounded-lg hover:bg-brand-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-200"
            >
              Cancel
            </button>
            <button
              onClick={handleDownload}
              disabled={loading}
              className="px-3 py-1.5 text-sm bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-40 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-200"
            >
              {loading ? "Preparing…" : `Download ${selected.toUpperCase()}`}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}