import { useEffect, useRef, type ReactNode } from 'react';

import { Icon } from './icons';

/**
 * A panel over the page: full screen on a phone, a panel on the right from `sm` up.
 * Built on the native <dialog> (focus trap, Escape and the top layer for free), like
 * Dialog. The body scrolls; the footer stays put (e.g. a message composer).
 */
export function Drawer({
  open,
  onClose,
  eyebrow,
  title,
  subtitle,
  toolbar,
  children,
  footer,
  closeLabel,
}: {
  open: boolean;
  onClose: () => void;
  eyebrow?: ReactNode;
  title: ReactNode;
  subtitle?: ReactNode;
  /** Under the title, above the scrolling body (e.g. a thread switcher). */
  toolbar?: ReactNode;
  children?: ReactNode;
  footer?: ReactNode;
  closeLabel: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
    if (!open) return;
    // The page behind must not scroll along with the panel.
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previous;
    };
  }, [open]);

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onCancel={onClose}
      className="fixed inset-0 m-0 ml-auto h-dvh max-h-none w-full max-w-none border-0 bg-surface p-0 text-ink shadow-lift open:flex open:flex-col open:animate-slide-in backdrop:bg-brand-950/45 backdrop:backdrop-blur-sm sm:w-[28rem] sm:border-l sm:border-line"
    >
      <header className="flex items-start justify-between gap-3 border-b border-line px-4 pt-4 pb-3 sm:px-5">
        <div className="min-w-0">
          {eyebrow && <p className="mb-1 text-xs font-semibold tracking-[0.14em] text-brand-600 uppercase">{eyebrow}</p>}
          <h2 className="text-lg leading-snug font-semibold break-words">{title}</h2>
          {subtitle && <div className="mt-0.5 text-sm text-ink-muted">{subtitle}</div>}
        </div>
        <button
          type="button"
          onClick={onClose}
          className="-mr-1 shrink-0 rounded-control p-1.5 text-ink-muted hover:bg-surface-muted hover:text-ink"
          aria-label={closeLabel}
        >
          <Icon name="x" />
        </button>
      </header>
      {toolbar && <div className="border-b border-line px-4 py-3 sm:px-5">{toolbar}</div>}
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-4 sm:px-5">{children}</div>
      {footer && <div className="border-t border-line bg-surface-muted/40 px-4 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] sm:px-5">{footer}</div>}
    </dialog>
  );
}
