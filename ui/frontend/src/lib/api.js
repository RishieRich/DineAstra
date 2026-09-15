/*
 * The only place the frontend talks to the API.
 *
 * Requests go to /api and Vite proxies them to port 8000, so there is no
 * host or port written down anywhere in the frontend.
 */

const TOKEN_KEY = 'darpan.token'
const USER_KEY = 'darpan.user'

export function readStoredSession() {
  try {
    const token = window.localStorage.getItem(TOKEN_KEY)
    const rawUser = window.localStorage.getItem(USER_KEY)
    if (!token || !rawUser) return null
    return { token, user: JSON.parse(rawUser) }
  } catch {
    return null
  }
}

export function storeSession(session) {
  try {
    window.localStorage.setItem(TOKEN_KEY, session.token)
    window.localStorage.setItem(USER_KEY, JSON.stringify(session.user))
  } catch {
    /* a browser with storage blocked still gets a working session in memory */
  }
}

export function clearSession() {
  try {
    window.localStorage.removeItem(TOKEN_KEY)
    window.localStorage.removeItem(USER_KEY)
  } catch {
    /* nothing to clean up */
  }
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request(path, { method = 'GET', body, token } = {}) {
  const headers = { Accept: 'application/json' }
  if (body) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`

  let response
  try {
    response = await fetch(path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError(
      'The Darpan API is not answering. Start it with: uvicorn ui.backend.main:app --port 8000',
      0,
    )
  }

  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    const detail =
      (payload && (payload.detail || payload.message)) ||
      'Something went wrong reading the property data.'
    throw new ApiError(detail, response.status)
  }
  return payload
}

export const api = {
  login: (email, password) =>
    request('/api/auth/login', { method: 'POST', body: { email, password } }),
  health: () => request('/api/health'),
  overview: (token, date) =>
    request(`/api/overview${date ? `?date=${date}` : ''}`, { token }),
  banquetEvents: (token, segment) =>
    request(`/api/banquet/events${segment ? `?segment=${segment}` : ''}`, { token }),
  banquetEvent: (token, eventId) =>
    request(`/api/banquet/events/${eventId}`, { token }),
  submissions: (token, date) =>
    request(`/api/operations/submissions${date ? `?date=${date}` : ''}`, { token }),
  connections: (token) => request('/api/system/connections', { token }),
  metrics: (token) => request('/api/system/metrics', { token }),
  brainDocuments: (token) => request('/api/brain/documents', { token }),
  brainDocument: (token, docId) => request(`/api/brain/documents/${docId}`, { token }),
  brainAsk: (token, question, documentId) =>
    request('/api/brain/ask', {
      method: 'POST',
      token,
      body: { question, document_id: documentId ?? null },
    }),
  brainChecklist: (token, documentId) =>
    request('/api/brain/generate-checklist', {
      method: 'POST',
      token,
      body: { document_id: documentId },
    }),
  brainUpload: (token, file) => upload('/api/brain/upload', file, token),
}

/** Multipart upload: no JSON content type, the browser sets the boundary. */
async function upload(path, file, token) {
  const form = new FormData()
  form.append('file', file)

  let response
  try {
    response = await fetch(path, {
      method: 'POST',
      headers: { Accept: 'application/json', Authorization: `Bearer ${token}` },
      body: form,
    })
  } catch {
    throw new ApiError('The Darpan API is not answering.', 0)
  }

  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    throw new ApiError(
      (payload && payload.detail) || 'That file was not accepted.',
      response.status,
    )
  }
  return payload
}
