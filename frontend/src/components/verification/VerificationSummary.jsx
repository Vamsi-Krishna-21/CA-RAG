import { useId, useState } from 'react'
import Icon from '../common/Icon.jsx'
import ConfidenceMeter from './ConfidenceMeter.jsx'
import EvidenceAlignment from './EvidenceAlignment.jsx'
import PipelineSteps from './PipelineSteps.jsx'
import { clampPct, statusInfo } from '../../utils/verification.js'

// Collapsed by default: a single quiet line. Expands to confidence, pipeline and evidence.
export default function VerificationSummary({ content, mode }) {
  const [open, setOpen] = useState(false)
  const panelId = useId()

  const {
    confidence,
    status,
    hallucination_risk: risk,
    citations = [],
    evidence = [],
    rewritten_queries = [],
  } = content

  const info = statusInfo(status)
  const sources = citations.length

  return (
    <section className={'verify tone-' + info.tone} aria-label="Verification">
      <button
        type="button"
        className="verify-pill"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="verify-dot" aria-hidden="true" />

        <span className="verify-status">
          {info.label}
        </span>

        <span className="verify-sep" aria-hidden="true" />

        <span>
          {clampPct(confidence)}% confidence
        </span>

        <span className="verify-sep" aria-hidden="true" />

        <span>
          {sources} {sources === 1 ? 'source' : 'sources'}
        </span>

        <Icon
          name="chevronDown"
          size={15}
          className="verify-chevron"
        />
      </button>

      <div
        id={panelId}
        className="verify-panel"
        hidden={!open}
      >
        <ConfidenceMeter
          confidence={confidence}
          status={status}
          risk={risk}
        />

        {mode && (
          <PipelineSteps
            mode={mode}
            rewrittenQueries={rewritten_queries}
          />
        )}

        {evidence.length > 0 && (
          <EvidenceAlignment evidence={evidence} />
        )}

        {evidence.length === 0 && (
          <p className="verify-empty">
            No evidence passed validation for this question.
          </p>
        )}
      </div>
    </section>
  )
}