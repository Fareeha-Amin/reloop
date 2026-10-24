import type { CandidateOut } from '../api/schema';
import { formatNumber, formatPercent } from '../i18n/format';
import { t } from '../i18n';
import { Button } from '../ui/Button';
import { Icon } from '../ui/icons';
import { Tag } from '../ui/Tag';
import { factorReason, vocabLabel } from '../vocab/display';

/** The score, decomposed: each factor's share of its weight, and the reason behind it. */
export function ScoreBreakdown({ candidate }: { candidate: CandidateOut }) {
  return (
    <ul className="space-y-2.5">
      {candidate.components.map((c) => (
        <li key={c.factor}>
          <div className="flex items-baseline justify-between gap-3 text-sm">
            <span className="min-w-0">
              <span className="font-semibold text-ink">{vocabLabel('ScoreFactor', c.factor)}</span>
              <span className="text-ink-muted"> · {factorReason(c)}</span>
            </span>
            <span className="shrink-0 font-mono text-xs text-ink-muted" title={t('score.contributionHint')}>
              {t('score.contribution', { points: formatNumber(c.contribution * 100), max: formatNumber(c.weight * 100) })}
            </span>
          </div>
          <div className="mt-1 h-1.5 overflow-hidden rounded-pill bg-surface-muted">
            <div className="h-full rounded-pill bg-brand-500" style={{ width: `${Math.round(c.value * 100)}%` }} />
          </div>
        </li>
      ))}
    </ul>
  );
}

export function CandidateCard({
  candidate,
  top,
  onOffer,
  offering,
  canOffer,
}: {
  candidate: CandidateOut;
  top: boolean;
  onOffer: () => void;
  offering: boolean;
  canOffer: boolean;
}) {
  return (
    <article
      className={`rounded-card border bg-surface p-5 shadow-card transition sm:p-6 ${
        top ? 'border-brand-300 ring-1 ring-brand-300' : 'border-line'
      }`}
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 gap-4">
          <span
            className={`grid size-12 shrink-0 place-items-center rounded-control font-display text-xl font-semibold ${
              top ? 'bg-brand-900 text-leaf' : 'bg-surface-muted text-ink-soft'
            }`}
          >
            {candidate.rank}
          </span>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-lg font-semibold">{candidate.organization_name}</h3>
              {top && (
                <Tag tone="reuse" icon="star">
                  {t('candidates.best')}
                </Tag>
              )}
            </div>
            <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-ink-muted">
              <span className="inline-flex items-center gap-1">
                <Icon name="pin" className="size-4" />
                {t('common.km', { km: formatNumber(candidate.distance_km) })}
              </span>
              <span className="inline-flex items-center gap-1">
                <Icon name="truck" className="size-4" />
                {candidate.pickup_capable ? t('candidates.collects') : t('candidates.dropoffOnly')}
              </span>
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-4 sm:flex-col sm:items-end">
          <div className="text-right">
            <p className="font-display text-3xl font-semibold text-brand-700">{formatPercent(candidate.score)}</p>
            <p className="text-xs text-ink-muted">{t('candidates.matchScore')}</p>
          </div>
          {canOffer && (
            <Button variant={top ? 'primary' : 'secondary'} size="sm" busy={offering} onClick={onOffer} iconAfter="arrowRight">
              {t('candidates.offerTo')}
            </Button>
          )}
        </div>
      </div>
      <details className="group mt-4 border-t border-line pt-4" open={top}>
        <summary className="flex cursor-pointer list-none items-center gap-1.5 text-sm font-semibold text-brand-700">
          <Icon name="chevronRight" className="size-4 transition group-open:rotate-90" />
          {t('candidates.why')}
        </summary>
        <div className="mt-4">
          <ScoreBreakdown candidate={candidate} />
        </div>
      </details>
    </article>
  );
}
