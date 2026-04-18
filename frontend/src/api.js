const BASE = '/api'

export async function submitMatch(form) {
  const res = await fetch(`${BASE}/match`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(form),
  })
  if (!res.ok) {
    const err = await res.text()
    throw new Error(err || `Server error ${res.status}`)
  }
  return res.json()
}

export async function getExamples() {
  const res = await fetch(`${BASE}/examples`)
  if (!res.ok) throw new Error('Failed to load examples')
  return res.json()
}
