import { useEffect, useState } from 'react'
import NcrtcLogo from '../components/NcrtcLogo.jsx'
import { getCurrentUser } from '../services/api.js'

function getToken() {
  return window.sessionStorage.getItem('ncrtc_access_token') || window.localStorage.getItem('ncrtc_access_token')
}

const modules = [
  {
    id: 'live-monitoring',
    title: 'Live Bus Monitoring',
    description: 'View real-time locations of all buses and check history of past trips on an interactive map.',
    detail: 'Monitor active buses, see their current speed, and review a vehicle’s recent route and location history.',
    color: 'blue',
    icon: 'bus',
  },
  {
    id: 'scheduling',
    title: 'Scheduling & Duties',
    description: 'Create routes, assign drivers to vehicles, and manage daily duties efficiently.',
    detail: 'Organise routes and stops, prepare depot duty rosters, and publish assignments for drivers.',
    color: 'green',
    icon: 'calendar',
  },
  {
    id: 'incidents',
    title: 'Incident Management',
    description: 'Raise, track, and resolve incidents such as breakdowns, complaints, or no-shows.',
    detail: 'Record operational issues and follow each incident through acknowledgement, resolution, and closure.',
    color: 'red',
    icon: 'alert',
  },
  {
    id: 'notices',
    title: 'Operational Notices',
    description: 'Publish important notices and updates for drivers and operational staff.',
    detail: 'Share operational updates with drivers and keep track of notice readership.',
    color: 'amber',
    icon: 'bell',
  },
]

function ModuleIcon({ name }) {
  const paths = {
    bus: <><path d="M5 19V7a3 3 0 0 1 3-3h8a3 3 0 0 1 3 3v12"/><path d="M5 12h14M8 19v2m10-2v2M7 16h.01M17 16h.01M8 8h8"/></>,
    calendar: <><rect x="4" y="5" width="16" height="16" rx="2"/><path d="M8 3v4m8-4v4M4 10h16m-8 4v3l2 1"/><circle cx="16" cy="17" r="4" fill="currentColor" stroke="none"/></>,
    alert: <><path d="m12 3 9 16H3L12 3Z"/><path d="M12 9v4m0 3h.01"/></>,
    bell: <><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/></>,
  }
  return <svg viewBox="0 0 24 24" aria-hidden="true" className="module-icon">{paths[name]}</svg>
}

function SignInIcon() {
  return <svg className="signin-lock-icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="10" width="14" height="12" rx="2.5"/><path d="M8.5 10V7a3.5 3.5 0 0 1 7 0v3"/><circle cx="12" cy="15" r="1.2" className="lock-hole"/><path d="M12 16v2" className="lock-hole-line"/></svg>
}

export default function HomePage() {
  const [selectedModule, setSelectedModule] = useState(null)
  const [user, setUser] = useState(null)
  const [checkingAccount, setCheckingAccount] = useState(() => Boolean(getToken()))

  useEffect(() => {
    const token = getToken()
    if (!token) return undefined
    let active = true
    getCurrentUser(token)
      .then((account) => { if (active) setUser(account) })
      .catch(() => {
        window.sessionStorage.removeItem('ncrtc_access_token')
        window.localStorage.removeItem('ncrtc_access_token')
      })
      .finally(() => { if (active) setCheckingAccount(false) })
    return () => { active = false }
  }, [])

  const portalPath = user?.role === 'control_operator' ? '/control-room' : '/welcome'

  return (
    <div id="top" className="page-shell">
      <header className="site-header">
        <a className="home-brand" href="#top" aria-label="NCRTC Bus Management System home"><NcrtcLogo className="home-logo"/></a>
        <nav className="header-nav" aria-label="Main navigation">
          <a className="overview-link" href="#top">Overview</a>
          {user ? <a className="button button-navy header-signin" href={portalPath}>Open Dashboard</a> : <a className="button button-navy header-signin" href="/sign-in">
            <SignInIcon /> <span>{checkingAccount ? 'Checking…' : 'Sign In'}</span>
          </a>}
        </nav>
      </header>

      <main>
        <section className="hero" aria-labelledby="hero-heading">
          <div className="hero-photo" aria-hidden="true" />
          <div className="hero-content">
            <p className="eyebrow">EFFICIENCY <span>│</span> SAFETY <span>│</span> BETTER CONNECTIVITY</p>
            <h1 id="hero-heading">Smarter Bus Operations.<br /><span>Connected Mobility.</span></h1>
            <p className="hero-description">A unified platform to monitor buses, coordinate schedules,<br className="desktop-break" /> manage incidents, and share operational notices.</p>
            <div className="hero-actions">
              <a className="button button-navy hero-signin" href={user ? portalPath : '/sign-in'}>
                {user ? <><span>Open Dashboard</span><span className="arrow">→</span></> : <><SignInIcon /> <span>{checkingAccount ? 'Checking account' : 'Sign In to Portal'}</span><span className="arrow">→</span></>}
              </a>
              <a className="explore-link" href="#modules">Explore the System <span>→</span></a>
            </div>
          </div>
        </section>

        <section id="modules" className="modules-section" aria-label="System modules">
          <div className="module-grid">
            {modules.map((module) => (
              <article className="module-card" key={module.id}>
                <div className={`icon-disc ${module.color}`}><ModuleIcon name={module.icon} /></div>
                <h2>{module.title}</h2>
                <p>{module.description}</p>
                <button className="learn-link" onClick={() => setSelectedModule(module)}>
                  Learn more <span>→</span>
                </button>
              </article>
            ))}
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <a className="footer-brand" href="#top" aria-label="NCRTC Bus Management System home"><NcrtcLogo inverse className="footer-logo"/></a>
        <div className="footer-description">A unified platform for efficient, safe and reliable bus operations<br />across the Delhi-NCR region.</div>
        <div className="footer-legal">© 2024 NCRTC Bus Management System<br />Authorized access only. All rights reserved.</div>
      </footer>

      {selectedModule && (
        <div className="dialog-backdrop" onMouseDown={(event) => event.target === event.currentTarget && setSelectedModule(null)}>
          <section className="module-dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title">
            <button className="dialog-close" aria-label="Close" onClick={() => setSelectedModule(null)}>×</button>
            <div className={`icon-disc ${selectedModule.color}`}><ModuleIcon name={selectedModule.icon} /></div>
            <h2 id="dialog-title">{selectedModule.title}</h2>
            <p>{selectedModule.detail}</p>
            <a className="button button-navy" href={user ? portalPath : '/sign-in'}>{user ? 'Open Dashboard' : 'Sign In to Portal'} <span className="arrow">→</span></a>
          </section>
        </div>
      )}
    </div>
  )
}
