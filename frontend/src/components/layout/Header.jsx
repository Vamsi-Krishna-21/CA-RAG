import { useTheme } from '../../context/ThemeContext.jsx'
import Icon from '../common/Icon.jsx'
import UserMenu from './UserMenu.jsx'

export default function Header({ onOpenMenu }) {
  const { theme, toggleTheme } = useTheme()
  const next = theme === 'light' ? 'dark' : 'light'

  return (
    <header className="header">
      <div className="header-left">
        <button type="button" className="icon-btn header-menu" onClick={onOpenMenu} aria-label="Open navigation">
          <Icon name="menu" />
        </button>
        <span className="wordmark header-brand">CA-RAG</span>
        <span className="header-tagline">Context-Aware Research Assistant</span>
      </div>
      <div className="header-right">
        <button type="button" className="icon-btn" onClick={toggleTheme} aria-label={`Switch to ${next} theme`}>
          <Icon name={theme === 'light' ? 'moon' : 'sun'} />
        </button>
        <UserMenu />
      </div>
    </header>
  )
}
