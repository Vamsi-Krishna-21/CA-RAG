import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'

import { streamMessage } from '../services/chatApi'
import { rememberMode } from '../utils/messages'

const ChatGenerationContext = createContext(null)

/**
 * Normalize a list of document IDs.
 *
 * Keeps the order supplied by the caller while removing:
 * - null / undefined values
 * - empty strings
 * - duplicate IDs
 */
function normalizeDocumentIds(documentIds = [], documentId = null) {
  const values = []

  if (Array.isArray(documentIds)) {
    values.push(...documentIds)
  }

  if (documentId !== null && documentId !== undefined) {
    values.push(documentId)
  }

  return [...new Set(
    values
      .filter((id) => id !== null && id !== undefined)
      .map((id) => String(id).trim())
      .filter(Boolean),
  )]
}

/**
 * Create a stable generation key.
 *
 * Backward compatibility:
 * - one document -> the document ID itself
 *
 * New behavior:
 * - conversation -> conversation:<id>
 * - multiple documents -> documents:<sorted ids>
 */
function makeGenerationKey({
  conversationId = null,
  documentIds = [],
  documentId = null,
} = {}) {
  if (conversationId !== null && conversationId !== undefined) {
    const normalizedConversationId = String(conversationId).trim()

    if (normalizedConversationId) {
      return `conversation:${normalizedConversationId}`
    }
  }

  const ids = normalizeDocumentIds(documentIds, documentId).sort()

  if (ids.length === 1) {
    return ids[0]
  }

  if (ids.length > 1) {
    return `documents:${ids.join(',')}`
  }

  return ''
}

/**
 * Normalize either:
 *
 *   "document-id"
 *
 * or:
 *
 *   {
 *     documentId,
 *     documentIds,
 *     conversationId
 *   }
 */
function normalizeGenerationContext(input) {
  if (
    input === null ||
    input === undefined ||
    input === ''
  ) {
    return {
      documentId: null,
      documentIds: [],
      conversationId: null,
    }
  }

  if (typeof input === 'string' || typeof input === 'number') {
    const documentId = String(input).trim()

    return {
      documentId: documentId || null,
      documentIds: documentId ? [documentId] : [],
      conversationId: null,
    }
  }

  const documentId =
    input.documentId !== null &&
    input.documentId !== undefined &&
    String(input.documentId).trim()
      ? String(input.documentId).trim()
      : null

  const conversationId =
    input.conversationId !== null &&
    input.conversationId !== undefined &&
    String(input.conversationId).trim()
      ? String(input.conversationId).trim()
      : null

  const documentIds = normalizeDocumentIds(
    input.documentIds,
    documentId,
  )

  return {
    documentId,
    documentIds,
    conversationId,
  }
}

/**
 * Check whether a generation belongs to the currently active chat.
 *
 * This supports all of the following:
 *
 *   document-id
 *   conversation:<id>
 *   documents:<id1>,<id2>
 */
function generationMatchesActiveChat(
  activeChatKey,
  generationKey,
  generation,
) {
  if (!activeChatKey) {
    return false
  }

  if (activeChatKey === generationKey) {
    return true
  }

  if (
    generation?.conversationId &&
    activeChatKey === `conversation:${generation.conversationId}`
  ) {
    return true
  }

  const documentIds = normalizeDocumentIds(
    generation?.documentIds,
    generation?.documentId,
  )

  if (documentIds.length === 1) {
    if (activeChatKey === documentIds[0]) {
      return true
    }
  }

  if (documentIds.length > 1) {
    const multiDocumentKey = `documents:${[...documentIds]
      .sort()
      .join(',')}`

    if (activeChatKey === multiDocumentKey) {
      return true
    }
  }

  return false
}

