import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';

import { unwrap } from '../../api/errors';
import { categoryValues, type OrganizationOut } from '../../api/schema';
import { client } from '../../app/api';
import { paths } from '../../app/paths';
import { formFromOrganisation, hasChanges, profileChanges, type ProfileForm } from '../../app/profileForm';
import { useMyOrganisation } from '../../app/queries';
import { ApiErrorAlert, fieldError } from '../../components/ApiErrorAlert';
import { LocationPicker } from '../../components/maps';
import { VerificationTag } from '../../components/StatusTag';
import { t } from '../../i18n';
import { Button, LinkButton } from '../../ui/Button';
import { Card, CardTitle, Facts } from '../../ui/Card';
import { Alert, LoadingBlock } from '../../ui/feedback';
import { ChoiceCards, TextInput, Toggle } from '../../ui/form';
import { Icon } from '../../ui/icons';
import { Page, PageHeader } from '../../ui/layout';
import { categoryIcon, vocabLabel } from '../../vocab/display';

/** Fields shown next to their inputs; anything else goes in the error banner. */
const INLINE = Object.fromEntries(
  ['contact_person', 'phone', 'storage_capacity', 'categories_accepted', 'address_text', 'latitude', 'longitude'].map((k) => [k, k]),
);

function ProfileEditor({ org }: { org: OrganizationOut }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<ProfileForm>(() => formFromOrganisation(org));
  const [saved, setSaved] = useState(false);
  const changes = profileChanges(org, form);

  const save = useMutation({
    mutationFn: () => unwrap(client.PATCH('/organisations/me', { body: changes })),
    onSuccess: (updated) => {
      queryClient.setQueryData(['organisation'], updated);
      setForm(formFromOrganisation(updated));
      setSaved(true);
    },
  });

  const set = <K extends keyof ProfileForm>(field: K, value: ProfileForm[K]) => {
    setSaved(false);
    setForm((current) => ({ ...current, [field]: value }));
  };
  const toggleCategory = (value: string) =>
    set(
      'categories_accepted',
      form.categories_accepted.includes(value) ? form.categories_accepted.filter((c) => c !== value) : [...form.categories_accepted, value],
    );
  const err = (field: string) => fieldError(save.error, field);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (hasChanges(changes)) save.mutate();
  }

  return (
    <form onSubmit={submit} className="space-y-6">
      <Card>
        <CardTitle aside={<VerificationTag status={org.verification_status} />}>{t('profile.identity')}</CardTitle>
        <Facts
          items={[
            { label: t('fields.orgName'), value: <Locked>{org.name}</Locked> },
            { label: t('fields.registrationId'), value: <Locked>{org.registration_id}</Locked> },
          ]}
        />
        <p className="mt-4 text-sm text-ink-muted">{t('profile.lockedNote')}</p>
      </Card>

      <Card>
        <CardTitle>{t('profile.contact')}</CardTitle>
        <div className="grid gap-4 sm:grid-cols-2">
          <TextInput
            label={t('fields.contactPerson')}
            value={form.contact_person}
            onChange={(e) => set('contact_person', e.target.value)}
            error={err('contact_person')}
            required
          />
          <TextInput
            label={t('fields.orgPhone')}
            type="tel"
            value={form.phone}
            onChange={(e) => set('phone', e.target.value)}
            error={err('phone')}
            required
          />
        </div>
      </Card>

      <Card>
        <CardTitle>{t('profile.accepting')}</CardTitle>
        <p className="mb-4 text-sm text-ink-muted">{t('profile.acceptingNote')}</p>
        <ChoiceCards
          legend={t('fields.categoriesAccepted')}
          name="categories"
          multiple
          value={form.categories_accepted}
          onChange={toggleCategory}
          error={err('categories_accepted')}
          choices={categoryValues.map((value) => ({ value, label: vocabLabel('Category', value), icon: categoryIcon(value) }))}
        />
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <TextInput
            label={t('fields.storageCapacity')}
            type="number"
            min={0}
            inputMode="numeric"
            value={form.storage_capacity}
            onChange={(e) => set('storage_capacity', e.target.value)}
            error={err('storage_capacity')}
            hint={t('fields.storageCapacityHint')}
            required
          />
          <Toggle
            label={t('fields.pickupCapable')}
            description={t('fields.pickupCapableHint')}
            checked={form.pickup_capable}
            onChange={(value) => set('pickup_capable', value)}
          />
        </div>
      </Card>

      <Card>
        <CardTitle>{t('auth.orgSectionLocation')}</CardTitle>
        <p className="mb-4 text-sm text-ink-muted">{t('profile.locationNote')}</p>
        <LocationPicker value={form.pin} onChange={(pin) => set('pin', pin)} error={err('latitude') ?? err('longitude')} />
        <TextInput
          className="mt-4"
          label={t('fields.address')}
          value={form.address_text}
          onChange={(e) => set('address_text', e.target.value)}
          error={err('address_text')}
          hint={t('fields.addressHint')}
          required
        />
      </Card>

      {/* Above Leaflet's controls (z-index 1000), below the header. */}
      <div className="sticky bottom-0 z-[1050]-mx-4 space-y-3 border-t border-line bg-canvas/90 px-4 py-4 backdrop-blur-md sm:mx-0 sm:rounded-card sm:border sm:px-5">
        <ApiErrorAlert error={save.error} inlineFields={INLINE} />
        {saved && !save.error && (
          <Alert kind="success" title={t('profile.savedTitle')}>
            {t('profile.savedText')}
          </Alert>
        )}
        <div className="flex flex-wrap items-center justify-end gap-2">
          {!hasChanges(changes) && !saved && <span className="mr-auto text-sm text-ink-muted">{t('profile.noChanges')}</span>}
          <Button type="button" variant="ghost" disabled={!hasChanges(changes) || save.isPending} onClick={() => setForm(formFromOrganisation(org))}>
            {t('profile.discard')}
          </Button>
          <Button type="submit" icon="check" busy={save.isPending} disabled={!hasChanges(changes)}>
            {t('profile.save')}
          </Button>
        </div>
      </div>
    </form>
  );
}

function Locked({ children }: { children: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <Icon name="lock" className="size-4 shrink-0 text-ink-muted" />
      <span className="min-w-0 break-words">{children}</span>
    </span>
  );
}

/** Edit the organisation's operational details. Matching reads them live. */
export function OrganisationProfile() {
  const org = useMyOrganisation();
  return (
    <Page width="narrow">
      <PageHeader
        back={{ to: paths.acceptor, label: t('acceptor.back') }}
        eyebrow={t('acceptor.eyebrow')}
        title={t('profile.title')}
        subtitle={t('profile.subtitle')}
        actions={
          <LinkButton to={paths.acceptor} variant="secondary" size="sm">
            {t('profile.done')}
          </LinkButton>
        }
      />
      <ApiErrorAlert error={org.error} />
      {org.isPending ? <LoadingBlock label={t('common.loading')} /> : org.data && <ProfileEditor key={org.data.id} org={org.data} />}
    </Page>
  );
}
