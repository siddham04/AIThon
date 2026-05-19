/** Shared auth / API error text for login & register. */
export function formatApiError(ex) {
  const ct =
    ex.response?.headers?.['content-type'] ||
    ex.response?.headers?.['Content-Type'] ||
    ''
  if (String(ct).includes('text/html')) {
    return 'The API URL returned a web page instead of JSON. On Vercel set HELIX_BACKEND_ORIGIN (or VITE_API_BASE) and redeploy — see docs/VERCEL.md.'
  }
  const d = ex.response?.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) {
    return d
      .map((x) => (typeof x === 'string' ? x : x.msg || JSON.stringify(x)))
      .join('; ')
  }
  if (d && typeof d === 'object') return JSON.stringify(d)
  if (ex.message === 'Network Error') return 'Cannot reach API — is the backend running?'
  return 'Request failed'
}
