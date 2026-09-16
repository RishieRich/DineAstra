import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import BrandMark from '../components/BrandMark'
import { useSession } from '../lib/session'

function Login() {
  const { signIn } = useSession()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('owner@dineastra.demo')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const destination = location.state?.from ?? '/overview'

  async function submit(credentials) {
    setBusy(true)
    setError(null)
    try {
      await signIn(credentials.email, credentials.password)
      navigate(destination, { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    await submit({ email, password })
  }

  return (
    <div className="login-shell">
      <section className="login-story" aria-label="DineAstra introduction">
        <div className="orbit orbit-one" />
        <div className="orbit orbit-two" />
        <div className="login-story__inner">
          <div className="brand-lockup brand-lockup--light">
            <BrandMark inverse />
            <div>
              <p className="brand-name">DineAstra</p>
              <p className="brand-byline">Restaurant intelligence by ARQ One AI Labs</p>
            </div>
          </div>

          <div className="login-copy">
            <p className="eyebrow eyebrow--gold">A private operating workspace</p>
            <h1>Every service tells a story. See the whole business.</h1>
            <p>
              Sales, food cost, events, standards and daily exceptions come
              together in one calm, decision-ready view.
            </p>
          </div>

          <div className="login-promises">
            <div><span>01</span><strong>Bring your files</strong><small>Excel, CSV and text intake</small></div>
            <div><span>02</span><strong>See what changed</strong><small>Versioned records and live KPIs</small></div>
            <div><span>03</span><strong>Ask DineAstra</strong><small>Plain-language answers over loaded data</small></div>
          </div>
        </div>
      </section>

      <section className="login-access">
        <div className="login-access__top">
          <span><i /> Demo workspace</span>
          <span>EN</span>
        </div>

        <form onSubmit={handleSubmit} className="login-card">
          <BrandMark size="lg" />
          <p className="eyebrow">Welcome back</p>
          <h2>Enter the Astra House workspace</h2>
          <p className="login-card__support">
            Use the demo credentials below or continue instantly.
          </p>

          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />

          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Enter password"
            required
          />

          {error ? <p role="alert" className="form-error">{error}</p> : null}

          <button type="submit" disabled={busy} className="primary-button">
            {busy ? 'Opening workspace…' : 'Continue securely'} <span aria-hidden="true">→</span>
          </button>
          <button
            type="button"
            disabled={busy}
            className="demo-button"
            onClick={() => submit({ email: 'owner@dineastra.demo', password: 'dineastra' })}
          >
            Explore with sample data
          </button>

          <p className="login-card__foot">
            Demo access · no customer data · resettable workspace
          </p>
        </form>
      </section>
    </div>
  )
}

export default Login
