import { useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router';

import { paths } from '../../app/paths';
import { useRecyclerPickupQuote, useDonation } from '../../app/queries';
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
import { bookRecyclerPickup } from '../../vocab/actions';

/** As BookPickup, but to the recycler a WASTE_REDIRECTED donation was assigned to. */
export function BookRecyclerPickup() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const donation = useDonation(id);
  const quote = useRecyclerPickupQuote(id);

  const [providerId, setProviderId] = useState<string | null>(null);
  const [when, setWhen] = useState(() => toLocalInput(tomorrowAt(DEFAULT_WINDOW_HOURS.start)));
  const [walletAmount, setWalletAmount] = useState('0');

  const q = quote.data;
  const chosen = useMemo(() => q?.providers.find((p) => p.provider_id === providerId) ?? q?.providers[0], [q, providerId]);
  const maxWallet = chosen ? Math.min(Number(q!.wallet_balance), Number(chosen.cost)) : 0;

  const mutation = useMutation({
    mutationFn: () => bookRecyclerPickup(id, chosen!.provider_id, fromLocalInput(when), walletAmount || '0'),
    onSuccess: async () => {
      await queryClient.invalidateQueries();
      navigate(paths.donation(id));
    },
  });

  if (donation.isPending || quote.isPending) return <LoadingBlock label={t('recyclerPickup.loading')} />;
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
        title={t('recyclerPickup.title')}
        subtitle={t('recyclerPickup.subtitle')}
        back={{ to: paths.donation(id), label: t('recyclerPickup.backToDonation') }}
      />

      <ApiErrorAlert error={quote.error ?? mutation.error} />

      {quote.error ? null : !q || q.providers.length === 0 ? (
        <EmptyState icon="truck" title={t('recyclerPickup.noProviders')} />
      ) : (
        <Card className="space-y-6">
          <p className="text-sm text-ink-soft">{t('recyclerPickup.distance', { km: formatNumber(q.distance_km) })}</p>

          <ChoiceCards
            legend={t('recyclerPickup.chooseCourier')}
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
            label={t('recyclerPickup.when')}
            hint={t('recyclerPickup.whenHint')}
            type="datetime-local"
            value={when}
            onChange={(e) => setWhen(e.target.value)}
            required
          />

          <TextInput
            label={t('recyclerPickup.walletAmount')}
            hint={t('recyclerPickup.walletHint', { amount: formatMoney(String(maxWallet), q.currency) })}
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
              <p>{t('recyclerPickup.summaryCost', { amount: formatMoney(chosen.cost, q.currency) })}</p>
              <p>
                {t('recyclerPickup.summaryWallet', {
                  amount: formatMoney(String(Math.min(Number(walletAmount) || 0, maxWallet)), q.currency),
                })}
              </p>
              <p>
                {t('recyclerPickup.summaryGateway', {
                  amount: formatMoney(
                    String(Math.max(Number(chosen.cost) - Math.min(Number(walletAmount) || 0, maxWallet), 0)),
                    q.currency,
                  ),
                })}
              </p>
            </div>
          )}

          <div className="flex items-center justify-between gap-3">
            <Marker>{t('recyclerPickup.simulatedNote')}</Marker>
            <Button busy={mutation.isPending} disabled={!chosen} onClick={() => mutation.mutate()}>
              {t('recyclerPickup.submit')}
            </Button>
          </div>
        </Card>
      )}
    </Page>
  );
}
