import Icon from './Icon.jsx'

export default function ErrorNotice({ title = 'Something went wrong', message, onRetry, retryLabel = 'Try again' }) {
  return (
    <div className="notice tone-bad" role="alert">
      <Icon name="alert" className="notice-icon" />
      <div className="notice-body">
        <div className="notice-title">{title}</div>
        {message && <div className="notice-text">{message}</div>}
        {onRetry && (
          <div className="notice-actions">
            <button type="button" className="btn btn-sm" onClick={onRetry}>
              <Icon name="retry" size={14} /> {retryLabel}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
