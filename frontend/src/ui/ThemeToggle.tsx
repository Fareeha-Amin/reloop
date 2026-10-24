import { Icon } from './icons';
import { useTheme } from './theme';

/** Switches between light and dark; the label says what a click will do. */
export function ThemeToggle({ toDarkLabel, toLightLabel }: { toDarkLabel: string; toLightLabel: string }) {
  const { theme, toggle } = useTheme();
  const label = theme === 'dark' ? toLightLabel : toDarkLabel;
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={label}
      title={label}
      className="relative grid size-10 place-items-center rounded-full text-ink-soft transition hover:bg-surface-muted hover:text-ink"
    >
      <Icon name={theme === 'dark' ? 'sun' : 'moon'} />
    </button>
  );
}
