/**
 * Resolves the base URL for FastAPI backend requests.
 *
 * If VITE_API_URL is provided, it normalizes the URL and ensures a single '/api' prefix.
 * If VITE_API_URL is unset, it defaults to '/api' to preserve local development proxy behavior.
 */

export function getApiBaseUrl(rawEnvUrl) {
  const envUrl =
    rawEnvUrl ??
    (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_URL) ??
    (typeof process !== 'undefined' && process.env?.VITE_API_URL) ??
    '';

  const normalizedUrl = typeof envUrl === 'string' ? envUrl.trim() : '';

  if (!normalizedUrl) {
    return '/api';
  }

  const clean = normalizedUrl.replace(/\/+$/, '');

  if (!clean) {
    return '/api';
  }

  return clean.endsWith('/api') ? clean : `${clean}/api`;
}


/**
 * Builds a normalized, absolute or relative API URL for a given path.
 *
 * Prevents double '/api' prefixes (e.g. '/api/conversations' with base '.../api')
 * and normalizes leading/trailing slashes.
 */
export function buildApiUrl(path = '', rawEnvUrl) {
  const base = getApiBaseUrl(rawEnvUrl)
  const cleanPath = (path || '').trim().replace(/^\/+/, '')

  const strippedPath = cleanPath.startsWith('api/')
    ? cleanPath.slice(4)
    : cleanPath === 'api'
      ? ''
      : cleanPath

  return strippedPath ? `${base}/${strippedPath}` : base
}
