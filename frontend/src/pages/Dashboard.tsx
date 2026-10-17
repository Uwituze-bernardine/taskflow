import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getDashboard } from '../api/dashboard'
import BarChart from '../components/BarChart'
import { ProjectStatusBadge } from '../components/Badges'
import TaskList from '../components/TaskList'
import { TASK_STATUS_LABELS, fullName } from '../lib/labels'
import type { DashboardData, TaskStatus } from '../types'

const COUNTED_STATUSES: TaskStatus[] = ['TODO', 'IN_PROGRESS', 'BLOCKED', 'UNDER_REVIEW', 'COMPLETED']

// FR-071 personalized dashboard, FR-072 pending, FR-073 overdue, FR-074 completed,
// FR-075 project progress, FR-076 team stats for managers, FR-077 visual indicators.
export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getDashboard().then(setData).catch(() => {}).finally(() => setLoading(false))
  }, [])

  if (loading) return <p>Loading…</p>
  if (!data) return <p className="error">Could not load the dashboard.</p>

  const { my_tasks, pending_tasks, overdue_tasks, projects, team_stats } = data

  return (
    <div className="dashboard-page">
      <div className="page-heading">
        <div><span className="page-eyebrow">YOUR WORKSPACE</span><h1>My Dashboard</h1><p className="muted">A clear view of your tasks, projects, and team progress.</p></div>
        <Link to="/tasks" className="dashboard-quick-link">View my tasks <span aria-hidden="true">→</span></Link>
      </div>

      <div className="stat-grid">
        <Stat label="Total Tasks" value={my_tasks.total} />
        <Stat label="To Do" value={my_tasks.TODO} />
        <Stat label="In Progress" value={my_tasks.IN_PROGRESS} />
        <Stat label="Completed" value={my_tasks.COMPLETED} />
        <Stat label="Overdue" value={my_tasks.overdue} tone="warning" />
      </div>

      {projects.length > 0 && (
        <section className="dashboard-panel">
          <div className="section-heading"><div><h2>Project progress</h2><p className="muted">A snapshot of the projects you’re part of.</p></div><Link to="/projects">All projects →</Link></div>
          <div className="card-grid">
            {projects.map((p) => (
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
          </div>
        </section>
      )}

      <section className="dashboard-panel">
        <div className="section-heading"><div><h2>Pending tasks</h2><p className="muted">Keep your next priorities in reach.</p></div><Link to="/tasks">All tasks →</Link></div>
        <TaskList tasks={pending_tasks} emptyText="Nothing pending - you're all caught up." />
      </section>

      {overdue_tasks.length > 0 && (
        <section className="dashboard-panel">
          <div className="section-heading"><div><h2>Overdue</h2><p className="muted">Tasks that may need your attention.</p></div></div>
          <TaskList tasks={overdue_tasks} />
        </section>
      )}

      {team_stats && (
        <section className="dashboard-panel">
          <div className="section-heading"><div><h2>Team statistics</h2><p className="muted">Workload and progress across your team.</p></div></div>
          <div className="stat-grid">
            <Stat label="Team tasks" value={team_stats.total} />
            <Stat label="Team overdue" value={team_stats.overdue} tone="warning" />
          </div>
          <div className="bar-chart">
            {COUNTED_STATUSES.map((s) => (
              <BarChart key={s} label={TASK_STATUS_LABELS[s]} value={team_stats.by_status[s]} max={team_stats.total} />
            ))}
          </div>

          <h3>By team member</h3>
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Member</th><th>Total</th><th>Completed</th><th>Overdue</th></tr></thead>
              <tbody>
                {team_stats.by_employee.map((e) => (
                  <tr key={e.user.id}>
                    <td>{fullName(e.user)}</td>
                    <td>{e.total}</td>
                    <td>{e.completed}</td>
                    <td className={e.overdue > 0 ? 'overdue' : ''}>{e.overdue}</td>
                  </tr>
                ))}
                {team_stats.by_employee.length === 0 && (
                  <tr><td colSpan={4} className="muted">No tasks assigned within your team yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}

function Stat({ label, value, tone }: { label: string; value: number; tone?: 'warning' }) {
  return (
    <div className={`stat-card ${tone ?? ''}`}>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  )
}

