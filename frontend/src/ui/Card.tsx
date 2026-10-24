import type { ReactNode } from 'react';
import { Link } from 'react-router';

export function Card({
  children,
  className = '',
  padded = true,
}: {
  children: ReactNode;
  className?: string;
  padded?: boolean;
}) {
  return (
    <div className={`rounded-card border border-line bg-surface shadow-card ${padded ? 'p-5 sm:p-6' : ''} ${className}`}>
      {children}
    </div>
  );
}

/** A whole card that is a link, lifting on hover. */
export function LinkCard({ to, children, className = '' }: { to: string; children: ReactNode; className?: string }) {
  return (
    <Link
      to={to}
      className={`block rounded-card border border-line bg-surface p-5 shadow-card transition duration-200 hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-lift ${className}`}
    >
      {children}
    </Link>
  );
}

export function CardTitle({ children, aside }: { children: ReactNode; aside?: ReactNode }) {
  return (
    <div className="mb-4 flex items-center justify-between gap-3">
      <h2 className="text-lg font-semibold">{children}</h2>
      {aside}
    </div>
  );
}

/** Label/value pairs. Falsy entries are skipped, so items can be conditional. */
export function Facts({ items }: { items: Array<{ label: ReactNode; value: ReactNode } | null | undefined | false | ''> }) {
  return (
    <dl className="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
      {items.filter(Boolean).map((item, index) => {
        const { label, value } = item as { label: ReactNode; value: ReactNode };
        return (
          <div key={index} className="min-w-0">
            <dt className="text-xs font-semibold tracking-wide text-ink-muted uppercase">{label}</dt>
            <dd className="mt-0.5 break-words text-ink">{value}</dd>
          </div>
        );
      })}
    </dl>
  );
}
