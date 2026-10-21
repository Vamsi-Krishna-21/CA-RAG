import AnswerText from './AnswerText.jsx'
import SourceList from '../citations/SourceList.jsx'
import VerificationSummary from '../verification/VerificationSummary.jsx'
import FeedbackButtons from '../feedback/FeedbackButtons.jsx'

export default function AssistantMessage({ message }) {
  const {
    answer,
    citations = [],
    evidence = [],
    rewritten_queries = [],
    response_time: responseTime,
  } = message.content

  // Live responses carry message_id; reloaded history rows use the row id.
  const messageId = message.content.message_id || message.id
  const formattedResponseTime =
    typeof responseTime === 'number' && Number.isFinite(responseTime)
      ? `${responseTime.toFixed(2)}s`
      : null

  return (
    <article
      className="msg msg-assistant"
      id={messageId ? `m-${messageId}` : undefined}
    >
      {/* Show the actual rewritten query first, only when query rewriting was used */}
      {rewritten_queries.length > 0 && (
        <section className="rewritten-query" aria-label="Rewritten query">
          <div className="rewritten-query-header">
            <span className="rewritten-query-check" aria-hidden="true">
              ✓
            </span>
            <span className="rewritten-query-label">
              Query rewritten
            </span>
          </div>

          <div className="rewritten-query-list">
            {rewritten_queries.map((query, index) => (
              <div className="rewritten-query-item" key={`${query}-${index}`}>
                {query}
              </div>
            ))}
          </div>
        </section>
      )}

      <AnswerText text={answer} />

      {citations.length > 0 && (
        <SourceList citations={citations} />
      )}

      <VerificationSummary
        content={message.content}
        mode={message.mode}
      />

      {formattedResponseTime && (
        <div className="response-time">
          Response time: {formattedResponseTime}
        </div>
      )}

      {messageId && (
        <FeedbackButtons
          messageId={messageId}
          usedChunks={evidence.map((e) => e.chunk_id)}
        />
      )}
    </article>
  )
}