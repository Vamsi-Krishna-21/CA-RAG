import { useState } from 'react'
import { sendFeedback } from '../../services/feedbackApi'
import Icon from '../common/Icon.jsx'

export default function FeedbackButtons({ messageId, usedChunks }) {
  const [given, setGiven] = useState(null)
  const [failed, setFailed] = useState(false)

  const rate = async (rating) => {
    if (given) return
    setGiven(rating)
    setFailed(false)
    try {
      await sendFeedback(messageId, rating, usedChunks)
    } catch {
      setGiven(null)
      setFailed(true)
    }
  }

  return (
    <div className="feedback">
      {given ? (
        <span className="feedback-thanks" role="status">Thanks for the feedback</span>
      ) : (
        <>
          <span className="feedback-label">Helpful?</span>
          <button type="button" className="icon-btn icon-btn-sm" onClick={() => rate('positive')} aria-label="Helpful" title="Helpful">
            <Icon name="thumbUp" size={15} />
          </button>
          <button type="button" className="icon-btn icon-btn-sm" onClick={() => rate('negative')} aria-label="Not helpful" title="Not helpful">
            <Icon name="thumbDown" size={15} />
          </button>
          {failed && <span className="feedback-error" role="alert">Couldn't send. Try again.</span>}
        </>
      )}
    </div>
  )
}
