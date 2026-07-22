import type { InputHTMLAttributes, ReactNode } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: ReactNode;
}

export function Input({ label, error, icon, className = "", ...rest }: InputProps) {
  return (
    <label className="flex flex-col gap-0.5">
      {label && <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider">{label}</span>}
      <div className="relative">
        {icon && (
          <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">
            {icon}
          </span>
        )}
        <input
          className={`w-full bg-white border rounded-lg px-2.5 py-1.5 text-sm text-slate-900
            placeholder-slate-400 outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500/30
            transition-colors font-mono tabular-nums
            ${icon ? "pl-8" : ""}
            ${error ? "border-red-300" : "border-brand-200"}
            ${className}`}
          {...rest}
        />
      </div>
      {error && <span className="text-[10px] text-red-600 mt-0.5">{error}</span>}
    </label>
  );
}
