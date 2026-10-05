export default function Skeleton({ lines = 3, widths = ['92%', '78%', '60%'] }) {
  return (
    <div className="skeleton-stack" aria-hidden="true">
      {Array.from({ length: lines }).map((_, i) => (
        <span key={i} className="skeleton" style={{ width: widths[i % widths.length] }} />
      ))}
    </div>
  )
}
