/** Shared auth / API error text for login, register, and guest flows. */
export function formatApiError(ex) {
  const ct =
    ex.response?.headers?.['content-type'] ||
    ex.response?.headers?.['Content-Type'] ||
    ''
  const status = ex.response?.status

  if (String(ct).includes('text/html')) {
    return 'The API URL returned a web page instead of JSON. Deploy the FastAPI backend (e.g. Render) and set HELIX_BACKEND_ORIGIN on Vercel, then redeploy — see docs/VERCEL.md.'
  }

  const d = ex.response?.data?.detail
  if (typeof d === 'string') {
    if (d.includes('HELIX_BACKEND_ORIGIN')) return `${d} Redeploy Vercel after saving the env var.`
    if (d.includes('Guest access is disabled')) {
      return 'Guest login is off on this API (HELIX_PRODUCTION=1). Use Sign in with demo@demo.com / demo123 or register.'
    }
    return d
  }
  if (Array.isArray(d)) {
    return d
      .map((x) => (typeof x === 'string' ? x : x.msg || JSON.stringify(x)))
      .join('; ')
  }
  if (d && typeof d === 'object') return JSON.stringify(d)

  if (status === 502) {
    return 'API proxy could not reach the backend — check HELIX_BACKEND_ORIGIN points to a live Render URL.'
  }
  if (status === 503) {
    return 'API not configured on Vercel — set HELIX_BACKEND_ORIGIN to your Render service URL and redeploy.'
  }
  if (ex.message === 'Network Error' || ex.code === 'ERR_NETWORK') {
    return 'Cannot reach the API. Deploy helix-backend (Render render.yaml) and set HELIX_BACKEND_ORIGIN on Vercel.'
  }
  return ex.message || 'Request failed'
}

/** First error from guest → demo fallback chain. */
export function formatGuestSessionError(guestEx, loginEx) {
  return formatApiError(guestEx) || formatApiError(loginEx) || 'Could not start a session — check the API is running.'
}
