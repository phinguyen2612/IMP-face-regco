import { useEffect, useState } from 'react';

const STORAGE_KEY = 'face-attendance-login-motion';

export function useLoginMotion() {
  const [enabled, setEnabled] = useState(() => {
    try { return localStorage.getItem(STORAGE_KEY) !== 'paused'; }
    catch { return true; }
  });
  const [reduced, setReduced] = useState(() => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false);
  const [hidden, setHidden] = useState(() => document.hidden);

  useEffect(() => {
    const query = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    const updateMotion = () => setReduced(query?.matches ?? false);
    const updateVisibility = () => setHidden(document.hidden);
    query?.addEventListener?.('change', updateMotion);
    document.addEventListener('visibilitychange', updateVisibility);
    updateMotion();
    updateVisibility();
    return () => {
      query?.removeEventListener?.('change', updateMotion);
      document.removeEventListener('visibilitychange', updateVisibility);
    };
  }, []);

  function toggle() {
    const next = !enabled;
    setEnabled(next);
    try { localStorage.setItem(STORAGE_KEY, next ? 'enabled' : 'paused'); }
    catch { /* The preference remains usable when browser storage is blocked. */ }
  }

  return { enabled, reduced, running: enabled && !reduced && !hidden, toggle };
}
