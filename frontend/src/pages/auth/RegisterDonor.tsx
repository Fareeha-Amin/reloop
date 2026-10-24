import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router';

import { unwrap } from '../../api/errors';
import { client } from '../../app/api';
import { paths } from '../../app/paths';
import { useSession } from '../../app/session';
import { ApiErrorAlert, fieldError } from '../../components/ApiErrorAlert';
import { t } from '../../i18n';
import { Button } from '../../ui/Button';
import { TextInput } from '../../ui/form';
import { AuthLayout } from './AuthLayout';

const FIELDS = { full_name: '', email: '', phone: '', password: '' };

export function RegisterDonor() {
  const { login } = useSession();
  const navigate = useNavigate();
  const [form, setForm] = useState(FIELDS);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const set = (field: keyof typeof FIELDS) => (e: { target: { value: string } }) => setForm({ ...form, [field]: e.target.value });

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await unwrap(client.POST('/auth/register/donor', { body: form }));
      await login(form.email, form.password);
      navigate(paths.donor, { replace: true });
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout title={t('auth.donorTitle')} subtitle={t('auth.donorSubtitle')}>
      <form onSubmit={submit} className="space-y-5">
        <ApiErrorAlert error={error} inlineFields={FIELDS} />
        <TextInput label={t('fields.fullName')} autoComplete="name" value={form.full_name} onChange={set('full_name')} error={fieldError(error, 'full_name')} required />
        <TextInput label={t('fields.email')} type="email" autoComplete="email" value={form.email} onChange={set('email')} error={fieldError(error, 'email')} required />
        <TextInput label={t('fields.phone')} type="tel" autoComplete="tel" value={form.phone} onChange={set('phone')} error={fieldError(error, 'phone')} hint={t('fields.phoneHint')} required />
        <TextInput
          label={t('fields.password')}
          type="password"
          autoComplete="new-password"
          value={form.password}
          onChange={set('password')}
          error={fieldError(error, 'password')}
          hint={t('fields.passwordHint')}
          required
        />
        <p className="text-xs text-ink-muted">{t('auth.donorPrivacy')}</p>
        <Button type="submit" size="lg" busy={busy} className="w-full">
          {t('auth.createAccount')}
        </Button>
      </form>
    </AuthLayout>
  );
}
