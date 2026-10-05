import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import useUpload from '../../hooks/useUpload.js'

// variant: 'no-docs' | 'choose' | 'ask' | 'unavailable'
export default function ChatEmptyState({
  variant,
  docs = [],
  docName,
  note,
  onSelect,
  onUpload,
}) {
  const inputRef = useRef(null)

  const [selectedIds, setSelectedIds] = useState([])

  const {
    progress,
    error: uploadError,
    upload,
  } = useUpload()

  const toggleDocument = (id) => {
    setSelectedIds((current) =>
      current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id],
    )
  }

  const handleUpload = async (event) => {
    const file = event.target.files?.[0]

    event.target.value = ''

    if (!file) return

    await upload(file)
    onUpload?.()
  }

  const handleStartChat = () => {
    if (selectedIds.length === 0) return

    onSelect?.(selectedIds)
  }

  return (
    <div className="empty">
      <h1 className="empty-title wordmark">
        CA-RAG
      </h1>

      <p className="empty-lead">
        Ask questions about your research papers.
      </p>

      {variant === 'no-docs' && (
        <>
          <p className="empty-body">
            Upload a paper and ask evidence-grounded
            questions, with source citations and verification.
          </p>

          <button
            type="button"
            className="btn btn-primary"
            onClick={() => inputRef.current?.click()}
            disabled={progress !== null}
          >
            {progress !== null
              ? `Uploading ${progress}%`
              : 'Upload document'}
          </button>

          <input
            ref={inputRef}
            type="file"
            hidden
            accept=".pdf,.docx,.pptx,.ppt,.xlsx,.xls,.csv,.txt,.md,.json"
            onChange={handleUpload}
          />

          {uploadError && (
            <p
              className="empty-body"
              role="alert"
            >
              {uploadError}
            </p>
          )}
        </>
      )}

      {variant === 'choose' && (
        <>
          <p className="empty-body">
            Select one or more documents to start a new chat.
          </p>

          {docs.length > 0 && (
            <div
              className="empty-chips"
              role="group"
              aria-label="Select documents"
            >
              {docs.slice(0, 12).map((d) => {
                const selected =
                  selectedIds.includes(d.id)

                return (
                  <button
                    key={d.id}
                    type="button"
                    className={
                      'chip' +
                      (selected ? ' selected' : '')
                    }
                    aria-pressed={selected}
                    onClick={() =>
                      toggleDocument(d.id)
                    }
                    title={d.filename}
                  >
                    {selected && '✓ '}
                    {d.filename}
                  </button>
                )
              })}
            </div>
          )}

          <button
            type="button"
            className="btn btn-primary"
            disabled={selectedIds.length === 0}
            onClick={handleStartChat}
          >
            Start chat
            {selectedIds.length > 0
              ? ` (${selectedIds.length})`
              : ''}
          </button>

          <button
            type="button"
            className="empty-link"
            onClick={() =>
              inputRef.current?.click()
            }
            disabled={progress !== null}
          >
            {progress !== null
              ? `Uploading ${progress}%`
              : 'Upload another document'}
          </button>

          <input
            ref={inputRef}
            type="file"
            hidden
            accept=".pdf,.docx,.pptx,.ppt,.xlsx,.xls,.csv,.txt,.md,.json"
            onChange={handleUpload}
          />

          {uploadError && (
            <p
              className="empty-body"
              role="alert"
            >
              {uploadError}
            </p>
          )}
        </>
      )}

      {variant === 'ask' && (
        <p className="empty-body">
          Ask anything about{' '}
          <strong className="empty-doc">
            {docName}
          </strong>
          . Answers cite the pages they come from and show
          how well the evidence supports them.
        </p>
      )}

      {variant === 'unavailable' && (
        <>
          <p className="empty-body">
            {note}
          </p>

          <Link
            className="btn"
            to="/documents"
          >
            Go to documents
          </Link>
        </>
      )}
    </div>
  )
}