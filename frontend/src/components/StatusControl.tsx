import { useEffect, useState } from 'react'
import { getWorkflowOptions } from '../api/tasks'
import type { TaskStatus, WorkflowOption } from '../types'

interface Props {
  status: TaskStatus
  customStatusId: number | null
  disabled?: boolean
  onChange: (key: string) => void
}

// FR-032/033/035: a status select that offers the six predefined statuses plus any
// administrator-defined ones, each shown against the predefined status it behaves like.
export default function StatusControl({ status, customStatusId, disabled, onChange }: Props) {
  const [options, setOptions] = useState<WorkflowOption[]>([])

  useEffect(() => {
    getWorkflowOptions().then(setOptions).catch(() => {})
  }, [])

  const value = customStatusId ? `custom:${customStatusId}` : status

  if (options.length === 0) return <p className="muted">Loading statuses…</p>

  return (
    <select value={value} disabled={disabled} onChange={(e) => onChange(e.target.value)}>
      {options.map((o) => (
        <option key={o.key} value={o.key}>{o.builtin ? o.label : `${o.label} (${options.find((b) => b.builtin && b.category === o.category)?.label})`}</option>
      ))}
    </select>
  )
}
