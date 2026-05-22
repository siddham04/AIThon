/** Demo dependency tree — Login → Auth API, User DB, JWT Service */

export const LOGIN_DEPENDENCY_GRAPH = {
  nodes: [
    {
      id: 'login',
      type: 'root',
      position: { x: 220, y: 20 },
      data: { label: 'Login' },
    },
    {
      id: 'auth-api',
      type: 'service',
      position: { x: 80, y: 140 },
      data: { label: 'Auth API' },
    },
    {
      id: 'user-db',
      type: 'data',
      position: { x: 220, y: 140 },
      data: { label: 'User DB' },
    },
    {
      id: 'jwt',
      type: 'service',
      position: { x: 360, y: 140 },
      data: { label: 'JWT Service' },
    },
  ],
  edges: [
    { id: 'e-login-auth', source: 'login', target: 'auth-api', animated: true },
    { id: 'e-login-db', source: 'login', target: 'user-db', animated: true },
    { id: 'e-login-jwt', source: 'login', target: 'jwt', animated: true },
  ],
}
