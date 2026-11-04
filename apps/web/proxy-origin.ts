/** Restore an explicitly configured external origin, never trust arbitrary forwarded headers. */
export function proxyOriginHeaders(host: string | undefined, origin: string | undefined, configured?: string): Record<string, string> {
  if (!configured) return {'x-forwarded-proto': 'http'};
  const trusted = new URL(configured);
  if (!['http:', 'https:'].includes(trusted.protocol) || trusted.username || trusted.password || trusted.pathname !== '/' || trusted.search || trusted.hash) {
    throw new Error('FR_PREVIEW_PUBLIC_ORIGIN must be an HTTP(S) origin without credentials or a path.');
  }
  if (host?.toLowerCase() === trusted.host.toLowerCase() || origin === trusted.origin) {
    return {host: trusted.host, 'x-forwarded-proto': trusted.protocol.slice(0, -1)};
  }
  return {'x-forwarded-proto': 'http'};
}
