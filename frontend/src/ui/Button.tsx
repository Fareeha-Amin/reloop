import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { Link } from 'react-router';

import { Icon, type IconName } from './icons';
import { Spinner } from './feedback';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'inverse' | 'outlineInverse';
export type ButtonSize = 'sm' | 'md' | 'lg';

const VARIANTS: Record<ButtonVariant, string> = {
  primary: 'bg-brand-700 text-brand-50 hover:bg-brand-800 shadow-card',
  secondary: 'bg-surface text-ink ring-1 ring-line-strong hover:bg-surface-muted',
  ghost: 'text-ink-soft hover:bg-surface-muted',
  danger: 'bg-surface text-danger-700 ring-1 ring-tone-danger-bg hover:bg-tone-danger-bg',
  // For dark (brand) backgrounds.
  inverse: 'bg-leaf text-brand-950 hover:bg-mint shadow-glow',
  outlineInverse: 'text-brand-50 ring-1 ring-brand-50/30 bg-brand-50/5 backdrop-blur-sm hover:bg-brand-50/15 hover:ring-brand-50/50',
};

const SIZES: Record<ButtonSize, string> = {
  sm: 'h-9 px-3 text-sm gap-1.5',
  md: 'h-11 px-4 text-sm gap-2',
  lg: 'h-13 px-6 text-base gap-2.5',
};

export function buttonClasses(variant: ButtonVariant = 'primary', size: ButtonSize = 'md', extra = ''): string {
  return [
    'inline-flex items-center justify-center rounded-control font-semibold whitespace-nowrap',
    'transition duration-150 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none',
    VARIANTS[variant],
    SIZES[size],
    extra,
  ].join(' ');
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: IconName;
  iconAfter?: IconName;
  busy?: boolean;
  children?: ReactNode;
}

export function Button({
  variant = 'primary',
  size = 'md',
  icon,
  iconAfter,
  busy = false,
  className = '',
  children,
  disabled,
  type = 'button',
  ...rest
}: ButtonProps) {
  return (
    <button type={type} className={buttonClasses(variant, size, className)} disabled={disabled || busy} {...rest}>
      {busy ? <Spinner className="size-4" /> : icon && <Icon name={icon} className="size-4.5" />}
      {children}
      {iconAfter && <Icon name={iconAfter} className="size-4.5" />}
    </button>
  );
}

interface LinkButtonProps {
  to: string;
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: IconName;
  iconAfter?: IconName;
  className?: string;
  children: ReactNode;
}

export function LinkButton({ to, variant = 'primary', size = 'md', icon, iconAfter, className = '', children }: LinkButtonProps) {
  return (
    <Link to={to} className={buttonClasses(variant, size, className)}>
      {icon && <Icon name={icon} className="size-4.5" />}
      {children}
      {iconAfter && <Icon name={iconAfter} className="size-4.5" />}
    </Link>
  );
}
