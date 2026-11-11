import type { ReactNode } from 'react';

export function StatusBadge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'success' | 'warning' | 'danger' }) {
  return <span className={`product-badge tone-${tone}`}><span className="badge-dot" aria-hidden="true" />{children}</span>;
}
