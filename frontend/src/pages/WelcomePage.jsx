import { useEffect, useRef, useState } from 'react'
import NcrtcLogo from '../components/NcrtcLogo.jsx'
import { getCurrentUser } from '../services/api.js'

function getToken() {
  return window.sessionStorage.getItem('ncrtc_access_token') || window.localStorage.getItem('ncrtc_access_token')
}

export default function WelcomePage() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const requested = useRef(false)

  useEffect(() => {
    if (requested.current) return
    requested.current = true
    const token = getToken()
    if (!token) {
      window.location.replace('/sign-in')
      return
    }
    getCurrentUser(token)
      .then(setUser)
      .catch(() => {
        window.localStorage.removeItem('ncrtc_access_token')
        window.sessionStorage.removeItem('ncrtc_access_token')
        window.location.replace('/sign-in?expired=1')
      })
      .finally(() => setLoading(false))
  }, [])

  function signOut() {
    window.localStorage.removeItem('ncrtc_access_token')
    window.sessionStorage.removeItem('ncrtc_access_token')
    window.location.assign('/')
  }

  return (
    <main className="welcome-page">
      <header className="welcome-header"><a href="/"><NcrtcLogo className="welcome-logo"/></a></header>
      <section className="welcome-card" aria-live="polite">
        {loading && <p>Loading your account…</p>}
        {!loading && user && <><div className="welcome-mark" aria-hidden="true">✓</div><h1>Hello <span>{user.role}</span> <span>{user.username}</span></h1><button className="welcome-signout" onClick={signOut}>Sign Out</button></>}
      </section>
    </main>
  )
}
