import type { ReactNode } from "react";

type BadgeVariant = "buy" | "sell" | "hold" | "default" | "success" | "warning" | "error" | "info";

interface BadgeProps {
  variant?: BadgeVariant;
  children: ReactNode;
  className?: string;
}

const variantClasses: Record<BadgeVariant, string> = {
  buy: "bg-emerald-50 text-emerald-700 border border-emerald-200",
  sell: "bg-red-50 text-red-700 border border-red-200",
  hold: "bg-amber-50 text-amber-700 border border-amber-200",
  default: "bg-brand-50 text-slate-600 border border-brand-100",
  success: "bg-emerald-50 text-emerald-700 border border-emerald-200",
  warning: "bg-amber-50 text-amber-700 border border-amber-200",
  error: "bg-red-50 text-red-700 border border-red-200",
  info: "bg-brand-50 text-brand-700 border border-brand-200",
};

export function Badge({ variant = "default", children, className = "" }: BadgeProps) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded-md ${variantClasses[variant]} ${className}`}>
      {children}
    </span>
  );
}
