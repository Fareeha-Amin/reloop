import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate } from 'react-router';

import { rejectReasonValues } from '../api/schema';
import { t } from '../i18n';
import { Button, type ButtonVariant } from '../ui/Button';
import { Dialog } from '../ui/Dialog';
import { Select, TextArea, TextInput } from '../ui/form';
import { specsFor, type ActionPayload, type ActionSpec, type Emphasis, type Surface } from '../vocab/actions';
import { vocabLabel } from '../vocab/display';
import { ApiErrorAlert } from './ApiErrorAlert';
import { fromLocalInput, toLocalInput, tomorrowAt } from './datetime';
import { DEFAULT_WINDOW_HOURS } from '../config';

const VARIANT: Record<Emphasis, ButtonVariant> = { primary: 'primary', secondary: 'secondary', danger: 'danger' };

function ActionDialog({
  spec,
  id,
  onClose,
  onDone,
}: {
  spec: ActionSpec;
  id: string;
  onClose: () => void;
  onDone?: (result: unknown) => void;
}) {
  const queryClient = useQueryClient();
  const [when, setWhen] = useState(() => toLocalInput(tomorrowAt(DEFAULT_WINDOW_HOURS.start)));
  const [reason, setReason] = useState('');
  const [reasonCode, setReasonCode] = useState<string>(rejectReasonValues[0]);
  const [note, setNote] = useState('');

  const mutation = useMutation({
    mutationFn: () => {
      const payload: ActionPayload = {};
      if (spec.input === 'datetime') payload.scheduledFor = fromLocalInput(when);
      if (spec.input === 'reason') payload.reason = reason;
      if (spec.input === 'reject') Object.assign(payload, { reasonCode, note });
      return spec.run!(id, payload);
    },
    onSuccess: async (result) => {
      await queryClient.invalidateQueries();
      onClose();
      onDone?.(result);
    },
  });

  return (
    <Dialog
      open
      onClose={onClose}
      title={t(spec.labelKey)}
      closeLabel={t('common.close')}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            {t('common.back')}
          </Button>
          <Button
            variant={VARIANT[spec.emphasis]}
            busy={mutation.isPending}
            onClick={() => mutation.mutate()}
            disabled={spec.input === 'reason' && reason.trim() === ''}
          >
            {t(spec.labelKey)}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {spec.confirmKey && <p>{t(spec.confirmKey)}</p>}
        {spec.input === 'datetime' && (
          <TextInput
            label={t('actions.when')}
            hint={t('actions.whenHint')}
            type="datetime-local"
            value={when}
            onChange={(e) => setWhen(e.target.value)}
            required
          />
        )}
        {spec.input === 'reason' && (
          <TextArea
            label={t('actions.reason')}
            hint={t('actions.reasonHint')}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            required
          />
        )}
        {spec.input === 'reject' && (
          <>
            <Select
              label={t('actions.rejectReason')}
              value={reasonCode}
              onChange={(e) => setReasonCode(e.target.value)}
              options={rejectReasonValues.map((value) => ({ value, label: vocabLabel('RejectReason', value) }))}
            />
            <TextArea label={t('actions.rejectNote')} hint={t('actions.rejectNoteHint')} value={note} onChange={(e) => setNote(e.target.value)} />
          </>
        )}
        <ApiErrorAlert error={mutation.error} />
      </div>
    </Dialog>
  );
}

/**
 * Buttons for exactly the actions the API allows (non-negotiable 12). Nothing here
 * decides whether an action is possible; the API's allowed_actions does.
 */
export function ActionBar({
  surface,
  id,
  allowed,
  onDone,
  size = 'md',
}: {
  surface: Surface;
  id: string;
  allowed: readonly string[];
  onDone?: (result: unknown) => void;
  size?: 'sm' | 'md' | 'lg';
}) {
  const navigate = useNavigate();
  const [open, setOpen] = useState<string | null>(null);
  const specs = specsFor(surface, allowed);
  if (specs.length === 0) return null;
  const openSpec = specs.find(([action]) => action === open)?.[1];

  return (
    <div className="flex flex-wrap gap-2">
      {specs.map(([action, spec]) => (
        <Button
          key={action}
          size={size}
          variant={VARIANT[spec.emphasis]}
          iconAfter={spec.input === 'navigate' ? 'arrowRight' : undefined}
          onClick={() => (spec.input === 'navigate' && spec.to ? navigate(spec.to(id)) : setOpen(action))}
        >
          {t(spec.labelKey)}
        </Button>
      ))}
      {openSpec && <ActionDialog key={open} spec={openSpec} id={id} onClose={() => setOpen(null)} onDone={onDone} />}
    </div>
  );
}
