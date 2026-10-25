import { useState, type FormEvent, type ReactNode } from 'react';
import { useNavigate } from 'react-router';

import { ApiError, unwrap } from '../../api/errors';
import { categoryValues, type Category } from '../../api/schema';
import { client } from '../../app/api';
import { paths } from '../../app/paths';
import { useSession } from '../../app/session';
import { ApiErrorAlert, fieldError } from '../../components/ApiErrorAlert';
import { LocationPicker, type Point } from '../../components/maps';
import { t } from '../../i18n';
import { Button } from '../../ui/Button';
import { Card, CardTitle, Facts } from '../../ui/Card';
import { Alert } from '../../ui/feedback';
import { ChoiceCards, TextInput, Toggle } from '../../ui/form';
import { Icon, type IconName } from '../../ui/icons';
import { Stepper } from '../../ui/layout';
import { categoryIcon, vocabLabel } from '../../vocab/display';
import { AuthLayout } from './AuthLayout';

const ACCOUNT = { full_name: '', email: '', phone: '', password: '' };
const ORG = { name: '', registration_id: '', contact_person: '', phone: '', address_text: '', storage_capacity: '' };

/** The second step holds the location; every other field is on the first. */
const LOCATION_FIELDS = ['organization.latitude', 'organization.longitude', 'organization.address_text'];
const stepOf = (field: string) => (LOCATION_FIELDS.includes(field) ? 1 : 0);

/** Field paths the form shows inline; anything else is listed in the error banner. */
const SHOWN = Object.fromEntries(
  [...Object.keys(ACCOUNT), ...Object.keys(ORG).map((k) => `organization.${k}`), ...LOCATION_FIELDS, 'organization.categories_accepted'].map((k) => [
    k,
    k,
  ]),
);

function Section({ icon, title, note, children }: { icon: IconName; title: string; note?: string; children: ReactNode }) {
  return (
    <Card>
      <CardTitle>
        <span className="flex items-center gap-2.5">
          <span className="grid size-8 place-items-center rounded-control bg-brand-50 text-brand-700">
            <Icon name={icon} className="size-4.5" />
          </span>
          {title}
        </span>
      </CardTitle>
      {note && <p className="-mt-2 mb-4 text-sm text-ink-muted">{note}</p>}
      {children}
    </Card>
  );
}

export function RegisterOrganisation() {
  const { login } = useSession();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
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
  const err = (path: string) => fieldError(error, path);

  function goTo(next: number) {
    setStep(next);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function toLocation(event: FormEvent) {
    event.preventDefault();
    goTo(1);
  }

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
              // Submit is disabled until a pin is dropped; the API checks the range.
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
      // Send the user back to the earliest step with a field the API refused.
      if (e instanceof ApiError) {
        const steps = Object.keys(e.fieldErrors).map(stepOf);
        if (steps.length > 0) goTo(Math.min(...steps));
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout title={t('auth.orgTitle')} subtitle={t('auth.orgSubtitle')} wide>
      <Stepper steps={[t('auth.orgStepDetails'), t('auth.orgStepLocation')]} current={step} />
      <ApiErrorAlert error={error} inlineFields={SHOWN} />

      {step === 0 && (
        <form onSubmit={toLocation} className="mt-4 space-y-6">
          <Section icon="user" title={t('auth.orgSectionAccount')} note={t('auth.orgAccountNote')}>
            <div className="grid gap-4 sm:grid-cols-2">
              <TextInput label={t('fields.fullName')} autoComplete="name" value={account.full_name} onChange={setA('full_name')} error={err('full_name')} required />
              <TextInput label={t('fields.phone')} type="tel" autoComplete="tel" value={account.phone} onChange={setA('phone')} error={err('phone')} required />
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
          </Section>

          <Section icon="building" title={t('auth.orgSectionOrg')} note={t('auth.orgFixedNote')}>
            <div className="grid gap-4 sm:grid-cols-2">
              <TextInput label={t('fields.orgName')} value={org.name} onChange={setO('name')} error={err('organization.name')} required />
              <TextInput
                label={t('fields.registrationId')}
                value={org.registration_id}
                onChange={setO('registration_id')}
                error={err('organization.registration_id')}
                required
              />
              <TextInput label={t('fields.contactPerson')} value={org.contact_person} onChange={setO('contact_person')} error={err('organization.contact_person')} required />
              <TextInput label={t('fields.orgPhone')} type="tel" value={org.phone} onChange={setO('phone')} error={err('organization.phone')} required />
            </div>
          </Section>

          <Section icon="box" title={t('auth.orgSectionAccepting')} note={t('auth.orgAcceptingNote')}>
            <ChoiceCards
              legend={t('fields.categoriesAccepted')}
              name="categories"
              multiple
              value={categories}
              onChange={toggleCategory}
              error={err('organization.categories_accepted')}
              choices={categoryValues.map((value) => ({ value, label: vocabLabel('Category', value), icon: categoryIcon(value) }))}
            />
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
          </Section>

          <div className="flex flex-col-reverse items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-ink-muted">{categories.length === 0 ? t('auth.orgPickCategory') : t('auth.orgNextIsLocation')}</p>
            <Button type="submit" size="lg" iconAfter="arrowRight" disabled={categories.length === 0}>
              {t('common.continue')}
            </Button>
          </div>
        </form>
      )}

      {step === 1 && (
        <form onSubmit={submit} className="mt-4 space-y-6">
          <Section icon="pin" title={t('auth.orgSectionLocation')} note={t('auth.orgLocationNote')}>
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
          </Section>

          <Card>
            <CardTitle
              aside={
                <Button variant="ghost" size="sm" icon="pencil" onClick={() => goTo(0)}>
                  {t('auth.orgEditDetails')}
                </Button>
              }
            >
              {t('auth.orgReview')}
            </CardTitle>
            <Facts
              items={[
                { label: t('fields.orgName'), value: org.name },
                { label: t('fields.registrationId'), value: org.registration_id },
                { label: t('fields.email'), value: account.email },
                { label: t('fields.contactPerson'), value: `${org.contact_person} · ${org.phone}` },
                { label: t('fields.categoriesAccepted'), value: categories.map((c) => vocabLabel('Category', c)).join(', ') },
                { label: t('fields.storageCapacity'), value: t('common.items', { count: Number(org.storage_capacity) || 0 }) },
                { label: t('acceptor.handover'), value: pickupCapable ? t('candidates.collects') : t('candidates.dropoffOnly') },
              ]}
            />
          </Card>

          <Alert kind="info" title={t('auth.orgNextTitle')}>
            {t('auth.orgPendingNote')}
          </Alert>

          <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
            <Button variant="ghost" icon="arrowLeft" onClick={() => goTo(0)}>
              {t('common.back')}
            </Button>
            <Button type="submit" size="lg" busy={busy} disabled={!pin} iconAfter="check">
              {t('auth.registerOrg')}
            </Button>
          </div>
        </form>
      )}
    </AuthLayout>
  );
}
