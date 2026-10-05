import { useId, useState } from 'react'
import Icon from '../common/Icon.jsx'

export default function SourceCard({ citation, index }) {
  const [open, setOpen] = useState(false)
  const detailsId = useId()

  return (
    <li className={'source' + (open ? ' is-open' : '')}>
      <button
        type="button"
        className="source-head"
        aria-expanded={open}
        aria-controls={detailsId}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="source-index">{index + 1}</span>

        <span className="source-main">
          <span className="source-name">{citation.document_name}</span>

          <span className="source-meta">
            Page {citation.page}
            {citation.section ? ` · ${citation.section}` : ''}
          </span>
        </span>

        <Icon
          name="chevronDown"
          size={16}
          className="source-chevron"
        />
      </button>

      <div id={detailsId} className="source-details" hidden={!open}>
        <dl>
          <dt>Document</dt>
          <dd>{citation.document_name}</dd>

          <dt>Page</dt>
          <dd>{citation.page}</dd>

          {citation.section && (
            <>
              <dt>Section</dt>
              <dd>{citation.section}</dd>
            </>
          )}

          <dt>Chunk ID</dt>
          <dd className="source-chunk">{citation.chunk_id}</dd>
        </dl>
      </div>
    </li>
  )
}