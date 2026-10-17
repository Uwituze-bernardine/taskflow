import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listProjects } from '../api/projects'
import { ProjectStatusBadge } from '../components/Badges'
import Pager from '../components/Pager'
import ProjectForm from '../components/ProjectForm'
import { useAuth } from '../context/AuthContext'
import { getErrorMessage } from '../lib/errors'
import { PROJECT_STATUS_LABELS, formatDate, fullName } from '../lib/labels'
import { canCreateProject } from '../lib/roles'
import type { Project, ProjectStatus } from '../types'

// FR-008 (create), FR-012 (see the projects I have access to), FR-013 (progress), FR-014 (dates).
export default function Projects() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [projects, setProjects] = useState<Project[]>([])
  const [count, setCount] = useState(0)
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<ProjectStatus | ''>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    listProjects({ status: status || undefined, page })
      .then((data) => { setProjects(data.results); setCount(data.count); setError(null) })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [status, page])

  useEffect(load, [load])

  return (
    <div>
      <div className="page-header">
        <div><h1>Projects</h1><p className="muted">Manage and monitor the projects you’re working on.</p></div>
        {canCreateProject(user?.role) && (
          <button onClick={() => setShowForm((s) => !s)}>{showForm ? 'Cancel' : 'New project'}</button>
        )}
      </div>

      {showForm && (
        <ProjectForm
          onSaved={(p) => navigate(`/projects/${p.id}`)}
          onCancel={() => setShowForm(false)}
        />
      )}

      <div className="filter-bar">
        <select value={status} onChange={(e) => { setStatus(e.target.value as ProjectStatus | ''); setPage(1) }}>
          <option value="">Current projects</option>
          {(Object.keys(PROJECT_STATUS_LABELS) as ProjectStatus[]).map((s) => (
            <option key={s} value={s}>{PROJECT_STATUS_LABELS[s]} only</option>
          ))}
        </select>
      </div>

      {error && <p className="error">{error}</p>}
      {loading ? (
        <p>Loading…</p>
      ) : (
        <div className="card-grid">
          {projects.map((p) => (
            <Link key={p.id} to={`/projects/${p.id}`} className="project-card">
              <div className="card-title">
                <h3>{p.name}</h3>
                <ProjectStatusBadge status={p.status} />
              </div>
              <p className="muted clamp">{p.description || 'No description'}</p>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${p.progress}%` }} />
              </div>
              <div className="card-footer">
                <span className="muted">{p.task_count} task{p.task_count === 1 ? '' : 's'}</span>
                <strong>{p.progress}%</strong>
              </div>
              <div className="muted small">
                {formatDate(p.start_date)} → {formatDate(p.end_date)}
              </div>
              <div className="muted small">Manager: {fullName(p.manager_detail)}</div>
            </Link>
          ))}
          {projects.length === 0 && (
            <p className="muted">
              {status ? 'No projects with this status.' : 'You are not part of any project yet.'}
            </p>
          )}
        </div>
      )}
      <Pager page={page} count={count} onChange={setPage} />
    </div>
  )
}
