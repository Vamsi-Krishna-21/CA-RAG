import { useState } from 'react'
import SourceCard from './SourceCard.jsx'

const INITIAL = 3

export default function SourceList({ citations }) {
  const [all, setAll] = useState(false)
  const shown = all ? citations : citations.slice(0, INITIAL)
  const hidden = citations.length - shown.length

  return (
    <section className="sources" aria-label="Sources">
      <h3 className="section-title">Sources</h3>
      <ul className="source-list">
        {shown.map((c, i) => (
          <SourceCard key={`${c.chunk_id}-${i}`} citation={c} index={i} />
        ))}
      </ul>
      {hidden > 0 && (
        <button type="button" className="link-btn" onClick={() => setAll(true)}>
          Show {hidden} more {hidden === 1 ? 'source' : 'sources'}
        </button>
      )}
    </section>
  )
}
