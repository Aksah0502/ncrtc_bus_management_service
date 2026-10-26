import { useState } from 'react'
import NcrtcLogo from '../components/NcrtcLogo.jsx'
import { getCurrentUser, signIn } from '../services/api.js'

function UserIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="3.5"/><path d="M5 20v-1.5a7 7 0 0 1 14 0V20"/></svg>
}
function LockIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5.5" y="10" width="13" height="11" rx="2"/><path d="M8.5 10V7a3.5 3.5 0 0 1 7 0v3m-3.5 4v3"/></svg>
}
function EyeIcon({ hidden }) {
  return hidden
    ? <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 3 21 21M10.6 10.7a2 2 0 0 0 2.7 2.7"/><path d="M9.9 5.2A10.8 10.8 0 0 1 12 5c5.2 0 8.5 5 8.5 7a8 8 0 0 1-2.4 3.3M6.2 6.3C4.4 7.6 3.5 9.2 3.5 12c0 2 3.3 7 8.5 7 1 0 2-.2 2.8-.6"/></svg>
    : <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3.5 12s3.3-7 8.5-7 8.5 7 8.5 7-3.3 7-8.5 7-8.5-7-8.5-7Z"/><circle cx="12" cy="12" r="2.7"/></svg>
}

export default function SignInPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(true)
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setMessage('')
    setLoading(true)
    try {
      const tokenResponse = await signIn(username.trim(), password)
      if (!tokenResponse?.access_token) throw new Error('The server did not return an access token.')
      const user = await getCurrentUser(tokenResponse.access_token)
      const store = remember ? window.localStorage : window.sessionStorage
      const otherStore = remember ? window.sessionStorage : window.localStorage
      otherStore.removeItem('ncrtc_access_token')
      store.setItem('ncrtc_access_token', tokenResponse.access_token)
      window.sessionStorage.setItem('ncrtc_username', user.username)
      const destination = user.role === 'control_operator'
        ? '/control-room'
        : user.role === 'admin'
          ? '/admin'
          : '/welcome'
      window.location.assign(destination)
    } catch (requestError) {
      setError(requestError.message || 'Unable to sign in. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="signin-page">
      <section className="signin-card" aria-label="Sign in to NCRTC">
        <aside className="signin-brand-panel">
          <div className="panel-decoration panel-decoration-top" />
          <div className="panel-orbit" />
          <NcrtcLogo className="signin-logo" />
          <div className="panel-decoration panel-decoration-bottom" />
        </aside>
        <section className="signin-form-panel">
          <div className="signin-content">
            <h1>Sign In</h1>
            <p className="signin-subtitle">Access your Control-Room Operator portal</p>
            <form className="signin-form" onSubmit={handleSubmit}>
              <label className="signin-input-wrap">
                <UserIcon /><span className="sr-only">Username</span>
                <input autoComplete="username" name="username" placeholder="Username" required value={username} onChange={(event) => setUsername(event.target.value)} />
              </label>
              <label className="signin-input-wrap">
                <LockIcon /><span className="sr-only">Password</span>
                <input autoComplete="current-password" name="password" placeholder="Password" required type={showPassword ? 'text' : 'password'} value={password} onChange={(event) => setPassword(event.target.value)} />
                <button className="password-toggle" type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword((shown) => !shown)}><EyeIcon hidden={showPassword}/></button>
              </label>
              <div className="signin-options">
                <label className="remember-label"><input type="checkbox" checked={remember} onChange={(event) => setRemember(event.target.checked)} /><span>Remember me</span></label>
                <button type="button" className="forgot-link" onClick={() => setMessage('Password reset is not available yet. Please contact your system administrator.')}>Forgot password?</button>
              </div>
              {error && <p className="signin-feedback signin-error" role="alert">{error}</p>}
              {message && <p className="signin-feedback signin-message" role="status">{message}</p>}
              <button className="signin-submit" type="submit" disabled={loading}>{loading ? <><span className="button-spinner"/> Signing In…</> : 'Sign In'}</button>
            </form>
          </div>
        </section>
      </section>
    </main>
  )
}
