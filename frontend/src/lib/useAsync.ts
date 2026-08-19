import { useCallback, useEffect, useState } from 'react'

interface AsyncState<T> {
  data: T | null
  loading: boolean
  error: string | null
}

// `fn` is intentionally excluded from the effect's deps: callers pass a
// fresh closure every render, and `deps` is the actual, caller-controlled
// re-fetch trigger (mirrors useEffect's own deps-array contract). oxlint's
// exhaustive-deps and complex-expression warnings on the line below are
// expected for this pattern and don't indicate a bug.
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]): AsyncState<T> & { refetch: () => void } {
  const [state, setState] = useState<AsyncState<T>>({ data: null, loading: true, error: null })
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let cancelled = false
    setState((s) => ({ ...s, loading: true, error: null }))
    fn()
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: null })
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setState({ data: null, loading: false, error: err instanceof Error ? err.message : 'Something went wrong' })
        }
      })
    return () => {
      cancelled = true
    }
  }, [...deps, reloadKey])

  const refetch = useCallback(() => setReloadKey((k) => k + 1), [])

  return { ...state, refetch }
}
