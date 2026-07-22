import { AlertTriangle, X } from "lucide-react";

interface StaleBannerProps {
  ticker: string;
  onRemove: () => void;
  onDismiss: () => void;
}

export function StaleBanner({ ticker, onRemove, onDismiss }: StaleBannerProps) {
  return (
    <div
      data-testid="stale-ticker-banner"
      role="alert"
      className="mb-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 backdrop-blur-sm px-3 sm:px-4 py-3 text-xs sm:text-sm"
    >
      <span className="flex items-center gap-2 text-amber-700">
        <AlertTriangle className="w-4 h-4 shrink-0 text-amber-600" />
        <span>
          <strong className="font-semibold text-amber-800">{ticker}</strong> is not available
          on Yahoo Finance — price and history are unavailable.
        </span>
      </span>
      <span className="flex items-center gap-3 shrink-0 self-end sm:self-auto">
        <button
          onClick={onRemove}
          data-testid="stale-ticker-remove"
          className="rounded-lg bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700 border border-amber-200 hover:bg-amber-100 transition-colors"
        >
          Remove
        </button>
        <button
          onClick={onDismiss}
          className="p-1 rounded-md text-amber-600/60 hover:text-amber-700 hover:bg-amber-50 transition-colors"
          aria-label="Dismiss"
        >
          <X className="w-4 h-4" />
        </button>
      </span>
    </div>
  );
}
