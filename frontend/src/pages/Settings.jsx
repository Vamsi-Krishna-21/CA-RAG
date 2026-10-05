import { useTheme } from '../context/ThemeContext.jsx'
import { useAuth } from '../context/AuthContext.jsx'

export default function Settings() {
  const { theme, toggleTheme } = useTheme()
  const { user } = useAuth()

  const choose = (value) => {
    if (value !== theme) toggleTheme()
  }

  return (
    <div className="page">
      <div className="page-inner">
        <header className="page-head">
          <h1 className="page-title">Settings</h1>
        </header>

        <section className="settings-section" aria-labelledby="set-appearance">
          <h2 id="set-appearance" className="settings-heading">Appearance</h2>
          <div className="setting-row">
            <div>
              <div className="setting-label">Theme</div>
              <div className="setting-hint">Choose a light or dark interface.</div>
            </div>
            <div className="segmented" role="radiogroup" aria-label="Theme">
              <button type="button" role="radio" aria-checked={theme === 'light'} onClick={() => choose('light')}>Light</button>
              <button type="button" role="radio" aria-checked={theme === 'dark'} onClick={() => choose('dark')}>Dark</button>
            </div>
          </div>
        </section>

        <section className="settings-section" aria-labelledby="set-account">
          <h2 id="set-account" className="settings-heading">Account</h2>
          <dl className="setting-list">
            <div className="setting-row">
              <dt className="setting-label">Name</dt>
              <dd>{user?.name}</dd>
            </div>
            {user?.username && (
              <div className="setting-row">
                <dt className="setting-label">Username</dt>
                <dd>{user.username}</dd>
              </div>
            )}
            <div className="setting-row">
              <dt className="setting-label">Email</dt>
              <dd>{user?.email}</dd>
            </div>
          </dl>
        </section>
      </div>
    </div>
  )
}
