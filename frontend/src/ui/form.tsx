import { useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react';

import { Icon, type IconName } from './icons';

const CONTROL =
  'w-full rounded-control border border-line-strong bg-surface px-3.5 py-2.5 text-[15px] text-ink placeholder:text-ink-muted/70 transition-colors focus:border-brand-400 aria-[invalid=true]:border-danger-500';

interface FieldProps {
  label: ReactNode;
  hint?: ReactNode;
  error?: string;
  children: (id: string, describedBy: string | undefined) => ReactNode;
  className?: string;
}

/** A labelled control with an optional hint and an error from the API. */
export function Field({ label, hint, error, children, className = '' }: FieldProps) {
  const id = useId();
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined;
  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1.5 block text-sm font-semibold text-ink-soft">
        {label}
      </label>
      {children(id, describedBy)}
      {error ? (
        <p id={`${id}-error`} className="mt-1.5 text-sm text-danger-700">
          {error}
        </p>
      ) : (
        hint && (
          <p id={`${id}-hint`} className="mt-1.5 text-xs text-ink-muted">
            {hint}
          </p>
        )
      )}
    </div>
  );
}

type InputProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'children'> & { label: ReactNode; hint?: ReactNode; error?: string };

export function TextInput({ label, hint, error, className, ...rest }: InputProps) {
  return (
    <Field label={label} hint={hint} error={error} className={className}>
      {(id, describedBy) => (
        <input id={id} aria-describedby={describedBy} aria-invalid={Boolean(error)} className={CONTROL} {...rest} />
      )}
    </Field>
  );
}

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & { label: ReactNode; hint?: ReactNode; error?: string };

export function TextArea({ label, hint, error, className, ...rest }: TextareaProps) {
  return (
    <Field label={label} hint={hint} error={error} className={className}>
      {(id, describedBy) => (
        <textarea
          id={id}
          aria-describedby={describedBy}
          aria-invalid={Boolean(error)}
          rows={3}
          className={`${CONTROL} resize-y`}
          {...rest}
        />
      )}
    </Field>
  );
}

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label: ReactNode;
  hint?: ReactNode;
  error?: string;
  options: Array<{ value: string; label: string }>;
};

export function Select({ label, hint, error, options, className, ...rest }: SelectProps) {
  return (
    <Field label={label} hint={hint} error={error} className={className}>
      {(id, describedBy) => (
        <select id={id} aria-describedby={describedBy} aria-invalid={Boolean(error)} className={CONTROL} {...rest}>
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      )}
    </Field>
  );
}

export interface Choice {
  value: string;
  label: string;
  description?: string;
  icon?: IconName;
}

/** Large radio (or checkbox) cards for a small set of choices. */
export function ChoiceCards({
  legend,
  name,
  choices,
  value,
  onChange,
  multiple = false,
  error,
  columns = 3,
}: {
  legend: ReactNode;
  name: string;
  choices: Choice[];
  value: string | string[];
  onChange: (value: string) => void;
  multiple?: boolean;
  error?: string;
  columns?: 2 | 3;
}) {
  const selected = Array.isArray(value) ? value : [value];
  const grid = columns === 2 ? 'sm:grid-cols-2' : 'sm:grid-cols-3';
  return (
    <fieldset>
      <legend className="mb-2 text-sm font-semibold text-ink-soft">{legend}</legend>
      <div className={`grid grid-cols-1 gap-3 ${grid}`}>
        {choices.map((choice) => {
          const checked = selected.includes(choice.value);
          return (
            <label
              key={choice.value}
              className={`relative flex cursor-pointer items-start gap-3 rounded-card border p-4 transition ${
                checked
                  ? 'border-brand-500 bg-brand-50 shadow-card ring-1 ring-brand-500'
                  : 'border-line bg-surface hover:border-line-strong'
              }`}
            >
              <input
                type={multiple ? 'checkbox' : 'radio'}
                name={name}
                value={choice.value}
                checked={checked}
                onChange={() => onChange(choice.value)}
                className="sr-only"
              />
              {choice.icon && (
                <span
                  className={`grid size-10 shrink-0 place-items-center rounded-control ${
                    checked ? 'bg-brand-700 text-brand-50' : 'bg-surface-muted text-ink-soft'
                  }`}
                >
                  <Icon name={choice.icon} />
                </span>
              )}
              <span className="min-w-0">
                <span className="block font-semibold">{choice.label}</span>
                {choice.description && <span className="mt-0.5 block text-xs text-ink-muted">{choice.description}</span>}
              </span>
              {checked && (
                <span className="absolute top-3 right-3 text-brand-600">
                  <Icon name="check" className="size-4" />
                </span>
              )}
            </label>
          );
        })}
      </div>
      {error && <p className="mt-1.5 text-sm text-danger-700">{error}</p>}
    </fieldset>
  );
}

/** An on/off switch with a description. */
export function Toggle({
  label,
  description,
  checked,
  onChange,
}: {
  label: ReactNode;
  description?: ReactNode;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-4 rounded-card border border-line bg-surface p-4">
      <span>
        <span className="block font-semibold">{label}</span>
        {description && <span className="mt-0.5 block text-sm text-ink-muted">{description}</span>}
      </span>
      <input type="checkbox" className="peer sr-only" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span className="relative mt-0.5 h-6 w-11 shrink-0 rounded-pill bg-line-strong transition peer-checked:bg-brand-600 peer-focus-visible:shadow-[var(--shadow-focus)] after:absolute after:top-0.5 after:left-0.5 after:size-5 after:rounded-full after:bg-knob after:shadow after:transition peer-checked:after:translate-x-5" />
    </label>
  );
}
