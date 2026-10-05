import { useId, useState } from 'react'
import Icon from '../common/Icon.jsx'
import { clampPct } from '../../utils/verification.js'

export default function EvidenceAlignment({ evidence }) {
  const [open, setOpen] = useState(false)
  const id = useId()

  return (
    <div className="evidence">
      <button type="button" className="evidence-toggle" aria-expanded={open} aria-controls={id} onClick={() => setOpen((o) => !o)}>
        <Icon name="chevronRight" size={15} className="evidence-chevron" />
        Evidence alignment
        <span className="evidence-count">{evidence.length} {evidence.length === 1 ? 'chunk' : 'chunks'}</span>
      </button>
      <ul id={id} className="evidence-list" hidden={!open}>
        {evidence.map((e) => {
          const pct = clampPct(e.similarity * 100)
          return (
            <li key={e.chunk_id}>
              <span className="evidence-chunk" title={e.chunk_id}>{e.chunk_id}</span>
              <span className="evidence-bar" aria-hidden="true">
                <span className="evidence-fill" style={{ width: `${pct}%` }} />
              </span>
              <span className="evidence-pct">{pct}%</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
