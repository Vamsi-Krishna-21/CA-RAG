import { useState } from 'react'
import { Link } from 'react-router-dom'
import { describeError } from '../../utils/errors'
import { formatDate } from '../../utils/dates'
import Icon from '../common/Icon.jsx'
import StatusBadge from './StatusBadge.jsx'

export default function DocumentRow({ doc, onDelete }) {
  const [confirming, setConfirming] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState('')

  const remove = async () => {
    setDeleting(true)
    setError('')
    try {
      await onDelete(doc.id)
    } catch (err) {
      setError(describeError(err, 'Could not delete this document.'))
      setDeleting(false)
    }
  }

  return (
    <li className="doc-row">
      <div className="doc-main">
        <span className="doc-icon"><Icon name="doc" size={20} /></span>
        <div className="doc-info">
          <div className="doc-name" title={doc.filename}>{doc.filename}</div>
          <div className="doc-meta">
            PDF · {doc.pages} {doc.pages === 1 ? 'page' : 'pages'} · Uploaded {formatDate(doc.uploaded_at)}
          </div>
          {doc.status === 'failed' && (
            <div className="doc-meta doc-failed">Processing failed. Delete it and upload the file again.</div>
          )}
        </div>
        <StatusBadge status={doc.status} />
        <div className="doc-actions">
          {doc.status === 'ready' && (
            <Link className="btn btn-sm" to={`/?document=${doc.id}`}>Chat</Link>
          )}
          {!confirming && (
            <button type="button" className="btn btn-sm btn-ghost" onClick={() => setConfirming(true)}>Delete</button>
          )}
        </div>
      </div>

      {confirming && (
        <div className="doc-confirm" role="alertdialog" aria-label={`Delete ${doc.filename}`}>
          <span>Delete this document and its chat history? This can't be undone.</span>
          <span className="doc-confirm-actions">
            <button type="button" className="btn btn-sm" onClick={() => setConfirming(false)} disabled={deleting}>Cancel</button>
            <button type="button" className="btn btn-sm btn-danger" onClick={remove} disabled={deleting}>
              {deleting ? 'Deleting…' : 'Delete'}
            </button>
          </span>
        </div>
      )}
      {error && <p className="error-text doc-error" role="alert">{error}</p>}
    </li>
  )
}
