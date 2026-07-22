import type { SelectHTMLAttributes } from "react";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: Array<{ value: string; label: string }>;
}

export function Select({ label, options, className = "", ...rest }: SelectProps) {
  return (
    <label className="flex flex-col gap-0.5">
      {label && <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider">{label}</span>}
      <select
        className={`bg-white border border-brand-200 rounded-lg px-2 py-1.5 text-sm text-slate-700
          focus:outline-none focus:ring-2 focus:ring-brand-500/30 transition-colors ${className}`}
        {...rest}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
    </label>
  );
}
