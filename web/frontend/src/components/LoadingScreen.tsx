interface LoadingScreenProps {
  message?: string;
  submessage?: string;
}

export function LoadingScreen({ message = "Loading…", submessage }: LoadingScreenProps) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-market-DEFAULT">
      <div className="text-center animate-fade-in">
        <div className="relative w-12 h-12 mx-auto mb-4">
          <div className="absolute inset-0 rounded-full bg-brand-50 blur-md animate-pulse" />
          <div className="w-12 h-12 rounded-full border-2 border-brand-200 border-t-brand-500 animate-spin" />
        </div>
        <p className="text-sm text-slate-600 font-medium">{message}</p>
        {submessage && <p className="text-xs text-slate-400 mt-1.5">{submessage}</p>}
      </div>
    </div>
  );
}
