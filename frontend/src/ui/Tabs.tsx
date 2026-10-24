import type { ReactNode } from 'react';

import { Icon, type IconName } from './icons';

export interface TabItem {
  value: string;
  label: ReactNode;
  icon?: IconName;
  /** A count shown beside the label, e.g. items waiting. */
  count?: number;
}

/** A row of page sections; scrolls sideways on narrow screens. */
export function Tabs({
  items,
  value,
  onChange,
  label,
}: {
  items: TabItem[];
  value: string;
  onChange: (value: string) => void;
  label: string;
}) {
  return (
    <div
      role="tablist"
      aria-label={label}
      className="-mx-4 mb-6 flex gap-1 overflow-x-auto border-b border-line px-4 sm:mx-0 sm:px-0"
    >
      {items.map((item) => {
        const active = item.value === value;
        return (
          <button
            key={item.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(item.value)}
            className={`-mb-px inline-flex shrink-0 items-center gap-2 border-b-2 px-3.5 py-3 text-sm font-semibold transition ${
              active ? 'border-brand-600 text-ink' : 'border-transparent text-ink-muted hover:text-ink'
            }`}
          >
            {item.icon && <Icon name={item.icon} className="size-4.5" />}
            {item.label}
            {item.count !== undefined && (
              <span
                className={`grid h-5 min-w-5 place-items-center rounded-pill px-1.5 text-[11px] font-bold ${
                  active ? 'bg-brand-900 text-leaf' : 'bg-surface-muted text-ink-soft'
                }`}
              >
                {item.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

export interface ChipItem {
  value: string | null;
  label: ReactNode;
  icon?: IconName;
}

/** A single-choice filter as pills. `null` is a valid value (e.g. "All"). */
export function Chips({
  items,
  value,
  onChange,
  label,
}: {
  items: ChipItem[];
  value: string | null;
  onChange: (value: string | null) => void;
  label: string;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="flex flex-wrap gap-2">
      {items.map((item) => {
        const active = item.value === value;
        return (
          <button
            key={item.value ?? '*'}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(item.value)}
            className={`inline-flex items-center gap-1.5 rounded-pill px-3.5 py-1.5 text-sm font-semibold transition ${
              active
                ? 'bg-brand-900 text-leaf shadow-card'
                : 'bg-surface text-ink-soft ring-1 ring-line hover:bg-surface-muted hover:text-ink'
            }`}
          >
            {item.icon && <Icon name={item.icon} className="size-4" />}
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
