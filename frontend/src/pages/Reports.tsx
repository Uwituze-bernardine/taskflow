import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listAllProjects } from '../api/projects'
import { exportReport, getReport } from '../api/reports'
import BarChart from '../components/BarChart'
import { ProjectStatusBadge } from '../components/Badges'
import { getErrorMessage } from '../lib/errors'
import { PRIORITIES, PRIORITY_LABELS, TASK_STATUSES, TASK_STATUS_LABELS, formatDate, fullName } from '../lib/labels'
import type { Project, Report } from '../types'

function isoDaysAgo(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() - days)
  return d.toISOString().slice(0, 10)
}

// FR-078 completion, FR-079 overdue, FR-080 project progress, FR-081 workload,
// FR-082 date range filter, FR-083 export, FR-084 charts/metrics.
export default function Reports() {
  const [start, setStart] = useState(isoDaysAgo(30))
  const [end, setEnd] = useState(isoDaysAgo(0))
  const [projectId, setProjectId] = useState('')
  const [projects, setProjects] = useState<Project[]>([])
  const [report, setReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    listAllProjects().then(setProjects).catch(() => {})
  }, [])

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    getReport({ start, end, project: projectId ? Number(projectId) : undefined })
      .then(setReport)
      .catch((err) => setError(getErrorMessage(err, 'Could not load the report. Only managers can view reports.')))
      .finally(() => setLoading(false))
  }, [start, end, projectId])

  useEffect(load, [load])

  async function handleExport() {
    setExporting(true)
    try {
      await exportReport({ start, end, project: projectId ? Number(projectId) : undefined })
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setExporting(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Reports</h1>
        <button className="btn-secondary" onClick={handleExport} disabled={exporting || !report}>
          {exporting ? 'Exporting…' : 'Export CSV'}
        </button>
      </div>

      <div className="filter-bar">
        <label className="inline-label">
          From <input type="date" value={start} max={end} onChange={(e) => setStart(e.target.value)} />
        </label>
        <label className="inline-label">
          To <input type="date" value={end} min={start} onChange={(e) => setEnd(e.target.value)} />
        </label>
        <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
          <option value="">All projects</option>
          {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      </div>

      {error && <p className="error">{error}</p>}
      {loading ? (
        <p>Loading…</p>
      ) : report ? (
        <>
          <p className="muted">
            {formatDate(report.start)} – {formatDate(report.end)}. Overdue, status, workload and project
            progress reflect the current moment, not this date range.
          </p>

          <div className="stat-grid">
            <Stat label="Tasks created" value={report.tasks_created} />
            <Stat label="Tasks completed" value={report.tasks_completed} />
            <Stat label="Overdue (now)" value={report.tasks_overdue} tone="warning" />
            <Stat label="Avg. completion (days)" value={report.avg_completion_days ?? '—'} />
          </div>

          <div className="report-columns">
            <section>
              <h2>Tasks by priority <span className="muted small">(created in range)</span></h2>
              <div className="bar-chart">
                {PRIORITIES.map((p) => (
                  <BarChart key={p} label={PRIORITY_LABELS[p]} value={report.tasks_by_priority[p]} max={report.tasks_created} />
                ))}
              </div>
            </section>
            <section>
              <h2>Tasks by status <span className="muted small">(current)</span></h2>
              <div className="bar-chart">
                {TASK_STATUSES.map((s) => (
                  <BarChart key={s} label={TASK_STATUS_LABELS[s]} value={report.tasks_by_status[s]} max={Object.values(report.tasks_by_status).reduce((a, b) => a + b, 0)} />
                ))}
              </div>
            </section>
          </div>

          <h2>Workload by employee <span className="muted small">(current)</span></h2>
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Employee</th><th>Total</th><th>Completed</th><th>Overdue</th></tr></thead>
              <tbody>
                {report.tasks_by_employee.map((e) => (
                  <tr key={e.user.id}>
                    <td>{fullName(e.user)}</td>
                    <td>{e.total}</td>
                    <td>{e.completed}</td>
                    <td className={e.overdue > 0 ? 'overdue' : ''}>{e.overdue}</td>
                  </tr>
                ))}
                {report.tasks_by_employee.length === 0 && (
                  <tr><td colSpan={4} className="muted">No assigned tasks in scope.</td></tr>
                )}
              </tbody>
            </table>
          </div>

          <h2>Project progress <span className="muted small">(current)</span></h2>
          <div className="card-grid">
            {report.projects.map((p) => (
              <Link key={p.id} to={`/projects/${p.id}`} className="project-card">
                <div className="card-title">
                  <h3>{p.name}</h3>
                  <ProjectStatusBadge status={p.status} />
                </div>
                <div className="progress-bar"><div className="progress-fill" style={{ width: `${p.progress}%` }} /></div>
                <div className="card-footer">
                  <span className="muted">{p.task_count} task{p.task_count === 1 ? '' : 's'}</span>
                  <strong>{p.progress}%</strong>
                </div>
              </Link>
            ))}
            {report.projects.length === 0 && <p className="muted">No projects in scope.</p>}
          </div>

          <h2>Overdue tasks <span className="muted small">(current)</span></h2>
          <ul className="task-list">
            {report.overdue_tasks.map((t) => (
              <li key={t.id}>
                <div className="task-main"><Link to={`/tasks/${t.id}`}>{t.title}</Link></div>
                <span className="muted">{t.project ?? 'No project'}</span>
                <span className="muted">{t.assignee ? fullName(t.assignee) : 'Unassigned'}</span>
                <span className="overdue">Due {formatDate(t.due_date)}</span>
              </li>
            ))}
            {report.overdue_tasks.length === 0 && <p className="muted">Nothing overdue.</p>}
          </ul>
        </>
      ) : null}
    </div>
  )
}

function Stat({ label, value, tone }: { label: string; value: number | string; tone?: 'warning' }) {
  return (
    <div className={`stat-card ${tone ?? ''}`}>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  )
}
