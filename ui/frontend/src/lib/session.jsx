import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { resetHeroCountUp } from '../components/HeroFigure'
import { api, clearSession, readStoredSession, storeSession } from './api'

const SessionContext = createContext(null)

export function SessionProvider({ children }) {
  const [session, setSession] = useState(() => readStoredSession())

  const signIn = useCallback(async (email, password) => {
    const result = await api.login(email, password)
    resetHeroCountUp()
    const next = { token: result.token, user: result.user }
    storeSession(next)
    setSession(next)
    return next
  }, [])

  const signOut = useCallback(() => {
    resetHeroCountUp()
    clearSession()
    setSession(null)
  }, [])

  const value = useMemo(
    () => ({
      session,
      token: session?.token ?? null,
      user: session?.user ?? null,
      signIn,
      signOut,
    }),
    [session, signIn, signOut],
  )

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

export function useSession() {
  const context = useContext(SessionContext)
  if (!context) throw new Error('useSession must be used inside a SessionProvider')
  return context
}

/** Fetch helper that knows about the token and reports its own loading state. */
export function useApiCall() {
  const { token } = useSession()
  return useCallback((fn, ...args) => fn(token, ...args), [token])
}
