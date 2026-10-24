import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { unwrap } from '../api/errors';
import { urgencyValues, type Category, type NeedOut, type Urgency } from '../api/schema';
import { client } from '../app/api';
import { useNeeds } from '../app/queries';
import { formatDate } from '../i18n/format';
import { t } from '../i18n';
import { Button } from '../ui/Button';
import { Card, CardTitle } from '../ui/Card';
import { Dialog } from '../ui/Dialog';
import { Skeleton } from '../ui/feedback';
import { Select, TextInput } from '../ui/form';
import { Icon } from '../ui/icons';
import { categoryIcon, vocabLabel } from '../vocab/display';
import { ApiErrorAlert, fieldError } from './ApiErrorAlert';
import { UrgencyTag } from './StatusTag';

const urgencyOptions = () => urgencyValues.map((u) => ({ value: u, label: vocabLabel('Urgency', u) }));

/** Add a need, or change one's quantity and urgency. The API checks the rules (one active need per category, ...). */
function NeedDialog({ need, categories, onClose }: { need: NeedOut | null; categories: string[]; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [category, setCategory] = useState(need?.category ?? categories[0] ?? '');
  const [quantity, setQuantity] = useState(String(need?.quantity_needed ?? ''));
  const [urgency, setUrgency] = useState<string>(need?.urgency ?? urgencyValues[1]);

  const save = useMutation({
    mutationFn: () => {
      const body = { quantity_needed: Number(quantity), urgency: urgency as Urgency };
      return need
        ? unwrap(client.PATCH('/organisations/me/needs/{need_id}', { params: { path: { need_id: need.id } }, body }))
        : unwrap(client.POST('/organisations/me/needs', { body: { ...body, category: category as Category } }));
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['needs'] });
      onClose();
    },
  });
  const inline = { quantity_needed: true };

  return (
    <Dialog
      open
      onClose={onClose}
      title={need ? t('needs.editTitle', { category: vocabLabel('Category', need.category) }) : t('needs.addTitle')}
      closeLabel={t('common.close')}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            {t('common.back')}
          </Button>
          <Button busy={save.isPending} onClick={() => save.mutate()} disabled={quantity === ''}>
            {t('needs.save')}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {!need && (
          <Select
            label={t('needs.category')}
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            options={categories.map((c) => ({ value: c, label: vocabLabel('Category', c) }))}
          />
        )}
        <TextInput
          label={t('needs.quantity')}
          hint={t('fields.quantityHint')}
          type="number"
          min={1}
          inputMode="numeric"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          error={fieldError(save.error, 'quantity_needed')}
        />
        <Select label={t('needs.urgency')} value={urgency} onChange={(e) => setUrgency(e.target.value)} options={urgencyOptions()} />
        <ApiErrorAlert error={save.error} inlineFields={inline} />
      </div>
    </Dialog>
  );
}

function NeedRow({ need, onEdit, onToggle, busy }: { need: NeedOut; onEdit: () => void; onToggle: () => void; busy: boolean }) {
  return (
    <li className="py-3">
      <div className="flex items-center gap-3">
        <span className="grid size-9 shrink-0 place-items-center rounded-control bg-brand-50 text-brand-700">
          <Icon name={categoryIcon(need.category)} className="size-4.5" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-semibold">{vocabLabel('Category', need.category)}</p>
          <p className="text-sm text-ink-muted">
            {need.is_active
              ? t('common.items', { count: need.quantity_needed })
              : t('needs.closedOn', { date: formatDate(need.updated_at) })}
          </p>
        </div>
        {need.is_active && <UrgencyTag urgency={need.urgency} />}
      </div>
      <div className="mt-1 -mb-1 flex justify-end gap-1">
        {need.is_active && (
          <Button variant="ghost" size="sm" onClick={onEdit}>
            {t('needs.edit')}
          </Button>
        )}
        <Button variant="ghost" size="sm" busy={busy} onClick={onToggle}>
          {need.is_active ? t('needs.close') : t('needs.reopen')}
        </Button>
      </div>
    </li>
  );
}

/** The organisation's needs list: what it asks donors for, and how urgently. */
export function NeedsCard({ categories }: { categories: string[] }) {
  const queryClient = useQueryClient();
  const needs = useNeeds();
  const [dialog, setDialog] = useState<{ need: NeedOut | null } | null>(null);

  const toggle = useMutation({
    mutationFn: (need: NeedOut) =>
      unwrap(
        client.PATCH('/organisations/me/needs/{need_id}', {
          params: { path: { need_id: need.id } },
          body: { is_active: !need.is_active },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['needs'] }),
  });

  const active = needs.data?.filter((n) => n.is_active) ?? [];
  const closed = needs.data?.filter((n) => !n.is_active) ?? [];
  const row = (need: NeedOut) => (
    <NeedRow
      key={need.id}
      need={need}
      onEdit={() => setDialog({ need })}
      onToggle={() => toggle.mutate(need)}
      busy={toggle.isPending && toggle.variables?.id === need.id}
    />
  );

  return (
    <Card>
      <CardTitle
        aside={
          <Button variant="secondary" size="sm" icon="plus" onClick={() => setDialog({ need: null })}>
            {t('needs.add')}
          </Button>
        }
      >
        {t('needs.title')}
      </CardTitle>
      <p className="text-sm text-ink-muted">{t('needs.intro')}</p>
      <ApiErrorAlert error={needs.error ?? toggle.error} />
      {needs.isPending ? (
        <Skeleton className="mt-4 h-16" />
      ) : active.length === 0 ? (
        <p className="mt-4 rounded-control bg-surface-muted px-4 py-3 text-sm text-ink-soft">{t('needs.empty')}</p>
      ) : (
        <ul className="mt-2 divide-y divide-line">{active.map(row)}</ul>
      )}
      {closed.length > 0 && (
        <details className="group mt-3 border-t border-line pt-3">
          <summary className="flex cursor-pointer list-none items-center gap-1.5 text-sm font-semibold text-ink-muted">
            <Icon name="chevronRight" className="size-4 transition group-open:rotate-90" />
            {t('needs.closed', { count: closed.length })}
          </summary>
          <ul className="divide-y divide-line">{closed.map(row)}</ul>
        </details>
      )}
      {dialog && <NeedDialog need={dialog.need} categories={categories} onClose={() => setDialog(null)} />}
    </Card>
  );
}
