import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router';

import { unwrap } from '../api/errors';
import type { DonationSummaryOut, QueueItemOut, RankingRunOut, SweepReportOut } from '../api/schema';
import { client } from '../app/api';
import { paths } from '../app/paths';
import { formatDate, formatDateTime, formatNumber, formatPercent, formatRelative } from '../i18n/format';
import { t } from '../i18n';
import { Button } from '../ui/Button';
import { Card, LinkCard } from '../ui/Card';
import { Dialog } from '../ui/Dialog';
import { Icon } from '../ui/icons';
import { Marker, Tag } from '../ui/Tag';
import { conditionLabel, vocabLabel } from '../vocab/display';
import { ActionBar } from './ActionBar';
import { ApiErrorAlert } from './ApiErrorAlert';
import { ScoreBreakdown } from './CandidateCard';
import { SHOW_MODEL_NOTE } from '../config';
import { ModelNote } from './ModelNote';
import { CategoryBadge, donationTitle } from './donation';
import { StatusTag } from './StatusTag';

/** A donation without its address (admin lists), linking to the recorded detail view. */
export function AdminDonationRow({ donation }: { donation: DonationSummaryOut }) {
  return (
    <LinkCard to={paths.adminDonation(donation.id)} className="p-4">
      <div className="flex items-center gap-4">
        <CategoryBadge category={donation.category} />
        <div className="min-w-0 flex-1">
          <p className="truncate font-semibold">{donationTitle(donation)}</p>
          <p className="text-sm text-ink-muted">
            {conditionLabel(donation.condition)} · {t('donation.listedOn', { date: formatDate(donation.created_at) })}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <StatusTag status={donation.status} />
          {donation.is_priority && (
            <Tag tone="attention" icon="flag">
              {t('donation.priority')}
            </Tag>
          )}
        </div>
      </div>
    </LinkCard>
  );
}

/** A donation waiting on an admin, with how it got here and the admin's actions. */
export function AwaitingCard({ item }: { item: QueueItemOut }) {
  const d = item.donation;
  return (
    <Card className="p-4 sm:p-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-start gap-4">
          <CategoryBadge category={d.category} />
          <div className="min-w-0">
            <Link to={paths.adminDonation(d.id)} className="font-semibold hover:text-brand-700 hover:underline">
              {donationTitle(d)}
            </Link>
            <p className="mt-0.5 text-sm text-ink-muted">
              {t('admin.arrived', {
                via: vocabLabel('DonationAction', item.via),
                from: vocabLabel('DonationStatus', item.from_state),
                when: formatRelative(item.entered_at),
              })}
            </p>
          </div>
        </div>
        <ActionBar surface="admin" id={d.id} allowed={item.allowed_actions} size="sm" />
      </div>
    </Card>
  );
}

/** Runs the deadline sweep now and shows what it did. */
export function SweepButton() {
  const queryClient = useQueryClient();
  const sweep = useMutation({
    mutationFn: () => unwrap(client.POST('/admin/sweep')),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'awaiting'] }),
  });
  return (
    <>
      <Button variant="inverse" icon="clock" busy={sweep.isPending} onClick={() => sweep.mutate()}>
        {t('admin.sweep')}
      </Button>
      {(sweep.data || sweep.error) && (
        <Dialog open onClose={() => sweep.reset()} title={t('admin.sweepTitle')} closeLabel={t('common.close')}>
          <ApiErrorAlert error={sweep.error} />
          {sweep.data && <SweepReport report={sweep.data} />}
        </Dialog>
      )}
    </>
  );
}

function SweepReport({ report }: { report: SweepReportOut }) {
  return (
    <div className="space-y-3">
      <p>
        {t('admin.sweepSummary', {
          examined: report.examined,
          applied: report.applied.length,
          at: formatDateTime(report.now),
        })}
      </p>
      {report.skipped_locked > 0 && <p className="text-ink-muted">{t('admin.sweepSkipped', { count: report.skipped_locked })}</p>}
      {report.applied.length > 0 && (
        <ul className="space-y-1.5">
          {report.applied.map((item) => (
            <li key={`${item.donation_id}-${item.action}`} className="flex flex-wrap items-center gap-2">
              <Link to={paths.adminDonation(item.donation_id)} className="font-mono text-xs text-brand-700 underline">
                {item.donation_id.slice(0, 8)}
              </Link>
              <span>{vocabLabel('DonationAction', item.action)}</span>
              <Icon name="arrowRight" className="size-3.5 text-ink-muted" />
              <StatusTag status={item.to_state} />
            </li>
          ))}
        </ul>
      )}
      {report.errors.map((error) => (
        <p key={error} className="text-danger-700">
          {error}
        </p>
      ))}
    </div>
  );
}

/** Each stored ranking run: the slate a decision was made against, with its config. */
export function RankingRuns({ runs }: { runs: RankingRunOut[] }) {
  if (runs.length === 0) return <p className="text-sm text-ink-muted">{t('admin.noRuns')}</p>;
  return (
    <ol className="space-y-4">
      {[...runs].reverse().map((run) => {
        const filtered = Object.entries(run.filtered_out).filter(([, n]) => n > 0);
        return (
          <li key={run.id} className="rounded-control border border-line bg-surface p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-semibold">
                {vocabLabel('RankingTrigger', run.trigger)} · {formatDateTime(run.created_at)}
              </p>
              <span className="font-mono text-xs text-ink-muted" title={t('admin.configVersion')}>
                {run.config_version}
              </span>
            </div>
            <p className="mt-1 text-sm text-ink-muted">
              {t('candidates.radius', { km: formatNumber(run.radius_km) })} · {t('admin.declines', { count: run.declines })}
              {filtered.length > 0 &&
                ` · ${t('candidates.filteredOut')} ${filtered.map(([reason, n]) => `${vocabLabel('FilterReason', reason)} (${n})`).join(', ')}`}
            </p>
            {SHOW_MODEL_NOTE && run.model && (
              <p className="mt-2">
                <ModelNote model={run.model} />
              </p>
            )}
            {run.slate.length === 0 ? (
              <p className="mt-3 text-sm text-ink-soft">{t('admin.emptySlate')}</p>
            ) : (
              <ul className="mt-3 divide-y divide-line">
                {run.slate.map((c) => (
                  <li key={c.organization_id} className="py-2">
                    <details className="group">
                      <summary className="flex cursor-pointer list-none items-center gap-3 text-sm">
                        <span className="grid size-7 shrink-0 place-items-center rounded-full bg-surface-muted font-semibold">{c.rank}</span>
                        <span className="min-w-0 flex-1 truncate font-medium">{c.organization_name}</span>
                        <span className="text-ink-muted">{t('common.km', { km: formatNumber(c.distance_km) })}</span>
                        <span className="w-12 text-right font-semibold text-brand-700">{formatPercent(c.score)}</span>
                        <Icon name="chevronRight" className="size-4 text-ink-muted transition group-open:rotate-90" />
                      </summary>
                      <div className="mt-3 pl-10">
                        <ScoreBreakdown candidate={c} />
                      </div>
                    </details>
                  </li>
                ))}
              </ul>
            )}
          </li>
        );
      })}
    </ol>
  );
}

/** "Simulated" next to anything the admin confirms on someone else's behalf. */
export function SimulatedNote({ children }: { children: string }) {
  return (
    <p className="flex flex-wrap items-center gap-2 text-xs text-ink-muted">
      <Marker>{t('honesty.simulated')}</Marker>
      {children}
    </p>
  );
}
