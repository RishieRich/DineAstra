import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useSession } from '../lib/session'

/**
 * Sign in. The demo credentials are printed on the card because this runs on
 * generated sample data and there is nothing behind it to protect.
 */
function Login() {
  const { signIn } = useSession()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('owner@darpan.demo')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const destination = location.state?.from ?? '/overview'

  async function handleSubmit(event) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await signIn(email, password)
      navigate(destination, { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center bg-burgundy-deep px-md py-xl">
      <div className="w-full max-w-md rounded-md border border-gold bg-burgundy p-lg">
        <div className="flex flex-wrap items-center justify-between gap-sm">
          <p className="text-xs tracking-[0.18em] text-gold-soft">
            Property intelligence
          </p>
          <span className="rounded-sm border border-gold px-sm py-xs text-xs tracking-[0.14em] text-gold-soft">
            Sample data
          </span>
        </div>
        <h1 className="mt-sm font-serif text-4xl text-gold">Darpan</h1>
        <p className="mt-sm text-sm text-gold-soft">
          The daily briefing for the general manager, computed from the
          property&rsquo;s own numbers.
        </p>

        <form onSubmit={handleSubmit} className="mt-lg flex flex-col gap-md">
          <div>
            <label htmlFor="email" className="block text-sm text-gold-soft">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-xs w-full rounded-sm border border-gold bg-burgundy-deep px-md py-sm text-gold"
              required
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm text-gold-soft">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-xs w-full rounded-sm border border-gold bg-burgundy-deep px-md py-sm text-gold"
              required
            />
          </div>

          {error ? (
            <p role="alert" className="text-sm text-gold-soft">
              {error}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={busy}
            className="rounded-sm border border-gold bg-gold px-md py-sm font-medium text-burgundy-deep"
          >
            {busy ? 'Signing in' : 'Sign in'}
          </button>
        </form>

        <p className="mt-lg border-t border-gold pt-md text-xs text-gold-soft">
          Sample data demo. Sign in with owner@darpan.demo and the password
          darpan.
        </p>
      </div>
    </div>
  )
}

export default Login
