export function Spinner({ size = "md", className = "" }: { size?: "sm" | "md" | "lg"; className?: string }) {
  const dim = size === "sm" ? "w-4 h-4" : size === "lg" ? "w-8 h-8" : "w-5 h-5";
  return (
    <div className={`relative ${dim} ${className}`} role="status" aria-label="Loading">
      <div className="absolute inset-0 rounded-full bg-brand-500/10 blur-sm" />
      <div className={`${dim} rounded-full border-2 border-brand-100 border-t-brand-600 animate-spin`} />
    </div>
  );
}
