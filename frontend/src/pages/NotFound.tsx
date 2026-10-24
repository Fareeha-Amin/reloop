import { paths } from '../app/paths';
import { t } from '../i18n';
import { LinkButton } from '../ui/Button';
import { EmptyState } from '../ui/feedback';
import { Page } from '../ui/layout';

export function NotFound() {
  return (
    <Page width="narrow">
      <EmptyState
        icon="map"
        title={t('notFound.title')}
        action={
          <LinkButton to={paths.home} variant="secondary">
            {t('notFound.home')}
          </LinkButton>
        }
      >
        {t('notFound.text')}
      </EmptyState>
    </Page>
  );
}
