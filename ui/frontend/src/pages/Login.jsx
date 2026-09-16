import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import BrandMark from '../components/BrandMark'
import { useSession } from '../lib/session'

const DEMO_EMAIL = 'owner@dineastra.demo'
const DEMO_PASSWORD = 'dineastra'

/*
 * The starfield behind the story panel.
 *
 * Positions are fixed rather than random: a field regenerated on every render
 * flickers, and one regenerated on every visit means no two screenshots of
 * the sign-in screen ever match. Twelve points, placed away from the
 * headline so nothing twinkles underneath text.
 */
const STARS = [
  { id: 'a', top: '12%', left: '18%', delay: '0s', size: 3 },
  { id: 'b', top: '8%', left: '46%', delay: '1.4s', size: 2 },
  { id: 'c', top: '22%', left: '64%', delay: '2.6s', size: 3 },
  { id: 'd', top: '31%', left: '9%', delay: '0.8s', size: 2 },
  { id: 'e', top: '44%', left: '72%', delay: '3.2s', size: 2 },
  { id: 'f', top: '57%', left: '84%', delay: '1.1s', size: 3 },
  { id: 'g', top: '68%', left: '13%', delay: '2.1s', size: 2 },
  { id: 'h', top: '76%', left: '58%', delay: '0.4s', size: 3 },
  { id: 'i', top: '86%', left: '31%', delay: '3.7s', size: 2 },
  { id: 'j', top: '91%', left: '78%', delay: '1.9s', size: 2 },
  { id: 'k', top: '17%', left: '88%', delay: '2.9s', size: 2 },
  { id: 'l', top: '63%', left: '41%', delay: '4.3s', size: 2 },
]

/*
 * The rotating proof line.
 *
 * Three claims, one at a time, eight seconds apart -- slow enough to finish
 * reading one before the next arrives, and slow enough that a reader filling
 * in the form to its right is never pulled back across the screen. Each is a
 * claim the product actually keeps.
 */
const PROOF_POINTS = [
  {
    id: 'provenance',
    lead: 'Every figure on every screen carries ',
    strong: 'where it came from',
    tail: ' and the window it was measured over.',
  },
  {
    id: 'intake',
    lead: 'Files in, answers out: ',
    strong: 'Excel, CSV and plain text',
    tail: ' load into the same versioned record.',
  },
  {
    id: 'honesty',
    lead: 'Nothing is invented. If the workspace has not got the data, ',
    strong: 'it says so',
    tail: ' instead of estimating.',
  },
]

const PROOF_INTERVAL_MS = 8000

/*
 * Field icons. Drawn at 20x20 on a 1.6 stroke so they sit at the same weight
 * as the input's own border, and inherit currentColor so the focus rule that
 * tints the icon needs no second declaration.
 */
function EnvelopeIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <rect x="2.4" y="4.4" width="15.2" height="11.2" rx="1.8" />
      <path d="M3 5.6 10 11l7-5.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function LockIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <rect x="3.6" y="8.6" width="12.8" height="8.4" rx="2" />
      <path d="M6.6 8.6V6.4a3.4 3.4 0 0 1 6.8 0v2.2" strokeLinecap="round" />
    </svg>
  )
}

