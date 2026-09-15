/*
 * The Ask stream.
 *
 * Server-sent events over POST, so fetch rather than EventSource. The three
 * event types arrive in order: meta, then token repeatedly, then done.
 */

export async function askStream(token, question, handlers, signal) {
  const response = await fetch('/api/ask', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ question }),
    signal,
  })

  if (!response.ok || !response.body) {
    const payload = await response.json().catch(() => null)
    throw new Error(
      (payload && payload.detail) || 'DineAstra could not reach its own API.',
    )
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  // SSE frames are separated by a blank line; a frame may arrive split across
  // reads, so only whole frames are parsed and the remainder is carried over.
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let boundary = buffer.indexOf('\n\n')
    while (boundary !== -1) {
      const frame = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)
      dispatch(frame, handlers)
      boundary = buffer.indexOf('\n\n')
    }
  }
}

function dispatch(frame, handlers) {
  let name = null
  const dataLines = []

  for (const line of frame.split('\n')) {
    if (line.startsWith('event: ')) name = line.slice(7).trim()
    else if (line.startsWith('data: ')) dataLines.push(line.slice(6))
  }

  if (!name || dataLines.length === 0) return

  let payload
  try {
    payload = JSON.parse(dataLines.join('\n'))
  } catch {
    return
  }

  if (name === 'meta') handlers.onMeta?.(payload)
  else if (name === 'token') handlers.onToken?.(payload.text)
  else if (name === 'done') handlers.onDone?.(payload)
}
