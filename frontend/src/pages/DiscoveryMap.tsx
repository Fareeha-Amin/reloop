import { useState } from 'react';

import { categoryValues, type DiscoveryOrganisationOut } from '../api/schema';
import { paths } from '../app/paths';
import { useDiscovery } from '../app/queries';
import { useSession } from '../app/session';
import { ApiErrorAlert } from '../components/ApiErrorAlert';
import { AreaMap } from '../components/maps';
import { UrgencyTag } from '../components/StatusTag';
import { formatNumber } from '../i18n/format';
import { t } from '../i18n';
import { LinkButton } from '../ui/Button';
import { EmptyState, Skeleton } from '../ui/feedback';
import { Icon } from '../ui/icons';
import { Page, PageHeader } from '../ui/layout';
import { Marker } from '../ui/Tag';
import { Chips } from '../ui/Tabs';
import { categoryIcon, vocabLabel } from '../vocab/display';
import { ROLE } from '../vocab/roles';

function Needs({ org }: { org: DiscoveryOrganisationOut }) {
  if (org.needs.length === 0) return <p className="text-sm text-ink-muted">{t('discover.noNeeds')}</p>;
  return (
    <ul className="space-y-1.5">
      {org.needs.map((need) => (
        <li key={need.category} className="flex flex-wrap items-center gap-2 text-sm">
          <Icon name={categoryIcon(need.category)} className="size-4 text-brand-600" />
          <span className="font-medium">
            {t('discover.need', { count: need.quantity_needed, category: vocabLabel('Category', need.category) })}
          </span>
          <UrgencyTag urgency={need.urgency} />
        </li>
      ))}
    </ul>
  );
}

function Accepts({ org }: { org: DiscoveryOrganisationOut }) {
  return (
    <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-ink-muted">
      {org.categories_accepted.map((c) => (
        <span key={c} className="inline-flex items-center gap-1">
          <Icon name={categoryIcon(c)} className="size-4" />
          {vocabLabel('Category', c)}
        </span>
      ))}
      <span className="inline-flex items-center gap-1">
        <Icon name="truck" className="size-4" />
        {org.pickup_capable ? t('candidates.collects') : t('candidates.dropoffOnly')}
      </span>
    </p>
  );
}

function OrgPopup({ org }: { org: DiscoveryOrganisationOut }) {
  return (
    <div className="min-w-52 space-y-2">
      <p className="font-display text-base font-semibold">{org.name}</p>
      <Accepts org={org} />
      <Needs org={org} />
    </div>
  );
}

function OrgItem({ org, selected, onSelect }: { org: DiscoveryOrganisationOut; selected: boolean; onSelect: () => void }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={`block w-full rounded-card border bg-surface p-4 text-left shadow-card transition hover:-translate-y-0.5 hover:shadow-lift ${
        selected ? 'border-clay-500 ring-1 ring-clay-500' : 'border-line hover:border-brand-200'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-sans text-base font-semibold">{org.name}</h3>
        <Icon name="pin" className={`size-5 shrink-0 ${selected ? 'text-clay-500' : 'text-ink-muted'}`} />
      </div>
      <div className="mt-1.5">
        <Accepts org={org} />
      </div>
      <div className="mt-3 border-t border-line pt-3">
        <Needs org={org} />
      </div>
    </button>
  );
}

/** Public: anyone can see which verified organisations are near, and what they need. */
export function DiscoveryMap() {
  const { user } = useSession();
  const [category, setCategory] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const discovery = useDiscovery(category);

  const orgs = discovery.data?.organisations ?? [];
  const errorKm = discovery.data?.position_error_km ?? 0;
  const byId = new Map(orgs.map((o) => [o.id, o]));
  const areas = orgs.map((o) => ({ id: o.id, center: { lat: o.latitude, lng: o.longitude }, radiusKm: errorKm }));

  const cta = !user ? (
    <LinkButton to={paths.register} icon="heart">
      {t('discover.ctaJoin')}
    </LinkButton>
  ) : user.role === ROLE.donor ? (
    <LinkButton to={paths.newDonation} icon="plus">
      {t('donor.newDonation')}
    </LinkButton>
  ) : null;

  return (
    <Page>
      <PageHeader eyebrow={t('discover.eyebrow')} title={t('discover.title')} subtitle={t('discover.subtitle')} actions={cta} />

      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <Chips
          label={t('discover.filter')}
          value={category}
          onChange={(value) => {
            setCategory(value);
            setSelected(null);
          }}
          items={[
            { value: null, label: t('discover.all'), icon: 'sparkles' },
            ...categoryValues.map((c) => ({ value: c, label: vocabLabel('Category', c), icon: categoryIcon(c) })),
          ]}
        />
        {discovery.data && <p className="text-sm text-ink-muted">{t('discover.count', { count: orgs.length })}</p>}
      </div>

      <ApiErrorAlert error={discovery.error} />

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="self-start lg:sticky lg:top-24 lg:col-span-3">
          <AreaMap
            areas={areas}
            selected={selected}
            onSelect={setSelected}
            renderPopup={(id) => {
              const org = byId.get(id);
              return org ? <OrgPopup org={org} /> : null;
            }}
            className="h-[22rem] sm:h-[32rem]"
          />
          {discovery.data?.positions_are_approximate && (
            <p className="mt-3 flex flex-wrap items-center gap-2 text-xs text-ink-muted">
              <Marker icon="pin">{t('honesty.approximate')}</Marker>
              {t('discover.approximate', { km: formatNumber(errorKm) })}
            </p>
          )}
        </div>

        <div className="space-y-3 lg:col-span-2">
          {discovery.isPending ? (
            <>
              <Skeleton />
              <Skeleton />
              <Skeleton />
            </>
          ) : orgs.length === 0 ? (
            <EmptyState icon="map" title={t('discover.emptyTitle')}>
              {t('discover.emptyText')}
            </EmptyState>
          ) : (
            orgs.map((org) => (
              <OrgItem key={org.id} org={org} selected={org.id === selected} onSelect={() => setSelected(org.id)} />
            ))
          )}
        </div>
      </div>
    </Page>
  );
}