function Login() {
  const { signIn } = useSession()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState(DEMO_EMAIL)
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [proofIndex, setProofIndex] = useState(0)

  const destination = location.state?.from ?? '/overview'

  // The proof line advances on its own, and stops while the form is being
  // submitted -- nothing on the screen should move during the one moment the
  // reader is waiting on an answer.
  useEffect(() => {
    if (busy) return undefined
    const timer = setInterval(() => {
      setProofIndex((current) => (current + 1) % PROOF_POINTS.length)
    }, PROOF_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [busy])

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

  function fillDemoCredentials() {
    setEmail(DEMO_EMAIL)
    setPassword(DEMO_PASSWORD)
    setError(null)
  }

  const proof = PROOF_POINTS[proofIndex]

  return (
    <div className="login-shell">
      <section className="login-story" aria-label="DineAstra introduction">
        <div className="login-aurora" aria-hidden="true"><i /><i /><i /></div>
        <div className="login-grid" aria-hidden="true" />
        <div className="login-stars" aria-hidden="true">
          {STARS.map((star) => (
            <i
              key={star.id}
              style={{
                top: star.top,
                left: star.left,
                width: `${star.size}px`,
                height: `${star.size}px`,
                animationDelay: star.delay,
              }}
            />
          ))}
        </div>
        <div className="orbit orbit-one" aria-hidden="true" />
        <div className="orbit orbit-two" aria-hidden="true" />
        <div className="orbit orbit-three" aria-hidden="true" />

        {/* The cascade runs top to bottom in reading order: who this is,
          * what it claims, how it works, and what it promises. Delays are
          * written out per block rather than nested, so the whole sequence
          * can be read off this one file. */}
        <div className="login-story__inner">
          <div className="brand-lockup reveal reveal--left" style={{ '--delay': '80ms' }}>
            <BrandMark inverse />
            <div>
              <p className="brand-name">DineAstra</p>
              <p className="brand-byline">Restaurant intelligence by ARQ One AI Labs</p>
            </div>
          </div>

          <div className="login-copy">
            <p className="eyebrow eyebrow--gold reveal" style={{ '--delay': '220ms' }}>
              A private operating workspace
            </p>
            <h1 className="cascade" style={{ '--delay': '330ms', '--stagger-step': '140ms' }}>
              <span>Every service tells a story.</span>
              <span className="headline-accent">See the whole business.</span>
            </h1>
            <p className="reveal" style={{ '--delay': '700ms' }}>
              Sales, food cost, events, standards and daily exceptions come
              together in one calm, decision-ready view.
            </p>
          </div>

          <div
            className="login-promises cascade"
            style={{ '--delay': '860ms', '--stagger-step': '120ms' }}
          >
            <div>
              <span>01</span>
              <strong>Bring your files</strong>
              <small>Excel, CSV and text intake</small>
            </div>
            <div>
              <span>02</span>
              <strong>See what changed</strong>
              <small>Versioned records and live KPIs</small>
            </div>
            <div>
              <span>03</span>
              <strong>Ask DineAstra</strong>
              <small>Plain-language answers over loaded data</small>
            </div>
          </div>

          <div className="login-proof reveal reveal--fade" style={{ '--delay': '1240ms' }}>
            <BrandMark inverse size="sm" />
            <p className="login-proof__line">
              {/* The key restarts the entrance animation on each change. */}
              <span key={proof.id}>
                {proof.lead}<b>{proof.strong}</b>{proof.tail}
              </span>
            </p>
            <span className="login-proof__dots" aria-hidden="true">
              {PROOF_POINTS.map((point) => (
                <i key={point.id} data-current={point.id === proof.id ? 'true' : 'false'} />
              ))}
            </span>
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
            Use the demo credentials below, or skip straight through with
            sample data already loaded.
          </p>

          <div className="login-field reveal" style={{ '--delay': '380ms' }}>
            <label htmlFor="email">Email</label>
            <div className="login-field__control">
              <span className="login-field__icon"><EnvelopeIcon /></span>
              <input
                id="email"
                type="email"
                autoComplete="username"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </div>
          </div>

          <div
            className="login-field login-field--secret reveal"
            style={{ '--delay': '450ms' }}
          >
            <label htmlFor="password">Password</label>
            <div className="login-field__control">
              <span className="login-field__icon"><LockIcon /></span>
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter password"
                required
              />
              <button
                type="button"
                className="login-field__reveal"
                onClick={() => setShowPassword((current) => !current)}
                aria-pressed={showPassword}
              >
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </div>
          </div>

          <p className="login-hint reveal" style={{ '--delay': '520ms' }}>
            Demo sign-in: <code>{DEMO_EMAIL}</code> · <code>{DEMO_PASSWORD}</code>
            <button type="button" onClick={fillDemoCredentials}>Fill for me</button>
          </p>

          {error ? (
            <p role="alert" className="form-error">{error}</p>
          ) : null}

          <button
            type="submit"
            disabled={busy}
            className="primary-button reveal"
            style={{ '--delay': '590ms' }}
          >
            {busy ? (
              <>
                <span className="spinner" aria-hidden="true" /> Opening workspace…
              </>
            ) : (
              <>
                Continue securely{' '}
                <span className="button-arrow" aria-hidden="true">→</span>
              </>
            )}
          </button>

          <p className="login-divider reveal" style={{ '--delay': '650ms' }}>or</p>

          <button
            type="button"
            disabled={busy}
            className="demo-button reveal"
            style={{ '--delay': '710ms' }}
            onClick={() => submit({ email: DEMO_EMAIL, password: DEMO_PASSWORD })}
          >
            Explore with sample data
          </button>

          <p className="login-card__foot reveal" style={{ '--delay': '770ms' }}>
            Demo access · no customer data · resettable workspace
          </p>
        </form>
      </section>
    </div>
  )
}

export default Login
