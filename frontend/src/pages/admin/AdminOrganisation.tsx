import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useParams } from 'react-router';

import { unwrap } from '../../api/errors';
import { verificationStatusValues, type AdminOrganizationDetail, type VerificationStatus } from '../../api/schema';
import { client } from '../../app/api';
import { paths } from '../../app/paths';
import { useAdminOrganisation } from '../../app/queries';
import { ApiErrorAlert } from '../../components/ApiErrorAlert';
import { PointMap } from '../../components/maps';
import { UrgencyTag, VerificationTag } from '../../components/StatusTag';
import { formatDate, formatDateTime } from '../../i18n/format';
import { t } from '../../i18n';
import { Button } from '../../ui/Button';
import { Card, CardTitle, Facts } from '../../ui/Card';
import { Alert, LoadingBlock } from '../../ui/feedback';
import { Select, TextArea } from '../../ui/form';
import { Icon } from '../../ui/icons';
import { Page, PageHeader } from '../../ui/layout';
import { categoryIcon, vocabLabel } from '../../vocab/display';

function VerificationForm({ org }: { org: AdminOrganizationDetail }) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<string>(org.verification_status);
  const [note, setNote] = useState(org.verification_note ?? '');
  const save = useMutation({
    mutationFn: () =>
      unwrap(
        client.PATCH('/admin/organisations/{org_id}/verification', {
          params: { path: { org_id: org.id } },
          body: { status: status as VerificationStatus, note: note.trim() || null },
        }),
      ),
    onSuccess: (updated) => {
      queryClient.setQueryData(['admin', 'organisation', org.id], updated);
      queryClient.invalidateQueries({ queryKey: ['admin', 'organisations'] });
    },
  });

  return (
    <Card>
      <CardTitle aside={<VerificationTag status={org.verification_status} />}>{t('admin.verification')}</CardTitle>
      <div className="space-y-4">
        <Select
          label={t('admin.verificationStatus')}
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          options={verificationStatusValues.map((v) => ({ value: v, label: vocabLabel('VerificationStatus', v) }))}
        />
        <TextArea
          label={t('admin.verificationNote')}
          hint={t('admin.verificationNoteHint')}
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
        <ApiErrorAlert error={save.error} />
        {save.isSuccess && <Alert kind="success" title={t('admin.verificationSaved')} />}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-ink-muted">
            {org.verification_updated_at
              ? t('admin.verificationUpdated', { at: formatDateTime(org.verification_updated_at) })
              : t('admin.verificationNever')}
          </p>
          <Button busy={save.isPending} onClick={() => save.mutate()}>
            {t('admin.verificationSave')}
          </Button>
        </div>
      </div>
    </Card>
  );
}

export function AdminOrganisation() {
  const { id = '' } = useParams();
  const org = useAdminOrganisation(id);

  if (org.isPending) return <LoadingBlock label={t('common.loading')} />;
  if (org.error) {
    return (
      <Page width="narrow">
        <ApiErrorAlert error={org.error} />
      </Page>
    );
  }

  const o = org.data;
  return (
    <Page>
      <PageHeader
        back={{ to: `${paths.admin}?tab=organisations`, label: t('admin.backToOrganisations') }}
        eyebrow={t('admin.organisationEyebrow')}
        title={o.name}
        subtitle={t('admin.registered', { date: formatDate(o.created_at) })}
      />
      <div className="grid gap-6 lg:grid-cols-5">
        <div className="space-y-6 lg:col-span-3">
          <Card>
            <CardTitle>{t('acceptor.profile')}</CardTitle>
            <Facts
              items={[
                { label: t('fields.registrationId'), value: o.registration_id },
                { label: t('admin.accountEmail'), value: o.account_email },
                { label: t('holder.contact'), value: o.contact_person },
                { label: t('holder.phone'), value: o.phone },
                { label: t('holder.address'), value: o.address_text },
                { label: t('acceptor.capacity'), value: t('common.items', { count: o.storage_capacity }) },
                { label: t('admin.categoriesAccepted'), value: o.categories_accepted.map((c) => vocabLabel('Category', c)).join(', ') },
                { label: t('acceptor.handover'), value: o.pickup_capable ? t('candidates.collects') : t('candidates.dropoffOnly') },
              ]}
            />
            <div className="mt-5">
              <PointMap point={{ lat: o.latitude, lng: o.longitude }} />
            </div>
          </Card>
          <Card>
            <CardTitle>{t('admin.needs')}</CardTitle>
            {o.needs.length === 0 ? (
              <p className="text-sm text-ink-muted">{t('admin.noNeeds')}</p>
            ) : (
              <ul className="divide-y divide-line">
                {o.needs.map((need) => (
                  <li key={need.id} className={`flex flex-wrap items-center gap-3 py-3 ${need.is_active ? '' : 'opacity-60'}`}>
                    <Icon name={categoryIcon(need.category)} className="size-5 text-brand-600" />
                    <span className="min-w-0 flex-1 font-medium">
                      {vocabLabel('Category', need.category)} · {t('common.items', { count: need.quantity_needed })}
                    </span>
                    {need.is_active ? <UrgencyTag urgency={need.urgency} /> : <span className="text-sm text-ink-muted">{t('admin.needClosed')}</span>}
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
        <div className="lg:col-span-2">
          <VerificationForm org={o} />
        </div>
      </div>
    </Page>
  );
}
