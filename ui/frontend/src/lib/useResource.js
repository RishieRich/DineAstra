import { useEffect, useState } from 'react'
import { useSession } from './session'

/**
 * Load one API resource. Returns { data, error, loading }.
 *
 * `loader` is called with the token; `deps` re-runs it. A request whose
 * result arrives after the component moved on is discarded rather than
 * written into state.
 */
export function useResource(loader, deps = []) {
  const { token } = useSession()
  const [state, setState] = useState({ data: null, error: null, loading: true })

  useEffect(() => {
    let live = true
    setState((prev) => ({ ...prev, loading: true, error: null }))

    loader(token)
      .then((data) => {
        if (live) setState({ data, error: null, loading: false })
      })
      .catch((error) => {
        if (live) setState({ data: null, error, loading: false })
      })

    return () => {
      live = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, ...deps])

  return state
}
