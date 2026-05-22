/** Default Render API from root `render.yaml` service name `helix-demo`. Override via HELIX_BACKEND_ORIGIN on Vercel. */
export const HELIX_DEFAULT_BACKEND_ORIGIN = 'https://helix-demo.onrender.com'

export function resolveBackendOrigin(env = process.env) {
  const fromEnv = (env.HELIX_BACKEND_ORIGIN || '').trim().replace(/\/$/, '')
  return fromEnv || HELIX_DEFAULT_BACKEND_ORIGIN
}
