import {Icon} from './Icon';

export function DataState({title, description, loading = false, error = false}: {title: string; description?: string; loading?: boolean; error?: boolean}) {
  return <div className={`data-state ${error ? 'is-error' : ''}`} role={error ? 'alert' : loading ? 'status' : undefined}>
    <span className={`data-state-icon ${loading ? 'is-loading' : ''}`}><Icon name={error ? 'warning' : loading ? 'clock' : 'image'}/></span>
    <strong>{title}</strong>{description && <p>{description}</p>}
  </div>;
}
