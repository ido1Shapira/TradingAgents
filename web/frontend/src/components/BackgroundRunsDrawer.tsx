import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Clock, X, ChevronRight, Plus, Loader } from "lucide-react";
import {
  startBackgroundRun,
  getBackgroundRuns,
  cancelBackgroundRun,
  deleteBackgroundRun,
  fetchWatchlist,
  addToWatchlist,
  type StartBackgroundRunRequest,
  type BackgroundEvery,
  type BackgroundRunState,
} from "../lib/api";
import { fmtEta } from "../lib/format";
import { useUi } from "../store/ui";

const EVERY_OPTIONS: BackgroundEvery[] = ["1d", "1w", "2w", "1mo"];
const PARALLEL_OPTIONS = [1, 2, 4];

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}
function daysAgoIso(n: number): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - n);
  return d.toISOString().slice(0, 10);
}

export function BackgroundRunsDrawer({ focusedTicker }: { focusedTicker: string }) {
  const open = useUi((s) => s.backgroundRunsOpen);
  const setOpen = useUi((s) => s.setBackgroundRunsOpen);
  const { data: watchlist = [] } = useQuery({ queryKey: ["watchlist"], queryFn: fetchWatchlist });
  const tickers = watchlist.map((w) => w.ticker);

  return (
    <>
      <div
        className={`drawer-overlay ${open ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"}`}
        onClick={() => setOpen(false)}
        aria-hidden
      />
      <aside
        data-testid="background-runs-drawer"
        className={`drawer-panel inset-x-0 bottom-0 border-t ${open ? "translate-y-0" : "translate-y-full"}`}
        style={{ height: "45vh" }}
        role="dialog"
        aria-label="Background past runs"
      >
        <header className="flex items-center justify-between border-b border-brand-100 px-5 py-3">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-brand-600" />
            <h2 className="font-semibold text-slate-900 text-sm">Background Past Runs</h2>
          </div>
          <button
            onClick={() => setOpen(false)}
            aria-label="Close"
            className="p-1 hover:bg-brand-50 rounded-lg text-slate-400 hover:text-slate-700 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-200"
          >
            <X className="w-4 h-4" />
          </button>
        </header>
        <div className="h-[calc(45vh-3.5rem)] overflow-y-auto p-4 space-y-4">
          <NewJobForm tickers={tickers.length > 0 ? tickers : [focusedTicker]} defaultTicker={focusedTicker} />
          <ActiveJobs />
          <PastJobs />
        </div>
      </aside>
    </>
  );
}

function ActiveJobs() {
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["background-runs"],
    queryFn: () => getBackgroundRuns(),
    refetchInterval: (q) => {
      const jobs = (q.state.data?.jobs ?? []) as BackgroundRunState[];
      return jobs.some((j) => j.status === "running" || j.status === "paused") ? 2000 : false;
    },
  });
  const active = (data?.jobs ?? []).filter(
    (j) => j.status === "running" || j.status === "paused"
  );
  if (active.length === 0) return null;
  return (
    <section>
      <h3 className="section-header flex items-center gap-2 mb-3">
        <span className="w-1.5 h-1.5 rounded-full bg-brand-600 animate-pulse" />
        Active jobs ({active.length})
      </h3>
      <ul className="space-y-2">
        {active.map((j) => (
          <li key={j.job_id}>
            <JobCard
              job={j}
              onChanged={() => qc.invalidateQueries({ queryKey: ["background-runs"] })}
            />
          </li>
        ))}
      </ul>
    </section>
  );
}

