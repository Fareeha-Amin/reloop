import type { CSSProperties } from 'react';
import { Link } from 'react-router';

import { paths } from '../app/paths';
import { useSession } from '../app/session';
import { t } from '../i18n';
import { LinkButton } from '../ui/Button';
import { Icon, type IconName } from '../ui/icons';
import { homeFor } from '../vocab/roles';

const delay = (ms: number): CSSProperties => ({ animationDelay: `${ms}ms` });

/** Items orbiting a glowing core: the circular economy, at a glance. */
function Orbit() {
  const orbiters: Array<{ icon: IconName; angle: number }> = [
    { icon: 'shirt', angle: -90 },
    { icon: 'book', angle: 30 },
    { icon: 'toy', angle: 150 },
  ];
  return (
    <div className="relative mx-auto aspect-square w-full max-w-[460px]" aria-hidden="true">
      {/* Rings */}
      <div className="absolute inset-[6%] rounded-full border border-leaf/15" />
      <div className="absolute inset-[18%] rounded-full border border-leaf/20" />
      <div className="absolute inset-[6%] animate-spin-slow rounded-full border-2 border-dashed border-leaf/30" />
      {/* Core */}
      <div className="absolute inset-[30%] grid place-items-center rounded-full bg-linear-to-br from-brand-700 to-brand-900 shadow-glow ring-1 ring-leaf/30">
        <div className="text-center">
          <Icon name="recycle" className="mx-auto size-10 text-leaf sm:size-12" />
          <p className="mt-1 font-display text-lg font-semibold text-brand-50 sm:text-xl">{t('landing.orbitCore')}</p>
        </div>
      </div>
      {/* Orbiting items: the ring turns, each badge turns back to stay upright */}
      <div className="absolute inset-[6%] animate-spin-slow">
        {orbiters.map(({ icon, angle }) => {
          const rad = (angle * Math.PI) / 180;
          return (
            <div
              key={icon}
              className="absolute -translate-x-1/2 -translate-y-1/2"
              style={{ left: `${50 + 50 * Math.cos(rad)}%`, top: `${50 + 50 * Math.sin(rad)}%` }}
            >
              <span className="grid size-14 animate-spin-slow-reverse place-items-center rounded-2xl bg-leaf text-brand-950 shadow-glow sm:size-16">
                <Icon name={icon} className="size-7 sm:size-8" />
              </span>
            </div>
          );
        })}
      </div>
      {/* Floating promises */}
      {(
        [
          { key: 'need', icon: 'heart', pos: 'top-[8%] -left-2 sm:-left-8', ms: 0 },
          { key: 'landfill', icon: 'leaf', pos: 'top-[46%] -right-2 sm:-right-10', ms: 1200 },
          { key: 'private', icon: 'pin', pos: 'bottom-[6%] left-[4%]', ms: 2400 },
        ] as const
      ).map((chip) => (
        <div key={chip.key} className={`absolute ${chip.pos} hidden animate-float sm:block`} style={delay(chip.ms)}>
          <span className="flex items-center gap-2 rounded-pill bg-brand-50/10 px-3.5 py-2 text-xs font-semibold text-brand-50 shadow-lift ring-1 ring-brand-50/20 backdrop-blur-md sm:text-sm">
            <Icon name={chip.icon} className="size-4 text-leaf" />
            {t(`landing.chips.${chip.key}`)}
          </span>
        </div>
      ))}
    </div>
  );
}

const BECOMES: Array<{ key: string; icon: IconName; glow: string }> = [
  { key: 'clothes', icon: 'shirt', glow: 'bg-leaf/40' },
  { key: 'toys', icon: 'toy', glow: 'bg-clay-500/50' },
  { key: 'books', icon: 'book', glow: 'bg-ochre-500/50' },
];

const PROMISES: Array<{ key: string; icon: IconName }> = [
  { key: 'need', icon: 'heart' },
  { key: 'deadEnd', icon: 'route' },
  { key: 'journey', icon: 'sparkles' },
];

