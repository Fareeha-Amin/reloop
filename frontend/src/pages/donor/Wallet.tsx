import { paths } from '../../app/paths';
import { useWallet } from '../../app/queries';
import { ApiErrorAlert } from '../../components/ApiErrorAlert';
import { formatDateTime, formatMoney } from '../../i18n/format';
import { t } from '../../i18n';
import { Card } from '../../ui/Card';
import { EmptyState, LoadingBlock } from '../../ui/feedback';
import { Icon } from '../../ui/icons';
import { Page, PageHeader } from '../../ui/layout';
import { vocabLabel } from '../../vocab/display';

export function Wallet() {
  const wallet = useWallet();

  if (wallet.isPending) return <LoadingBlock label={t('common.loading')} />;
  if (wallet.error) {
    return (
      <Page width="narrow">
        <ApiErrorAlert error={wallet.error} />
      </Page>
    );
  }

  const w = wallet.data!;

  return (
    <Page width="narrow">
      <PageHeader
        eyebrow={t('wallet.eyebrow')}
        title={t('wallet.title')}
        subtitle={t('wallet.subtitle')}
        back={{ to: paths.donor, label: t('wallet.backToDashboard') }}
      />

      <Card className="mb-6">
        <p className="text-sm font-semibold text-ink-muted uppercase">{t('wallet.balance')}</p>
        <p className="mt-1 text-3xl font-semibold text-brand-700">{formatMoney(w.balance, w.currency)}</p>
      </Card>

      {w.transactions.length === 0 ? (
        <EmptyState icon="wallet" title={t('wallet.empty')}>
          {t('wallet.emptyText')}
        </EmptyState>
      ) : (
        <ul className="space-y-3">
          {w.transactions.map((txn) => {
            const positive = Number(txn.amount) >= 0;
            return (
              <li key={txn.id} className="flex items-center justify-between gap-4 rounded-control border border-line bg-surface p-4">
                <div className="flex items-center gap-3 min-w-0">
                  <span className={`grid size-9 shrink-0 place-items-center rounded-control ${positive ? 'bg-brand-50 text-brand-700' : 'bg-surface-muted text-ink-soft'}`}>
                    <Icon name={positive ? 'arrowUp' : 'arrowDown'} className="size-4.5" />
                  </span>
                  <div className="min-w-0">
                    <p className="truncate font-semibold">{vocabLabel('WalletTxnType', txn.type)}</p>
                    <p className="text-sm text-ink-muted">{formatDateTime(txn.created_at)}</p>
                  </div>
                </div>
                <p className={`shrink-0 font-semibold ${positive ? 'text-brand-700' : 'text-ink-soft'}`}>
                  {positive ? '+' : ''}
                  {formatMoney(txn.amount, w.currency)}
                </p>
              </li>
            );
          })}
        </ul>
      )}
    </Page>
  );
}