export function ChatGenerationProvider({ children }) {
  /**
   * Map:
   *
   * generationKey -> generation state
   *
   * We use a ref as the authoritative mutable store so background
   * generations survive normal React re-renders without being recreated.
   */
  const generationsRef = useRef(new Map())

  const [generations, setGenerations] = useState({})

  /**
   * The currently active chat.
   *
   * Existing Chat.jsx passes a document ID here.
   *
   * The new chat UI can pass:
   *
   *   {
   *     conversationId,
   *     documentIds,
   *     documentId
   *   }
   */
  const [activeChatKey, setActiveChatKey] = useState('')

  const activeChatKeyRef = useRef('')

  /**
   * Track mounted state so asynchronous callbacks don't update
   * React state after the provider has been unmounted.
   */
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true

    return () => {
      mountedRef.current = false

      /**
       * Abort every currently running generation when the provider
       * itself is unmounted.
       *
       * Normally this provider lives at application level, so navigating
       * between pages does NOT trigger this cleanup.
       */
      generationsRef.current.forEach((generation) => {
        if (
          generation?.controller &&
          !generation.controller.signal.aborted
        ) {
          generation.controller.abort()
        }
      })

      generationsRef.current.clear()
    }
  }, [])

  /**
   * Keep activeChatKey in a ref as well as state.
   *
   * Streaming callbacks happen asynchronously and must always see the
   * latest active chat rather than the value captured by an old render.
   */
  useEffect(() => {
    activeChatKeyRef.current = activeChatKey
  }, [activeChatKey])

  /**
   * Update the active chat.
   *
   * Backward compatible with:
   *
   *   setActiveChat(documentId)
   *
   * New code may use:
   *
   *   setActiveChat({
   *     conversationId,
   *     documentIds,
   *     documentId,
   *   })
   */
  const setActiveChat = useCallback((chatContext) => {
    let key = ''

    if (
      chatContext !== null &&
      chatContext !== undefined &&
      chatContext !== ''
    ) {
      if (
        typeof chatContext === 'object' &&
        !Array.isArray(chatContext)
      ) {
        key = makeGenerationKey(chatContext)
      } else {
        key = String(chatContext).trim()
      }
    }

    activeChatKeyRef.current = key
    setActiveChatKey(key)
  }, [])

  /**
   * Update a generation in both the ref store and React state.
   */
  const updateGeneration = useCallback((key, patch) => {
  if (!key) {
    return null
  }

  const existing = generationsRef.current.get(key)

  if (!existing) {
    return null
  }

  const updated = {
    ...existing,
    ...patch,
  }

  generationsRef.current.set(key, updated)

  if (mountedRef.current) {
    setGenerations((prev) => ({
      ...prev,
      [key]: updated,
    }))
  }

  return updated
}, [])

  /**
   * Start a background streaming generation.
   *
   * Supported input:
   *
   * {
   *   documentId,
   *   documentIds,
   *   conversationId,
   *   query,
   *   mode,
   *   generationId
   * }
   *
   * `documentId` remains supported for the existing single-PDF flow.
   */
  const startGeneration = useCallback(
    async ({
      documentId = null,
      documentIds = [],
      conversationId = null,
      query,
      mode = 'carag',
      generationId = null,
    }) => {
      const normalizedDocumentIds = normalizeDocumentIds(
        documentIds,
        documentId,
      )

      const primaryDocumentId =
        documentId !== null &&
        documentId !== undefined &&
        String(documentId).trim()
          ? String(documentId).trim()
          : normalizedDocumentIds[0] || null

      const normalizedConversationId =
        conversationId !== null &&
        conversationId !== undefined &&
        String(conversationId).trim()
          ? String(conversationId).trim()
          : null

      const normalizedQuery =
        typeof query === 'string'
          ? query.trim()
          : ''

      if (!primaryDocumentId && normalizedDocumentIds.length === 0) {
        throw new Error('A document must be selected before asking a question.')
      }

      if (!normalizedQuery) {
        throw new Error('Please enter a question.')
      }

      /**
       * Rebuild the document list so the primary document is always
       * included first.
       */
      const finalDocumentIds = [
        ...(primaryDocumentId ? [primaryDocumentId] : []),
        ...normalizedDocumentIds.filter(
          (id) => id !== primaryDocumentId,
        ),
      ]

      const key = makeGenerationKey({
        conversationId: normalizedConversationId,
        documentIds: finalDocumentIds,
        documentId: primaryDocumentId,
      })

      if (!key) {
        throw new Error('Unable to create a generation context.')
      }

      /**
       * Prevent two simultaneous generations for the exact same
       * conversation/document scope.
       */
      const existing = generationsRef.current.get(key)

      if (
        existing &&
        (
          existing.status === 'starting' ||
          existing.status === 'streaming'
        )
      ) {
        return existing
      }

      const controller = new AbortController()

      const generation = {
        id:
          generationId ||
          `${Date.now()}-${Math.random().toString(36).slice(2)}`,

        key,

        documentId: primaryDocumentId,

        documentIds: finalDocumentIds,

        conversationId: normalizedConversationId,

        query: normalizedQuery,

        mode,

        status: 'starting',

        answer: '',

        confidence: null,

        hallucination_risk: null,

        citations: [],

        evidence: [],

        verification: null,

        rewritten_queries: [],

        stage: 'Starting',

        progress: 0,

        message_id: null,

        error: null,

        controller,
      }

      generationsRef.current.set(key, generation)

      if (mountedRef.current) {
        setGenerations((previous) => ({
          ...previous,
          [key]: generation,
        }))
      }

      /**
       * Remember the selected mode so the next chat uses the same
       * mode as before.
       */
      try {
        rememberMode(mode)
      } catch {
        /**
         * Remembering the mode is helpful but should never prevent
         * generation from starting.
         */
      }

      /**
       * Streaming callbacks.
       */
      const handlers = {
        /**
         * Query rewriting stage.
         */
        onRewrite: (data) => {
          const rewrittenQueries =
            Array.isArray(data?.rewritten_queries)
              ? data.rewritten_queries
              : Array.isArray(data?.queries)
                ? data.queries
                : []

          updateGeneration(key, {
            status: 'streaming',

            stage:
              data?.stage ||
              'Rewriting query',

            progress:
              typeof data?.progress === 'number'
                ? data.progress
                : 10,

            rewritten_queries: rewrittenQueries,
          })
        },

        /**
         * Generic stage/progress events.
         */
        onStage: (data) => {
          updateGeneration(key, {
            status: 'streaming',

            stage:
              data?.stage ||
              data?.message ||
              'Processing',

            progress:
              typeof data?.progress === 'number'
                ? data.progress
                : undefined,
          })
        },

        /**
         * Explicit progress event.
         */
        onProgress: (data) => {
          updateGeneration(key, {
            status: 'streaming',

            stage:
              data?.stage ||
              data?.message ||
              generation.stage,

            progress:
              typeof data?.progress === 'number'
                ? data.progress
                : generation.progress,
          })
        },

        /**
         * Evidence/candidate information.
         */
        onEvidence: (data) => {
          const evidence =
            Array.isArray(data?.evidence)
              ? data.evidence
              : Array.isArray(data?.candidates)
                ? data.candidates
                : []

          updateGeneration(key, {
            status: 'streaming',

            stage:
              data?.stage ||
              'Retrieving evidence',

            progress:
              typeof data?.progress === 'number'
                ? data.progress
                : 35,

            evidence,
          })
        },

        /**
         * Verification information.
         */
        onVerification: (data) => {
          updateGeneration(key, {
            status: 'streaming',

            stage:
              data?.stage ||
              'Validating evidence',

            progress:
              typeof data?.progress === 'number'
                ? data.progress
                : 60,

            verification:
              data?.verification ??
              data,

            hallucination_risk:
              data?.hallucination_risk ??
              data?.risk ??
              null,

            confidence:
              data?.confidence ??
              null,
          })
        },

        /**
         * Incremental answer token.
         */
        onToken: (data) => {
          const token =
            typeof data === 'string'
              ? data
              : (
                  data?.token ??
                  data?.text ??
                  data?.content ??
                  ''
                )

          if (!token) {
            return
          }

          const current =
            generationsRef.current.get(key)

          if (!current) {
            return
          }

          updateGeneration(key, {
            status: 'streaming',

            stage:
              data?.stage ||
              'Generating answer',

            progress:
              typeof data?.progress === 'number'
                ? data.progress
                : Math.max(
                    current.progress || 0,
                    70,
                  ),

            answer:
              `${current.answer || ''}${token}`,
          })
        },

        /**
         * Final streaming response.
         */
        onDone: (data) => {
          const responseConversationId =
            data?.conversation_id ??
            data?.conversationId ??
            normalizedConversationId ??
            null

          const responseDocumentIds =
            Array.isArray(data?.document_ids) &&
            data.document_ids.length > 0
              ? normalizeDocumentIds(
                  data.document_ids,
                  primaryDocumentId,
                )
              : finalDocumentIds

          const responseDocumentId =
            data?.document_id ??
            primaryDocumentId ??
            responseDocumentIds[0] ??
            null

          const completed = updateGeneration(key, {
            status: 'completed',

            stage:
              data?.stage ||
              'Complete',

            progress: 100,

            answer:
              data?.answer ??
              data?.response ??
              data?.content ??
              generationsRef.current.get(key)?.answer ??
              '',

            confidence:
              data?.confidence ??
              null,

            hallucination_risk:
              data?.hallucination_risk ??
              data?.risk ??
              null,

            citations:
              Array.isArray(data?.citations)
                ? data.citations
                : [],

            evidence:
              Array.isArray(data?.evidence)
                ? data.evidence
                : generationsRef.current.get(key)?.evidence ||
                  [],

            verification:
              data?.verification ??
              null,

            rewritten_queries:
              Array.isArray(data?.rewritten_queries)
                ? data.rewritten_queries
                : generationsRef.current.get(key)
                    ?.rewritten_queries || [],

            message_id:
              data?.message_id ??
              data?.messageId ??
              null,

            conversationId:
                data?.conversation_id ||
                generation.conversationId ||
                null,

            documentId:
              responseDocumentId,

            documentIds:
              responseDocumentIds,

            error: null,
          })

          /**
           * A completed generation should produce a notification only
           * when the user is no longer viewing that chat.
           */
          const activeKey =
            activeChatKeyRef.current

          const isCurrentChat =
            generationMatchesActiveChat(
              activeKey,
              key,
              completed || {
                conversationId: responseConversationId,
                documentId: responseDocumentId,
                documentIds: responseDocumentIds,
              },
            )

          if (
            completed &&
            !isCurrentChat &&
            typeof window !== 'undefined' &&
            typeof window.dispatchEvent === 'function'
          ) {
            window.dispatchEvent(
              new CustomEvent('carag:generation-complete', {
                detail: {
                  generationId: completed.id,

                  documentId:
                    responseDocumentId,

                  documentIds:
                    responseDocumentIds,

                  conversationId:
                    responseConversationId,

                  messageId:
                    completed.message_id,

                  query:
                    completed.query,

                  mode:
                    completed.mode,
                },
              }),
            )
          }

          /**
           * Keep the completed generation temporarily so that:
           *
           * - navigating back to the chat can display it immediately
           * - the completion notification has useful context
           * - the chat UI does not suddenly lose the answer
           *
           * After 30 seconds, remove it unless a newer generation
           * has replaced it.
           */
          window.setTimeout(() => {
            const current =
              generationsRef.current.get(key)

            if (
              current &&
              current.id === generation.id &&
              current.status === 'completed'
            ) {
              generationsRef.current.delete(key)

              if (mountedRef.current) {
                setGenerations((previous) => {
                  const next = {
                    ...previous,
                  }

                  delete next[key]

                  return next
                })
              }
            }
          }, 30000)
        },

        /**
         * Streaming error.
         */
        onError: (error) => {
          if (
            error?.name === 'AbortError' ||
            controller.signal.aborted
          ) {
            updateGeneration(key, {
              status: 'cancelled',

              stage: 'Cancelled',

              error: null,
            })

            return
          }

          const message =
            error instanceof Error
              ? error.message
              : (
                  error?.message ||
                  String(error || 'Generation failed.')
                )

          updateGeneration(key, {
            status: 'error',

            stage: 'Generation failed',

            error: message,
          })
        },
      }

      try {
        /**
         * IMPORTANT:
         *
         * The extended streamMessage signature is:
         *
         * streamMessage(
         *   documentId,
         *   query,
         *   mode,
         *   handlers,
         *   signal,
         *   documentIds,
         *   conversationId
         * )
         *
         * The final two arguments are what allow the backend to know
         * that this request belongs to multiple PDFs and/or a specific
         * conversation.
         */
        await streamMessage(
          primaryDocumentId,
          normalizedQuery,
          mode,
          handlers,
          controller.signal,
          finalDocumentIds,
          normalizedConversationId,
        )

        /**
         * Some older versions of chatApi.js may finish the stream
         * without emitting onDone.
         *
         * Preserve the answer already received from tokens and mark
         * the generation complete rather than leaving it stuck in
         * "streaming".
         */
        const current =
          generationsRef.current.get(key)

        if (
          current &&
          (
            current.status === 'starting' ||
            current.status === 'streaming'
          )
        ) {
          updateGeneration(key, {
            status: 'completed',

            stage: 'Complete',

            progress: 100,
          })

          /**
           * This fallback intentionally does not dispatch a second
           * notification. A proper onDone event is responsible for
           * completion notifications.
           */
        }
      } catch (error) {
        if (
          error?.name === 'AbortError' ||
          controller.signal.aborted
        ) {
          updateGeneration(key, {
            status: 'cancelled',

            stage: 'Cancelled',

            error: null,
          })
        } else {
          const message =
            error instanceof Error
              ? error.message
              : (
                  error?.message ||
                  String(error || 'Generation failed.')
                )

          updateGeneration(key, {
            status: 'error',

            stage: 'Generation failed',

            error: message,
          })
        }
      }

      return generationsRef.current.get(key)
    },
    [updateGeneration],
  )

  /**
   * Cancel a running generation.
   *
   * Supports:
   *
   *   cancelGeneration(documentId)
   *
   * and:
   *
   *   cancelGeneration({
   *     documentId,
   *     documentIds,
   *     conversationId
   *   })
   */
  const cancelGeneration = useCallback(
    (chatContext) => {
      const normalized =
        normalizeGenerationContext(chatContext)

      const key = makeGenerationKey(normalized)

      if (!key) {
        return false
      }

      const generation =
        generationsRef.current.get(key)

      if (!generation) {
        return false
      }

      if (
        generation.controller &&
        !generation.controller.signal.aborted
      ) {
        generation.controller.abort()
      }

      updateGeneration(key, {
        status: 'cancelled',

        stage: 'Cancelled',

        error: null,
      })

      return true
    },
    [updateGeneration],
  )

  /**
   * Retrieve the current generation for a document,
   * multi-document context, or conversation.
   *
   * Supports:
   *
   *   getGeneration(documentId)
   *
   *   getGeneration({
   *     documentId,
   *     documentIds,
   *     conversationId
   *   })
   */
  const getGeneration = useCallback(
    (chatContext) => {
      const normalized =
        normalizeGenerationContext(chatContext)

      const key =
        makeGenerationKey(normalized)

      if (!key) {
        return null
      }

      return generationsRef.current.get(key) || null
    },
    [],
  )

  /**
   * Determine whether a generation is currently running.
   */
  const isGenerating = useCallback(
    (chatContext) => {
      const generation =
        getGeneration(chatContext)

      if (!generation) {
        return false
      }

      return (
        generation.status === 'starting' ||
        generation.status === 'streaming'
      )
    },
    [getGeneration],
  )

  /**
   * Memoize the context value so consumers only re-render when one
   * of the exposed values actually changes.
   */
  const value = useMemo(
    () => ({
      generations,

      activeChatKey,

      setActiveChat,

      startGeneration,

      cancelGeneration,

      getGeneration,

      isGenerating,
    }),
    [
      generations,
      activeChatKey,
      setActiveChat,
      startGeneration,
      cancelGeneration,
      getGeneration,
      isGenerating,
    ],
  )

  return (
    <ChatGenerationContext.Provider value={value}>
      {children}
    </ChatGenerationContext.Provider>
  )
}

/**
 * Hook used by Chat.jsx and other components.
 */
export function useChatGeneration() {
  const context =
    useContext(ChatGenerationContext)

  if (!context) {
    throw new Error(
      'useChatGeneration must be used inside ChatGenerationProvider.',
    )
  }

  return context
}

export default ChatGenerationContext