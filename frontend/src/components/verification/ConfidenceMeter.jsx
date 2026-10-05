import { clampPct, riskPct, statusInfo } from '../../utils/verification.js'

export default function ConfidenceMeter({ confidence, status, risk }) {
  const pct = clampPct(confidence)
  const info = statusInfo(status)

  return (
    <div className={'meter-block tone-' + info.tone}>
      <div className="stat-row">
        <div className="stat">
          <span className="stat-label">Confidence</span>
          <span className="stat-value">{pct}%</span>
        </div>
        <div className="stat">
          <span className="stat-label">Status</span>
          <span className="stat-value stat-text">{info.label}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Hallucination risk</span>
          <span className="stat-value stat-text">
            {info.risk ? `${info.risk} · ` : ''}
            {riskPct(risk)}%
          </span>
        </div>
      </div>
      <div
        className="meter"
        role="meter"
        aria-label="Confidence"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct}
      >
        <div className="meter-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}
