const BASE = '/api'

// ── Token storage ─────────────────────────────────────────────────────────────
const TOKEN_KEY = 'trialmatch_token'
export const getToken    = ()  => localStorage.getItem(TOKEN_KEY)
export const setToken    = (t) => localStorage.setItem(TOKEN_KEY, t)
export const clearToken  = ()  => localStorage.removeItem(TOKEN_KEY)

let _onUnauthorized = null
export function setUnauthorizedHandler(fn) { _onUnauthorized = fn }

// ── Base fetch helpers ────────────────────────────────────────────────────────
function authHeader() {
  const t = getToken()
  return t ? { Authorization: `Bearer ${t}` } : {}
}

async function _json(res) {
  if (res.status === 401) {
    clearToken()
    _onUnauthorized?.()
    throw new Error('Session expired. Please sign in again.')
  }
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `Server error ${res.status}`)
  }
  return res.json()
}

async function _get(path) {
  return _json(await fetch(`${BASE}${path}`, { headers: authHeader() }))
}

async function _post(path, body) {
  return _json(await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify(body),
  }))
}

async function _del(path) {
  return _json(await fetch(`${BASE}${path}`, { method: 'DELETE', headers: authHeader() }))
}

// ── Auth ──────────────────────────────────────────────────────────────────────
export async function register(email, password, name) {
  const res = await _post('/auth/register', { email, password, name })
  setToken(res.token)
  return res
}

export async function login(email, password) {
  const res = await _post('/auth/login', { email, password })
  setToken(res.token)
  return res
}

export async function getMe() {
  return _get('/auth/me')
}

export function logout() {
  clearToken()
}

// ── Match ─────────────────────────────────────────────────────────────────────
export async function startMatch(form) {
  const { job_id } = await _post('/match/start', form)
  return job_id
}

export function streamMatch(jobId, { onLog, onDone, onError }) {
  const token = getToken()
  const url   = `${BASE}/match/stream/${jobId}${token ? `?token=${token}` : ''}`
  const es    = new EventSource(url)
  es.onmessage = (e) => {
    const msg = JSON.parse(e.data)
    if      (msg.type === 'log')   onLog(msg.line)
    else if (msg.type === 'done')  { onDone(msg);          es.close() }
    else if (msg.type === 'error') { onError(msg.message); es.close() }
  }
  es.onerror = () => { onError('Connection lost'); es.close() }
  return es
}

export async function getExamples() {
  return _json(await fetch(`${BASE}/examples`))
}

// ── Patients ──────────────────────────────────────────────────────────────────
export const getSavedPatients = ()       => _get('/patients')
export const savePatient      = (data)   => _post('/patients', data)
export const deletePatient    = (id)     => _del(`/patients/${id}`)

// ── History ───────────────────────────────────────────────────────────────────
export const getHistory    = ()    => _get('/history')
export const saveHistory   = (d)   => _post('/history', d)
export const deleteHistory = (id)  => _del(`/history/${id}`)

// ── Notes ─────────────────────────────────────────────────────────────────────
export const getNotes   = ()    => _get('/notes')
export const saveNote   = (d)   => _post('/notes', d)
export const deleteNote = (id)  => _del(`/notes/${id}`)

// ── Bookmarks ─────────────────────────────────────────────────────────────────
export const getBookmarks    = ()      => _get('/bookmarks')
export const addBookmark     = (data)  => _post('/bookmarks', data)
export const removeBookmark  = (id)    => _del(`/bookmarks/${id}`)

// ── Feedback ──────────────────────────────────────────────────────────────────
export const getFeedback     = ()      => _get('/feedback')
export const submitFeedback  = (data)  => _post('/feedback', data)
export const deleteFeedback  = (id)    => _del(`/feedback/${id}`)

// ── CSV Export ────────────────────────────────────────────────────────────────
export async function exportCsv(resultPayload) {
  const res = await fetch(`${BASE}/export/csv`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify(resultPayload),
  })
  if (!res.ok) throw new Error('CSV export failed')
  const blob = await res.blob()
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href = url; a.download = 'trialmatch_results.csv'; a.click()
  URL.revokeObjectURL(url)
}

// ── PDF Export ────────────────────────────────────────────────────────────────
export async function exportPdf(resultPayload) {
  const res = await fetch(`${BASE}/export/pdf`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify(resultPayload),
  })
  if (!res.ok) throw new Error('PDF export failed')
  const blob = await res.blob()
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href = url; a.download = 'trialmatch_report.pdf'; a.click()
  URL.revokeObjectURL(url)
}
