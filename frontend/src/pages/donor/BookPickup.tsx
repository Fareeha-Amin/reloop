import { useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router';

import { paths } from '../../app/paths';
import { usePickupQuote, useDonation } from '../../app/queries';
import { fromLocalInput, toLocalInput, tomorrowAt } from '../../components/datetime';
import { donationTitle } from '../../components/donation';
import { ApiErrorAlert } from '../../components/ApiErrorAlert';
import { DEFAULT_WINDOW_HOURS } from '../../config';
import { formatMoney, formatNumber } from '../../i18n/format';
import { t } from '../../i18n';
import { Button } from '../../ui/Button';
import { Card } from '../../ui/Card';
import { EmptyState, LoadingBlock } from '../../ui/feedback';
import { ChoiceCards, TextInput } from '../../ui/form';
import { Page, PageHeader } from '../../ui/layout';
import { Marker } from '../../ui/Tag';
import { bookPickup } from '../../vocab/actions';

export function BookPickup() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const donation = useDonation(id);
  const quote = usePickupQuote(id);

  const [providerId, setProviderId] = useState<string | null>(null);
  const [when, setWhen] = useState(() => toLocalInput(tomorrowAt(DEFAULT_WINDOW_HOURS.start)));
  const [walletAmount, setWalletAmount] = useState('0');

  const q = quote.data;
  const chosen = useMemo(() => q?.providers.find((p) => p.provider_id === providerId) ?? q?.providers[0], [q, providerId]);
  const maxWallet = chosen ? Math.min(Number(q!.wallet_balance), Number(chosen.cost)) : 0;

  const mutation = useMutation({
    mutationFn: () => bookPickup(id, chosen!.provider_id, fromLocalInput(when), walletAmount || '0'),
    onSuccess: async () => {
      await queryClient.invalidateQueries();
      navigate(paths.donation(id));
    },
  });

  if (donation.isPending || quote.isPending) return <LoadingBlock label={t('pickup.loading')} />;
  if (donation.error) {
    return (
      <Page width="narrow">
        <ApiErrorAlert error={donation.error} />
      </Page>
    );
  }

  const d = donation.data!;

  return (
    <Page width="narrow">
      <PageHeader
        eyebrow={donationTitle(d)}
        title={t('pickup.title')}
        subtitle={t('pickup.subtitle')}
        back={{ to: paths.donation(id), label: t('pickup.backToDonation') }}
      />

      <ApiErrorAlert error={quote.error ?? mutation.error} />

      {quote.error ? null : !q || q.providers.length === 0 ? (
        <EmptyState icon="truck" title={t('pickup.noProviders')} />
      ) : (
        <Card className="space-y-6">
          <p className="text-sm text-ink-soft">{t('pickup.distance', { km: formatNumber(q.distance_km) })}</p>

          <ChoiceCards
            legend={t('pickup.chooseCourier')}
            name="provider"
            value={chosen?.provider_id ?? ''}
            onChange={setProviderId}
            choices={q.providers.map((p) => ({
              value: p.provider_id,
              label: p.provider_name,
              description: formatMoney(p.cost, q.currency),
            }))}
          />

          <TextInput
            label={t('pickup.when')}
            hint={t('pickup.whenHint')}
            type="datetime-local"
            value={when}
            onChange={(e) => setWhen(e.target.value)}
            required
          />

          <TextInput
            label={t('pickup.walletAmount')}
            hint={t('pickup.walletHint', { amount: formatMoney(String(maxWallet), q.currency) })}
            type="number"
            min={0}
            max={maxWallet}
            step="0.01"
            value={walletAmount}
            onChange={(e) => setWalletAmount(e.target.value)}
            disabled={maxWallet <= 0}
          />

          {chosen && (
            <div className="rounded-control bg-surface-muted px-4 py-3 text-sm text-ink-soft">
              <p>{t('pickup.summaryCost', { amount: formatMoney(chosen.cost, q.currency) })}</p>
              <p>
                {t('pickup.summaryWallet', {
                  amount: formatMoney(String(Math.min(Number(walletAmount) || 0, maxWallet)), q.currency),
                })}
              </p>
              <p>
                {t('pickup.summaryGateway', {
                  amount: formatMoney(
                    String(Math.max(Number(chosen.cost) - Math.min(Number(walletAmount) || 0, maxWallet), 0)),
                    q.currency,
                  ),
                })}
              </p>
            </div>
          )}

          <div className="flex items-center justify-between gap-3">
            <Marker>{t('pickup.simulatedNote')}</Marker>
            <Button busy={mutation.isPending} disabled={!chosen} onClick={() => mutation.mutate()}>
              {t('pickup.submit')}
            </Button>
          </div>
        </Card>
      )}
    </Page>
  );
}
