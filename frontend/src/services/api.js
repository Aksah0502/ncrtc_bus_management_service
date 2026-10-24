const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')

async function readError(response) {
  const data = await response.json().catch(() => null)
  if (typeof data?.detail === 'string') return data.detail
  if (Array.isArray(data?.detail)) return data.detail.map((item) => item.msg).filter(Boolean).join(', ')
  return `Request failed (${response.status}). Please try again.`
}

async function apiRequest(path, { token, signal, ...options } = {}) {
  const headers = new Headers(options.headers || {})
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers, signal })
  if (!response.ok) throw new Error(await readError(response))
  if (response.status === 204) return null
  return response.json()
}

export async function signIn(username, password) {
  const body = new URLSearchParams({ username, password })
  return apiRequest('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
}

export async function getCurrentUser(accessToken) {
  return apiRequest('/auth/me', { token: accessToken })
}

function depotQuery(depotId) {
  return depotId ? `?depot_id=${encodeURIComponent(depotId)}` : ''
}

export function getFleetVehicles(token, depotId) {
  return apiRequest(`/fleet/vehicles${depotQuery(depotId)}`, { token })
}

export function getDepots(token) {
  return apiRequest('/fleet/depots', { token })
}

export function getLiveLocations(token, depotId, signal) {
  return apiRequest(`/vehicles/live-locations${depotQuery(depotId)}`, { token, signal })
}

export function getLiveDetails(token, vehicleId, signal) {
  return apiRequest(`/vehicles/${encodeURIComponent(vehicleId)}/live-details`, { token, signal })
}
