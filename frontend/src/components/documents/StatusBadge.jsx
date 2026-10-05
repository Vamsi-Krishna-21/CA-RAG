const MAP = {
  ready: { label: 'Ready', tone: 'good' },
  processing: { label: 'Processing', tone: 'warn' },
  failed: { label: 'Failed', tone: 'bad' },
}

export default function StatusBadge({ status }) {
  const s = MAP[status] || { label: status, tone: 'warn' }
  return (
    <span className={'status tone-' + s.tone}>
      {status === 'processing' ? <span className="spinner" aria-hidden="true" /> : <span className="status-dot" aria-hidden="true" />}
      {s.label}
    </span>
  )
}
