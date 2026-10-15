interface Props {
  label: string
  value: number
  max: number
}

/** A single labelled horizontal bar - used for simple "count by X" breakdowns (FR-077/084). */
export default function BarRow({ label, value, max }: Props) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0
  return (
    <div className="bar-row">
      <span className="bar-label">{label}</span>
      <div className="bar-track"><div className="bar-fill" style={{ width: `${pct}%` }} /></div>
      <span className="bar-value">{value}</span>
    </div>
  )
}
