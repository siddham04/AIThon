/** JWT storage — sessionStorage limits XSS persistence vs localStorage. */
const TOKEN_KEY = 'helix_token'
const USER_KEY = 'helix_user'

export function readAuthToken() {
  try {
    return sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY) || ''
  } catch {
    return ''
  }
}

export function writeAuthToken(token) {
  try {
    if (token) {
      sessionStorage.setItem(TOKEN_KEY, token)
      localStorage.removeItem(TOKEN_KEY)
    } else {
      sessionStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(TOKEN_KEY)
    }
  } catch {
    /* noop */
  }
}

export function readAuthUser() {
  try {
    const raw =
      sessionStorage.getItem(USER_KEY) || localStorage.getItem(USER_KEY) || 'null'
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export function writeAuthUser(user) {
  try {
    if (user) {
      sessionStorage.setItem(USER_KEY, JSON.stringify(user))
      localStorage.removeItem(USER_KEY)
    } else {
      sessionStorage.removeItem(USER_KEY)
      localStorage.removeItem(USER_KEY)
    }
  } catch {
    /* noop */
  }
}

export function clearAuthStorage() {
  writeAuthToken(null)
  writeAuthUser(null)
}
