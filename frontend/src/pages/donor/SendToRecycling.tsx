/** Send to recycling: the donor's own choice, not a fallback. A short form, separate
 * from "New donation", because this never enters matching (app.domain.lifecycle: a
 * donor-only LISTED -> WASTE_REDIRECTED edge). The confirmation step says so plainly. */

import { useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router';

import { ApiError, unwrap } from '../../api/errors';
import { categoryValues, conditionValues, type Category, type Condition, type RecycleDonationCreate } from '../../api/schema';
import { client } from '../../app/api';
import { paths } from '../../app/paths';
import { keys } from '../../app/queries';
import { ApiErrorAlert, fieldError } from '../../components/ApiErrorAlert';
import { fromLocalInput, toLocalInput, tomorrowAt } from '../../components/datetime';
import { donationTitle } from '../../components/donation';
import { LocationPicker, type Point } from '../../components/maps';
import { DEFAULT_WINDOW_HOURS } from '../../config';
import { formatDateTime } from '../../i18n/format';
import { t } from '../../i18n';
import { Button } from '../../ui/Button';
import { Card, Facts } from '../../ui/Card';
import { Alert } from '../../ui/feedback';
import { ChoiceCards, TextInput } from '../../ui/form';
import { Page, PageHeader, Stepper } from '../../ui/layout';
import { categoryIcon, conditionLabel, vocabLabel } from '../../vocab/display';

const FIELD_STEP: Record<string, number> = {
  category: 0,
  quantity: 0,
  condition: 0,
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
  pin: Point | null;
  address: string;
  windowStart: string;
  windowEnd: string;
}

export function SendToRecycling() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [step, setStep] = useState(0);
  const [draft, setDraft] = useState<Draft>(() => ({
    category: '',
    condition: '',
    quantity: '',
    pin: null,
    address: '',
    windowStart: toLocalInput(tomorrowAt(DEFAULT_WINDOW_HOURS.start)),
    windowEnd: toLocalInput(tomorrowAt(DEFAULT_WINDOW_HOURS.end)),
  }));
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const update = (patch: Partial<Draft>) => setDraft((d) => ({ ...d, ...patch }));
  const err = (field: string) => fieldError(error, field);

  const steps = [t('sendToRecycling.stepWhat'), t('sendToRecycling.stepWhere'), t('sendToRecycling.stepConfirm')];

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
      quantity: Number(draft.quantity),
      condition: draft.condition || null,
      pickup_address_text: draft.address,
      pickup_latitude: draft.pin?.lat,
      pickup_longitude: draft.pin?.lng,
      pickup_window_start: fromLocalInput(draft.windowStart),
      pickup_window_end: fromLocalInput(draft.windowEnd),
    } as RecycleDonationCreate;

    try {
      const donation = await unwrap(client.POST('/donations/recycle', { body }));
      await queryClient.invalidateQueries({ queryKey: keys.myDonations });
      navigate(paths.donation(donation.id));
    } catch (e) {
      setError(e);
      setBusy(false);
      if (e instanceof ApiError) {
        const stepsWithErrors = Object.keys(e.fieldErrors).map((f) => FIELD_STEP[f] ?? 1);
        if (stepsWithErrors.length > 0) setStep(Math.min(...stepsWithErrors));
      }
    }
  }

  return (
    <Page width="narrow">
      <PageHeader
        eyebrow={t('sendToRecycling.eyebrow')}
        title={t('sendToRecycling.title')}
        back={{ to: paths.donor, label: t('donor.back') }}
      />
      <Stepper steps={steps} current={step} />
      <ApiErrorAlert error={error} inlineFields={FIELD_STEP} />

      {step === 0 && (
        <form onSubmit={next} className="mt-4 space-y-6">
          <p className="text-sm text-ink-muted">{t('sendToRecycling.intro')}</p>
          <ChoiceCards
            legend={t('fields.category')}
            name="category"
            value={draft.category}
            onChange={(v) => update({ category: v as Category })}
            error={err('category')}
            choices={categoryValues.map((value) => ({ value, label: vocabLabel('Category', value), icon: categoryIcon(value) }))}
          />
          <ChoiceCards
            legend={t('sendToRecycling.conditionOptional')}
            name="condition"
            value={draft.condition}
            onChange={(v) => update({ condition: v as Condition })}
            error={err('condition')}
            choices={conditionValues.map((value) => ({ value, label: vocabLabel('Condition', value) }))}
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
          <div className="flex justify-end">
            <Button type="submit" size="lg" iconAfter="arrowRight" disabled={!draft.category}>
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
            <p className="mb-4 text-sm text-ink-muted">{t('sendToRecycling.whenText')}</p>
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
            <h2 className="mb-4 text-lg font-semibold">{t('sendToRecycling.reviewTitle')}</h2>
            <Facts
              items={[
                {
                  label: t('fields.item'),
                  value: draft.category ? donationTitle({ quantity: Number(draft.quantity), category: draft.category }) : '',
                },
                { label: t('fields.condition'), value: conditionLabel(draft.condition || null) },
                { label: t('fields.pickupAddress'), value: draft.address },
                {
                  label: t('fields.window'),
                  value: t('common.range', {
                    from: formatDateTime(fromLocalInput(draft.windowStart) || new Date().toISOString()),
                    to: formatDateTime(fromLocalInput(draft.windowEnd) || new Date().toISOString()),
                  }),
                },
              ]}
            />
          </Card>
          <Alert kind="warning" title={t('sendToRecycling.confirmTitle')}>
            {t('sendToRecycling.confirmText')}
          </Alert>
          <div className="flex justify-between">
            <Button variant="ghost" icon="arrowLeft" onClick={() => setStep(1)}>
              {t('common.back')}
            </Button>
            <Button size="lg" busy={busy} onClick={submit} icon="recycle">
              {t('sendToRecycling.submit')}
            </Button>
          </div>
        </div>
      )}
    </Page>
  );
}
