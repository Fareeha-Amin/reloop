import type { ReactNode } from 'react';

import type { Tone } from '../vocab/display';
import { Icon, type IconName } from './icons';

/** Classes per tone. The colours themselves are tokens in styles/theme.css. */
const TONES: Record<Tone, string> = {
  neutral: 'bg-tone-neutral-bg text-tone-neutral-fg',
  info: 'bg-tone-info-bg text-tone-info-fg',
  progress: 'bg-tone-progress-bg text-tone-progress-fg',
  attention: 'bg-tone-attention-bg text-tone-attention-fg',
  active: 'bg-tone-active-bg text-tone-active-fg',
  reuse: 'bg-tone-reuse-bg text-tone-reuse-fg',
  recovery: 'bg-tone-recovery-bg text-tone-recovery-fg',
  recovered: 'bg-tone-recovered-bg text-tone-recovered-fg',
  danger: 'bg-tone-danger-bg text-tone-danger-fg',
  muted: 'bg-tone-muted-bg text-tone-muted-fg',
};

export function Tag({
  tone,
  children,
  dot = false,
  icon,
  size = 'sm',
}: {
  tone: Tone;
  children: ReactNode;
  dot?: boolean;
  icon?: IconName;
  size?: 'sm' | 'md';
}) {
  const sizing = size === 'md' ? 'px-3 py-1 text-sm' : 'px-2.5 py-0.5 text-xs';
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-pill font-semibold whitespace-nowrap ${sizing} ${TONES[tone]}`}>
      {dot && <span className="size-1.5 rounded-full bg-current" />}
      {icon && <Icon name={icon} className="size-3.5" />}
      {children}
    </span>
  );
}

const DOTS: Record<Tone, string> = {
  neutral: 'bg-tone-neutral-fg',
  info: 'bg-tone-info-fg',
  progress: 'bg-tone-progress-fg',
  attention: 'bg-ochre-500',
  active: 'bg-brand-500',
  reuse: 'bg-brand-800',
  recovery: 'bg-clay-500',
  recovered: 'bg-tone-recovered-bg',
  danger: 'bg-danger-500',
  muted: 'bg-tone-muted-fg',
};

/** A solid dot in a tone's colour (timelines, map legends). */
export function ToneDot({ tone, className = 'size-3' }: { tone: Tone; className?: string }) {
  return <span className={`inline-block shrink-0 rounded-full ${DOTS[tone]} ${className}`} />;
}

/** A small outlined label for honesty markers: Simulated, Estimate, Placeholder, Approximate. */
export function Marker({ children, icon = 'info' }: { children: ReactNode; icon?: IconName }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-pill border border-dashed border-ochre-500 bg-ochre-100/60 px-2 py-0.5 text-[11px] font-semibold tracking-wide text-ochre-700 uppercase">
      <Icon name={icon} className="size-3" />
      {children}
    </span>
  );
}
