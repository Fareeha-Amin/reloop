import { Link } from 'react-router';

import { paths } from '../../app/paths';
import { t } from '../../i18n';
import { Icon, type IconName } from '../../ui/icons';
import { AuthLayout } from './AuthLayout';

function RoleCard({ to, icon, title, text }: { to: string; icon: IconName; title: string; text: string }) {
  return (
    <Link
      to={to}
      className="group flex items-start gap-4 rounded-card border border-line bg-surface p-6 shadow-card transition hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-lift"
    >
      <span className="grid size-14 shrink-0 place-items-center rounded-card bg-brand-50 text-brand-700 transition group-hover:bg-brand-900 group-hover:text-leaf">
        <Icon name={icon} className="size-7" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-lg font-semibold">{title}</span>
        <span className="mt-1 block text-sm text-ink-muted">{text}</span>
      </span>
      <Icon name="arrowRight" className="mt-1 size-5 text-ink-muted transition group-hover:translate-x-1 group-hover:text-brand-700" />
    </Link>
  );
}

export function RegisterChoice() {
  return (
    <AuthLayout
      title={t('auth.chooseTitle')}
      subtitle={
        <>
          {t('auth.haveAccount')}{' '}
          <Link to={paths.login} className="font-semibold text-brand-700 hover:underline">
            {t('auth.loginLink')}
          </Link>
        </>
      }
    >
      <div className="space-y-4">
        <RoleCard to={paths.registerDonor} icon="heart" title={t('auth.donorCardTitle')} text={t('auth.donorCardText')} />
        <RoleCard to={paths.registerOrganisation} icon="building" title={t('auth.orgCardTitle')} text={t('auth.orgCardText')} />
        <p className="pt-2 text-sm text-ink-muted">{t('auth.adminNote')}</p>
      </div>
    </AuthLayout>
  );
}
