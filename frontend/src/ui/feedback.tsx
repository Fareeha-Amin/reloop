import type { ReactNode } from 'react';

import { Icon, type IconName } from './icons';

export function Spinner({ className = 'size-5' }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={`${className} animate-spin`} aria-hidden="true">
      <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeOpacity="0.2" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export function LoadingBlock({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-ink-muted" role="status">
      <Spinner />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function Skeleton({ className = 'h-24' }: { className?: string }) {
  return <div className={`animate-pulse-soft rounded-card bg-surface-muted ${className}`} />;
}

type AlertKind = 'info' | 'success' | 'warning' | 'danger';

const ALERT: Record<AlertKind, { box: string; icon: IconName }> = {
  info: { box: 'bg-tone-info-bg text-tone-info-fg', icon: 'info' },
  success: { box: 'bg-tone-active-bg text-tone-active-fg', icon: 'check' },
  warning: { box: 'bg-tone-attention-bg text-tone-attention-fg', icon: 'alert' },
  danger: { box: 'bg-tone-danger-bg text-tone-danger-fg', icon: 'alert' },
};

export function Alert({
  kind = 'info',
  title,
  children,
  action,
}: {
  kind?: AlertKind;
  title?: ReactNode;
  children?: ReactNode;
  action?: ReactNode;
}) {
  const style = ALERT[kind];
  return (
    <div className={`flex gap-3 rounded-control px-4 py-3 text-sm ${style.box}`} role={kind === 'danger' ? 'alert' : 'status'}>
      <Icon name={style.icon} className="mt-0.5 size-5 shrink-0" />
      <div className="min-w-0 flex-1">
        {title && <p className="font-semibold">{title}</p>}
        {children && <div className={title ? 'mt-0.5 opacity-90' : ''}>{children}</div>}
      </div>
      {action && <div className="shrink-0 self-center">{action}</div>}
    </div>
  );
}

export function EmptyState({
  icon = 'leaf',
  title,
  children,
  action,
}: {
  icon?: IconName;
  title: ReactNode;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center rounded-card border border-dashed border-line-strong bg-surface/60 px-6 py-14 text-center">
      <span className="grid size-14 place-items-center rounded-full bg-brand-50 text-brand-600">
        <Icon name={icon} className="size-7" />
      </span>
      <h3 className="mt-4 text-xl font-semibold">{title}</h3>
      {children && <p className="mt-2 max-w-md text-sm text-ink-muted">{children}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
