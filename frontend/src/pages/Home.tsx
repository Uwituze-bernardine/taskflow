import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import homeBackground from '../assets/login-bg.jpg'

const features = [
  { icon: '▦', title: 'Projects in one place', text: 'Keep plans, owners, and progress together from kickoff to done.' },
  { icon: '✓', title: 'Tasks that move forward', text: 'Prioritize work, assign teammates, and make the next step clear.' },
  { icon: '◷', title: 'A team that stays in sync', text: 'Follow due dates and updates with a shared calendar and notifications.' },
]

export default function Home() {
  const { user, isLoading } = useAuth()

  if (isLoading) return <div className="page-center">Loading…</div>
  if (user) return <Navigate to="/dashboard" replace />

  return (
    <main className="public-home">
      <header className="public-nav">
        <Link to="/" className="public-brand"><span className="public-brand-mark">✓</span>TaskFlow</Link>
        <nav aria-label="Main navigation">
          <a href="#features">Features</a>
          <a href="#how-it-works">How it works</a>
        </nav>
        <div className="public-nav-actions">
          <Link to="/login" className="public-login">Sign in</Link>
          <Link to="/register" className="public-cta">Get started</Link>
        </div>
      </header>

      <section
        className="public-hero"
        id="how-it-works"
        style={{
          backgroundImage: `linear-gradient(rgba(255, 255, 255, 0.76), rgba(248, 240, 210, 0.78)), url(${homeBackground})`,
        }}
      >
        <span className="public-eyebrow"><span /> A calmer way to get work done</span>
        <h1>Everything your team needs,<br />finally in one place.</h1>
        <p>Plan projects, organize tasks, and keep your team moving forward — all with one clear view of the work.</p>
        <div className="public-hero-actions">
          <Link to="/register" className="public-cta">Start organizing <span aria-hidden="true">→</span></Link>
          <Link to="/login" className="public-secondary-cta">I already have an account</Link>
        </div>

        <div className="public-preview" aria-label="TaskFlow workspace preview">
          <div className="preview-sidebar">
            <div className="preview-brand"><span className="public-brand-mark">✓</span> TaskFlow</div>
            <span className="preview-nav-item active">▦ &nbsp; Overview</span>
            <span className="preview-nav-item">✓ &nbsp; My tasks</span>
            <span className="preview-nav-item">▤ &nbsp; Projects</span>
            <span className="preview-nav-item">◷ &nbsp; Calendar</span>
            <div className="preview-sidebar-spacer" />
            <span className="preview-profile"><span className="preview-avatar">T</span> Your workspace</span>
          </div>
          <div className="preview-content">
            <div className="preview-heading"><div><small>WORKSPACE / OVERVIEW</small><h2>Your team at a glance</h2></div><span className="preview-action">+ New task</span></div>
            <div className="preview-stats">
              <div><small>Active projects</small><strong>08</strong><span>Across your team</span></div>
              <div><small>Tasks in progress</small><strong>24</strong><span>Moving right along</span></div>
              <div><small>Completed this week</small><strong>16</strong><span className="preview-positive">↑ Great momentum</span></div>
            </div>
            <div className="preview-board">
              <div className="preview-board-heading"><div><h3>Project tasks</h3><span>What the team is working on</span></div><span className="preview-link">View all →</span></div>
              <div className="preview-columns">
                <div className="preview-column"><span className="preview-column-title"><i /> TO DO <b>2</b></span><article><small>WEBSITE REDESIGN</small><strong>Review page structure</strong><span className="preview-task-meta">Due today <span className="preview-avatar">A</span></span></article><article><small>MOBILE APP</small><strong>Prepare wireframes</strong><span className="preview-task-meta">Due Friday <span className="preview-avatar avatar-alt">J</span></span></article></div>
                <div className="preview-column"><span className="preview-column-title progress"><i /> IN PROGRESS <b>1</b></span><article><small>WEBSITE REDESIGN</small><strong>Build the new landing page</strong><span className="preview-task-meta">Due tomorrow <span className="preview-avatar">A</span></span></article></div>
                <div className="preview-column"><span className="preview-column-title complete"><i /> COMPLETED <b>1</b></span><article><small>TEAM OPERATIONS</small><strong>Share project kickoff notes</strong><span className="preview-task-meta">Finished <span className="preview-avatar avatar-alt">M</span></span></article></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="public-features" id="features">
        <div className="public-section-heading"><span className="public-eyebrow"><span /> BUILT FOR YOUR EVERYDAY</span><h2>Less chasing. More progress.</h2><p>Everything stays connected, so your team can focus on meaningful work.</p></div>
        <div className="public-feature-grid">
          {features.map((feature) => <article className="public-feature" key={feature.title}><span className="public-feature-icon">{feature.icon}</span><h3>{feature.title}</h3><p>{feature.text}</p></article>)}
        </div>
        <div className="public-bottom-cta"><div><h2>Ready to get in sync?</h2><p>Bring your team’s work together with TaskFlow.</p></div><Link to="/register" className="public-cta">Create your workspace <span aria-hidden="true">→</span></Link></div>
      </section>
      <footer className="public-footer"><Link to="/" className="public-brand"><span className="public-brand-mark">✓</span>TaskFlow</Link><span>Plan · Assign · Track · Achieve</span><span>© {new Date().getFullYear()} TaskFlow</span></footer>
    </main>
  )
}