function JobCard({ job, onChanged }: { job: BackgroundRunState; onChanged: () => void }) {
  const pct = job.total ? Math.min(100, (job.current_index / job.total) * 100) : 0;
  const showEta = job.status === "running" && job.current_index < job.total;
  const etaText = job.current_index === 0 ? "Calculating..." : fmtEta(job.eta_s);
  return (
    <div className="glass-panel p-3" data-testid={`job-card-${job.job_id}`}>
      <div className="flex items-center justify-between">
        <div className="text-sm">
          <span className="font-medium text-slate-900">{job.ticker}</span>
          <span className="text-slate-400 text-xs">
            {" "}
            &middot; {job.date_from} &rarr; {job.date_to} &middot; {job.every}
          </span>
        </div>
        <StatusPill status={job.status} />
      </div>
      <div className="progress-bar mt-2" role="progressbar" aria-valuenow={job.current_index} aria-valuemax={job.total}>
        <div className="progress-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="mt-1 text-xs text-slate-500 data-text">
        {job.current_index} / {job.total} ({pct.toFixed(1)}%)
        {showEta && <span className="ml-2 text-slate-400">ETA: {etaText}</span>}
      </div>
      <div className="mt-2 flex gap-2">
          <button
            onClick={async () => {
              await cancelBackgroundRun(job.job_id);
              onChanged();
            }}
            className="px-2.5 py-1 text-xs font-medium rounded-lg bg-red-50 text-red-700 border border-red-200 hover:bg-red-100 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-200"
          >
          Cancel
        </button>
      </div>
      {job.current_index > 0 && (
        <div className="mt-3 border-t border-brand-100 pt-2" data-testid="iteration-feed">
          <div className="text-[10px] font-medium text-slate-400 mb-1">Recent iterations</div>
          <ul className="text-xs space-y-0.5 max-h-32 overflow-y-auto">
            {Array.from({ length: Math.min(5, job.current_index) }).map((_, i) => {
              const n = job.current_index - i;
              return (
                <li key={n} className="text-slate-400">
                  <span className="text-slate-400">#</span>{n} — completed
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}

function StatusPill({ status }: { status: BackgroundRunState["status"] }) {
  const color = {
    running: "bg-brand-50 text-brand-600 border-brand-200",
    paused: "bg-amber-50 text-amber-700 border-amber-200",
    done: "bg-emerald-50 text-emerald-700 border-emerald-200",
    cancelled: "bg-brand-50 text-slate-600 border-brand-100",
    error: "bg-red-50 text-red-700 border-red-200",
  }[status];
  return (
    <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-md border ${color}`}>{status}</span>
  );
}

function PastJobs() {
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["background-runs"],
    queryFn: () => getBackgroundRuns(),
  });
  const past = (data?.jobs ?? []).filter(
    (j) => j.status === "done" || j.status === "cancelled" || j.status === "error"
  );
  const delMutation = useMutation({
    mutationFn: (jobId: string) => deleteBackgroundRun(jobId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["background-runs"] }),
  });
  if (past.length === 0) return null;
  return (
    <section>
      <details className="glass-panel p-3">
        <summary className="cursor-pointer text-sm font-medium text-slate-600 hover:text-slate-700 transition-colors [&::-webkit-details-marker]:hidden">
          <span className="flex items-center gap-2">
            <ChevronRight className="w-3 h-3 text-slate-400" />
            Past jobs (last {Math.min(10, past.length)})
          </span>
        </summary>
        <ul className="mt-2 space-y-1">
          {past.slice(0, 10).map((j) => (
            <li key={j.job_id} className="flex items-center gap-2 text-sm py-1">
              <span className="font-medium text-slate-700 text-xs">{j.ticker}</span>
              <span className="text-xs text-slate-400">
                {j.date_from} &rarr; {j.date_to} &middot; {j.every}
              </span>
              <StatusPill status={j.status} />
              <span className="text-xs data-text text-slate-400">
                {j.current_index}/{j.total}
              </span>
              <button
                disabled={delMutation.isPending}
                onClick={() => delMutation.mutate(j.job_id)}
                className="ml-auto shrink-0 text-slate-400 hover:text-red-700 disabled:opacity-30 transition-colors p-1 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-200"
                title="Delete this past run"
              >
                <X className="w-3 h-3" />
              </button>
            </li>
          ))}
        </ul>
      </details>
    </section>
  );
}

function NewJobForm({ tickers, defaultTicker }: { tickers: string[]; defaultTicker: string }) {
  const qc = useQueryClient();
  const [selected, setSelected] = useState(defaultTicker);
  const [customTicker, setCustomTicker] = useState("");
  const [dateFrom, setDateFrom] = useState(daysAgoIso(30));
  const [dateTo, setDateTo] = useState(todayIso());
  const [every, setEvery] = useState<BackgroundEvery>("1d");
  const [parallel, setParallel] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const isCustom = selected === "__custom__";
  const resolvedTicker = isCustom ? customTicker.toUpperCase() : selected;

  const mutation = useMutation({
    mutationFn: async (body: StartBackgroundRunRequest) => {
      if (!tickers.includes(body.ticker)) {
        await addToWatchlist(body.ticker, "", "");
        qc.invalidateQueries({ queryKey: ["watchlist"] });
      }
      return startBackgroundRun(body);
    },
    onSuccess: () => {
      setError(null);
      qc.invalidateQueries({ queryKey: ["background-runs"] });
    },
    onError: (e: Error) => setError(e.message),
  });

  return (
    <details open className="glass-panel p-3">
      <summary className="cursor-pointer text-sm font-medium text-slate-700 hover:text-slate-900 transition-colors [&::-webkit-details-marker]:hidden">
        <span className="flex items-center gap-2">
          <Plus className="w-3.5 h-3.5 text-emerald-700" />
          New job
        </span>
      </summary>
      <form
        className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm"
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate({ ticker: resolvedTicker, date_from: dateFrom, date_to: dateTo, every, parallel });
        }}
      >
        <label className="flex flex-col gap-0.5">
          <span className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">Ticker</span>
          <select
            value={selected}
            onChange={(e) => {
              setSelected(e.target.value);
              setError(null);
            }}
            className="bg-white border border-brand-100 rounded-lg px-2 py-1.5 text-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-brand-200"
            aria-label="Ticker"
          >
            {tickers.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
            <option value="__custom__">Custom ticker…</option>
          </select>
          {isCustom && (
            <input
              value={customTicker}
              onChange={(e) => setCustomTicker(e.target.value.toUpperCase())}
              placeholder="Type ticker…"
              className="mt-1 bg-white border border-brand-200 rounded-lg px-2 py-1.5 text-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-brand-300"
              aria-label="Custom ticker input"
              autoFocus
            />
          )}
        </label>
        <label className="flex flex-col gap-0.5">
          <span className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">From</span>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="bg-white border border-brand-100 rounded-lg px-2 py-1.5 text-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-brand-200"
          />
        </label>
        <label className="flex flex-col gap-0.5">
          <span className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">To</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="bg-white border border-brand-100 rounded-lg px-2 py-1.5 text-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-brand-200"
          />
        </label>
        <label className="flex flex-col gap-0.5">
          <span className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">Every</span>
          <select
            value={every}
            onChange={(e) => setEvery(e.target.value as BackgroundEvery)}
            className="bg-white border border-brand-100 rounded-lg px-2 py-1.5 text-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-brand-200"
          >
            {EVERY_OPTIONS.map((o) => (
              <option key={o} value={o}>{o}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-0.5">
          <span className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">Parallel</span>
          <select
            value={parallel}
            onChange={(e) => setParallel(Number(e.target.value))}
            className="bg-white border border-brand-100 rounded-lg px-2 py-1.5 text-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-brand-200"
          >
            {PARALLEL_OPTIONS.map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </label>
        <div className="col-span-2 flex items-center gap-2 mt-1">
          <button
            type="submit"
            disabled={mutation.isPending}
            className="btn-primary text-xs"
          >
            {mutation.isPending ? (
              <><Loader className="inline w-3 h-3 mr-1.5 animate-spin" /> Starting…</>
            ) : "Start"}
          </button>
          {error && <span className="text-xs text-red-700" role="alert">{error}</span>}
        </div>
      </form>
    </details>
  );
}
