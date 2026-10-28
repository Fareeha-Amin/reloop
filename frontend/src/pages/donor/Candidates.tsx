import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router';

import { paths } from '../../app/paths';
import { useCandidates, useDonation } from '../../app/queries';
import { ApiErrorAlert } from '../../components/ApiErrorAlert';
import { CandidateCard } from '../../components/CandidateCard';
import { ModelNote } from '../../components/ModelNote';
import { donationTitle } from '../../components/donation';
import { formatNumber } from '../../i18n/format';
import { t } from '../../i18n';
import { Button, LinkButton } from '../../ui/Button';
import { Alert, EmptyState, LoadingBlock } from '../../ui/feedback';
import { Page, PageHeader } from '../../ui/layout';
import { offerAllowed, offerTo } from '../../vocab/actions';
import { vocabLabel } from '../../vocab/display';

export function Candidates() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const donation = useDonation(id);
  const slate = useCandidates(id);

  const offer = useMutation({
    mutationFn: (organizationId: string | null) => offerTo(id, organizationId),
    onSuccess: async () => {
      await queryClient.invalidateQueries();
      navigate(paths.donation(id));
    },
  });

  if (donation.isPending || slate.isPending) return <LoadingBlock label={t('candidates.ranking')} />;
  if (donation.error || slate.error) {
    return (
      <Page width="narrow">
        <ApiErrorAlert error={donation.error ?? slate.error} />
      </Page>
    );
  }

  const d = donation.data!;
  const s = slate.data!;
  const canOffer = offerAllowed(d.allowed_actions);
  const filtered = Object.entries(s.filtered_out).filter(([, n]) => n > 0);

  return (
    <Page>
      <PageHeader
        eyebrow={donationTitle(d)}
        title={t('candidates.title')}
        subtitle={t('candidates.subtitle')}
        back={{ to: paths.donation(id), label: t('candidates.backToDonation') }}
      />

      {!canOffer && (
        <div className="mb-6">
          <Alert
            kind="info"
            title={t('candidates.alreadyOffered')}
            action={
              <LinkButton to={paths.donation(id)} variant="secondary" size="sm">
                {t('candidates.viewDonation')}
              </LinkButton>
            }
          />
        </div>
      )}

      <div className="mb-6 flex flex-wrap items-center gap-x-6 gap-y-2 rounded-card border border-line bg-surface-muted/60 px-5 py-4 text-sm text-ink-soft">
        <span>{t('candidates.radius', { km: formatNumber(s.radius_km) })}</span>
        {s.declines > 0 && <span>{t('candidates.declines', { count: s.declines })}</span>}
        {filtered.length > 0 && (
          <span>
            {t('candidates.filteredOut')}{' '}
            {filtered.map(([reason, n]) => `${vocabLabel('FilterReason', reason)} (${n})`).join(', ')}
          </span>
        )}
        <span className="ml-auto">
          <ModelNote model={s.model} />
        </span>
      </div>

      <ApiErrorAlert error={offer.error} />

      {s.candidates.length === 0 ? (
        <EmptyState
          icon="map"
          title={t('candidates.emptyTitle')}
          action={
            canOffer && (
              <Button busy={offer.isPending} onClick={() => offer.mutate(null)} iconAfter="arrowRight">
                {t('candidates.continueEmpty')}
              </Button>
            )
          }
        >
          {t('candidates.emptyText')}
        </EmptyState>
      ) : (
        <div className="space-y-4">
          {s.candidates.map((c, index) => (
            <CandidateCard
              key={c.organization_id}
              candidate={c}
              top={index === 0}
              canOffer={canOffer}
              offering={offer.isPending && offer.variables === c.organization_id}
              onOffer={() => offer.mutate(c.organization_id)}
            />
          ))}
          <p className="pt-2 text-sm text-ink-muted">{t('candidates.howScored')}</p>
        </div>
      )}
    </Page>
  );
}
