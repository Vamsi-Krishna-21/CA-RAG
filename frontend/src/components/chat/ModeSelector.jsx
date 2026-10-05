import { MODES } from '../../utils/verification.js'

const ORDER = ['carag', 'traditional']

export default function ModeSelector({ mode, onChange, disabled }) {
  const onKeyDown = (e) => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return
    e.preventDefault()
    const i = ORDER.indexOf(mode)
    const next = ORDER[(i + (e.key === 'ArrowRight' ? 1 : ORDER.length - 1)) % ORDER.length]
    onChange(next)
  }

  return (
    <div className="mode">
      <div className="segmented" role="radiogroup" aria-label="Answer mode" aria-describedby="mode-hint" onKeyDown={onKeyDown}>
        {ORDER.map((key) => (
          <button
            key={key}
            type="button"
            role="radio"
            aria-checked={mode === key}
            tabIndex={mode === key ? 0 : -1}
            disabled={disabled}
            onClick={() => onChange(key)}
          >
            {MODES[key].label}
          </button>
        ))}
      </div>
      <span id="mode-hint" className="mode-hint">{MODES[mode].hint}</span>
    </div>
  )
}
