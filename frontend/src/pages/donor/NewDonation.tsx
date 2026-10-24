import { useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router';

import { ApiError, unwrap } from '../../api/errors';
import { categoryValues, conditionValues, type Category, type Condition, type DonationCreate } from '../../api/schema';
import { client } from '../../app/api';
import { paths } from '../../app/paths';
import { keys } from '../../app/queries';
import { ApiErrorAlert, fieldError } from '../../components/ApiErrorAlert';
import { fromLocalInput, toLocalInput, tomorrowAt } from '../../components/datetime';
import { donationTitle } from '../../components/donation';
import { PhotoPicker } from '../../components/images';
import { LocationPicker, type Point } from '../../components/maps';
import { DEFAULT_WINDOW_HOURS } from '../../config';
import { formatDateTime } from '../../i18n/format';
import { t } from '../../i18n';
import { Button } from '../../ui/Button';
import { Card, Facts } from '../../ui/Card';
import { Alert } from '../../ui/feedback';
import { ChoiceCards, TextArea, TextInput, Toggle } from '../../ui/form';
import { Page, PageHeader, Stepper } from '../../ui/layout';
import { categoryIcon, vocabLabel } from '../../vocab/display';

/** Which step shows each field, so an API error sends the donor back to it. */
const FIELD_STEP: Record<string, number> = {
  category: 0,
  quantity: 0,
  condition: 0,
  note: 0,
  is_priority: 0,
  pickup_latitude: 1,
  pickup_longitude: 1,
  pickup_address_text: 1,
  pickup_window_start: 1,
  pickup_window_end: 1,
};

interface Draft {
  category: Category | '';
  condition: Condition | '';
  quantity: string;
  note: string;
  isPriority: boolean;
  pin: Point | null;
  address: string;
  windowStart: string;
  windowEnd: string;
}

export function NewDonation() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [step, setStep] = useState(0);
  const [draft, setDraft] = useState<Draft>(() => ({
    category: '',
    condition: '',
    quantity: '',
    note: '',
    isPriority: false,
    pin: null,
    address: '',
    windowStart: toLocalInput(tomorrowAt(DEFAULT_WINDOW_HOURS.start)),
    windowEnd: toLocalInput(tomorrowAt(DEFAULT_WINDOW_HOURS.end)),
  }));
  const [photos, setPhotos] = useState<File[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const update = (patch: Partial<Draft>) => setDraft((d) => ({ ...d, ...patch }));
  const err = (field: string) => fieldError(error, field);

  const steps = [t('newDonation.stepWhat'), t('newDonation.stepWhere'), t('newDonation.stepReview')];

  function next(event: FormEvent) {
    event.preventDefault();
    setStep((s) => s + 1);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  async function submit() {
    setBusy(true);
    setError(null);
    const body = {
      category: draft.category,
      condition: draft.condition,
      quantity: Number(draft.quantity),
      note: draft.note.trim() || null,
      is_priority: draft.isPriority,
      pickup_address_text: draft.address,
      pickup_latitude: draft.pin?.lat,
      pickup_longitude: draft.pin?.lng,
      pickup_window_start: fromLocalInput(draft.windowStart),
      pickup_window_end: fromLocalInput(draft.windowEnd),
    } as DonationCreate;

    let donationId: string;
    try {
      donationId = (await unwrap(client.POST('/donations', { body }))).id;
    } catch (e) {
      setError(e);
      setBusy(false);
      if (e instanceof ApiError) {
        const steps = Object.keys(e.fieldErrors).map((f) => FIELD_STEP[f] ?? 2);
        if (steps.length > 0) setStep(Math.min(...steps));
      }
      return;
    }

    if (photos.length > 0) {
      const form = new FormData();
      photos.forEach((file) => form.append('files', file));
      try {
        await unwrap(
          client.POST('/donations/{donation_id}/images', {
            params: { path: { donation_id: donationId } },
            body: { files: [] },
            bodySerializer: () => form,
          }),
        );
      } catch (e) {
        // The donation exists; say what failed and let the donor carry on from its page.
        await queryClient.invalidateQueries({ queryKey: keys.myDonations });
        navigate(paths.donation(donationId), { state: { photoError: e instanceof ApiError ? e.message : null } });
        return;
      }
    }
    await queryClient.invalidateQueries({ queryKey: keys.myDonations });
    navigate(paths.candidates(donationId));
  }

  return (
    <Page width="narrow">
      <PageHeader eyebrow={t('newDonation.eyebrow')} title={t('newDonation.title')} back={{ to: paths.donor, label: t('donor.back') }} />
      <Stepper steps={steps} current={step} />
      <ApiErrorAlert error={error} inlineFields={FIELD_STEP} />

      {step === 0 && (
        <form onSubmit={next} className="mt-4 space-y-6">
          <ChoiceCards
            legend={t('fields.category')}
            name="category"
            value={draft.category}
            onChange={(v) => update({ category: v as Category })}
            error={err('category')}
            choices={categoryValues.map((value) => ({ value, label: vocabLabel('Category', value), icon: categoryIcon(value) }))}
          />
          <ChoiceCards
            legend={t('fields.condition')}
            name="condition"
            value={draft.condition}
            onChange={(v) => update({ condition: v as Condition })}
            error={err('condition')}
            choices={conditionValues.map((value) => ({
              value,
              label: vocabLabel('Condition', value),
              description: t(`newDonation.conditionHelp.${value}`),
            }))}
          />
          <TextInput
            label={t('fields.quantity')}
            hint={t('fields.quantityHint')}
            type="number"
            inputMode="numeric"
            min={1}
            value={draft.quantity}
            onChange={(e) => update({ quantity: e.target.value })}
            error={err('quantity')}
            required
          />
          <TextArea
            label={t('fields.note')}
            hint={t('fields.noteHint')}
            value={draft.note}
            onChange={(e) => update({ note: e.target.value })}
            error={err('note')}
          />
          <Toggle label={t('fields.priority')} description={t('fields.priorityHint')} checked={draft.isPriority} onChange={(isPriority) => update({ isPriority })} />
          <div className="flex justify-end">
            <Button type="submit" size="lg" iconAfter="arrowRight" disabled={!draft.category || !draft.condition}>
              {t('common.continue')}
            </Button>
          </div>
        </form>
      )}

      {step === 1 && (
        <form onSubmit={next} className="mt-4 space-y-6">
          <div>
            <h2 className="mb-1 text-lg font-semibold">{t('newDonation.whereTitle')}</h2>
            <p className="mb-4 text-sm text-ink-muted">{t('newDonation.whereText')}</p>
            <LocationPicker value={draft.pin} onChange={(pin) => update({ pin })} error={err('pickup_latitude')} />
          </div>
          <TextInput
            label={t('fields.pickupAddress')}
            hint={t('fields.addressHint')}
            value={draft.address}
            onChange={(e) => update({ address: e.target.value })}
            error={err('pickup_address_text')}
            required
          />
          <div>
            <h2 className="mb-1 text-lg font-semibold">{t('newDonation.whenTitle')}</h2>
            <p className="mb-4 text-sm text-ink-muted">{t('newDonation.whenText')}</p>
            <div className="grid gap-4 sm:grid-cols-2">
              <TextInput
                label={t('fields.windowStart')}
                type="datetime-local"
                value={draft.windowStart}
                onChange={(e) => update({ windowStart: e.target.value })}
                error={err('pickup_window_start')}
                required
              />
              <TextInput
                label={t('fields.windowEnd')}
                type="datetime-local"
                value={draft.windowEnd}
                onChange={(e) => update({ windowEnd: e.target.value })}
                error={err('pickup_window_end')}
                required
              />
            </div>
          </div>
          <div className="flex justify-between">
            <Button variant="ghost" icon="arrowLeft" onClick={() => setStep(0)}>
              {t('common.back')}
            </Button>
            <Button type="submit" size="lg" iconAfter="arrowRight" disabled={!draft.pin}>
              {t('common.continue')}
            </Button>
          </div>
        </form>
      )}

      {step === 2 && (
        <div className="mt-4 space-y-6">
          <Card>
            <h2 className="mb-1 text-lg font-semibold">{t('newDonation.photosTitle')}</h2>
            <p className="mb-4 text-sm text-ink-muted">{t('newDonation.photosText')}</p>
            <PhotoPicker files={photos} onChange={setPhotos} />
          </Card>
          <Card>
            <h2 className="mb-4 text-lg font-semibold">{t('newDonation.reviewTitle')}</h2>
            <Facts
              items={[
                {
                  label: t('fields.item'),
                  value: draft.category ? donationTitle({ quantity: Number(draft.quantity), category: draft.category }) : '',
                },
                { label: t('fields.condition'), value: draft.condition ? vocabLabel('Condition', draft.condition) : '' },
                { label: t('fields.pickupAddress'), value: draft.address },
                {
                  label: t('fields.window'),
                  value: t('common.range', {
                    from: formatDateTime(fromLocalInput(draft.windowStart) || new Date().toISOString()),
                    to: formatDateTime(fromLocalInput(draft.windowEnd) || new Date().toISOString()),
                  }),
                },
                draft.note.trim() !== '' && { label: t('fields.note'), value: draft.note },
                draft.isPriority && { label: t('fields.priority'), value: t('common.yes') },
              ]}
            />
          </Card>
          <Alert kind="info">{t('newDonation.nextHint')}</Alert>
          <div className="flex justify-between">
            <Button variant="ghost" icon="arrowLeft" onClick={() => setStep(1)}>
              {t('common.back')}
            </Button>
            <Button size="lg" busy={busy} onClick={submit} iconAfter="sparkles">
              {t('newDonation.submit')}
            </Button>
          </div>
        </div>
      )}
    </Page>
  );
}
