import { useEffect, useRef, useState } from 'react'
import Icon from '../common/Icon.jsx'
import ModeSelector from './ModeSelector.jsx'

const MAX_HEIGHT = 200

export default function ChatComposer({ onSend, sending, disabled, placeholder, mode, onModeChange }) {
  const [text, setText] = useState('')
  const ref = useRef(null)

  // Auto-grow up to MAX_HEIGHT, then scroll.
  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`
  }, [text])

  // Return focus to the box once an answer arrives (not on first load, so mobile keyboards stay closed).
  const wasSending = useRef(false)
  useEffect(() => {
    if (wasSending.current && !sending) ref.current?.focus()
    wasSending.current = sending
  }, [sending])

  const canSend = !disabled && !sending && text.trim().length > 0

  const submit = () => {
    if (!canSend) return
    onSend(text)
    setText('')
  }

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <form
      className={'composer' + (disabled ? ' is-disabled' : '')}
      onSubmit={(e) => {
        e.preventDefault()
        submit()
      }}
    >
      <label htmlFor="chat-input" className="sr-only">Your question</label>
      <textarea
        id="chat-input"
        ref={ref}
        rows={1}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        readOnly={sending}
        aria-busy={sending}
      />
      <div className="composer-bar">
        <ModeSelector mode={mode} onChange={onModeChange} disabled={sending} />
        <button type="submit" className="send-btn" disabled={!canSend} aria-label={sending ? 'Sending' : 'Send message'}>
          {sending ? <span className="spinner spinner-on-dark" /> : <Icon name="arrowUp" size={18} />}
        </button>
      </div>
      <p className="composer-tip">Enter to send · Shift + Enter for a new line</p>
    </form>
  )
}
