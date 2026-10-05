import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { DocumentsProvider } from '../../hooks/useDocuments.jsx'
import useLocalStorage from '../../hooks/useLocalStorage.js'
import Header from './Header.jsx'
import Sidebar from './Sidebar.jsx'
import GenerationNotification from '../common/GenerationNotification.jsx'

export default function AppShell({ children }) {
  const [collapsed, setCollapsed] = useLocalStorage(
    'carag_sidebar_collapsed',
    false,
  )

  const [mobileOpen, setMobileOpen] = useState(false)
  const { pathname } = useLocation()

  useEffect(() => {
    setMobileOpen(false)
  }, [pathname])

  useEffect(() => {
    if (!mobileOpen) return undefined

    const onKey = (e) => {
      if (e.key === 'Escape') {
        setMobileOpen(false)
      }
    }

    document.addEventListener('keydown', onKey)

    return () => {
      document.removeEventListener('keydown', onKey)
    }
  }, [mobileOpen])

  return (
    <DocumentsProvider>
      <div
        className={
          'shell' + (collapsed ? ' is-collapsed' : '')
        }
      >
        <a
          className="skip-link"
          href="#main"
        >
          Skip to content
        </a>

        <Sidebar
          collapsed={collapsed}
          onToggleCollapsed={() =>
            setCollapsed((c) => !c)
          }
          mobileOpen={mobileOpen}
          onCloseMobile={() => setMobileOpen(false)}
        />

        {mobileOpen && (
          <div
            className="scrim"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
        )}

        <div className="shell-main">
          <Header
            onOpenMenu={() => setMobileOpen(true)}
          />

          <GenerationNotification />

          <main
            id="main"
            className="shell-content"
            tabIndex={-1}
          >
            {children}
          </main>
        </div>
      </div>
    </DocumentsProvider>
  )
}