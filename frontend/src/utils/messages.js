// Chat messages, and a small per-browser memory of which mode produced an answer
// (the backend does not store the mode).

const KEY = 'carag_message_modes'
const MAX = 500

function readMap() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '{}')
  } catch {
    return {}
  }
}

export function rememberMode(messageId, mode) {
  if (!messageId) return
  try {
    const map = readMap()
    map[messageId] = mode
    const keys = Object.keys(map)
    if (keys.length > MAX) keys.slice(0, keys.length - MAX).forEach((k) => delete map[k])
    localStorage.setItem(KEY, JSON.stringify(map))
  } catch {
    /* storage unavailable: mode simply stays unknown */
  }
}

export function recallMode(messageId) {
  if (!messageId) return undefined
  const mode = readMap()[messageId]
  return mode === 'carag' || mode === 'traditional' ? mode : undefined
}

// History rows: { id, role, content, created_at }.
export function normalizeHistory(rows) {
  return rows.map((m) => ({
    key: m.id,
    id: m.id,
    role: m.role,
    content: m.content,
    createdAt: m.created_at,
    mode: m.role === 'assistant' ? recallMode(m.id) : undefined,
  }))
}
