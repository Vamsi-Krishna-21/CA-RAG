import AssistantMessage from './AssistantMessage.jsx'
import ErrorMessage from './ErrorMessage.jsx'
import UserMessage from './UserMessage.jsx'

export default function MessageList({ messages, onRetry, children }) {
  return (
    <div className="messages" role="log" aria-live="polite" aria-relevant="additions">
      {messages.map((m) => {
        if (m.role === 'user') return <UserMessage key={m.key} message={m} />
        if (m.role === 'error') return <ErrorMessage key={m.key} message={m} onRetry={onRetry} />
        return <AssistantMessage key={m.key} message={m} />
      })}
      {children}
    </div>
  )
}
