export default function AuthLayout({ title, subtitle, children, footer }) {
  return (
    <main className="auth">
      <div className="auth-inner">
        <div className="auth-brand">
          <span className="wordmark auth-wordmark">CA-RAG</span>
          <p>Context-Aware Research Assistant</p>
        </div>
        <div className="auth-card">
          <h1>{title}</h1>
          {subtitle && <p className="auth-sub">{subtitle}</p>}
          {children}
        </div>
        {footer && <div className="auth-footer">{footer}</div>}
      </div>
    </main>
  )
}
