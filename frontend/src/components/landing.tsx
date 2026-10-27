import { Fragment, type CSSProperties, type ReactNode } from 'react';

import { t } from '../i18n';
import { Icon, type IconName } from '../ui/icons';

/*
 * Landing-page visuals. Everything here is ILLUSTRATIVE: the journey cards, the match
 * mock-up, the example organisation names and the design images (docs/design, copied to
 * public/landing) describe how ReLoop works. They are not live data and show no real
 * donor, organisation or donation. Each image is a single component, so a different
 * licensed image can replace it without touching the page layout.
 */

export const delay = (ms: number): CSSProperties => ({ animationDelay: `${ms}ms` });

/* -------------------------------------------------------------------- Hero journey */

function JourneyCard({
  icon,
  tile,
  messageKey,
  pos,
  ms,
  photo,
}: {
  icon: IconName;
  tile: string;
  messageKey: 'listed' | 'matched' | 'warmer';
  pos: string;
  ms: number;
  photo?: string;
}) {
  return (
    <div
      className={`relative w-full max-w-xs rounded-card bg-surface p-3.5 shadow-lift ring-1 ring-line animate-float sm:absolute sm:w-64 sm:max-w-none ${pos}`}
      style={delay(ms)}
    >
      {photo && <img src={photo} alt="" className="mb-3 h-36 w-full rounded-xl object-cover" />}
      <span className="flex items-center gap-3">
        <span className={`grid size-12 shrink-0 place-items-center rounded-2xl ${tile}`}>
          <Icon name={icon} className="size-6" />
        </span>
        <span className="min-w-0">
          <span className="block text-sm font-semibold text-ink sm:text-base">{t(`landing.journey.${messageKey}.title`)}</span>
          <span className="block text-sm text-ink-muted">{t(`landing.journey.${messageKey}.text`)}</span>
        </span>
      </span>
    </div>
  );
}

/*
 * The donation's journey as a flow: three cards, joined by arrows, reading top to bottom
 * in a zigzag. On small screens the cards stack. On sm and up they sit on a 480 × 480
 * stage. The first card carries the design photo (docs/design/jacket.png, cropped to
 * remove its baked-in card). The card text is illustrative, not live data.
 */
export function JourneyVisual() {
  return (
    <div className="relative mx-auto flex w-full max-w-md flex-col items-center gap-5 sm:block sm:h-[480px] sm:max-w-[480px]" aria-hidden="true">
      {/* Backdrop: blurred shapes in the brand palette */}
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute top-[6%] left-[10%] size-64 rounded-full bg-leaf/15 blur-3xl" />
        <div className="absolute top-[42%] right-[4%] size-72 rounded-full bg-clay-500/25 blur-3xl" />
        <div className="absolute bottom-[2%] left-[18%] size-56 rounded-full bg-mint/20 blur-3xl" />
      </div>

      {/* Arrows between the cards: sm and up only */}
      <svg className="pointer-events-none absolute inset-0 hidden size-full sm:block" viewBox="0 0 480 480" fill="none">
        <defs>
          <marker id="journey-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0 0 10 5 0 10" className="fill-leaf" />
          </marker>
        </defs>
        <path d="M262 116 C 330 116, 344 170, 344 230" className="stroke-leaf/70" strokeWidth="2" strokeDasharray="6 6" markerEnd="url(#journey-arrow)" />
        <path d="M344 336 L 344 378" className="stroke-leaf/70" strokeWidth="2" strokeDasharray="6 6" markerEnd="url(#journey-arrow)" />
      </svg>

      <JourneyCard
        icon="shirt"
        tile="bg-clay-100 text-clay-700"
        messageKey="listed"
        pos="sm:top-0 sm:left-0"
        ms={0}
        photo="/landing/jacket.jpg"
      />
      <JourneyCard icon="building" tile="bg-brand-50 text-brand-700" messageKey="matched" pos="sm:top-[236px] sm:left-[216px]" ms={1200} />
      <JourneyCard icon="heart" tile="bg-brand-100 text-brand-700" messageKey="warmer" pos="sm:top-[384px] sm:left-24" ms={2400} />
    </div>
  );
}

/* ------------------------------------------------------------------- Step art */

/** A rounded frame for the illustrated scene of a step or section. */
function Scene({ className, children }: { className: string; children: ReactNode }) {
  return (
    <div className={`relative grid h-52 place-items-center overflow-hidden rounded-card ${className}`} aria-hidden="true">
      {children}
    </div>
  );
}

/** A design image in a step's frame. Decorative, so it has no alt text. */
function Photo({ src }: { src: string }) {
  return <img src={src} alt="" className="h-52 w-full rounded-card object-cover" />;
}

/** Step 1: folded clothes (docs/design/clothes.png). */
export function ListScene() {
  return <Photo src="/landing/clothes.jpg" />;
}

