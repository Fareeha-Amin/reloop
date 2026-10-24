import { useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router';

import { ApiError } from '../../api/errors';
import { paths } from '../../app/paths';
import { useSession } from '../../app/session';
import { ApiErrorAlert } from '../../components/ApiErrorAlert';
import { t } from '../../i18n';
import { Button } from '../../ui/Button';
import { Alert } from '../../ui/feedback';
import { TextInput } from '../../ui/form';
import { homeFor } from '../../vocab/roles';
import { AuthLayout } from './AuthLayout';

export function Login() {
  const { login } = useSession();
  const navigate = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from;
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const user = await login(email, password);
      navigate(from ?? homeFor(user.role), { replace: true });
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  const badCredentials = error instanceof ApiError && error.status === 401;

  return (
    <AuthLayout
      title={t('auth.loginTitle')}
      subtitle={
        <>
          {t('auth.noAccount')}{' '}
          <Link to={paths.register} className="font-semibold text-brand-700 hover:underline">
            {t('auth.registerLink')}
          </Link>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-5">
        {badCredentials ? <Alert kind="danger">{t('auth.badCredentials')}</Alert> : <ApiErrorAlert error={error} />}
        <TextInput label={t('fields.email')} type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <TextInput
          label={t('fields.password')}
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <Button type="submit" size="lg" busy={busy} className="w-full">
          {t('auth.loginButton')}
        </Button>
      </form>
    </AuthLayout>
  );
}
