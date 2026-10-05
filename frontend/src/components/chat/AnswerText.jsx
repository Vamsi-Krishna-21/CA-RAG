// Renders the answer text with paragraph spacing, simple lists, **bold** and `code`.
// Everything is emitted as React text nodes (no HTML injection).

const BULLET = /^\s*[-*•]\s+(.*)$/
const NUMBERED = /^\s*\d+[.)]\s+(.*)$/

function inline(text, keyBase) {
  const out = []
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g
  let last = 0
  let m
  let i = 0
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(text.slice(last, m.index))
    const tok = m[0]
    out.push(
      tok.startsWith('**')
        ? <strong key={`${keyBase}-${i++}`}>{tok.slice(2, -2)}</strong>
        : <code key={`${keyBase}-${i++}`}>{tok.slice(1, -1)}</code>,
    )
    last = m.index + tok.length
  }
  if (last < text.length) out.push(text.slice(last))
  return out
}

export function parseBlocks(text) {
  const blocks = []
  const lines = String(text || '').replace(/\r\n/g, '\n').split('\n')
  let para = []
  let list = null

  const flushPara = () => {
    if (para.length) blocks.push({ type: 'p', lines: para })
    para = []
  }
  const flushList = () => {
    if (list) blocks.push(list)
    list = null
  }

  for (const line of lines) {
    if (!line.trim()) {
      flushPara()
      flushList()
      continue
    }
    const b = line.match(BULLET)
    const n = line.match(NUMBERED)
    if (b || n) {
      flushPara()
      const type = b ? 'ul' : 'ol'
      if (!list || list.type !== type) {
        flushList()
        list = { type, items: [] }
      }
      list.items.push((b || n)[1])
    } else {
      flushList()
      para.push(line.trim())
    }
  }
  flushPara()
  flushList()
  return blocks
}

export default function AnswerText({ text }) {
  const blocks = parseBlocks(text)
  return (
    <div className="answer">
      {blocks.map((b, i) => {
        if (b.type === 'ul' || b.type === 'ol') {
          const List = b.type
          return (
            <List key={i}>
              {b.items.map((item, j) => (
                <li key={j}>{inline(item, `${i}-${j}`)}</li>
              ))}
            </List>
          )
        }
        return (
          <p key={i}>
            {b.lines.map((l, j) => (
              <span key={j}>
                {j > 0 && <br />}
                {inline(l, `${i}-${j}`)}
              </span>
            ))}
          </p>
        )
      })}
    </div>
  )
}
