/**
 * Light or dark. With no saved choice the app follows the system preference (CSS
 * color-scheme in styles/theme.css). Choosing a theme sets <html data-theme> and
 * remembers it in this browser.
 */

import { useCallback, useSyncExternalStore } from 'react';

export type Theme = 'light' | 'dark';

const KEY = 'reloop.theme';
const listeners = new Set<() => void>();
const systemDark = () => typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches;

function saved(): Theme | null {
  try {
    const value = window.localStorage.getItem(KEY);
    return value === 'light' || value === 'dark' ? value : null;
  } catch {
    return null;
  }
}

function apply(theme: Theme | null): void {
  if (typeof document === 'undefined') return;
  if (theme) document.documentElement.dataset.theme = theme;
  else delete document.documentElement.dataset.theme;
}

// Applied as soon as this module loads, before the first render, so a saved choice
// that differs from the system does not flash the other theme.
if (typeof window !== 'undefined') {
  apply(saved());
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => listeners.forEach((l) => l()));
}

function current(): Theme {
  return saved() ?? (systemDark() ? 'dark' : 'light');
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useTheme(): { theme: Theme; toggle: () => void } {
  const theme = useSyncExternalStore(subscribe, current, () => 'light' as Theme);
  const toggle = useCallback(() => {
    const next: Theme = current() === 'dark' ? 'light' : 'dark';
    try {
      window.localStorage.setItem(KEY, next);
    } catch {
      // Storage unavailable: the choice lasts until reload.
    }
    apply(next);
    listeners.forEach((l) => l());
  }, []);
  return { theme, toggle };
}
