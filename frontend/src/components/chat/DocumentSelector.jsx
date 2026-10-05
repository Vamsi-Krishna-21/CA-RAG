import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import useDismiss from '../../hooks/useDismiss.js'
import Icon from '../common/Icon.jsx'

export default function DocumentSelector({
  docs = [],
  selectedIds = [],
  loading = false,
  onSelect,
}) {
  const [open, setOpen] = useState(false)
  const [draftIds, setDraftIds] = useState(
    Array.isArray(selectedIds)
      ? selectedIds
      : [],
  )

  const ref = useRef(null)

  /**
   * Keep the draft selection synchronized with
   * the parent's actual selection when the selector
   * is closed.
   */
  useEffect(() => {
    if (!open) {
      setDraftIds(
        Array.isArray(selectedIds)
          ? selectedIds
          : [],
      )
    }
  }, [selectedIds, open])

  const close = useCallback(() => {
    setOpen(false)
  }, [])

  useDismiss(ref, open, close)

  const safeSelectedIds = useMemo(
    () =>
      Array.isArray(selectedIds)
        ? selectedIds
        : [],
    [selectedIds],
  )

  const selectedDocuments = useMemo(
    () =>
      docs.filter((document) =>
        safeSelectedIds.includes(
          document.id,
        ),
      ),
    [docs, safeSelectedIds],
  )

  const selectedCount =
    selectedDocuments.length

  const label =
    selectedCount > 0
      ? selectedCount === 1
        ? selectedDocuments[0].filename
        : `${selectedCount} documents selected`
      : loading
        ? 'Loading documents…'
        : docs.length
          ? 'Select documents'
          : 'No documents ready'

  const toggleDocument = (id) => {
    setDraftIds((current) => {
      const currentIds =
        Array.isArray(current)
          ? current
          : []

      return currentIds.includes(id)
        ? currentIds.filter(
            (item) => item !== id,
          )
        : [...currentIds, id]
    })
  }

  const selectAll = () => {
    setDraftIds(
      docs.map((document) => document.id),
    )
  }

  const clearSelection = () => {
    setDraftIds([])
  }

  const openSelector = () => {
    setDraftIds(safeSelectedIds)
    setOpen((current) => !current)
  }

  const applySelection = () => {
    const uniqueIds = [
      ...new Set(
        Array.isArray(draftIds)
          ? draftIds
          : [],
      ),
    ]

    onSelect?.(uniqueIds)
    close()
  }

  const draftCount =
    Array.isArray(draftIds)
      ? draftIds.length
      : 0

  return (
    <div
      className="docsel"
      ref={ref}
    >
      <button
        type="button"
        className="docsel-btn"
        aria-haspopup="true"
        aria-expanded={open}
        disabled={
          loading ||
          docs.length === 0
        }
        onClick={openSelector}
        title={
          selectedCount > 0
            ? selectedDocuments
                .map(
                  (document) =>
                    document.filename,
                )
                .join(', ')
            : undefined
        }
      >
        <Icon
          name="doc"
          size={16}
        />

        <span className="docsel-label">
          {label}
        </span>

        <Icon
          name="chevronDown"
          size={16}
        />
      </button>

      {open && (
        <div
          className="docsel-list"
          role="group"
          aria-label="Choose documents"
        >
          <div className="docsel-actions">
            <button
              type="button"
              className="docsel-action"
              disabled={
                docs.length === 0
              }
              onClick={selectAll}
            >
              Select all
            </button>

            <button
              type="button"
              className="docsel-action"
              disabled={
                draftCount === 0
              }
              onClick={clearSelection}
            >
              Clear
            </button>
          </div>

          {docs.map((document) => {
            const selected =
              Array.isArray(draftIds) &&
              draftIds.includes(
                document.id,
              )

            return (
              <button
                key={document.id}
                type="button"
                className={
                  'docsel-item' +
                  (selected
                    ? ' selected'
                    : '')
                }
                aria-pressed={selected}
                onClick={() =>
                  toggleDocument(
                    document.id,
                  )
                }
              >
                <span className="docsel-item-name">
                  {document.filename}
                </span>

                <span className="docsel-item-meta">
                  {document.pages}{' '}
                  {document.pages === 1
                    ? 'page'
                    : 'pages'}
                </span>

                {selected && (
                  <Icon
                    name="check"
                    size={15}
                  />
                )}
              </button>
            )
          })}

          <button
            type="button"
            className="docsel-foot"
            disabled={
              draftCount === 0
            }
            onClick={applySelection}
          >
            Done
            {draftCount > 0
              ? ` (${draftCount})`
              : ''}
          </button>

          <Link
            className="docsel-foot"
            to="/documents"
            onClick={close}
          >
            Manage documents
          </Link>
        </div>
      )}
    </div>
  )
}