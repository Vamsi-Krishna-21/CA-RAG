// Presentation helpers for the values the backend already returns.
// Nothing here computes new scores: `status`, `confidence`, `hallucination_risk`
// and `evidence[].similarity` come straight from the API.

const STATUS = {
  HIGHLY_SUPPORTED: { label: 'Highly supported', tone: 'good', risk: 'Low' },
  SUPPORTED: { label: 'Supported', tone: 'good', risk: 'Low' },
  PARTIALLY_SUPPORTED: { label: 'Partially supported', tone: 'warn', risk: 'Moderate' },
  INSUFFICIENT_EVIDENCE: { label: 'Insufficient evidence', tone: 'bad', risk: 'High' },
  CA_RAG_VALIDATED: { label: 'Similarity validated', tone: 'good', risk: null },
}

export function statusInfo(status) {
  if (STATUS[status]) return STATUS[status]
  const label = String(status || 'Unknown').toLowerCase().replace(/_/g, ' ')
  return { label: label.charAt(0).toUpperCase() + label.slice(1), tone: 'warn', risk: null }
}

export const clampPct = (n) => Math.max(0, Math.min(100, Math.round(Number(n) || 0)))

// The backend reports risk as 0..1.
export const riskPct = (risk) => clampPct((Number(risk) || 0) * 100)

// Which features are included in each mode's displayed pipeline.
export const PIPELINE = [
  { key: 'retrieve', label: 'Evidence Retrieval', modes: ['enhanced_carag', 'carag', 'traditional_rag'] },
  { key: 'semantic_chunking', label: 'Semantic Chunking', modes: ['carag'] },
  { key: 'candidate_generation', label: 'Multi-Candidate Answer Generation', modes: ['enhanced_carag', 'carag'] },
  { key: 'adaptive_chunking', label: 'Adaptive Chunking', modes: ['enhanced_carag', 'traditional_rag'] },
  { key: 'similarity_validation', label: 'Similarity Validation', modes: ['enhanced_carag', 'carag'] },
  { key: 'answer_selection', label: 'Best Candidate Selection', modes: ['enhanced_carag', 'carag'] },
  { key: 'query_rewrite', label: 'Query Rewriting', modes: ['enhanced_carag'] },
  { key: 'check', label: 'Hallucination Detection', modes: ['enhanced_carag', 'traditional_rag'] },
  { key: 'confidence', label: 'Confidence Scoring', modes: ['enhanced_carag', 'traditional_rag'] },
  { key: 'cite', label: 'Source Citation', modes: ['enhanced_carag', 'traditional_rag'] },
  { key: 'feedback', label: 'Feedback Learning', modes: ['enhanced_carag'] },
]

export const MODES = {
  enhanced_carag: { label: 'Enhance CA-RAG', hint: 'Enhanced verification + citations' },
  carag: { label: 'CA-RAG', hint: 'Research-paper validation' },
  traditional_rag: { label: 'Traditional RAG', hint: 'Baseline retrieval' },
}
