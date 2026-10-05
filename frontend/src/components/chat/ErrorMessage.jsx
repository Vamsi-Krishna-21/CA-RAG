import ErrorNotice from '../common/ErrorNotice.jsx'

export default function ErrorMessage({ message, onRetry }) {
  return (
    <div className="msg msg-assistant">
      <ErrorNotice
        title="No answer was generated"
        message={message.content.message}
        onRetry={() => onRetry(message)}
        retryLabel="Retry"
      />
    </div>
  )
}
