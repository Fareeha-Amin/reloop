import { useEffect, useRef, type ReactNode } from 'react';

import { Icon } from './icons';

/** A modal built on the native <dialog> element (focus trap and Escape for free). */
export function Dialog({
  open,
  onClose,
  title,
  children,
  footer,
  closeLabel,
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
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
  }, [open]);

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onCancel={onClose}
      className="m-auto w-[min(32rem,calc(100vw-2rem))] rounded-card border border-line bg-surface p-0 text-ink shadow-lift backdrop:bg-brand-950/45 backdrop:backdrop-blur-sm"
    >
      <div className="flex items-start justify-between gap-4 px-6 pt-6">
        <h2 className="text-xl font-semibold">{title}</h2>
        <button type="button" onClick={onClose} className="rounded-control p-1 text-ink-muted hover:bg-surface-muted" aria-label={closeLabel}>
          <Icon name="x" />
        </button>
      </div>
      <div className="px-6 py-4 text-sm text-ink-soft">{children}</div>
      {footer && <div className="flex flex-wrap justify-end gap-2 border-t border-line bg-surface-muted/50 px-6 py-4">{footer}</div>}
    </dialog>
  );
}
