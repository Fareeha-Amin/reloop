import type { ModelOut } from '../api/schema';
import { formatNumber } from '../i18n/format';
import { t } from '../i18n';
import { Marker } from '../ui/Tag';

/**
 * Where a breakdown's weights came from: the assigned prior, or a fit from real outcomes,
 * with the version and the sample it was trained on. Every number and flag is the API's;
 * the labels are the only thing this component decides.
 */
export function ModelNote({ model }: { model: ModelOut }) {
  const sample = model.training_sample;
  return (
    <span className="inline-flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-ink-muted">
      <Marker icon={model.is_prior ? 'info' : 'star'}>{model.is_prior ? t('model.prior') : t('model.fitted')}</Marker>
      <span className="font-mono" title={t('model.versionHint')}>
        {model.config_version}
      </span>
      <span>
        {t('model.sample', {
          real: sample.real,
          accepted: sample.real_accepted,
          synthetic: sample.synthetic,
        })}
      </span>
      {model.max_shift_from_prior !== null && model.max_shift_from_prior !== undefined && (
        <span>{t('model.shift', { points: formatNumber(model.max_shift_from_prior * 100) })}</span>
      )}
    </span>
  );
}
