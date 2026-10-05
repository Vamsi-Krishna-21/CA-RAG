import { useRef, useState } from 'react'
import Icon from '../common/Icon.jsx'

export default function UploadDropzone({ progress, error, onFile }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)
  const uploading = progress !== null

  return (
    <div
      className={'dropzone' + (dragging ? ' is-dragging' : '')}
      onDragOver={(e) => {
        e.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragging(false)
        onFile(e.dataTransfer.files[0])
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        hidden
        onChange={(e) => {
          onFile(e.target.files[0])
          e.target.value = ''
        }}
      />
      {uploading ? (
        <div className="dropzone-progress" role="status">
          <div className="dropzone-progress-text">Uploading… {progress}%</div>
          <div className="progress" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress}>
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
        </div>
      ) : (
        <>
          <button type="button" className="btn btn-primary" onClick={() => inputRef.current?.click()}>
            <Icon name="upload" size={16} /> Upload document
          </button>
          <span className="dropzone-hint">or drop a PDF here</span>
        </>
      )}
      {error && <p className="error-text dropzone-error" role="alert">{error}</p>}
    </div>
  )
}
