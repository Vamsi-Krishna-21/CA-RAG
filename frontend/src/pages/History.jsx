import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import ErrorNotice from '../components/common/ErrorNotice.jsx'
import Skeleton from '../components/common/Skeleton.jsx'
import { useDocuments } from '../hooks/useDocuments.jsx'
import { getHistory } from '../services/chatApi'
import { dayGroup, formatTime, parseServerDate } from '../utils/dates'
import { describeError } from '../utils/errors'

const GROUPS = ['Today', 'Yesterday', 'Older']

export default function History() {
  const { docs, loading: docsLoading, error: docsError, refresh } = useDocuments()
  const [items, setItems] = useState([])
  const [state, setState] = useState('loading') // loading | ready | error
  const [error, setError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  const docKey = docs.map((d) => d.id).join(',')

  // There is no "list conversations" endpoint: history is stored per document,
  // so fetch each document's messages and list the questions asked.
  useEffect(() => {
    if (docsLoading) return undefined
    if (docs.length === 0) {
      setItems([])
      setState('ready')
      return undefined
    }
    let cancelled = false
    setState('loading')
    Promise.allSettled(docs.map((d) => getHistory(d.id))).then((results) => {
      if (cancelled) return
      const collected = []
      let failures = 0
      results.forEach((r, i) => {
        if (r.status !== 'fulfilled') {
          failures += 1
          return
        }
        r.value
          .filter((m) => m.role === 'user')
          .forEach((m) =>
            collected.push({
              id: m.id,
              text: m.content?.query || '',
              createdAt: m.created_at,
              docId: docs[i].id,
              docName: docs[i].filename,
            }),
          )
      })
      if (failures === results.length) {
        setError(describeError(results[0].reason, 'Could not load your history.'))
        setState('error')
        return
      }
      collected.sort((a, b) => (parseServerDate(b.createdAt) || 0) - (parseServerDate(a.createdAt) || 0))
      setItems(collected)
      setState('ready')
    })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docsLoading, docKey, reloadKey])

  const grouped = useMemo(() => {
    const map = { Today: [], Yesterday: [], Older: [] }
    items.forEach((it) => map[dayGroup(it.createdAt)].push(it))
    return map
  }, [items])

  const retry = useCallback(() => {
    if (docsError) refresh()
    setReloadKey((k) => k + 1)
  }, [docsError, refresh])

  let body
  if (docsLoading || state === 'loading') {
    body = <Skeleton lines={5} widths={['70%', '55%', '80%', '48%', '66%']} />
  } else if (docsError && docs.length === 0) {
    body = <ErrorNotice title="Can't load your history" message={docsError} onRetry={retry} />
  } else if (state === 'error') {
    body = <ErrorNotice title="Can't load your history" message={error} onRetry={retry} />
  } else if (items.length === 0) {
    body = (
      <div className="empty-inline">
        <h2>No conversations yet</h2>
        <p>Questions you ask about your documents will appear here.</p>
        <Link className="btn" to="/">Start a chat</Link>
      </div>
    )
  } else {
    body = GROUPS.filter((g) => grouped[g].length > 0).map((g) => (
      <section key={g} className="history-group" aria-label={g}>
        <h2 className="history-heading">{g}</h2>
        <ul>
          {grouped[g].map((it) => (
            <li key={it.id}>
              <Link className="history-item" to={`/?document=${it.docId}&message=${it.id}`}>
                <span className="history-text">{it.text}</span>
                <span className="history-meta">
                  <span className="history-doc">{it.docName}</span>
                  <span>{formatTime(it.createdAt)}</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    ))
  }

  return (
    <div className="page">
      <div className="page-inner">
        <header className="page-head">
          <h1 className="page-title">History</h1>
          <p className="page-sub">Questions you've asked across your documents.</p>
        </header>
        {body}
      </div>
    </div>
  )
}
