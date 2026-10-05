import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'

import {
  useLocation,
  useSearchParams,
} from 'react-router-dom'

import ChatComposer from '../components/chat/ChatComposer.jsx'
import ChatEmptyState from '../components/chat/ChatEmptyState.jsx'
import DocumentSelector from '../components/chat/DocumentSelector.jsx'
import MessageList from '../components/chat/MessageList.jsx'
import TypingIndicator from '../components/chat/TypingIndicator.jsx'
import ErrorNotice from '../components/common/ErrorNotice.jsx'
import Skeleton from '../components/common/Skeleton.jsx'

import { useDocuments } from '../hooks/useDocuments.jsx'
import useLocalStorage from '../hooks/useLocalStorage.js'

import {
  createConversation,
  getConversation,
} from '../services/conversationApi.js'

import { getHistory } from '../services/chatApi'

import { describeError } from '../utils/errors'

import {
  normalizeHistory,
} from '../utils/messages'

import {
  useChatGeneration,
} from '../context/ChatGenerationContext.jsx'


/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

function getMessageId(message) {
  return (
    message?.content?.message_id ||
    message?.id ||
    null
  )
}


/*
 * Convert persistent background-generation state into
 * the message shape already consumed by MessageList.
 */
function generationToMessage(generation) {
  if (!generation) {
    return null
  }

  if (generation.status === 'error') {
    return {
      key: `generation-error-${generation.id}`,
      role: 'error',

      content: {
        message:
          generation.error ||
          'The answer could not be generated.',

        query:
          generation.query || '',

        mode:
          generation.mode || 'carag',
      },
    }
  }

  if (
    generation.status !== 'starting' &&
    generation.status !== 'streaming' &&
    generation.status !== 'generating' &&
    generation.status !== 'completed'
  ) {
    return null
  }

  const isCompleted =
    generation.status === 'completed'

  return {
    key:
      generation.message_id ||
      generation.id,

    id:
      generation.message_id ||
      undefined,

    role: 'assistant',

    mode:
      generation.mode ||
      'carag',

    content: {
      answer:
        generation.answer || '',

      confidence:
        generation.confidence ?? 0,

      status:
        isCompleted
          ? 'completed'
          : 'generating',

      hallucination_risk:
        generation.hallucination_risk ?? 0,

      citations:
        Array.isArray(
          generation.citations,
        )
          ? generation.citations
          : [],

      evidence:
        Array.isArray(
          generation.evidence,
        )
          ? generation.evidence
          : [],

      verification:
        generation.verification ?? null,

      rewritten_queries:
        Array.isArray(
          generation.rewritten_queries,
        )
          ? generation.rewritten_queries
          : [],

      stage:
        generation.stage || '',

      progress:
        generation.progress ?? null,

      message_id:
        generation.message_id ||
        undefined,
    },
  }
}


/*
 * Normalize selected document IDs.
 */
function normalizeDocumentIds(ids) {
  if (!Array.isArray(ids)) {
    return []
  }

  return [
    ...new Set(
      ids
        .filter(
          (id) =>
            id !== null &&
            id !== undefined,
        )
        .map((id) => String(id))
        .filter(Boolean),
    ),
  ]
}


/*
 * Build the generation keys that may represent
 * the currently visible generation.
 *
 * A generation can initially be stored using:
 *
 *   documents:id1,id2,id3
 *
 * and later receive:
 *
 *   conversation:<conversation-id>
 *
 * Therefore Chat.jsx must check BOTH.
 */
function getGenerationKeys(
  documentId,
  selectedDocumentIds,
  conversationId,
) {
  const ids =
    normalizeDocumentIds(
      selectedDocumentIds,
    )

  const keys = []

  if (conversationId) {
    keys.push(
      `conversation:${conversationId}`,
    )
  }

  if (ids.length > 1) {
    keys.push(
      `documents:${[
        ...ids,
      ].sort().join(',')}`,
    )
  }

  if (ids.length === 1) {
    keys.push(ids[0])
  }

  if (documentId) {
    keys.push(String(documentId))
  }

  return [
    ...new Set(
      keys.filter(Boolean),
    ),
  ]
}


