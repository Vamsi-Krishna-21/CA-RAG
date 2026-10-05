import { useCallback, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext.jsx'
import useDismiss from '../../hooks/useDismiss.js'
import Icon from '../common/Icon.jsx'

export default function UserMenu() {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const close = useCallback(() => setOpen(false), [])
  useDismiss(ref, open, close)

  const initial = (user?.name || '?').trim().charAt(0).toUpperCase()

  return (
    <div className="menu-wrap" ref={ref}>
      <button
        type="button"
        className="avatar-btn"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Account menu"
        onClick={() => setOpen((o) => !o)}
      >
        {initial}
      </button>
      {open && (
        <div className="menu" role="menu">
          <div className="menu-head">
            <div className="menu-name">{user?.name}</div>
            <div className="menu-email">{user?.email}</div>
          </div>
          <Link className="menu-item" role="menuitem" to="/settings" onClick={close}>
            <Icon name="settings" size={16} /> Settings
          </Link>
          <button type="button" className="menu-item" role="menuitem" onClick={logout}>
            <Icon name="logout" size={16} /> Log out
          </button>
        </div>
      )}
    </div>
  )
}
