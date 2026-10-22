import assert from 'node:assert/strict'
import test from 'node:test'
import { getApiBaseUrl, buildApiUrl } from './apiConfig.js'

test('getApiBaseUrl defaults to /api when VITE_API_URL is unset or empty', () => {
  assert.equal(getApiBaseUrl(undefined), '/api')
  assert.equal(getApiBaseUrl(''), '/api')
  assert.equal(getApiBaseUrl('   '), '/api')
  assert.equal(getApiBaseUrl('/'), '/api')
})

test('getApiBaseUrl appends /api to domain or origin without trailing slash', () => {
  assert.equal(getApiBaseUrl('https://carag-backend.onrender.com'), 'https://carag-backend.onrender.com/api')
  assert.equal(getApiBaseUrl('https://carag-backend.onrender.com/'), 'https://carag-backend.onrender.com/api')
  assert.equal(getApiBaseUrl('http://localhost:8000'), 'http://localhost:8000/api')
})

test('getApiBaseUrl preserves existing /api without duplication', () => {
  assert.equal(getApiBaseUrl('https://carag-backend.onrender.com/api'), 'https://carag-backend.onrender.com/api')
  assert.equal(getApiBaseUrl('https://carag-backend.onrender.com/api/'), 'https://carag-backend.onrender.com/api')
  assert.equal(getApiBaseUrl('/api'), '/api')
  assert.equal(getApiBaseUrl('/api/'), '/api')
})

test('buildApiUrl resolves relative endpoints when env is unset', () => {
  assert.equal(buildApiUrl('/chat/stream', undefined), '/api/chat/stream')
  assert.equal(buildApiUrl('chat/stream', undefined), '/api/chat/stream')
  assert.equal(buildApiUrl('/api/chat/stream', undefined), '/api/chat/stream')
  assert.equal(buildApiUrl('/api/conversations', undefined), '/api/conversations')
  assert.equal(buildApiUrl('/api/conversations/123/pin', undefined), '/api/conversations/123/pin')
})

test('buildApiUrl prevents double /api when full domain is set', () => {
  const backend = 'https://carag-backend.onrender.com'
  assert.equal(buildApiUrl('/chat/stream', backend), 'https://carag-backend.onrender.com/api/chat/stream')
  assert.equal(buildApiUrl('/api/chat/stream', backend), 'https://carag-backend.onrender.com/api/chat/stream')
  assert.equal(buildApiUrl('/api/conversations', backend), 'https://carag-backend.onrender.com/api/conversations')
  assert.equal(buildApiUrl('/api/conversations/123', backend), 'https://carag-backend.onrender.com/api/conversations/123')
})

test('buildApiUrl handles env URL that already includes /api', () => {
  const backendWithApi = 'https://carag-backend.onrender.com/api'
  assert.equal(buildApiUrl('/chat/stream', backendWithApi), 'https://carag-backend.onrender.com/api/chat/stream')
  assert.equal(buildApiUrl('/api/chat/stream', backendWithApi), 'https://carag-backend.onrender.com/api/chat/stream')
  assert.equal(buildApiUrl('/api/conversations', backendWithApi), 'https://carag-backend.onrender.com/api/conversations')
})

test('buildApiUrl preserves query parameters', () => {
  const backend = 'https://carag-backend.onrender.com'
  assert.equal(buildApiUrl('/api/conversations?limit=10', backend), 'https://carag-backend.onrender.com/api/conversations?limit=10')
  assert.equal(buildApiUrl('/chat/history?document_id=doc1', undefined), '/api/chat/history?document_id=doc1')
})
