import type { ReactNode } from 'react';
import { Link } from 'react-router';

import { DeclineFlow, HandoverScene, JourneyVisual, ListScene, MatchScene, NeedsScene, delay } from '../components/landing';
import { paths } from '../app/paths';
import { useSession } from '../app/session';
import { t } from '../i18n';
import { LinkButton } from '../ui/Button';
import { Icon, type IconName } from '../ui/icons';
import { homeFor } from '../vocab/roles';

const PROMISES: Array<{ key: string; icon: IconName }> = [
  { key: 'need', icon: 'heart' },
  { key: 'deadEnd', icon: 'route' },
  { key: 'journey', icon: 'sparkles' },
];

const STEPS: Array<{ key: string; icon: IconName; art: ReactNode }> = [
  { key: 'list', icon: 'camera', art: <ListScene /> },
  { key: 'choose', icon: 'star', art: <MatchScene /> },
  { key: 'handover', icon: 'hands', art: <HandoverScene /> },
];

export function Landing() {
  const { user } = useSession();

  return (
    <main className="overflow-x-clip">
      {/* ---------------------------------------------------------------- Hero */}
      <section className="relative isolate overflow-hidden bg-brand-950 text-brand-50">
        <div className="pointer-events-none absolute inset-0 -z-10">
          <div className="absolute -top-48 left-1/2 size-[46rem] -translate-x-1/2 rounded-full bg-mint/20 blur-3xl" />
          <div className="absolute -right-40 bottom-[-18rem] size-[34rem] rounded-full bg-clay-500/25 blur-3xl" />
          <div
            className="absolute inset-0 opacity-[0.07]"
            style={{
              backgroundImage: 'radial-gradient(var(--color-leaf) 1px, transparent 1px)',
              backgroundSize: '28px 28px',
            }}
          />
        </div>

        <div className="mx-auto grid max-w-6xl items-center gap-14 px-4 pt-16 pb-28 sm:px-6 lg:grid-cols-[1.1fr_1fr] lg:pt-24 lg:pb-36">
          <div>
            <p className="inline-flex animate-rise items-center gap-2 rounded-pill bg-brand-50/10 px-3.5 py-1.5 text-xs font-semibold tracking-wide text-leaf ring-1 ring-leaf/30 backdrop-blur">
              <Icon name="recycle" className="size-4" />
              {t('landing.eyebrow')}
            </p>
            <h1 className="mt-6 animate-rise text-5xl leading-[1.02] font-semibold sm:text-6xl lg:text-7xl" style={delay(80)}>
              <span className="block text-brand-50">{t('landing.titleA')}</span>
              <span className="block bg-linear-to-r from-leaf via-mint to-leaf bg-clip-text pb-2 text-transparent">
                {t('landing.titleB')}
              </span>
            </h1>
            <p className="mt-6 max-w-xl animate-rise text-lg leading-relaxed text-brand-100/90 sm:text-xl" style={delay(160)}>
              {t('landing.subtitle')}
            </p>
            <div className="mt-9 flex animate-rise flex-wrap gap-3" style={delay(240)}>
              {user ? (
                <LinkButton to={homeFor(user.role)} variant="inverse" size="lg" iconAfter="arrowRight">
                  {t('landing.toDashboard')}
                </LinkButton>
              ) : (
                <>
                  <LinkButton to={paths.registerDonor} variant="inverse" size="lg" iconAfter="arrowRight">
                    {t('landing.ctaDonate')}
                  </LinkButton>
                  <LinkButton to={paths.registerOrganisation} variant="outlineInverse" size="lg">
                    {t('landing.ctaOrganisation')}
                  </LinkButton>
                </>
              )}
            </div>
            <ul className="mt-10 flex animate-rise flex-wrap gap-x-6 gap-y-2 text-sm text-brand-100/80" style={delay(320)}>
              {(['verified', 'private', 'tracked'] as const).map((key) => (
                <li key={key} className="flex items-center gap-2">
                  <Icon name="check" className="size-4 text-leaf" />
                  {t(`landing.trust.${key}`)}
                </li>
              ))}
            </ul>
          </div>
          <div className="animate-rise px-2 sm:px-10 lg:px-0" style={delay(200)}>
            <JourneyVisual />
          </div>
        </div>
      </section>

      {/* ---------------------------------------------------------- Promises */}
      <section className="relative z-10 mx-auto -mt-16 max-w-6xl px-4 sm:px-6">
        <div className="grid gap-4 md:grid-cols-3">
          {PROMISES.map((p, i) => (
            <div
              key={p.key}
              className="animate-rise rounded-card border border-line bg-surface p-6 shadow-lift"
              style={delay(300 + i * 90)}
            >
              <span className="grid size-11 place-items-center rounded-xl bg-brand-50 text-brand-700">
                <Icon name={p.icon} />
              </span>
              <p className="mt-4 text-xs font-semibold tracking-[0.14em] text-brand-600 uppercase">
                {t(`landing.promises.${p.key}.label`)}
              </p>
              <h3 className="mt-1.5 text-xl font-semibold">{t(`landing.promises.${p.key}.title`)}</h3>
              <p className="mt-1.5 text-ink-muted">{t(`landing.promises.${p.key}.text`)}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ----------------------------------------------------------- How it works */}
      <section className="mx-auto max-w-6xl px-4 pt-28 pb-24 sm:px-6">
        <div className="text-center">
          <p className="text-xs font-semibold tracking-[0.16em] text-brand-600 uppercase">{t('landing.stepsEyebrow')}</p>
          <h2 className="mt-3 text-4xl font-semibold sm:text-5xl">{t('landing.stepsTitle')}</h2>
        </div>
        <ol className="mt-14 grid gap-14 md:grid-cols-3 md:gap-6">
          {STEPS.map((s, i) => (
            <li key={s.key}>
              {/* The badges are positioned against the image, not the whole step */}
              <div className="relative">
                {s.art}
                <span className="absolute top-3 left-3 grid size-7 place-items-center rounded-full bg-surface text-xs font-bold text-brand-900 shadow-card">
                  {i + 1}
                </span>
                <span className="absolute -bottom-7 left-5 grid size-14 place-items-center rounded-full bg-brand-900 text-leaf shadow-glow ring-8 ring-canvas">
                  <Icon name={s.icon} className="size-6" />
                </span>
              </div>
              <h3 className="mt-12 text-xl font-semibold">{t(`landing.steps.${s.key}.title`)}</h3>
              <p className="mt-2 max-w-xs text-ink-muted">{t(`landing.steps.${s.key}.text`)}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* -------------------------------------------------------- A "no" is never the end */}
      <section className="relative isolate overflow-hidden bg-brand-950 text-brand-50">
        <div className="pointer-events-none absolute inset-0 -z-10">
          <div className="absolute -top-40 right-[-6rem] size-[32rem] rounded-full bg-leaf/10 blur-3xl" />
          <div className="absolute bottom-[-12rem] left-[10%] size-[28rem] rounded-full bg-clay-500/20 blur-3xl" />
        </div>
        <div className="mx-auto max-w-6xl px-4 py-24 sm:px-6">
          <p className="text-xs font-semibold tracking-[0.16em] text-leaf uppercase">{t('landing.flow.eyebrow')}</p>
          <h2 className="mt-3 max-w-3xl text-4xl leading-tight font-semibold sm:text-5xl">{t('landing.flow.title')}</h2>
          <p className="mt-4 max-w-2xl text-lg text-brand-100/90">{t('landing.flow.text')}</p>
          <DeclineFlow />
        </div>
      </section>

      {/* ------------------------------------------------------ Organisations */}
      <section className="mx-auto max-w-6xl px-4 pt-24 pb-24 sm:px-6">
        <div className="grid items-center gap-10 overflow-hidden rounded-card border border-line bg-surface p-8 shadow-card sm:p-12 lg:grid-cols-[1.1fr_1fr]">
          <div>
            <p className="text-xs font-semibold tracking-[0.16em] text-clay-700 uppercase">{t('landing.orgEyebrow')}</p>
            <h2 className="mt-3 text-3xl leading-tight font-semibold sm:text-4xl">{t('landing.orgTitle')}</h2>
            <p className="mt-4 max-w-xl text-lg text-ink-muted">{t('landing.orgText')}</p>
            {!user && (
              <div className="mt-8">
                <LinkButton to={paths.registerOrganisation} variant="primary" size="lg" iconAfter="arrowRight">
                  {t('landing.ctaOrganisation')}
                </LinkButton>
              </div>
            )}
          </div>
          <div className="space-y-3">
            <NeedsScene />
            <div className="grid grid-cols-4 gap-3" aria-hidden="true">
              {(['building', 'school', 'heart', 'hands'] as const).map((icon, i) => (
                <div
                  key={icon}
                  className={`grid h-16 place-items-center rounded-card ${
                    i % 3 === 0 ? 'bg-brand-900 text-leaf' : 'bg-surface-muted text-brand-600'
                  }`}
                >
                  <Icon name={icon} className="size-7" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* --------------------------------------------------------------- CTA */}
      <section className="mx-auto max-w-6xl px-4 py-24 sm:px-6">
        <div className="relative isolate overflow-hidden rounded-[2rem] bg-brand-900 px-6 py-16 text-center sm:px-12 sm:py-20">
          <div className="absolute -top-32 left-1/2 -z-10 size-[30rem] -translate-x-1/2 rounded-full bg-mint/30 blur-3xl" />
          <div className="absolute -bottom-40 -left-20 -z-10 size-80 rounded-full bg-clay-500/25 blur-3xl" />
          <h2 className="mx-auto max-w-2xl text-4xl leading-tight font-semibold text-brand-50 sm:text-5xl">{t('landing.ctaTitle')}</h2>
          <p className="mx-auto mt-4 max-w-xl text-lg text-brand-100/90">{t('landing.ctaText')}</p>
          <div className="mt-9 flex flex-wrap justify-center gap-3">
            {user ? (
              <LinkButton to={homeFor(user.role)} variant="inverse" size="lg" iconAfter="arrowRight">
                {t('landing.toDashboard')}
              </LinkButton>
            ) : (
              <>
                <LinkButton to={paths.registerDonor} variant="inverse" size="lg" iconAfter="arrowRight">
                  {t('landing.ctaDonate')}
                </LinkButton>
                <LinkButton to={paths.map} variant="outlineInverse" size="lg" icon="map">
                  {t('landing.exploreMap')}
                </LinkButton>
              </>
            )}
          </div>
          {!user && (
            <p className="mt-6 text-sm text-brand-100/70">
              {t('landing.haveAccount')}{' '}
              <Link to={paths.login} className="font-semibold text-leaf underline-offset-4 hover:underline">
                {t('nav.login')}
              </Link>
            </p>
          )}
        </div>
      </section>

      {/* ------------------------------------------------------------ Numbers */}
      <section className="bg-surface-muted/70">
        <div className="mx-auto grid max-w-6xl gap-10 px-4 py-20 sm:px-6 lg:grid-cols-[1.2fr_1fr] lg:items-center">
          <div>
            <p className="text-xs font-semibold tracking-[0.16em] text-clay-700 uppercase">{t('landing.whyEyebrow')}</p>
            <p className="mt-4 font-display text-6xl font-semibold text-brand-700 sm:text-8xl">{t('landing.stats.textile.value')}</p>
            <p className="mt-4 max-w-lg text-xl text-ink-soft">{t('landing.stats.textile.text')}</p>
            <p className="mt-3 text-xs text-ink-muted">{t('landing.stats.textile.source')}</p>
          </div>
          <div className="grid gap-4">
            {(['postConsumer', 'unaccounted'] as const).map((key) => (
              <div key={key} className="rounded-card border border-line bg-surface p-6 shadow-card">
                <p className="font-display text-4xl font-semibold text-clay-500">{t(`landing.stats.${key}.value`)}</p>
                <p className="mt-2 text-ink-soft">{t(`landing.stats.${key}.text`)}</p>
                <p className="mt-3 text-xs text-ink-muted">{t(`landing.stats.${key}.source`)}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
