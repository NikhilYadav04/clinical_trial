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

export async function submitMatchStream(form, { onStep, onLog, onResult, onError }) {
  const res = await fetch(`${BASE}/match/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(form),
  })
  if (!res.ok) {
    const err = await res.text()
    throw new Error(err || `Server error ${res.status}`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop()
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      try {
        const event = JSON.parse(line.slice(6))
        if (event.type === 'step')   onStep?.(event)
        if (event.type === 'log')    onLog?.(event)
        if (event.type === 'result') onResult?.(event.data)
        if (event.type === 'error')  onError?.(new Error(event.message))
      } catch { /* ignore parse errors */ }
    }
  }
}

export async function getExamples() {
  const res = await fetch(`${BASE}/examples`)
  if (!res.ok) throw new Error('Failed to load examples')
  return res.json()
}
