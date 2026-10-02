import { useState, type FormEvent } from 'react'
import { ShieldCheck } from 'lucide-react'
import { api } from '../services/api'
import type { AuthUser } from '../types/api'

interface LoginScreenProps {
  onAuthenticated: (user: AuthUser) => void
  initialRole?: number
}

const demoProfiles = [
  { label: 'Control-room administrator', username: 'admin@ner.gov.in', password: 'NerDemo@2026' },
  { label: 'Field officer', username: 'field@ner.gov.in', password: 'FieldDemo@2026' },
  { label: 'Logistics operator', username: 'logistics@ner.gov.in', password: 'LogisticsDemo@2026' },
  { label: 'District authority', username: 'district@ner.gov.in', password: 'DistrictDemo@2026' },
  { label: 'Read-only viewer', username: 'viewer@ner.gov.in', password: 'ViewerDemo@2026' },
  { label: 'Vehicle driver', username: 'driver@ner.gov.in', password: 'DriverDemo@2026' },
]

export function LoginScreen({ onAuthenticated, initialRole = 0 }: LoginScreenProps) {
  const [username, setUsername] = useState(demoProfiles[initialRole].username)
  const [password, setPassword] = useState(demoProfiles[initialRole].password)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const chooseProfile = (index: number) => {
    const profile = demoProfiles[index]
    setUsername(profile.username)
    setPassword(profile.password)
    setError('')
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const session = await api.login(username, password)
      api.setSession(session)
      onAuthenticated(session.user)
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : ''
      setError(
        caught instanceof TypeError || /failed to fetch|networkerror/i.test(message)
          ? 'The NER Logistics API is offline. Start the backend service and try again.'
          : /incorrect|invalid|unauthorized|401/i.test(message)
            ? 'Username or password is incorrect.'
            : message || 'Sign-in could not be completed. Please try again.',
      )
    } finally {
      setLoading(false)
    }
  }

  return <div className="login-screen">
    <section className="login-card">
      <div className="login-brand"><ShieldCheck size={28}/><div><strong>Welcome to NERRO</strong><small>SECURE WORKSPACE ACCESS</small></div></div>
      <div className="login-heading"><ShieldCheck size={25} /><h1>Role-based operational access</h1><p>Each user receives only the tools required for their assigned responsibilities.</p></div>
      <form onSubmit={submit}>
        <label>Choose your demo workspace<select defaultValue={initialRole} onChange={(event) => chooseProfile(Number(event.target.value))}>{demoProfiles.map((profile, index) => <option key={profile.username} value={index}>{profile.label}</option>)}</select></label>
        <label>Email<input type="email" value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" required /></label>
        <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required /></label>
        {error && <p className="login-error" role="alert">{error}</p>}
        <button className="primary" disabled={loading}>{loading ? 'Signing in…' : 'Sign in securely'}</button>
      </form>
      <p className="demo-credentials">Select a role to test its isolated workspace and permissions.</p>
    </section>
  </div>
}
