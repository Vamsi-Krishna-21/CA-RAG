import ErrorNotice from '../components/common/ErrorNotice.jsx'
import Skeleton from '../components/common/Skeleton.jsx'
import DocumentRow from '../components/documents/DocumentRow.jsx'
import UploadDropzone from '../components/documents/UploadDropzone.jsx'
import { useDocuments } from '../hooks/useDocuments.jsx'
import useUpload from '../hooks/useUpload.js'

export default function Documents() {
  const { docs, loading, error, refresh, remove } = useDocuments()
  const { progress, error: uploadError, upload } = useUpload(refresh)

  return (
    <div className="page">
      <div className="page-inner">
        <header className="page-head">
          <h1 className="page-title">Documents</h1>
          <p className="page-sub">Upload research papers as PDFs. Each paper gets its own evidence index.</p>
        </header>

        <UploadDropzone progress={progress} error={uploadError} onFile={upload} />

        <section className="doc-section" aria-label="Your documents">
          {loading ? (
            <Skeleton lines={3} widths={['100%', '100%', '100%']} />
          ) : error && docs.length === 0 ? (
            <ErrorNotice title="Can't load your documents" message={error} onRetry={refresh} />
          ) : docs.length === 0 ? (
            <div className="empty-inline">
              <h2>No documents yet</h2>
              <p>Upload a PDF above to start asking questions about it.</p>
            </div>
          ) : (
            <>
              {error && <ErrorNotice title="Couldn't refresh the list" message={error} onRetry={refresh} />}
              <ul className="doc-list">
                {docs.map((d) => (
                  <DocumentRow key={d.id} doc={d} onDelete={remove} />
                ))}
              </ul>
            </>
          )}
        </section>
      </div>
    </div>
  )
}
