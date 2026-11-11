import type { ReactNode } from 'react';

export function PageHeader({ group, title, description, actions }: { group: string; title: string; description: string; actions?: ReactNode }) {
  return <header className="page-heading"><div><p className="eyebrow">{group}</p><h1>{title}</h1><p className="page-description">{description}</p></div>{actions && <div className="page-heading-actions">{actions}</div>}</header>;
}