const STEPS: Array<{ key: string; icon: IconName }> = [
  { key: 'list', icon: 'camera' },
  { key: 'choose', icon: 'star' },
  { key: 'handover', icon: 'hands' },
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
          <div className="animate-rise px-6 sm:px-10 lg:px-0" style={delay(200)}>
            <Orbit />
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
              <h3 className="mt-4 text-xl font-semibold">{t(`landing.promises.${p.key}.title`)}</h3>
              <p className="mt-1.5 text-ink-muted">{t(`landing.promises.${p.key}.text`)}</p>
            </div>
          ))}
        </div>
      </section>

      {/* -------------------------------------------- What your donation becomes */}
      <section className="mx-auto max-w-6xl px-4 pt-24 pb-8 sm:px-6">
        <p className="text-xs font-semibold tracking-[0.16em] text-brand-600 uppercase">{t('landing.becomesEyebrow')}</p>
        <h2 className="mt-3 max-w-3xl text-4xl leading-tight font-semibold sm:text-5xl">{t('landing.becomesTitle')}</h2>
        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {BECOMES.map((b) => (
            <article key={b.key} className="group overflow-hidden rounded-card border border-line bg-surface shadow-card transition duration-300 hover:-translate-y-1 hover:shadow-lift">
              <div className="relative grid h-48 place-items-center overflow-hidden bg-brand-900">
                <div className={`absolute size-56 rounded-full blur-3xl transition duration-500 group-hover:scale-125 ${b.glow}`} />
                <div
                  className="absolute inset-0 opacity-10"
                  style={{ backgroundImage: 'radial-gradient(var(--color-leaf) 1px, transparent 1px)', backgroundSize: '18px 18px' }}
                />
                <span className="relative grid size-24 place-items-center rounded-[2rem] bg-brand-50/10 text-leaf ring-1 ring-brand-50/20 backdrop-blur transition duration-300 group-hover:rotate-[-6deg] group-hover:scale-105">
                  <Icon name={b.icon} className="size-12" />
                </span>
              </div>
              <div className="p-6">
                <p className="text-xs font-semibold tracking-[0.14em] text-ink-muted uppercase">{t(`landing.becomes.${b.key}.from`)}</p>
                <h3 className="mt-2 text-2xl leading-snug font-semibold">{t(`landing.becomes.${b.key}.to`)}</h3>
                <p className="mt-2 text-ink-muted">{t(`landing.becomes.${b.key}.text`)}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* ---------------------------------------------------------- Statement */}
      <section className="mx-auto max-w-5xl px-4 py-24 text-center sm:px-6">
        <Icon name="leaf" className="mx-auto size-9 text-brand-500" />
        <p className="mt-6 font-display text-3xl leading-snug font-semibold text-balance sm:text-5xl sm:leading-tight">
          {t('landing.statement')}
        </p>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-ink-muted">{t('landing.statementText')}</p>
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

      {/* -------------------------------------------------------------- Steps */}
      <section className="mx-auto max-w-6xl px-4 py-24 sm:px-6">
        <div className="text-center">
          <p className="text-xs font-semibold tracking-[0.16em] text-brand-600 uppercase">{t('landing.stepsEyebrow')}</p>
          <h2 className="mt-3 text-4xl font-semibold sm:text-5xl">{t('landing.stepsTitle')}</h2>
        </div>
        <ol className="relative mt-14 grid gap-10 md:grid-cols-3 md:gap-6">
          <div className="absolute top-8 right-[16%] left-[16%] hidden h-0.5 bg-linear-to-r from-brand-200 via-brand-400 to-brand-200 md:block" aria-hidden="true" />
          {STEPS.map((s, i) => (
            <li key={s.key} className="relative text-center">
              <span className="relative mx-auto grid size-16 place-items-center rounded-full bg-brand-900 text-leaf shadow-glow ring-8 ring-canvas">
                <Icon name={s.icon} className="size-7" />
                <span className="absolute -top-1 -right-1 grid size-6 place-items-center rounded-full bg-leaf text-xs font-bold text-brand-950">
                  {i + 1}
                </span>
              </span>
              <h3 className="mt-5 text-xl font-semibold">{t(`landing.steps.${s.key}.title`)}</h3>
              <p className="mx-auto mt-2 max-w-xs text-ink-muted">{t(`landing.steps.${s.key}.text`)}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* ------------------------------------------------------ Organisations */}
      <section className="mx-auto max-w-6xl px-4 pb-24 sm:px-6">
        <div className="grid items-center gap-10 overflow-hidden rounded-card border border-line bg-surface p-8 shadow-card sm:p-12 lg:grid-cols-[1.3fr_1fr]">
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
          <div className="grid grid-cols-2 gap-3" aria-hidden="true">
            {(['building', 'school', 'heart', 'hands'] as const).map((icon, i) => (
              <div
                key={icon}
                className={`grid aspect-square place-items-center rounded-card ${
                  i % 3 === 0 ? 'bg-brand-900 text-leaf' : 'bg-surface-muted text-brand-600'
                }`}
              >
                <Icon name={icon} className="size-10" />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* --------------------------------------------------------------- CTA */}
      <section className="mx-auto max-w-6xl px-4 pb-24 sm:px-6">
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
    </main>
  );
}