/* -------------------------------------------------------------------------- */
/* Chat page                                                                  */
/* -------------------------------------------------------------------------- */

export default function Chat() {
  /* ---------------------------------------------------------------------- */
  /* Documents                                                              */
  /* ---------------------------------------------------------------------- */

  const {
    docs,
    loading: docsLoading,
    error: docsError,
    refresh,
  } = useDocuments()

  const [
    searchParams,
    setSearchParams,
  ] = useSearchParams()

  const location =
    useLocation()

  const documentId =
    searchParams.get(
      'document',
    ) || ''

  const documentIdsParam =
    searchParams.get(
      'documents',
    ) || ''

  const conversationId =
    searchParams.get(
      'conversation',
    ) || ''

  const focusMessage =
    searchParams.get(
      'message',
    ) || ''

  const [
    lastDoc,
    setLastDoc,
  ] = useLocalStorage(
    'carag_last_document',
    '',
  )


  /* ---------------------------------------------------------------------- */
  /* Persistent background generation                                      */
  /* ---------------------------------------------------------------------- */

  const {
    generations,
    setActiveChat,
    startGeneration,
  } = useChatGeneration()


  /* ---------------------------------------------------------------------- */
  /* Mounted state                                                          */
  /* ---------------------------------------------------------------------- */

  const mountedRef =
    useRef(false)

  useEffect(() => {
    mountedRef.current = true

    return () => {
      mountedRef.current = false
    }
  }, [])


  /* ---------------------------------------------------------------------- */
  /* Document state                                                         */
  /* ---------------------------------------------------------------------- */

  const readyDocs =
    useMemo(
      () =>
        Array.isArray(docs)
          ? docs.filter(
              (doc) =>
                doc.status ===
                'ready',
            )
          : [],
      [docs],
    )

  const knownDoc =
    docs.find(
      (doc) =>
        String(doc.id) ===
        String(documentId),
    )

  const currentDoc =
    knownDoc &&
    knownDoc.status === 'ready'
      ? knownDoc
      : null


  /*
   * All documents selected for the current chat.
   *
   * The first document remains the primary document.
   */
  const [
    selectedDocumentIds,
    setSelectedDocumentIds,
  ] = useState([])


  /* ---------------------------------------------------------------------- */
  /* Reset the selection when starting a fresh chat                       */
  /* ---------------------------------------------------------------------- */

  useEffect(() => {
    if (!location.state?.fresh) {
      return
    }

    setSelectedDocumentIds([])
    setMessages([])
    setHistoryState('idle')
    setHistoryError('')
    focusedRef.current = ''
  }, [
    location.state?.fresh,
  ])


  /* ---------------------------------------------------------------------- */
  /* Restore selected documents from URL                                   */
  /* ---------------------------------------------------------------------- */

  useEffect(() => {
    const urlDocumentIds =
      normalizeDocumentIds(
        documentIdsParam
          ? documentIdsParam.split(',')
          : [],
      )

    if (
      urlDocumentIds.length > 0
    ) {
      setSelectedDocumentIds(
        urlDocumentIds,
      )

      return
    }

    if (!documentId) {
      return
    }

    setSelectedDocumentIds(
      (current) => {
        const normalized =
          normalizeDocumentIds(
            current,
          )

        /*
         * If the URL still points to the
         * current multi-document selection,
         * preserve it.
         */
        if (
          normalized.length > 0 &&
          normalized.includes(
            String(documentId),
          )
        ) {
          return normalized
        }

        return [
          String(documentId),
        ]
      },
    )
  }, [
    documentId,
    documentIdsParam,
  ])


  /* ---------------------------------------------------------------------- */
  /* Restore documents from a conversation                                 */
  /* ---------------------------------------------------------------------- */

  useEffect(() => {
    /*
     * Recents may open:
     *
     * /chat?conversation=123
     *
     * In that case there is no document information
     * in the URL yet.
     *
     * Load the conversation and restore its documents.
     */
    if (
      !conversationId ||
      documentId ||
      documentIdsParam ||
      docsLoading
    ) {
      return undefined
    }

    let cancelled = false

    getConversation(
      conversationId,
    )
      .then((conversation) => {
        if (cancelled) {
          return
        }

        const ids =
          normalizeDocumentIds(
            conversation?.document_ids,
          )

        if (ids.length === 0) {
          return
        }

        const primaryId =
          ids[0]

        setSelectedDocumentIds(ids)

        setLastDoc(
          primaryId,
        )

        setSearchParams(
          (previous) => {
            const next =
              new URLSearchParams(
                previous,
              )

            next.set(
              'document',
              primaryId,
            )

            next.set(
              'documents',
              ids.join(','),
            )

            next.set(
              'conversation',
              String(
                conversationId,
              ),
            )

            return next
          },
          {
            replace: true,
          },
        )
      })
      .catch(() => {
        /*
         * History loading will report the actual
         * conversation error if one exists.
         */
      })

    return () => {
      cancelled = true
    }
  }, [
    conversationId,
    documentId,
    documentIdsParam,
    docsLoading,
    setLastDoc,
    setSearchParams,
  ])


  /* ---------------------------------------------------------------------- */
  /* Make sure selected IDs refer to ready documents                        */
  /* ---------------------------------------------------------------------- */

  useEffect(() => {
    if (
      readyDocs.length === 0
    ) {
      return
    }

    const readyIds =
      new Set(
        readyDocs.map(
          (doc) =>
            String(doc.id),
        ),
      )

    setSelectedDocumentIds(
      (current) => {
        const filtered =
          normalizeDocumentIds(
            current,
          ).filter(
            (id) =>
              readyIds.has(id),
          )

        if (
          filtered.length === 0 &&
          documentId &&
          readyIds.has(
            String(documentId),
          )
        ) {
          return [
            String(documentId),
          ]
        }

        return filtered
      },
    )
  }, [
    readyDocs,
    documentId,
  ])


  /*
   * Primary document.
   */
  const currentId =
    selectedDocumentIds[0] ||
    documentId ||
    ''


  /* ---------------------------------------------------------------------- */
  /* Chat state                                                             */
  /* ---------------------------------------------------------------------- */

  const [
    mode,
    setMode,
  ] = useState('carag')

  const [
    messages,
    setMessages,
  ] = useState([])

  const [
    historyState,
    setHistoryState,
  ] = useState('idle')

  const [
    historyError,
    setHistoryError,
  ] = useState('')

  const [
    reloadKey,
    setReloadKey,
  ] = useState(0)


  /* ---------------------------------------------------------------------- */
  /* UI refs                                                                */
  /* ---------------------------------------------------------------------- */

  const scrollRef =
    useRef(null)

  const activeDocRef =
    useRef('')

  const focusedRef =
    useRef('')


  /* ---------------------------------------------------------------------- */
  /* Current generation                                                     */
  /* ---------------------------------------------------------------------- */

  const generationKeys =
    useMemo(
      () =>
        getGenerationKeys(
          currentId,
          selectedDocumentIds,
          conversationId,
        ),
      [
        currentId,
        selectedDocumentIds,
        conversationId,
      ],
    )

  const currentGeneration =
    generationKeys
      .map(
        (key) =>
          generations[key],
      )
      .find(
        (generation) =>
          generation &&
          (
            !conversationId ||
            generation.conversationId ===
              conversationId
          ),
      ) ||
    null


  const sending =
    currentGeneration?.status ===
      'starting' ||
    currentGeneration?.status ===
      'streaming' ||
    currentGeneration?.status ===
      'generating'

  const sendingMode =
    currentGeneration?.mode ||
    mode


  /* ---------------------------------------------------------------------- */
  /* Active document ref                                                   */
  /* ---------------------------------------------------------------------- */

  useEffect(() => {
    activeDocRef.current =
      currentId
  }, [
    currentId,
  ])


  /* ---------------------------------------------------------------------- */
  /* Tell generation manager which chat is visible                         */
  /* ---------------------------------------------------------------------- */

  useEffect(() => {
    const ids =
      normalizeDocumentIds(
        selectedDocumentIds,
      )

    const primaryId =
      ids[0] ||
      currentId ||
      null

    setActiveChat({
      documentId:
        primaryId,

      documentIds:
        ids.length > 0
          ? ids
          : primaryId
            ? [primaryId]
            : [],

      conversationId:
        conversationId ||
        null,
    })
  }, [
    currentId,
    selectedDocumentIds,
    conversationId,
    setActiveChat,
  ])


  /* ---------------------------------------------------------------------- */
  /* Reopen last document                                                  */
  /* ---------------------------------------------------------------------- */

  useEffect(() => {
    if (
      docsLoading ||
      documentId ||
      conversationId ||
      location.state?.fresh
    ) {
      return
    }

    if (
      lastDoc &&
      readyDocs.some(
        (doc) =>
          String(doc.id) ===
          String(lastDoc),
      )
    ) {
      setSearchParams(
        (previous) => {
          const next =
            new URLSearchParams(
              previous,
            )

          next.set(
            'document',
            String(lastDoc),
          )

          next.set(
            'documents',
            String(lastDoc),
          )

          return next
        },
        {
          replace: true,
        },
      )
    }
  }, [
    docsLoading,
    documentId,
    conversationId,
    lastDoc,
    readyDocs,
    location.state,
    setSearchParams,
  ])


  /* ---------------------------------------------------------------------- */
  /* Validate document in URL                                              */
  /* ---------------------------------------------------------------------- */

  useEffect(() => {
    if (
      !docsLoading &&
      !docsError &&
      documentId &&
      !knownDoc
    ) {
      setSearchParams(
        {},
        {
          replace: true,
        },
      )
    }
  }, [
    docsLoading,
    docsError,
    documentId,
    knownDoc,
    setSearchParams,
  ])


  /* ---------------------------------------------------------------------- */
  /* Load conversation history                                             */
  /* ---------------------------------------------------------------------- */

  useEffect(() => {
    if (!currentId) {
      setMessages([])
      setHistoryState('idle')
      setHistoryError('')

      return undefined
    }

    let cancelled = false

    setHistoryState(
      'loading',
    )

    setHistoryError('')

    getHistory(
      currentId,
      conversationId || null,
    )
      .then((rows) => {
        if (cancelled) {
          return
        }

        setMessages(
          normalizeHistory(
            Array.isArray(rows)
              ? rows
              : [],
          ),
        )

        setHistoryState(
          'ready',
        )
      })
      .catch((error) => {
        if (cancelled) {
          return
        }

        setHistoryError(
          describeError(
            error,
            'Could not load this conversation.',
          ),
        )

        setHistoryState(
          'error',
        )
      })

    return () => {
      cancelled = true
    }
  }, [
    currentId,
    conversationId,
    reloadKey,
  ])


  /* ---------------------------------------------------------------------- */
  /* Merge background generation into history                              */
  /* ---------------------------------------------------------------------- */

  const displayMessages =
    useMemo(() => {
      if (!currentGeneration) {
        return messages
      }

      const liveMessage =
        generationToMessage(
          currentGeneration,
        )

      if (!liveMessage) {
        return messages
      }

      const generationMessageId =
        currentGeneration.message_id

      /*
       * Prevent duplicate final messages.
       */
      if (
        generationMessageId &&
        messages.some(
          (message) =>
            getMessageId(
              message,
            ) ===
            generationMessageId,
        )
      ) {
        return messages
      }

      return [
        ...messages,
        liveMessage,
      ]
    }, [
      messages,
      currentGeneration,
    ])


  /* ---------------------------------------------------------------------- */
  /* Auto-scroll                                                            */
  /* ---------------------------------------------------------------------- */

  useEffect(() => {
    const element =
      scrollRef.current

    if (
      !element ||
      historyState !== 'ready'
    ) {
      return
    }

    if (
      focusMessage &&
      focusedRef.current !==
        focusMessage
    ) {
      const target =
        document.getElementById(
          `m-${focusMessage}`,
        )

      if (target) {
        focusedRef.current =
          focusMessage

        target.scrollIntoView({
          block: 'center',
        })

        target.classList.add(
          'is-linked',
        )

        return
      }
    }

    element.scrollTo({
      top:
        element.scrollHeight,

      behavior:
        focusedRef.current
          ? 'auto'
          : 'smooth',
    })
  }, [
    displayMessages,
    sending,
    historyState,
    focusMessage,
  ])


  /* ---------------------------------------------------------------------- */
  /* Select documents                                                       */
  /* ---------------------------------------------------------------------- */

  const selectDoc =
    useCallback(
      async (ids) => {
        const normalizedIds =
          normalizeDocumentIds(
            ids,
          )

        if (
          normalizedIds.length ===
          0
        ) {
          return
        }

        let resolvedConversationId = conversationId
        if (!resolvedConversationId) {
          try {
            const conversation =
              await createConversation({
                title: 'New chat',
                documentIds: normalizedIds,
              })

            resolvedConversationId =
              String(conversation.id)
          } catch (error) {
            setHistoryError(
              describeError(
                error,
                'Could not start a new chat.',
              ),
            )
            setHistoryState('error')
            return
          }
        }

        setSelectedDocumentIds(
          normalizedIds,
        )

        const primaryId =
          normalizedIds[0]

        /*
         * Preserve the conversation ID while
         * changing the document selection.
         */
        setSearchParams(
          (previous) => {
            const next =
              new URLSearchParams(
                previous,
              )

            next.set(
              'document',
              primaryId,
            )

            next.set(
              'documents',
              normalizedIds.join(','),
            )

            next.set(
              'conversation',
              resolvedConversationId,
            )

            return next
          },
        )

        setLastDoc(
          primaryId,
        )

        focusedRef.current =
          ''

        window.dispatchEvent(
          new Event('carag:conversation-updated'),
        )
      },
      [
        conversationId,
        setSearchParams,
        setLastDoc,
        setHistoryError,
        setHistoryState,
      ],
    )


  /* ---------------------------------------------------------------------- */
  /* Send message                                                           */
  /* ---------------------------------------------------------------------- */

  const send =
    useCallback(
      (
        text,
        options = {},
      ) => {
        const query =
          String(text || '')
            .trim()

        if (
          !query ||
          !currentId ||
          sending
        ) {
          return
        }

        const selectedIds =
          normalizeDocumentIds(
            selectedDocumentIds,
          )

        const documentIds =
          selectedIds.length > 0
            ? selectedIds
            : [
                currentId,
              ]

        const primaryDocumentId =
          documentIds[0]

        const usedMode =
          options.mode ||
          mode

        const stamp =
          Date.now()

        /*
         * Add user message immediately.
         */
        if (!options.retry) {
          setMessages(
            (current) => [
              ...current,

              {
                key:
                  `u-${stamp}`,

                role: 'user',

                content: {
                  query,

                  document_ids:
                    documentIds,
                },
              },
            ],
          )
        }

        /*
         * Start persistent background generation.
         *
         * IMPORTANT:
         * When this is the first message of a new chat,
         * the backend can create the conversation.
         *
         * Once the generation completes, we put the
         * returned conversation ID into the URL.
         */
        void startGeneration({
          documentId:
            primaryDocumentId,

          documentIds,

          conversationId:
            conversationId ||
            null,

          query,

          mode:
            usedMode,
        })
          .then(
            (generation) => {
              if (
                !mountedRef.current
              ) {
                return
              }

              /*
               * Existing conversation:
               * nothing needs to be changed.
               */
              if (conversationId) {
                return
              }

              const resolvedConversationId =
                generation?.conversationId ||
                generation?.conversation_id ||
                null

              if (
                !resolvedConversationId
              ) {
                return
              }

              /*
               * Preserve the document/documentIds
               * parameters while adding conversation.
               */
              setSearchParams(
                (previous) => {
                  const next =
                    new URLSearchParams(
                      previous,
                    )

                  next.set(
                    'document',
                    primaryDocumentId,
                  )

                  next.set(
                    'documents',
                    documentIds.join(','),
                  )

                  next.set(
                    'conversation',
                    String(
                      resolvedConversationId,
                    ),
                  )

                  return next
                },
                {
                  replace: true,
                },
              )

              /*
               * Tell Recents to reload.
               */
              window.dispatchEvent(
                new CustomEvent(
                  'carag:conversation-updated',
                  {
                    detail: {
                      conversationId:
                        String(
                          resolvedConversationId,
                        ),
                    },
                  },
                ),
              )
            },
          )
          .catch(() => {
            /*
             * startGeneration already manages
             * generation errors.
             */
          })
      },
      [
        currentId,
        selectedDocumentIds,
        conversationId,
        mode,
        sending,
        startGeneration,
        setSearchParams,
      ],
    )


  /* ---------------------------------------------------------------------- */
  /* Retry                                                                  */
  /* ---------------------------------------------------------------------- */

  const retry =
    useCallback(
      (errorMessage) => {
        setMessages(
          (current) =>
            current.filter(
              (message) =>
                message.key !==
                errorMessage.key,
            ),
        )

        send(
          errorMessage
            ?.content
            ?.query || '',

          {
            retry: true,

            mode:
              errorMessage
                ?.content
                ?.mode ||
              mode,
          },
        )
      },
      [
        send,
        mode,
      ],
    )


  /* ---------------------------------------------------------------------- */
  /* Conversation body                                                      */
  /* ---------------------------------------------------------------------- */

  let body

  if (docsLoading) {
    body = (
      <Skeleton
        lines={4}
      />
    )
  } else if (
    docsError &&
    docs.length === 0
  ) {
    body = (
      <ErrorNotice
        title="Can't load your documents"
        message={docsError}
        onRetry={refresh}
      />
    )
  } else if (
    readyDocs.length === 0
  ) {
    const pending =
      docs.some(
        (doc) =>
          doc.status ===
          'processing',
      )

    body =
      pending ? (
        <ChatEmptyState
          variant="unavailable"
          note="Your document is still being processed. It will be ready to ask about in a moment."
        />
      ) : (
        <ChatEmptyState
          variant="no-docs"
          onUpload={refresh}
        />
      )
  } else if (
    knownDoc &&
    !currentDoc
  ) {
    body = (
      <ChatEmptyState
        variant="unavailable"
        note={
          knownDoc.status ===
          'failed'
            ? 'This document could not be processed. Delete it and upload it again.'
            : 'This document is still being processed.'
        }
      />
    )
  } else if (!currentDoc) {
    body = (
      <ChatEmptyState
        variant="choose"
        docs={readyDocs}
        onSelect={selectDoc}
        onUpload={refresh}
      />
    )
  } else if (
    historyState ===
      'loading' ||
    historyState === 'idle'
  ) {
    body = (
      <Skeleton
        lines={5}
      />
    )
  } else if (
    historyState ===
    'error'
  ) {
    body = (
      <ErrorNotice
        title="Can't load this conversation"
        message={
          historyError
        }
        onRetry={() =>
          setReloadKey(
            (key) =>
              key + 1,
          )
        }
      />
    )
  } else if (
    displayMessages.length ===
    0
  ) {
    body = (
      <ChatEmptyState
        variant="ask"
        docName={
          currentDoc.filename
        }
      />
    )
  } else {
    body = (
      <MessageList
        messages={
          displayMessages
        }
        onRetry={retry}
      >
        {sending &&
          !currentGeneration?.answer && (
            <TypingIndicator
              mode={sendingMode}
            />
          )}
      </MessageList>
    )
  }


  /* ---------------------------------------------------------------------- */
  /* Composer                                                               */
  /* ---------------------------------------------------------------------- */

  const placeholder =
    currentDoc
      ? selectedDocumentIds.length >
        1
        ? 'Ask a question across your selected PDFs…'
        : 'Ask a question about your research paper…'
      : 'Choose a document to start asking questions'


  /* ---------------------------------------------------------------------- */
  /* Render                                                                 */
  /* ---------------------------------------------------------------------- */

  return (
    <div className="chat">

      <div className="chat-bar">
        <DocumentSelector
          docs={readyDocs}

          selectedIds={
            selectedDocumentIds
          }

          loading={
            docsLoading
          }

          onSelect={
            selectDoc
          }
        />
      </div>


      <div
        className="chat-scroll"
        ref={scrollRef}
      >
        <div className="chat-column">
          {body}
        </div>
      </div>


      <div className="chat-dock">
        <div className="chat-column">

          <ChatComposer
            onSend={(text) =>
              send(text)
            }

            sending={
              sending
            }

            disabled={
              !currentDoc ||
              historyState !==
                'ready'
            }

            placeholder={
              placeholder
            }

            mode={
              mode
            }

            onModeChange={
              setMode
            }
          />

        </div>
      </div>

    </div>
  )
}