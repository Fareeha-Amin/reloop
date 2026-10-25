import type { ReactNode } from 'react';

import { t } from '../../i18n';
import { Icon, LogoMark, type IconName } from '../../ui/icons';

/** The platform's loop, as the side panel tells it: the same for every visitor. */
const LOOP: Array<{ key: string; icon: IconName }> = [
  { key: 'list', icon: 'heart' },
  { key: 'match', icon: 'hands' },
  { key: 'reroute', icon: 'route' },
  { key: 'recover', icon: 'recycle' },
];

/**
 * Split layout for the sign-in and registration pages. The green panel explains the
 * platform in general terms (not promises to one kind of user). It keeps its own height
 * and stays in view (sticky) beside a long form; on a wide form it takes a narrower
 * column. Below `lg` it is hidden and the form has the page.
 */
export function AuthLayout({ title, subtitle, children, wide = false }: { title: string; subtitle?: ReactNode; children: ReactNode; wide?: boolean }) {
  const columns = wide ? 'lg:grid-cols-[minmax(0,5fr)_minmax(0,9fr)]' : 'lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]';
  return (
    <main className={`mx-auto grid max-w-6xl items-start gap-8 px-4 py-10 sm:px-6 lg:gap-12 lg:py-16 ${columns}`}>
      <aside className="relative hidden overflow-hidden rounded-card bg-brand-950 p-8 text-brand-50 lg:sticky lg:top-24 lg:block xl:p-10">
        <div className="pointer-events-none absolute -right-24 -bottom-28 size-80 rounded-full bg-leaf/20 blur-3xl" />
        <div className="pointer-events-none absolute -top-24 -left-20 size-64 rounded-full bg-clay-500/15 blur-3xl" />
        <div className="relative">
          <LogoMark className="size-11" />
          <p className="mt-6 text-xs font-semibold tracking-[0.14em] text-leaf uppercase">{t('auth.aside.eyebrow')}</p>
          <p className="mt-2 font-display text-2xl leading-tight font-semibold text-surface xl:text-3xl">{t('auth.aside.title')}</p>
          <ol className="mt-6">
            {LOOP.map((step, index) => (
              <li key={step.key} className="relative flex gap-4 pb-5 last:pb-0">
                {index < LOOP.length - 1 && <span className="absolute top-10 bottom-1 left-[19px] w-px bg-brand-50/15" aria-hidden="true" />}
                <span className="grid size-10 shrink-0 place-items-center rounded-full bg-brand-50/10 text-leaf ring-1 ring-brand-50/15">
                  <Icon name={step.icon} className="size-5" />
                </span>
                <div className="min-w-0 pt-1">
                  <p className="font-semibold text-surface">{t(`auth.aside.${step.key}.title`)}</p>
                  <p className="mt-0.5 text-sm text-brand-100">{t(`auth.aside.${step.key}.text`)}</p>
                </div>
              </li>
            ))}
          </ol>
          <p className="mt-6 border-t border-brand-50/15 pt-4 text-sm text-brand-100">{t('auth.aside.footer')}</p>
        </div>
      </aside>
      <section className={`min-w-0 animate-rise ${wide ? '' : 'lg:max-w-lg'}`}>
        <h1 className="text-3xl font-semibold sm:text-4xl">{title}</h1>
        {subtitle && <div className="mt-2 text-ink-muted">{subtitle}</div>}
        <div className="mt-8">{children}</div>
      </section>
    </main>
  );
}
