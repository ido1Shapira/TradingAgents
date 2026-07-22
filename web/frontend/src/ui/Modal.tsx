import type { ReactNode } from "react";
import { X } from "lucide-react";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}

export function Modal({ open, onClose, title, children, footer }: ModalProps) {
  if (!open) return null;

  return (
    <>
      <div className="drawer-overlay opacity-100 pointer-events-auto" onClick={onClose} aria-hidden />
      <div className="fixed inset-0 z-50 flex items-start justify-center pt-8 md:pt-12 pb-8 overflow-y-auto">
        <div
          className="glass-panel w-full max-w-lg mx-2 md:mx-4 animate-slide-up overflow-hidden"
          role="dialog"
          aria-label={title}
        >
          <header className="flex items-center justify-between border-b border-brand-100 px-5 py-3">
            <h2 className="font-semibold text-slate-900 text-sm">{title}</h2>
            <button
              onClick={onClose}
              aria-label="Close"
              className="p-1 hover:bg-brand-50 rounded-lg text-slate-400 hover:text-slate-600 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </header>
          <div className="p-5 max-h-[70vh] overflow-y-auto">{children}</div>
          {footer && (
            <footer className="border-t border-brand-100 px-5 py-3 flex items-center justify-between">
              {footer}
            </footer>
          )}
        </div>
      </div>
    </>
  );
}
