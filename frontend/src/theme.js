const STORAGE_KEY = 'fams-theme'

export function getStoredTheme() {
  return localStorage.getItem(STORAGE_KEY)
}

export function applyTheme(theme) {
  if (theme) {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem(STORAGE_KEY, theme)
  } else {
    document.documentElement.removeAttribute('data-theme')
    localStorage.removeItem(STORAGE_KEY)
  }
}

export function getActiveTheme() {
  const stored = getStoredTheme()
  if (stored) return stored
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}
