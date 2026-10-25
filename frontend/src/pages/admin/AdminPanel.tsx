import { useState } from 'react';
import { useSearchParams } from 'react-router';

import {
  donationStatusValues,
  verificationStatusValues,
  type OrganizationCountsOut,
  type OrganizationOut,
  type QueueItemOut,
} from '../../api/schema';
import { paths } from '../../app/paths';
import { useAdminDonations, useAdminOrganisations, useAwaitingAdmin, useOrganisationCounts, useRecyclers } from '../../app/queries';
import { AdminDonationRow, AwaitingCard, SimulatedNote, SweepButton } from '../../components/admin';
import { ApiErrorAlert } from '../../components/ApiErrorAlert';
import { RecentActivity } from '../../components/NotificationList';
import { VerificationTag } from '../../components/StatusTag';
import { ADMIN_PAGE_SIZE } from '../../config';
import { formatDate, formatMoney } from '../../i18n/format';
import { t } from '../../i18n';
import { Button } from '../../ui/Button';
import { Card, LinkCard } from '../../ui/Card';
import { Alert, EmptyState, Skeleton } from '../../ui/feedback';
import { Select } from '../../ui/form';
import { Icon } from '../../ui/icons';
import { HeroBanner, Page } from '../../ui/layout';
import { Tag } from '../../ui/Tag';
import { Chips, Tabs } from '../../ui/Tabs';
import { categoryIcon, statusTone, vocabLabel } from '../../vocab/display';

const TABS = ['awaiting', 'organisations', 'donations', 'recyclers'] as const;
type Tab = (typeof TABS)[number];

function Loading() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-20" />
      <Skeleton className="h-20" />
    </div>
  );
}

