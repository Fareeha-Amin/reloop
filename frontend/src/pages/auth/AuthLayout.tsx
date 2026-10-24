import type { ReactNode } from 'react';

import { t } from '../../i18n';
import { Icon, LogoMark } from '../../ui/icons';

/** Split layout for the sign-in and registration pages. */
export function AuthLayout({ title, subtitle, children, wide = false }: { title: string; subtitle?: ReactNode; children: ReactNode; wide?: boolean }) {
  return (
    <main className="mx-auto grid max-w-6xl gap-8 px-4 py-10 sm:px-6 lg:grid-cols-[2fr_3fr] lg:py-16">
      <aside className="relative hidden overflow-hidden rounded-card bg-brand-950 p-10 text-brand-50 lg:flex lg:flex-col lg:justify-between">
        <div className="pointer-events-none absolute -right-20 -bottom-24 size-80 rounded-full bg-leaf/20 blur-3xl" />
        <LogoMark className="size-12" />
        <div className="relative">
          <p className="font-display text-3xl leading-tight font-semibold text-surface">{t('auth.asideQuote')}</p>
          <ul className="mt-8 space-y-3 text-sm text-brand-100">
            {(['one', 'two', 'three'] as const).map((key) => (
              <li key={key} className="flex gap-2">
                <Icon name="check" className="mt-0.5 size-4 shrink-0 text-leaf" />
                {t(`auth.asidePoints.${key}`)}
              </li>
            ))}
          </ul>
        </div>
      </aside>
      <section className={`animate-rise ${wide ? '' : 'lg:max-w-lg'}`}>
        <h1 className="text-3xl font-semibold sm:text-4xl">{title}</h1>
        {subtitle && <div className="mt-2 text-ink-muted">{subtitle}</div>}
        <div className="mt-8">{children}</div>
      </section>
    </main>
  );
}
