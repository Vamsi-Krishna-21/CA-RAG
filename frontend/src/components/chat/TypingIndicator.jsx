export default function TypingIndicator({ mode, stage }) {
  const defaultMessage =
    mode === 'carag'
      ? 'CA-RAG is verifying the evidence…'
      : 'Traditional RAG is verifying the evidence…'

  const message = stage || defaultMessage

  return (
    <div className="typing-indicator">
      <div className="typing-indicator-content">
        <span
          className="typing-indicator-dots"
          aria-hidden="true"
        >
          <span />
          <span />
          <span />
        </span>

        <span className="typing-indicator-text">
          {message}
        </span>
      </div>
    </div>
  )
}