/** Step 2: a suggested-match mock-up, using fictional organisation names. */
export function MatchScene() {
  return (
    <Scene className="bg-linear-to-br from-brand-50 to-sky-100">
      <div className="w-64 rounded-card bg-surface p-3 shadow-lift ring-1 ring-line">
        <p className="px-1 pb-2 text-xs font-semibold text-ink-muted">{t('landing.match.title')}</p>
        <div className="flex items-center gap-3 rounded-xl bg-brand-50 p-2.5">
          <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-brand-900 text-leaf">
            <Icon name="school" className="size-4.5" />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-semibold text-ink">{t('landing.match.first.name')}</span>
            <span className="block truncate text-xs text-ink-muted">{t('landing.match.first.need')}</span>
          </span>
          <span className="grid size-5 shrink-0 place-items-center rounded-full bg-brand-700 text-brand-50">
            <Icon name="check" className="size-3" />
          </span>
        </div>
        <div className="flex items-center gap-3 p-2.5">
          <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-clay-100 text-clay-700">
            <Icon name="building" className="size-4.5" />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-semibold text-ink">{t('landing.match.second.name')}</span>
            <span className="block truncate text-xs text-ink-muted">{t('landing.match.second.need')}</span>
          </span>
          <span className="size-5 shrink-0 rounded-full ring-1 ring-line-strong" />
        </div>
      </div>
    </Scene>
  );
}

/*
 * Step 3: a handover (docs/design/handover_box.png). The vest in that image carries an
 * organisation's name; it must be replaced before launch unless that name is fictional.
 */
export function HandoverScene() {
  return <Photo src="/landing/handover_box.jpg" />;
}

/** The organisation section's needs card (docs/design/childrens_home_needs.png). */
export function NeedsScene() {
  return <img src="/landing/childrens_home_needs.png" alt="" className="w-full rounded-card" />;
}

/* ------------------------------------------------------------ Decline flow */

type FlowTone = 'neutral' | 'declined' | 'recovery' | 'outcome';

/** Surface and text per node. Declined and recovery reuse the status tone tokens. */
const FLOW_TONES: Record<FlowTone, { card: string; tile: string; title: string; text: string }> = {
  neutral: { card: 'bg-surface', tile: 'bg-brand-50 text-brand-700', title: 'text-ink', text: 'text-ink-muted' },
  declined: { card: 'bg-surface', tile: 'bg-tone-danger-bg text-tone-danger-fg', title: 'text-ink', text: 'text-ink-muted' },
  recovery: { card: 'bg-surface', tile: 'bg-tone-recovery-bg text-tone-recovery-fg', title: 'text-ink', text: 'text-ink-muted' },
  outcome: { card: 'bg-brand-900 ring-1 ring-leaf/40', tile: 'bg-leaf text-brand-950', title: 'text-brand-50', text: 'text-brand-100/85' },
};

export const FLOW_STEPS: Array<{ key: string; icon: IconName; tone: FlowTone }> = [
  { key: 'listed', icon: 'shirt', tone: 'neutral' },
  { key: 'declinedA', icon: 'building', tone: 'declined' },
  { key: 'declinedB', icon: 'building', tone: 'declined' },
  { key: 'recycling', icon: 'recycle', tone: 'recovery' },
  { key: 'outcome', icon: 'leaf', tone: 'outcome' },
];

/**
 * A donation's route through the platform as a row of nodes. Declined nodes carry a
 * cross on their icon; the arrows point along the route. On large screens it reads left
 * to right; below that the route runs top to bottom.
 */
export function DeclineFlow() {
  return (
    <ol className="mt-12 flex flex-col gap-3 lg:flex-row lg:items-stretch lg:gap-2">
      {FLOW_STEPS.map((step, i) => {
        const tone = FLOW_TONES[step.tone];
        return (
          <Fragment key={step.key}>
            {i > 0 && (
              <li className="flex justify-center lg:shrink-0" aria-hidden="true">
                <Icon name="arrowRight" className="size-5 rotate-90 text-leaf lg:rotate-0" />
              </li>
            )}
            <li className={`flex min-w-0 flex-1 items-center gap-3 rounded-card p-4 shadow-card ${tone.card}`}>
              <span className={`relative grid size-11 shrink-0 place-items-center rounded-xl ${tone.tile}`}>
                <Icon name={step.icon} className="size-5" />
                {step.tone === 'declined' && (
                  <span className="absolute -top-1.5 -right-1.5 grid size-5 place-items-center rounded-full bg-danger-500 text-brand-50">
                    <Icon name="x" className="size-3" />
                  </span>
                )}
              </span>
              <span className="min-w-0">
                <span className={`block text-sm font-semibold ${tone.title}`}>{t(`landing.flow.${step.key}.title`)}</span>
                <span className={`block text-xs ${tone.text}`}>{t(`landing.flow.${step.key}.text`)}</span>
              </span>
            </li>
          </Fragment>
        );
      })}
    </ol>
  );
}
