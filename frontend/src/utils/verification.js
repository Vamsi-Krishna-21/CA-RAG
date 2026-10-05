// Presentation helpers for the values the backend already returns.
// Nothing here computes new scores: `status`, `confidence`, `hallucination_risk`
// and `evidence[].similarity` come straight from the API.

const STATUS = {
  HIGHLY_SUPPORTED: { label: 'Highly supported', tone: 'good', risk: 'Low' },
  SUPPORTED: { label: 'Supported', tone: 'good', risk: 'Low' },
  PARTIALLY_SUPPORTED: { label: 'Partially supported', tone: 'warn', risk: 'Moderate' },
  INSUFFICIENT_EVIDENCE: { label: 'Insufficient evidence', tone: 'bad', risk: 'High' },
}

export function statusInfo(status) {
  if (STATUS[status]) return STATUS[status]
  const label = String(status || 'Unknown').toLowerCase().replace(/_/g, ' ')
  return { label: label.charAt(0).toUpperCase() + label.slice(1), tone: 'warn', risk: null }
}

export const clampPct = (n) => Math.max(0, Math.min(100, Math.round(Number(n) || 0)))

// The backend reports risk as 0..1.
export const riskPct = (risk) => clampPct((Number(risk) || 0) * 100)

// Which pipeline stages run in each mode (from the backend's chat route).
export const PIPELINE = [
  { key: 'rewrite', label: 'Query rewriting', modes: ['carag'] },
  { key: 'retrieve', label: 'Evidence retrieval', modes: ['carag', 'traditional'] },
  { key: 'validate', label: 'Similarity validation', modes: ['carag'] },
  { key: 'check', label: 'Hallucination check', modes: ['carag', 'traditional'] },
  { key: 'cite', label: 'Source citation', modes: ['carag', 'traditional'] },
]

export const MODES = {
  carag: { label: 'CA-RAG', hint: 'Verification + citations' },
  traditional: { label: 'Traditional RAG', hint: 'Baseline retrieval' },
}
