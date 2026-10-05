// The backend sends UTC timestamps without a timezone suffix
// (e.g. "2026-09-30T05:03:11.123456"). Without a suffix JavaScript would read
// them as local time, so treat a missing offset as UTC.
export function parseServerDate(iso) {
  if (!iso) return null
  const hasOffset = /([zZ]|[+-]\d{2}:?\d{2})$/.test(iso)
  const d = new Date(hasOffset ? iso : `${iso}Z`)
  return Number.isNaN(d.getTime()) ? null : d
}

export function formatDate(iso) {
  const d = parseServerDate(iso)
  return d ? d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }) : ''
}

export function formatTime(iso) {
  const d = parseServerDate(iso)
  return d ? d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }) : ''
}

export function dayGroup(iso, now = new Date()) {
  const d = parseServerDate(iso)
  if (!d) return 'Older'
  const startOfDay = (x) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime()
  const diff = Math.round((startOfDay(now) - startOfDay(d)) / 86400000)
  if (diff <= 0) return 'Today'
  if (diff === 1) return 'Yesterday'
  return 'Older'
}
