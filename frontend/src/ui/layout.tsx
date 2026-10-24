import type { ReactNode } from 'react';
import { Link } from 'react-router';

import { Icon } from './icons';

export function Page({ children, width = 'wide' }: { children: ReactNode; width?: 'narrow' | 'wide' }) {
  const max = width === 'narrow' ? 'max-w-3xl' : 'max-w-6xl';
  return <main className={`mx-auto w-full ${max} animate-rise px-4 pt-6 pb-20 sm:px-6 sm:pt-10`}>{children}</main>;
}

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  actions,
  back,
}: {
  eyebrow?: ReactNode;
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  back?: { to: string; label: string };
}) {
  return (
    <header className="mb-8">
      {back && (
        <Link to={back.to} className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-ink-muted hover:text-ink">
          <Icon name="arrowLeft" className="size-4" />
          {back.label}
        </Link>
      )}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          {eyebrow && <p className="mb-2 text-xs font-semibold tracking-[0.14em] text-brand-600 uppercase">{eyebrow}</p>}
          <h1 className="text-3xl font-semibold text-ink sm:text-4xl">{title}</h1>
          {subtitle && <div className="mt-2 max-w-2xl text-ink-muted">{subtitle}</div>}
        </div>
        {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
      </div>
    </header>
  );
}

export function Section({ title, aside, children }: { title: ReactNode; aside?: ReactNode; children: ReactNode }) {
  return (
    <section className="mt-10">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-xl font-semibold">{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  );
}

/** Numbered steps, e.g. the three-step donation flow. */
export function Stepper({ steps, current }: { steps: string[]; current: number }) {
  return (
    <ol className="mb-8 flex items-center gap-2 sm:gap-3">
      {steps.map((label, index) => {
        const done = index < current;
        const active = index === current;
        return (
          <li key={label} className="flex min-w-0 flex-1 items-center gap-2 sm:gap-3">
            <span
              className={`grid size-8 shrink-0 place-items-center rounded-full text-sm font-bold transition ${
                done ? 'bg-brand-600 text-brand-50' : active ? 'bg-brand-900 text-leaf ring-4 ring-brand-100' : 'bg-surface-muted text-ink-muted'
              }`}
              aria-current={active ? 'step' : undefined}
            >
              {done ? <Icon name="check" className="size-4" /> : index + 1}
            </span>
            <span className={`hidden truncate text-sm font-semibold sm:block ${active ? 'text-ink' : 'text-ink-muted'}`}>{label}</span>
            {index < steps.length - 1 && <span className={`h-0.5 flex-1 rounded ${done ? 'bg-brand-400' : 'bg-line'}`} />}
          </li>
        );
      })}
    </ol>
  );
}

/** The deep-green welcome banner at the top of each role's home page. */
export function HeroBanner({
  eyebrow,
  title,
  intro,
  actions,
  children,
}: {
  eyebrow: ReactNode;
  title: ReactNode;
  intro?: ReactNode;
  actions?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <div className="relative mb-10 overflow-hidden rounded-card bg-brand-900 p-6 text-brand-50 shadow-lift sm:p-10">
      <div className="pointer-events-none absolute -top-24 -right-16 size-72 rounded-full bg-leaf/25 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-32 left-10 size-72 rounded-full bg-clay-500/20 blur-3xl" />
      <div className="relative flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-semibold tracking-[0.14em] text-leaf uppercase">{eyebrow}</p>
          <h1 className="mt-2 text-3xl font-semibold text-surface sm:text-4xl">{title}</h1>
          {intro && <div className="mt-2 max-w-xl text-brand-100">{intro}</div>}
          {children && <div className="mt-4">{children}</div>}
        </div>
        {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
      </div>
    </div>
  );
}
