import { useCallback, useState } from 'react'

import { uploadDocument } from '../services/documentApi'

import { describeError } from '../utils/errors'

const SUPPORTED_EXTENSIONS = [
  '.pdf',
  '.docx',
  '.pptx',
  '.ppt',
  '.xlsx',
  '.xls',
  '.csv',
  '.txt',
  '.md',
  '.json',
]

export default function useUpload(onDone) {
  const [progress, setProgress] = useState(null) // null = idle, 0..100 = uploading

  const [error, setError] = useState('')

  const upload = useCallback(
    async (file) => {
      if (!file) return

      const extension = file.name
        .slice(file.name.lastIndexOf('.'))
        .toLowerCase()

      if (!SUPPORTED_EXTENSIONS.includes(extension)) {
        setError(
          'Unsupported file format. Supported: PDF, DOCX, PPTX, PPT, XLSX, XLS, CSV, TXT, MD, JSON.',
        )
        return
      }

      setError('')
      setProgress(0)

      try {
        const result = await uploadDocument(file, (p) =>
          setProgress(Number.isFinite(p) ? p : 0),
        )

        if (onDone) await onDone(result)
      } catch (err) {
        setError(describeError(err, 'Upload failed.'))
      } finally {
        setProgress(null)
      }
    },
    [onDone],
  )

  return {
    progress,
    error,
    upload,
    clearError: () => setError(''),
  }
}