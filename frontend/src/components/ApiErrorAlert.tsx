import { ApiError } from '../api/errors';
import { t } from '../i18n';
import { Alert } from '../ui/feedback';

/**
 * Shows what the API said went wrong, or that it could not be reached. `inlineFields`:
 * field paths the form already shows next to their inputs, so they are not repeated.
 */
export function ApiErrorAlert({ error, inlineFields }: { error: unknown; inlineFields?: Record<string, unknown> }) {
  if (!error) return null;
  if (!(error instanceof ApiError)) {
    return (
      <Alert kind="danger" title={t('errors.unreachableTitle')}>
        {t('errors.unreachable')}
      </Alert>
    );
  }
  const unshownFields = Object.entries(error.fieldErrors).filter(([field]) => !inlineFields || !(field in inlineFields));
  const lines = [...error.formErrors, ...unshownFields.map(([field, message]) => `${field}: ${message}`)];
  return (
    <Alert kind="danger" title={error.detail ?? t(error.status === 422 ? 'errors.validation' : 'errors.generic')}>
      {lines.length > 0 && (
        <ul className="list-inside list-disc">
          {lines.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      )}
    </Alert>
  );
}

/** The API's message for one field, if any. */
export function fieldError(error: unknown, field: string): string | undefined {
  return error instanceof ApiError ? error.fieldErrors[field] : undefined;
}
