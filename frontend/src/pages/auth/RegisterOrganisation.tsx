import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router';

import { unwrap } from '../../api/errors';
import { categoryValues, type Category } from '../../api/schema';
import { client } from '../../app/api';
import { paths } from '../../app/paths';
import { useSession } from '../../app/session';
import { ApiErrorAlert, fieldError } from '../../components/ApiErrorAlert';
import { LocationPicker, type Point } from '../../components/maps';
import { t } from '../../i18n';
import { Button } from '../../ui/Button';
import { Card } from '../../ui/Card';
import { ChoiceCards, TextInput, Toggle } from '../../ui/form';
import { categoryIcon, vocabLabel } from '../../vocab/display';
import { AuthLayout } from './AuthLayout';

const ACCOUNT = { full_name: '', email: '', phone: '', password: '' };
const ORG = { name: '', registration_id: '', contact_person: '', phone: '', address_text: '', storage_capacity: '' };

/** Field paths the form shows inline; anything else is listed in the error banner. */
const SHOWN = Object.fromEntries(
  [...Object.keys(ACCOUNT), ...Object.keys(ORG).map((k) => `organization.${k}`), 'organization.latitude', 'organization.categories_accepted'].map((k) => [k, k]),
);

export function RegisterOrganisation() {
  const { login } = useSession();
  const navigate = useNavigate();
  const [account, setAccount] = useState(ACCOUNT);
  const [org, setOrg] = useState(ORG);
  const [pin, setPin] = useState<Point | null>(null);
  const [pickupCapable, setPickupCapable] = useState(true);
  const [categories, setCategories] = useState<Category[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const setA = (field: keyof typeof ACCOUNT) => (e: { target: { value: string } }) => setAccount({ ...account, [field]: e.target.value });
  const setO = (field: keyof typeof ORG) => (e: { target: { value: string } }) => setOrg({ ...org, [field]: e.target.value });
  const toggleCategory = (value: string) =>
    setCategories((current) =>
      current.includes(value as Category) ? current.filter((c) => c !== value) : [...current, value as Category],
    );

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await unwrap(
        client.POST('/auth/register/acceptor', {
          body: {
            ...account,
            organization: {
              ...org,
              storage_capacity: Number(org.storage_capacity),
              // No pin: send nothing, and the API says the location is required.
              latitude: pin?.lat as number,
              longitude: pin?.lng as number,
              pickup_capable: pickupCapable,
              categories_accepted: categories,
            },
          },
        }),
      );
      await login(account.email, account.password);
      navigate(paths.acceptor, { replace: true });
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  const err = (path: string) => fieldError(error, path);

  return (
    <AuthLayout title={t('auth.orgTitle')} subtitle={t('auth.orgSubtitle')} wide>
      <form onSubmit={submit} className="space-y-6">
        <ApiErrorAlert error={error} inlineFields={SHOWN} />

        <Card>
          <h2 className="mb-4 text-lg font-semibold">{t('auth.orgSectionAccount')}</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <TextInput label={t('fields.fullName')} autoComplete="name" value={account.full_name} onChange={setA('full_name')} error={err('full_name')} required />
            <TextInput label={t('fields.phone')} type="tel" value={account.phone} onChange={setA('phone')} error={err('phone')} required />
            <TextInput label={t('fields.email')} type="email" autoComplete="email" value={account.email} onChange={setA('email')} error={err('email')} required />
            <TextInput
              label={t('fields.password')}
              type="password"
              autoComplete="new-password"
              value={account.password}
              onChange={setA('password')}
              error={err('password')}
              hint={t('fields.passwordHint')}
              required
            />
          </div>
        </Card>

        <Card>
          <h2 className="mb-1 text-lg font-semibold">{t('auth.orgSectionOrg')}</h2>
          <p className="mb-4 text-sm text-ink-muted">{t('auth.orgFixedNote')}</p>
          <div className="grid gap-4 sm:grid-cols-2">
            <TextInput label={t('fields.orgName')} value={org.name} onChange={setO('name')} error={err('organization.name')} required />
            <TextInput label={t('fields.registrationId')} value={org.registration_id} onChange={setO('registration_id')} error={err('organization.registration_id')} required />
            <TextInput label={t('fields.contactPerson')} value={org.contact_person} onChange={setO('contact_person')} error={err('organization.contact_person')} required />
            <TextInput label={t('fields.orgPhone')} type="tel" value={org.phone} onChange={setO('phone')} error={err('organization.phone')} required />
          </div>
          <div className="mt-6">
            <ChoiceCards
              legend={t('fields.categoriesAccepted')}
              name="categories"
              multiple
              value={categories}
              onChange={toggleCategory}
              error={err('organization.categories_accepted')}
              choices={categoryValues.map((value) => ({ value, label: vocabLabel('Category', value), icon: categoryIcon(value) }))}
            />
          </div>
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <TextInput
              label={t('fields.storageCapacity')}
              type="number"
              min={0}
              inputMode="numeric"
              value={org.storage_capacity}
              onChange={setO('storage_capacity')}
              error={err('organization.storage_capacity')}
              hint={t('fields.storageCapacityHint')}
              required
            />
            <Toggle label={t('fields.pickupCapable')} description={t('fields.pickupCapableHint')} checked={pickupCapable} onChange={setPickupCapable} />
          </div>
        </Card>

        <Card>
          <h2 className="mb-1 text-lg font-semibold">{t('auth.orgSectionLocation')}</h2>
          <p className="mb-4 text-sm text-ink-muted">{t('auth.orgLocationNote')}</p>
          <LocationPicker value={pin} onChange={setPin} error={err('organization.latitude')} />
          <TextInput
            className="mt-4"
            label={t('fields.address')}
            value={org.address_text}
            onChange={setO('address_text')}
            error={err('organization.address_text')}
            hint={t('fields.addressHint')}
            required
          />
        </Card>

        <p className="text-sm text-ink-muted">{t('auth.orgPendingNote')}</p>
        <Button type="submit" size="lg" busy={busy} className="w-full sm:w-auto">
          {t('auth.registerOrg')}
        </Button>
      </form>
    </AuthLayout>
  );
}
