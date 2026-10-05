import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '../common/Icon.jsx'

import {
  listConversations,
  renameConversation,
  togglePinConversation,
  toggleArchiveConversation,
  deleteConversation,
  shareConversation,
} from '../../services/conversationApi.js'

export default function SidebarDocuments({
  activeId,
  onNavigate,
}) {
  const [conversations, setConversations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [openMenuId, setOpenMenuId] = useState(null)
  const [busyId, setBusyId] = useState(null)

  // Inline rename state
  const [renamingId, setRenamingId] = useState(null)
  const [renameValue, setRenameValue] = useState('')

  // Delete / archive confirmation
  const [confirmAction, setConfirmAction] = useState(null)

  // Small success/info message
  const [toast, setToast] = useState(null)

  const menuRef = useRef(null)
  const renameInputRef = useRef(null)

  const loadConversations = async () => {
    try {
      setLoading(true)
      setError('')

      const data = await listConversations()

      setConversations(
        Array.isArray(data)
          ? data
          : [],
      )
    } catch (err) {
      setError(
        err?.message ||
        'Could not load recent chats.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadConversations()

    const handleRefresh = () => {
      loadConversations()
    }

    window.addEventListener(
      'carag:conversation-updated',
      handleRefresh,
    )

    return () => {
      window.removeEventListener(
        'carag:conversation-updated',
        handleRefresh,
      )
    }
  }, [])

  // Close menu when clicking outside.
  useEffect(() => {
    const handleOutsideClick = (event) => {
      if (
        menuRef.current &&
        !menuRef.current.contains(event.target)
      ) {
        setOpenMenuId(null)
      }
    }

    document.addEventListener(
      'mousedown',
      handleOutsideClick,
    )

    return () => {
      document.removeEventListener(
        'mousedown',
        handleOutsideClick,
      )
    }
  }, [])

  // Focus rename input when rename mode starts.
  useEffect(() => {
    if (renamingId && renameInputRef.current) {
      renameInputRef.current.focus()
      renameInputRef.current.select()
    }
  }, [renamingId])

  // Close confirmation modal with Escape.
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        if (confirmAction) {
          setConfirmAction(null)
        } else if (renamingId) {
          cancelRename()
        }
      }
    }

    document.addEventListener(
      'keydown',
      handleKeyDown,
    )

    return () => {
      document.removeEventListener(
        'keydown',
        handleKeyDown,
      )
    }
  }, [confirmAction, renamingId])

  // Automatically hide toast.
  useEffect(() => {
    if (!toast) return

    const timer = window.setTimeout(() => {
      setToast(null)
    }, 2800)

    return () => {
      window.clearTimeout(timer)
    }
  }, [toast])

  const notifyConversationChanged = () => {
    window.dispatchEvent(
      new Event('carag:conversation-updated'),
    )
  }

  const showToast = (
    message,
    type = 'success',
  ) => {
    setToast({
      message,
      type,
    })
  }

  const runAction = async (
    conversationId,
    action,
  ) => {
    try {
      setBusyId(conversationId)
      setError('')

      await action()

      setOpenMenuId(null)

      await loadConversations()

      notifyConversationChanged()
    } catch (err) {
      setError(
        err?.message ||
        'Could not update conversation.',
      )
    } finally {
      setBusyId(null)
    }
  }

  /*
   * ---------------- Rename ----------------
   */

  const startRename = (conversation) => {
    setOpenMenuId(null)

    const currentTitle =
      conversation.title?.trim() ||
      'New chat'

    setRenamingId(conversation.id)
    setRenameValue(currentTitle)
  }

  const cancelRename = () => {
    setRenamingId(null)
    setRenameValue('')
  }

  const saveRename = async (conversation) => {
    const currentTitle =
      conversation.title?.trim() ||
      'New chat'

    const trimmedTitle =
      renameValue.trim()

    if (!trimmedTitle) {
      setError('Chat name cannot be empty.')
      return
    }

    if (trimmedTitle === currentTitle) {
      cancelRename()
      return
    }

    try {
      setBusyId(conversation.id)
      setError('')

      await renameConversation(
        conversation.id,
        trimmedTitle,
      )

      setConversations((current) =>
        current.map((item) =>
          item.id === conversation.id
            ? {
                ...item,
                title: trimmedTitle,
              }
            : item,
        ),
      )

      setRenamingId(null)
      setRenameValue('')

      notifyConversationChanged()

      showToast(
        'Chat renamed successfully.',
      )
    } catch (err) {
      setError(
        err?.message ||
        'Could not rename chat.',
      )
    } finally {
      setBusyId(null)
    }
  }

  const handleRenameKeyDown = (
    event,
    conversation,
  ) => {
    if (event.key === 'Enter') {
      event.preventDefault()
      saveRename(conversation)
    }

    if (event.key === 'Escape') {
      event.preventDefault()
      cancelRename()
    }
  }

  /*
   * ---------------- Pin ----------------
   */

  const handlePin = async (conversation) => {
    await runAction(
      conversation.id,
      () =>
        togglePinConversation(
          conversation.id,
        ),
    )

    showToast(
      conversation.pinned
        ? 'Chat unpinned.'
        : 'Chat pinned.',
    )
  }

  /*
   * ---------------- Archive ----------------
   */

  const requestArchive = (conversation) => {
    setOpenMenuId(null)

    setConfirmAction({
      type: 'archive',
      conversation,
    })
  }

  const confirmArchive = async () => {
    if (!confirmAction) return

    const conversation =
      confirmAction.conversation

    setConfirmAction(null)

    try {
      setBusyId(conversation.id)
      setError('')

      await toggleArchiveConversation(
        conversation.id,
      )

      setConversations((current) =>
        current.filter(
          (item) =>
            item.id !== conversation.id,
        ),
      )

      notifyConversationChanged()

      showToast(
        'Chat archived.',
      )

      if (activeId === conversation.id) {
        window.history.pushState(
          {},
          '',
          '/',
        )

        window.dispatchEvent(
          new PopStateEvent('popstate'),
        )
      }
    } catch (err) {
      setError(
        err?.message ||
        'Could not archive conversation.',
      )
    } finally {
      setBusyId(null)
    }
  }

  /*
   * ---------------- Delete ----------------
   */

  const requestDelete = (conversation) => {
    setOpenMenuId(null)

    setConfirmAction({
      type: 'delete',
      conversation,
    })
  }

  const confirmDelete = async () => {
    if (!confirmAction) return

    const conversation =
      confirmAction.conversation

    setConfirmAction(null)

    try {
      setBusyId(conversation.id)
      setError('')

      await deleteConversation(
        conversation.id,
      )

      setConversations((current) =>
        current.filter(
          (item) =>
            item.id !== conversation.id,
        ),
      )

      notifyConversationChanged()

      showToast(
        'Chat deleted.',
      )

      if (activeId === conversation.id) {
        window.history.pushState(
          {},
          '',
          '/',
        )

        window.dispatchEvent(
          new PopStateEvent('popstate'),
        )
      }
    } catch (err) {
      setError(
        err?.message ||
        'Could not delete conversation.',
      )
    } finally {
      setBusyId(null)
    }
  }

  /*
   * ---------------- Share ----------------
   */

  const handleShare = async (conversation) => {
    setOpenMenuId(null)

    try {
      setBusyId(conversation.id)
      setError('')

      const result =
        await shareConversation(
          conversation.id,
        )

      const token =
        result?.share_token ||
        result?.token

      if (!token) {
        throw new Error(
          'Share token was not returned.',
        )
      }

      const shareUrl =
        `${window.location.origin}/shared/${token}`

      try {
        await navigator.clipboard.writeText(
          shareUrl,
        )

        showToast(
          'Share link copied to clipboard.',
        )
      } catch {
        showToast(
          'Share link created. Clipboard access was unavailable.',
          'info',
        )
      }
    } catch (err) {
      setError(
        err?.message ||
        'Could not create share link.',
      )
    } finally {
      setBusyId(null)
    }
  }

  /*
   * ---------------- Menu ----------------
   */

  const toggleMenu = (
    event,
    conversationId,
  ) => {
    event.preventDefault()
    event.stopPropagation()

    setOpenMenuId((current) =>
      current === conversationId
        ? null
        : conversationId,
    )
  }

  const handleActionClick = (
    event,
    callback,
  ) => {
    event.preventDefault()
    event.stopPropagation()
    callback()
  }

  return (
    <>
      <section
        className="side-docs"
        aria-label="Recent chats"
      >
        <div className="side-docs-head">
          <span className="side-heading">
            Recents
          </span>
        </div>

        {loading ? (
          <div className="side-note">
            Loading…
          </div>
        ) : error ? (
          <div
            className="side-note side-note-error"
            role="alert"
          >
            {error}
          </div>
        ) : conversations.length === 0 ? (
          <div className="side-note">
            No recent chats.
          </div>
        ) : (
          <ul className="side-doc-list">
            {conversations.map(
              (conversation) => {
                const title =
                  conversation.title?.trim() ||
                  'New chat'

                const conversationId =
                  conversation.id

                const isMenuOpen =
                  openMenuId ===
                  conversationId

                const isBusy =
                  busyId ===
                  conversationId

                const isPinned =
                  conversation.pinned === true

                const isRenaming =
                  renamingId ===
                  conversationId

                return (
                  <li
                    key={conversationId}
                    className="side-chat-item"
                    ref={
                      isMenuOpen
                        ? menuRef
                        : undefined
                    }
                  >
                    <div
                      className={
                        'side-chat-row' +
                        (
                          activeId ===
                          conversationId
                            ? ' active'
                            : ''
                        )
                      }
                    >
                      {isRenaming ? (
                        <div className="side-chat-rename">
                          <Icon
                            name="chat"
                            size={16}
                          />

                          <input
                            ref={
                              renameInputRef
                            }
                            className="side-chat-rename-input"
                            value={renameValue}
                            onChange={(event) =>
                              setRenameValue(
                                event.target.value,
                              )
                            }
                            onKeyDown={(event) =>
                              handleRenameKeyDown(
                                event,
                                conversation,
                              )
                            }
                            disabled={isBusy}
                            maxLength={200}
                            aria-label="Chat name"
                          />

                          <button
                            type="button"
                            className="side-chat-rename-action save"
                            onClick={() =>
                              saveRename(
                                conversation,
                              )
                            }
                            disabled={
                              isBusy ||
                              !renameValue.trim()
                            }
                            title="Save"
                            aria-label="Save chat name"
                          >
                            <Icon
                              name="check"
                              size={15}
                            />
                          </button>

                          <button
                            type="button"
                            className="side-chat-rename-action cancel"
                            onClick={
                              cancelRename
                            }
                            disabled={isBusy}
                            title="Cancel"
                            aria-label="Cancel rename"
                          >
                            <Icon
                              name="close"
                              size={15}
                            />
                          </button>
                        </div>
                      ) : (
                        <>
                          <Link
                            to={`/chat?conversation=${conversationId}`}
                            className="side-doc"
                            aria-current={
                              activeId ===
                              conversationId
                                ? 'true'
                                : undefined
                            }
                            title={title}
                            onClick={onNavigate}
                          >
                            <Icon
                              name="chat"
                              size={16}
                            />

                            <span className="side-doc-name">
                              {title}
                            </span>

                            {isPinned && (
                              <span
                                className="side-chat-pin"
                                title="Pinned"
                                aria-label="Pinned"
                              >
                                <Icon
                                  name="pin"
                                  size={13}
                                />
                              </span>
                            )}
                          </Link>

                          <button
                            type="button"
                            className={
                              'side-chat-menu-btn' +
                              (
                                isMenuOpen
                                  ? ' is-open'
                                  : ''
                              )
                            }
                            onClick={(event) =>
                              toggleMenu(
                                event,
                                conversationId,
                              )
                            }
                            disabled={isBusy}
                            aria-label={`Actions for ${title}`}
                            aria-haspopup="menu"
                            aria-expanded={
                              isMenuOpen
                            }
                            title="Chat actions"
                          >
                            <Icon
                              name="more"
                              size={17}
                            />
                          </button>

                          {isMenuOpen && (
                            <div
                              className="side-chat-menu"
                              role="menu"
                            >
                              <button
                                type="button"
                                className="side-chat-menu-item"
                                role="menuitem"
                                disabled={isBusy}
                                onClick={(event) =>
                                  handleActionClick(
                                    event,
                                    () =>
                                      handleShare(
                                        conversation,
                                      ),
                                  )
                                }
                              >
                                <Icon
                                  name="share"
                                  size={16}
                                />
                                <span>
                                  Share
                                </span>
                              </button>

                              <button
                                type="button"
                                className="side-chat-menu-item"
                                role="menuitem"
                                disabled={isBusy}
                                onClick={(event) =>
                                  handleActionClick(
                                    event,
                                    () =>
                                      startRename(
                                        conversation,
                                      ),
                                  )
                                }
                              >
                                <Icon
                                  name="edit"
                                  size={16}
                                />
                                <span>
                                  Rename
                                </span>
                              </button>

                              <button
                                type="button"
                                className="side-chat-menu-item"
                                role="menuitem"
                                disabled={isBusy}
                                onClick={(event) =>
                                  handleActionClick(
                                    event,
                                    () =>
                                      handlePin(
                                        conversation,
                                      ),
                                  )
                                }
                              >
                                <Icon
                                  name="pin"
                                  size={16}
                                />
                                <span>
                                  {isPinned
                                    ? 'Unpin chat'
                                    : 'Pin chat'}
                                </span>
                              </button>

                              <button
                                type="button"
                                className="side-chat-menu-item"
                                role="menuitem"
                                disabled={isBusy}
                                onClick={(event) =>
                                  handleActionClick(
                                    event,
                                    () =>
                                      requestArchive(
                                        conversation,
                                      ),
                                  )
                                }
                              >
                                <Icon
                                  name="archive"
                                  size={16}
                                />
                                <span>
                                  Archive
                                </span>
                              </button>

                              <div className="side-chat-menu-divider" />

                              <button
                                type="button"
                                className="side-chat-menu-item danger"
                                role="menuitem"
                                disabled={isBusy}
                                onClick={(event) =>
                                  handleActionClick(
                                    event,
                                    () =>
                                      requestDelete(
                                        conversation,
                                      ),
                                  )
                                }
                              >
                                <Icon
                                  name="trash"
                                  size={16}
                                />
                                <span>
                                  Delete
                                </span>
                              </button>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  </li>
                )
              },
            )}
          </ul>
        )}
      </section>

      {/* ---------------- Delete / Archive Modal ---------------- */}

      {confirmAction && (
        <div
          className="chat-confirm-overlay"
          role="presentation"
          onMouseDown={(event) => {
            if (
              event.target ===
              event.currentTarget
            ) {
              setConfirmAction(null)
            }
          }}
        >
          <div
            className="chat-confirm-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="chat-confirm-title"
          >
            <div className="chat-confirm-icon">
              <Icon
                name={
                  confirmAction.type ===
                  'delete'
                    ? 'trash'
                    : 'archive'
                }
                size={20}
              />
            </div>

            <div className="chat-confirm-content">
              <h2
                id="chat-confirm-title"
                className="chat-confirm-title"
              >
                {confirmAction.type ===
                'delete'
                  ? 'Delete chat?'
                  : 'Archive chat?'}
              </h2>

              <p className="chat-confirm-text">
                <strong>
                  {confirmAction.conversation
                    .title?.trim() ||
                    'New chat'}
                </strong>
                {confirmAction.type ===
                'delete'
                  ? ' will be permanently deleted along with its messages.'
                  : ' will be moved out of Recents. You can keep the conversation and restore it later.'}
              </p>

              {confirmAction.type ===
                'delete' && (
                <p className="chat-confirm-note">
                  Your uploaded documents
                  will not be deleted.
                </p>
              )}
            </div>

            <div className="chat-confirm-actions">
              <button
                type="button"
                className="chat-confirm-cancel"
                onClick={() =>
                  setConfirmAction(null)
                }
              >
                Cancel
              </button>

              <button
                type="button"
                className={
                  'chat-confirm-primary' +
                  (
                    confirmAction.type ===
                    'delete'
                      ? ' danger'
                      : ''
                  )
                }
                onClick={
                  confirmAction.type ===
                  'delete'
                    ? confirmDelete
                    : confirmArchive
                }
              >
                {confirmAction.type ===
                'delete'
                  ? 'Delete'
                  : 'Archive'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ---------------- Toast ---------------- */}

      {toast && (
        <div
          className={
            'chat-action-toast' +
            (
              toast.type === 'info'
                ? ' info'
                : ''
            )
          }
          role="status"
        >
          <span className="chat-action-toast-icon">
            <Icon
              name={
                toast.type === 'info'
                  ? 'alert'
                  : 'check'
              }
              size={16}
            />
          </span>

          <span>
            {toast.message}
          </span>

          <button
            type="button"
            className="chat-action-toast-close"
            onClick={() =>
              setToast(null)
            }
            aria-label="Close notification"
          >
            <Icon
              name="close"
              size={14}
            />
          </button>
        </div>
      )}
    </>
  )
}