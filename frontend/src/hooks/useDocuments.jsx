import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { listDocuments, deleteDocument } from '../services/documentApi'
import { describeError } from '../utils/errors'

const DocumentsContext = createContext(null)

// One shared document list for the sidebar, chat and documents page.
// Polls every 4s while any document is still processing.
export function DocumentsProvider({ children }) {
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    try {
      setDocs(await listDocuments())
      setError('')
    } catch (err) {
      setError(describeError(err, 'Could not load your documents.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const processing = docs.some((d) => d.status === 'processing')
  useEffect(() => {
    if (!processing) return undefined
    const timer = setInterval(refresh, 4000)
    return () => clearInterval(timer)
  }, [processing, refresh])

  const remove = useCallback(
    async (id) => {
      await deleteDocument(id)
      await refresh()
    },
    [refresh],
  )

  const value = useMemo(() => ({ docs, loading, error, refresh, remove }), [docs, loading, error, refresh, remove])
  return <DocumentsContext.Provider value={value}>{children}</DocumentsContext.Provider>
}

export function useDocuments() {
  return useContext(DocumentsContext)
}
