import { useEffect, useState } from 'react'
import { listCustomPriorities } from '../api/customPriorities'
import { PRIORITIES, PRIORITY_LABELS } from '../lib/labels'
import type { CustomPriority, Priority } from '../types'

interface Props {
  priority: Priority
  customPriorityId: number | null
  onChange: (priority: Priority, customPriorityId: number | null) => void
}

// FR-093: a priority select that offers the 4 base levels plus any administrator-defined ones.
export default function PriorityControl({ priority, customPriorityId, onChange }: Props) {
  const [customs, setCustoms] = useState<CustomPriority[]>([])

  useEffect(() => {
    listCustomPriorities().then((all) => setCustoms(all.filter((c) => c.is_active))).catch(() => {})
  }, [])

  const value = customPriorityId ? `custom:${customPriorityId}` : priority

  function handleChange(key: string) {
    if (key.startsWith('custom:')) {
      const id = Number(key.slice(7))
      const match = customs.find((c) => c.id === id)
      if (match) onChange(match.category, match.id)
    } else {
      onChange(key as Priority, null)
    }
  }

  return (
    <select value={value} onChange={(e) => handleChange(e.target.value)}>
      {PRIORITIES.map((p) => <option key={p} value={p}>{PRIORITY_LABELS[p]}</option>)}
      {customs.map((c) => (
        <option key={c.id} value={`custom:${c.id}`}>{c.name} ({PRIORITY_LABELS[c.category]})</option>
      ))}
    </select>
  )
}
