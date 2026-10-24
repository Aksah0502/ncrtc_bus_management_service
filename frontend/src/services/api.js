const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')

async function readError(response) {
  const data = await response.json().catch(() => null)
  if (typeof data?.detail === 'string') return data.detail
  if (Array.isArray(data?.detail)) return data.detail.map((item) => item.msg).filter(Boolean).join(', ')
  return `Request failed (${response.status}). Please try again.`
}

export async function signIn(username, password) {
  const body = new URLSearchParams({ username, password })
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
  if (!response.ok) throw new Error(await readError(response))
  return response.json()
}

export async function getCurrentUser(accessToken) {
  const response = await fetch(`${API_BASE_URL}/auth/me`, { headers: { Authorization: `Bearer ${accessToken}` } })
  if (!response.ok) throw new Error(await readError(response))
  return response.json()
}
