const STORAGE_KEY = 'helix_onboarding_seen'

export function hasSeenOnboarding() {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === '1'
  } catch {
    return true
  }
}

export function markOnboardingSeen() {
  try {
    window.localStorage.setItem(STORAGE_KEY, '1')
  } catch {
    /* noop */
  }
}
