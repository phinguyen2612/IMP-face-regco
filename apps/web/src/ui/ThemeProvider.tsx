import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

export type Theme = 'light' | 'dark';
type ThemeContextValue = { theme: Theme; toggleTheme: () => void };
const ThemeContext = createContext<ThemeContextValue | null>(null);
const STORAGE_KEY = 'face-attendance-theme';

function initialPreference(): { theme: Theme; saved: boolean } {
  let saved: string | null = null;
  try { saved = window.localStorage.getItem(STORAGE_KEY); } catch { /* Use the device theme when storage is blocked. */ }
  if (saved === 'light' || saved === 'dark') return { theme: saved, saved: true };
  return { theme: window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light', saved: false };
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [preference, setPreference] = useState(initialPreference);
  const { theme, saved } = preference;
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    if (saved) { try { window.localStorage.setItem(STORAGE_KEY, theme); } catch { /* The current theme still works without persistence. */ } }
  }, [theme, saved]);
  useEffect(() => {
    if (saved || !window.matchMedia) return;
    const query = window.matchMedia('(prefers-color-scheme: dark)');
    const update = (event: MediaQueryListEvent) => setPreference(current => ({ ...current, theme: event.matches ? 'dark' : 'light' }));
    query.addEventListener?.('change', update);
    return () => query.removeEventListener?.('change', update);
  }, [saved]);
  const value = useMemo(() => ({
    theme,
    toggleTheme: () => setPreference(current => ({ theme: current.theme === 'light' ? 'dark' : 'light', saved: true })),
  }), [theme]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const value = useContext(ThemeContext);
  if (!value) throw new Error('useTheme must be used inside ThemeProvider');
  return value;
}
