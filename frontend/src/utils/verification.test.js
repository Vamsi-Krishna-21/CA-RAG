import assert from 'node:assert/strict'
import test from 'node:test'
import { PIPELINE } from './verification.js'

const activeFeatures = (mode) =>
  PIPELINE.filter((feature) => feature.modes.includes(mode))
    .map((feature) => feature.label)

test('feature matrix keeps semantic chunking exclusive to original CA-RAG', () => {
  assert.deepEqual(activeFeatures('carag'), [
    'Evidence Retrieval',
    'Semantic Chunking',
    'Multi-Candidate Answer Generation',
    'Similarity Validation',
    'Best Candidate Selection',
  ])
  assert.ok(!activeFeatures('enhanced_carag').includes('Semantic Chunking'))
  assert.ok(!activeFeatures('traditional_rag').includes('Semantic Chunking'))
})

test('Enhance CA-RAG retains adaptive chunking and feedback learning', () => {
  const enhancedFeatures = activeFeatures('enhanced_carag')
  assert.ok(enhancedFeatures.includes('Adaptive Chunking'))
  assert.ok(enhancedFeatures.includes('Feedback Learning'))
})

test('Traditional RAG feature mapping remains unchanged', () => {
  assert.deepEqual(activeFeatures('traditional_rag'), [
    'Evidence Retrieval',
    'Adaptive Chunking',
    'Hallucination Detection',
    'Confidence Scoring',
    'Source Citation',
  ])
})
