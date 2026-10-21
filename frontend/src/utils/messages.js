// Chat messages, and a small per-browser memory of which mode produced an answer.
// The backend stores the mode on assistant messages when available.

const KEY = 'carag_message_modes'
const MAX = 500

function readMap() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '{}')
  } catch {
    return {}
  }
}

function normalizeMode(mode) {
  if (!mode) return undefined

  switch (String(mode).trim().toLowerCase()) {
    case 'enhanced':
    case 'enhanced_carag':
    case 'enhance_ca_rag':
      return 'enhanced_carag'
    case 'ca_rag':
    case 'carag':
      return 'carag'
    case 'traditional':
    case 'traditional_rag':
      return 'traditional_rag'
    default:
      return undefined
  }
}

export function rememberMode(messageIdOrMode, maybeMode) {
  if (maybeMode === undefined) {
    const normalized = normalizeMode(messageIdOrMode)
    if (normalized) {
      try {
        localStorage.setItem('carag_active_mode', normalized)
      } catch {
        /* storage unavailable */
      }
    }
    return
  }

  const messageId = messageIdOrMode
  const mode = maybeMode
  if (!messageId) return
  const normalized = normalizeMode(mode)
  if (!normalized) return

  try {
    const map = readMap()
    map[messageId] = normalized
    const keys = Object.keys(map)
    if (keys.length > MAX) keys.slice(0, keys.length - MAX).forEach((k) => delete map[k])
    localStorage.setItem(KEY, JSON.stringify(map))
  } catch {
    /* storage unavailable: mode simply stays unknown */
  }
}

export function recallActiveMode() {
  try {
    return normalizeMode(localStorage.getItem('carag_active_mode')) || 'enhanced_carag'
  } catch {
    return 'enhanced_carag'
  }
}

export function recallMode(messageId) {
  if (!messageId) return undefined
  const mode = normalizeMode(readMap()[messageId])
  return mode
}

// History rows: { id, role, content, created_at }.
export function normalizeHistory(rows) {
  return rows.map((m) => ({
    key: m.id,
    id: m.id,
    role: m.role,
    content: m.content,
    createdAt: m.created_at,
    mode:
      m.role === 'assistant'
        ? (m.content?.mode || recallMode(m.id) || 'enhanced_carag')
        : undefined,
  }))
}
