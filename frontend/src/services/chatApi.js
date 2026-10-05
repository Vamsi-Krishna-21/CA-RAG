import client from './axiosClient'

/**
 * Normal non-streaming chat request.
 *
 * Supports:
 * - Single PDF
 * - Multiple PDFs
 * - Conversation-based chat
 *
 * Kept for compatibility with other parts of the application.
 */
export async function sendMessage(
  documentId,
  query,
  mode = 'carag',
  documentIds = [],
  conversationId = null,
) {
  const resolvedDocumentIds =
    documentIds?.length > 0
      ? documentIds
      : documentId
        ? [documentId]
        : []

  const res = await client.post('/chat', {
    document_id: documentId || null,
    document_ids: resolvedDocumentIds,
    conversation_id: conversationId,
    query,
    mode,
  })

  return res.data
}


/**
 * Stream a chat response from the backend.
 *
 * Backend endpoint:
 *
 * POST /api/chat/stream
 *
 * Supports:
 * - Single PDF
 * - Multiple PDFs
 * - Conversation-based chat
 *
 * Events:
 * - stage
 * - query_rewrite
 * - progress
 * - token
 * - done
 * - error
 */
export async function streamMessage(
  documentId,
  query,
  mode = 'carag',
  handlers = {},
  signal,
  documentIds = [],
  conversationId = null,
) {
  const token = localStorage.getItem('carag_token')

  const resolvedDocumentIds =
    documentIds?.length > 0
      ? documentIds
      : documentId
        ? [documentId]
        : []

  const response = await fetch('/api/chat/stream', {
    method: 'POST',

    headers: {
      'Content-Type': 'application/json',

      ...(token
        ? {
            Authorization: `Bearer ${token}`,
          }
        : {}),
    },

    body: JSON.stringify({
      document_id: documentId || null,
      document_ids: resolvedDocumentIds,
      conversation_id: conversationId,
      query,
      mode,
    }),

    signal,
  })


  // ------------------------------------------------------------
  // Authentication error
  // ------------------------------------------------------------

  if (response.status === 401) {
    localStorage.removeItem('carag_token')
    window.location.href = '/login'

    throw new Error(
      'Your session has expired. Please log in again.',
    )
  }


  // ------------------------------------------------------------
  // Other HTTP errors
  // ------------------------------------------------------------

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`

    try {
      const data = await response.json()

      message =
        data.detail ||
        data.message ||
        message
    } catch {
      // Keep default message.
    }

    throw new Error(message)
  }


  // ------------------------------------------------------------
  // Streaming support
  // ------------------------------------------------------------

  if (!response.body) {
    throw new Error(
      'Streaming is not supported by this browser.',
    )
  }


  const reader = response.body.getReader()

  const decoder = new TextDecoder('utf-8')

  let buffer = ''

  let finalResponse = null


  // ------------------------------------------------------------
  // Process one complete SSE event
  // ------------------------------------------------------------

  const processEvent = (rawEvent) => {
    if (!rawEvent.trim()) {
      return
    }


    let eventName = 'message'

    const dataLines = []


    for (const line of rawEvent.split(/\r?\n/)) {

      if (line.startsWith('event:')) {
        eventName = line
          .slice(6)
          .trim()

      } else if (line.startsWith('data:')) {
        dataLines.push(
          line
            .slice(5)
            .trimStart(),
        )
      }
    }


    if (dataLines.length === 0) {
      return
    }


    const rawData = dataLines.join('\n')

    let data


    try {
      data = JSON.parse(rawData)
    } catch {
      data = {
        text: rawData,
      }
    }


    // ----------------------------------------------------------
    // Handle event
    // ----------------------------------------------------------

    switch (eventName) {

      case 'stage':
        handlers.onStage?.(data)
        break


      case 'query_rewrite':
        handlers.onQueryRewrite?.(data)
        handlers.onRewrite?.(data)
        break


      case 'progress':
        handlers.onProgress?.(data)
        break


      case 'token':
        handlers.onToken?.(
          data.text || '',
        )
        break


      case 'done':
        finalResponse = data

        handlers.onDone?.(data)

        break


      case 'error':
        handlers.onError?.(data)

        break


      default:
        handlers.onEvent?.(
          eventName,
          data,
        )

        break
    }
  }


  // ------------------------------------------------------------
  // Read stream
  // ------------------------------------------------------------

  while (true) {

    const {
      value,
      done,
    } = await reader.read()


    if (done) {
      break
    }


    buffer += decoder.decode(
      value,
      {
        stream: true,
      },
    )


    /*
     * SSE events are separated by a blank line.
     *
     * Network chunks can split an SSE event,
     * so incomplete data remains in `buffer`.
     */

    const events = buffer.split(
      /\r?\n\r?\n/,
    )

    buffer =
      events.pop() || ''


    for (const event of events) {
      processEvent(event)
    }
  }


  // Flush decoder.
  buffer += decoder.decode()


  if (buffer.trim()) {
    processEvent(buffer)
  }


  // ------------------------------------------------------------
  // Ensure server sent final response
  // ------------------------------------------------------------

  if (!finalResponse) {
    throw new Error(
      'The server ended the stream without a final response.',
    )
  }


  return finalResponse
}


/**
 * Load conversation history.
 *
 * Kept for compatibility with the existing
 * document-based history screen.
 */
export async function getHistory(
  documentId,
  conversationId = null,
) {
  const params = {
    document_id: documentId,
  }

  if (conversationId) {
    params.conversation_id = conversationId
  }

  const res = await client.get(
    '/chat/history',
    {
      params,
    },
  )

  return res.data
}