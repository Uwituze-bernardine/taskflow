import { Link } from 'react-router-dom'
import { fullName, formatDate } from '../lib/labels'
import type { Task } from '../types'
import { PriorityBadge, StatusBadge } from './Badges'

interface Props {
  tasks: Task[]
  showProject?: boolean
  emptyText?: string
}

export default function TaskList({ tasks, showProject = true, emptyText = 'No tasks to show.' }: Props) {
  if (tasks.length === 0) return <p className="muted">{emptyText}</p>
  return (
    <ul className="task-list">
      {tasks.map((t) => (
        <li key={t.id}>
          <div className="task-main">
            <Link to={`/tasks/${t.id}`}>{t.title}</Link>
            <span className="muted">
              #{t.id}
              {showProject && t.project_name ? ` · ${t.project_name}` : ''}
            </span>
          </div>
          <PriorityBadge priority={t.priority} label={t.priority_label} />
          <StatusBadge status={t.status} />
          <span className="muted task-assignee">{fullName(t.assigned_to_detail)}</span>
          <span className={t.is_overdue ? 'overdue' : 'muted'}>
            {t.due_date ? `${t.is_overdue ? 'Overdue · ' : 'Due '}${formatDate(t.due_date)}` : 'No due date'}
          </span>
        </li>
      ))}
    </ul>
  )
}
