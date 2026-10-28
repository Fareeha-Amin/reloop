/** Impact totals: reuse and recycling kept apart, every figure marked as an estimate
 * (app.domain.impact; non-negotiable 8). No business logic here: the API already split
 * the totals and set `placeholders`; this only lays them out. */

import { t } from '../i18n';
import { formatNumber } from '../i18n/format';
import { Card } from '../ui/Card';
import { Marker } from '../ui/Tag';
import { Icon } from '../ui/icons';
import type { ImpactTotalsOut } from '../api/schema';

function MetricCard({ icon, label, value }: { icon: 'heart' | 'recycle' | 'leaf'; label: string; value: string }) {
  return (
    <Card className="flex items-center gap-3.5 p-4 sm:p-5">
      <span className="grid size-11 shrink-0 place-items-center rounded-control bg-brand-50 text-brand-700">
        <Icon name={icon} className="size-5.5" />
      </span>
      <div className="min-w-0">
        <p className="truncate text-2xl font-semibold">{value}</p>
        <p className="truncate text-sm text-ink-muted">{label}</p>
      </div>
    </Card>
  );
}

export function ImpactCard({
  totals,
  title,
  showRecycled = true,
}: {
  totals: ImpactTotalsOut;
  title: string;
  /** Recycling is never credited to an organisation: its row omits those two metrics
   * rather than show a figure that can only ever be zero. */
  showRecycled?: boolean;
}) {
  return (
    <section>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-semibold">{title}</h2>
        <div className="flex flex-wrap gap-1.5">
          <Marker icon="info">{t('honesty.estimatedMass')}</Marker>
          {totals.placeholders && <Marker icon="alert">{t('honesty.placeholderWeights')}</Marker>}
        </div>
      </div>
      <div className={`grid gap-4 sm:grid-cols-2 ${showRecycled ? 'lg:grid-cols-4' : 'lg:grid-cols-2'}`}>
        <MetricCard icon="heart" label={t('impact.reusedItems')} value={t('common.items', { count: totals.reused_items })} />
        <MetricCard icon="leaf" label={t('impact.carbonAvoided')} value={t('impact.kg', { value: formatNumber(totals.carbon_avoided_kg) })} />
        {showRecycled && (
          <>
            <MetricCard icon="recycle" label={t('impact.recycledItems')} value={t('common.items', { count: totals.recycled_items })} />
            <MetricCard icon="recycle" label={t('impact.recycledMass')} value={t('impact.kg', { value: formatNumber(totals.recycled_mass_kg) })} />
          </>
        )}
      </div>
    </section>
  );
}