/** Everything waiting on an admin, grouped by the state it waits in. */
function Awaiting({ items }: { items: QueueItemOut[] }) {
  if (items.length === 0) {
    return (
      <EmptyState icon="check" title={t('admin.allClearTitle')}>
        {t('admin.allClearText')}
      </EmptyState>
    );
  }
  const groups = donationStatusValues
    .map((status) => ({ status, items: items.filter((i) => i.donation.status === status) }))
    .filter((g) => g.items.length > 0);
  return (
    <div className="space-y-8">
      {groups.map((group) => (
        <section key={group.status}>
          <h3 className="mb-3 flex items-center gap-2 font-sans text-base font-semibold">
            <Tag tone={statusTone(group.status)} dot size="md">
              {vocabLabel('DonationStatus', group.status)}
            </Tag>
            <span className="text-sm font-normal text-ink-muted">{t('admin.waiting', { count: group.items.length })}</span>
          </h3>
          <div className="space-y-3">
            {group.items.map((item) => (
              <AwaitingCard key={item.donation.id} item={item} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function OrganisationRow({ org }: { org: OrganizationOut }) {
  return (
    <LinkCard to={paths.adminOrganisation(org.id)} className="p-4">
      <div className="flex flex-wrap items-center gap-4">
        <span className="grid size-11 shrink-0 place-items-center rounded-control bg-brand-50 text-brand-700">
          <Icon name="building" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate font-semibold">{org.name}</p>
          <p className="text-sm text-ink-muted">
            {org.registration_id} · {t('admin.registered', { date: formatDate(org.created_at) })}
          </p>
        </div>
        <div className="flex items-center gap-2 text-ink-muted">
          {org.categories_accepted.map((c) => (
            <Icon key={c} name={categoryIcon(c)} className="size-4.5" />
          ))}
        </div>
        <VerificationTag status={org.verification_status} />
      </div>
    </LinkCard>
  );
}

function Organisations({ counts }: { counts: OrganizationCountsOut | undefined }) {
  const [status, setStatus] = useState<string | null>(null);
  const orgs = useAdminOrganisations(status);
  const total = counts ? Object.values(counts.by_status).reduce((sum, n) => sum + (n ?? 0), 0) : undefined;
  return (
    <div className="space-y-5">
      {counts && counts.awaiting_verification > 0 && (
        <Alert kind="warning" title={t('admin.awaitingVerification', { count: counts.awaiting_verification })}>
          {t('admin.awaitingVerificationText')}
        </Alert>
      )}
      <Chips
        label={t('admin.filterVerification')}
        value={status}
        onChange={setStatus}
        items={[
          { value: null, label: t('admin.all'), count: total },
          ...verificationStatusValues.map((v) => ({ value: v, label: vocabLabel('VerificationStatus', v), count: counts?.by_status[v] })),
        ]}
      />
      <ApiErrorAlert error={orgs.error} />
      {orgs.isPending ? (
        <Loading />
      ) : orgs.data && orgs.data.length > 0 ? (
        <div className="space-y-3">
          {orgs.data.map((org) => (
            <OrganisationRow key={org.id} org={org} />
          ))}
          {orgs.data.length === ADMIN_PAGE_SIZE && <p className="text-sm text-ink-muted">{t('admin.firstPage', { count: ADMIN_PAGE_SIZE })}</p>}
        </div>
      ) : (
        <EmptyState icon="building" title={t('admin.noOrganisations')} />
      )}
    </div>
  );
}

function Donations() {
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(0);
  const donations = useAdminDonations(status || null, page);
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <Select
          label={t('admin.filterStatus')}
          className="w-full sm:w-64"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(0);
          }}
          options={[{ value: '', label: t('admin.all') }, ...donationStatusValues.map((s) => ({ value: s, label: vocabLabel('DonationStatus', s) }))]}
        />
        <p className="text-sm text-ink-muted">{t('admin.redacted')}</p>
      </div>
      <ApiErrorAlert error={donations.error} />
      {donations.isPending ? (
        <Loading />
      ) : donations.data && donations.data.length > 0 ? (
        <div className="space-y-3">
          {donations.data.map((d) => (
            <AdminDonationRow key={d.id} donation={d} />
          ))}
        </div>
      ) : (
        <EmptyState icon="box" title={t('admin.noDonations')} />
      )}
      {(page > 0 || donations.data?.length === ADMIN_PAGE_SIZE) && (
        <div className="flex items-center justify-between">
          <Button variant="secondary" size="sm" icon="arrowLeft" disabled={page === 0} onClick={() => setPage(page - 1)}>
            {t('admin.previous')}
          </Button>
          <span className="text-sm text-ink-muted">{t('admin.page', { page: page + 1 })}</span>
          <Button
            variant="secondary"
            size="sm"
            iconAfter="arrowRight"
            disabled={donations.data?.length !== ADMIN_PAGE_SIZE}
            onClick={() => setPage(page + 1)}
          >
            {t('admin.next')}
          </Button>
        </div>
      )}
    </div>
  );
}

function Recyclers() {
  const recyclers = useRecyclers();
  if (recyclers.isPending) return <Loading />;
  return (
    <div className="space-y-4">
      <ApiErrorAlert error={recyclers.error} />
      <SimulatedNote>{t('admin.recyclersNote')}</SimulatedNote>
      {recyclers.data && recyclers.data.length > 0 ? (
        <div className="grid gap-3 md:grid-cols-2">
          {recyclers.data.map((r) => (
            <Card key={r.id} className="p-4 sm:p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-semibold">{r.name}</p>
                  <p className="text-sm text-ink-muted">{r.address_text}</p>
                </div>
                <Tag tone={r.is_active ? 'active' : 'muted'} dot>
                  {r.is_active ? t('admin.active') : t('admin.inactive')}
                </Tag>
              </div>
              <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-sm">
                <span className="flex items-center gap-2 text-ink-muted">
                  {r.categories_accepted.map((c) => (
                    <span key={c} className="inline-flex items-center gap-1">
                      <Icon name={categoryIcon(c)} className="size-4" />
                      {vocabLabel('Category', c)}
                    </span>
                  ))}
                </span>
                <span className="font-semibold">{t('recycling.perKg', { amount: formatMoney(r.rate_per_kg, r.currency) })}</span>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState icon="recycle" title={t('admin.noRecyclers')}>
          {t('admin.noRecyclersText')}
        </EmptyState>
      )}
    </div>
  );
}

export function AdminPanel() {
  const [params, setParams] = useSearchParams();
  const tab: Tab = (TABS as readonly string[]).includes(params.get('tab') ?? '') ? (params.get('tab') as Tab) : 'awaiting';
  const awaiting = useAwaitingAdmin();
  const counts = useOrganisationCounts();

  return (
    <Page>
      <HeroBanner eyebrow={t('admin.eyebrow')} title={t('admin.title')} intro={t('admin.intro')} actions={<SweepButton />} />

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="min-w-0 lg:col-span-2">
          <Tabs
            label={t('admin.sections')}
            value={tab}
            onChange={(value) => setParams(value === 'awaiting' ? {} : { tab: value }, { replace: true })}
            items={[
              { value: 'awaiting', label: t('admin.tabAwaiting'), icon: 'flag', count: awaiting.data?.length },
              {
                value: 'organisations',
                label: t('admin.tabOrganisations'),
                icon: 'building',
                // Organisations waiting for verification, hidden when there are none.
                count: counts.data?.awaiting_verification || undefined,
                countLabel: t('admin.awaitingVerification', { count: counts.data?.awaiting_verification ?? 0 }),
                urgent: true,
              },
              { value: 'donations', label: t('admin.tabDonations'), icon: 'box' },
              { value: 'recyclers', label: t('admin.tabRecyclers'), icon: 'recycle' },
            ]}
          />
          {tab === 'awaiting' && (
            <>
              <ApiErrorAlert error={awaiting.error} />
              {awaiting.isPending ? <Loading /> : <Awaiting items={awaiting.data ?? []} />}
            </>
          )}
          {tab === 'organisations' && <Organisations counts={counts.data} />}
          {tab === 'donations' && <Donations />}
          {tab === 'recyclers' && <Recyclers />}
        </div>
        <aside>
          <RecentActivity />
        </aside>
      </div>
    </Page>
  );
}
