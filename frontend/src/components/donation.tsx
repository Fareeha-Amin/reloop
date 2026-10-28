import type { DonationOut, HandoverOptionOut, HolderOut } from '../api/schema';
import { paths } from '../app/paths';
import { formatDate, formatDateTime } from '../i18n/format';
import { t } from '../i18n';
import { Card, CardTitle, Facts, LinkCard } from '../ui/Card';
import { Icon } from '../ui/icons';
import { Tag } from '../ui/Tag';
import { categoryIcon, conditionLabel, vocabLabel } from '../vocab/display';
import { UnreadMessagesTag } from './chat';
import { PointMap } from './maps';
import { StatusTag } from './StatusTag';

export function CategoryBadge({ category, size = 'md' }: { category: string; size?: 'md' | 'lg' }) {
  const box = size === 'lg' ? 'size-14 rounded-card' : 'size-11 rounded-control';
  return (
    <span className={`grid shrink-0 place-items-center bg-brand-50 text-brand-700 ${box}`}>
      <Icon name={categoryIcon(category)} className={size === 'lg' ? 'size-7' : 'size-5.5'} />
    </span>
  );
}

/** "12 Clothes · Gently used" */
export function donationTitle(d: { quantity: number; category: string }): string {
  return t('donation.title', { count: d.quantity, category: vocabLabel('Category', d.category) });
}

export function DonationCard({ donation }: { donation: DonationOut }) {
  return (
    <LinkCard to={paths.donation(donation.id)}>
      <div className="flex items-start gap-4">
        <CategoryBadge category={donation.category} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="truncate font-sans text-base font-semibold">{donationTitle(donation)}</h3>
            <StatusTag status={donation.status} />
          </div>
          <p className="mt-1 text-sm text-ink-muted">
            {conditionLabel(donation.condition)} · {t('donation.listedOn', { date: formatDate(donation.created_at) })}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {donation.is_priority && (
              <Tag tone="attention" icon="flag">
                {t('donation.priority')}
              </Tag>
            )}
            {donation.holder && (
              <Tag tone="active" icon="building">
                {donation.holder.organization_name}
              </Tag>
            )}
            {donation.escalation_cause && (
              <Tag tone="attention" icon="alert">
                {t('donation.needsDecision')}
              </Tag>
            )}
            <UnreadMessagesTag summary={donation.chat} />
          </div>
        </div>
      </div>
    </LinkCard>
  );
}

/** The organisation holding the donation, with its address and contact for the handover. */
export function HolderCard({ holder, title, note }: { holder: HolderOut; title?: string; note?: string }) {
  return (
    <Card>
      <CardTitle aside={<Tag tone="active" icon="check">{t('holder.accepted')}</Tag>}>{title ?? t('holder.title')}</CardTitle>
      <div className="grid gap-5 md:grid-cols-2">
        <div className="space-y-4">
          <div>
            <p className="text-lg font-semibold">{holder.organization_name}</p>
            <p className="mt-1 text-sm text-ink-muted">
              {holder.pickup_capable ? t('holder.collects') : t('holder.dropoffOnly')}
            </p>
          </div>
          <Facts
            items={[
              { label: t('holder.address'), value: holder.address_text },
              { label: t('holder.contact'), value: holder.contact_person },
              {
                label: t('holder.phone'),
                value: (
                  <a className="font-semibold text-brand-700 underline-offset-2 hover:underline" href={`tel:${holder.phone}`}>
                    {holder.phone}
                  </a>
                ),
              },
              holder.handover && {
                label: vocabLabel('HandoverMode', holder.handover.mode),
                value: formatDateTime(holder.handover.scheduled_for),
              },
            ]}
          />
          <p className="text-xs text-ink-muted">{note ?? t('holder.privacy')}</p>
        </div>
        <PointMap point={{ lat: holder.latitude, lng: holder.longitude }} />
      </div>
    </Card>
  );
}

/** The three ways an accepted donation can reach the organisation, as the donor sees
 * them: the organisation's own collection is informational (it schedules it, not the
 * donor), drop-off and platform pickup are the donor's buttons, above this card. Only
 * rendered while a handover hasn't been chosen yet (ACCEPTED). */
export function HandoverOptionsCard({ options }: { options: HandoverOptionOut[] }) {
  if (options.length === 0) return null;
  return (
    <Card>
      <CardTitle>{t('holder.pathsTitle')}</CardTitle>
      <ul className="space-y-2.5">
        {options.map((o) => (
          <li key={o.path} className="flex items-center gap-3 text-sm">
            <Icon
              name={o.available ? 'check' : 'x'}
              className={`size-4 shrink-0 ${o.available ? 'text-brand-600' : 'text-ink-muted'}`}
            />
            <span className={o.available ? '' : 'text-ink-muted line-through'}>{vocabLabel('HandoverMode', o.path)}</span>
            {!o.you_do_it && <Tag tone="neutral">{t('holder.theyDoIt')}</Tag>}
          </li>
        ))}
      </ul>
    </Card>
  );
}
