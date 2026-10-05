import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext.jsx'
import Icon from '../common/Icon.jsx'
import SidebarDocuments from '../sidebar/SidebarDocuments.jsx'

const NAV = [
  {
    to: '/',
    label: 'Chat',
    icon: 'chat',
    isActive: (p) => p === '/' || p === '/chat',
  },
  {
    to: '/documents',
    label: 'Documents',
    icon: 'doc',
    isActive: (p) => p.startsWith('/documents'),
  },
  {
    to: '/history',
    label: 'History',
    icon: 'history',
    isActive: (p) => p.startsWith('/history'),
  },
  {
    to: '/settings',
    label: 'Settings',
    icon: 'settings',
    isActive: (p) => p.startsWith('/settings'),
  },
]

export default function Sidebar({
  collapsed,
  onToggleCollapsed,
  mobileOpen,
  onCloseMobile,
}) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const [params] = useSearchParams()

  const onChat =
  pathname === '/' ||
  pathname === '/chat'

  const activeConversationId =
      onChat
      ? params.get('conversation')
      : null

  const newChat = () => {
    navigate('/', {
      state: {
        fresh: Date.now(),
      },
    })

    onCloseMobile()
  }

  return (
    <aside
      id="app-sidebar"
      className={'sidebar' + (mobileOpen ? ' is-open' : '')}
      aria-label="Primary"
    >
      <div className="side-top">
        <span className="wordmark side-brand">CA-RAG</span>

        <button
          type="button"
          className="icon-btn side-collapse"
          onClick={onToggleCollapsed}
          aria-label={
            collapsed
              ? 'Expand sidebar'
              : 'Collapse sidebar'
          }
          aria-expanded={!collapsed}
          aria-controls="app-sidebar"
        >
          <Icon name="panel" />
        </button>

        <button
          type="button"
          className="icon-btn side-close"
          onClick={onCloseMobile}
          aria-label="Close navigation"
        >
          <Icon name="close" />
        </button>
      </div>

      <button
        type="button"
        className="side-new"
        onClick={newChat}
        title="New chat"
      >
        <Icon name="plus" size={16} />
        <span className="side-label">New chat</span>
      </button>

      <nav className="side-nav" aria-label="Main">
        {NAV.map((item) => {
          const active = item.isActive(pathname)

          return (
            <Link
              key={item.to}
              to={item.to}
              className={
                'side-link' +
                (active ? ' active' : '')
              }
              aria-current={
                active ? 'page' : undefined
              }
              title={item.label}
              onClick={onCloseMobile}
            >
              <Icon
                name={item.icon}
                size={18}
              />

              <span className="side-label">
                {item.label}
              </span>
            </Link>
          )
        })}
      </nav>

      <div className="side-scroll">
        <SidebarDocuments
          activeId={activeConversationId}
          onNavigate={onCloseMobile}
        />
      </div>

      <div className="side-user">
        <div
          className="side-avatar"
          aria-hidden="true"
        >
          {(user?.name || '?')
            .trim()
            .charAt(0)
            .toUpperCase()}
        </div>

        <div className="side-user-text">
          <div className="side-user-name">
            {user?.name}
          </div>

          <div className="side-user-email">
            {user?.email}
          </div>
        </div>

        <Link
          to="/settings"
          className="icon-btn side-user-action"
          aria-label="Settings"
          title="Settings"
          onClick={onCloseMobile}
        >
          <Icon
            name="settings"
            size={17}
          />
        </Link>

        <button
          type="button"
          className="icon-btn side-user-action"
          onClick={logout}
          aria-label="Log out"
          title="Log out"
        >
          <Icon
            name="logout"
            size={17}
          />
        </button>
      </div>
    </aside>
  )
}