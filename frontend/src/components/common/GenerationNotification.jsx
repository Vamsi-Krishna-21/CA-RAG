import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Icon from './Icon.jsx'
import { useChatGeneration } from '../../context/ChatGenerationContext.jsx'

export default function GenerationNotification() {
  const navigate = useNavigate()
  const {
    notifications,
    dismissNotification,
  } = useChatGeneration()

  const notification = Array.isArray(notifications)
  ? notifications[0]
  : null

  useEffect(() => {
    if (!notification) return undefined

    const timer = window.setTimeout(() => {
      dismissNotification(notification.id)
    }, 8000)

    return () => window.clearTimeout(timer)
  }, [notification, dismissNotification])

  if (!notification) return null

  const openChat = () => {
    dismissNotification(notification.id)

    const params = new URLSearchParams()

    if (notification.documentId) {
      params.set('document', notification.documentId)
    }

    if (notification.messageId) {
      params.set('message', notification.messageId)
    }

    navigate(`/chat${params.toString() ? `?${params}` : ''}`)
  }

  return (
    <div className="generation-notification" role="status">
      <button
        type="button"
        className="generation-notification-main"
        onClick={openChat}
      >
        <span className="generation-notification-icon" aria-hidden="true">
          <Icon name="check" size={16} />
        </span>

        <span className="generation-notification-body">
          <span className="generation-notification-title">
            Response ready
          </span>

          <span className="generation-notification-text">
            Your {notification.mode === 'traditional'
              ? 'Traditional RAG'
              : 'CA-RAG'} response is ready.
          </span>
        </span>
      </button>

      <button
        type="button"
        className="generation-notification-close"
        aria-label="Dismiss notification"
        onClick={() => dismissNotification(notification.id)}
      >
        <Icon name="close" size={16} />
      </button>
    </div>
  )
}