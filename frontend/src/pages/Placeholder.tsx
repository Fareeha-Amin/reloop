import { paths } from '../app/paths';
import { t } from '../i18n';
import { LinkButton } from '../ui/Button';
import { EmptyState } from '../ui/feedback';
import { Page } from '../ui/layout';

/**
 * STUB, and labelled as one: the acceptor dashboard, admin panel and discovery map arrive
 * in the second half of Phase 3. Until then their routes show this page.
 */
export function Placeholder() {
  return (
    <Page width="narrow">
      <EmptyState
        icon="sparkles"
        title={t('placeholder.title')}
        action={
          <LinkButton to={paths.notifications} variant="secondary" icon="bell">
            {t('placeholder.notifications')}
          </LinkButton>
        }
      >
        {t('placeholder.text')}
      </EmptyState>
    </Page>
  );
}

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
