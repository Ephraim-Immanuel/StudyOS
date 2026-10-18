import { useCallback, useEffect, useRef, useState } from 'react'

// Runs an async loader on mount and whenever `deps` change.
// Returns { data, error, loading, reload }.
export function useAsync(loader, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true })
  const loaderRef = useRef(loader)
  loaderRef.current = loader
  const counter = useRef(0)

  const run = useCallback(() => {
    const id = ++counter.current // ignore stale responses from older calls
    setState((s) => ({ ...s, loading: true, error: null }))
    loaderRef.current()
      .then((data) => id === counter.current && setState({ data, error: null, loading: false }))
      .catch((error) => id === counter.current && setState({ data: null, error, loading: false }))
  }, [])

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(run, deps)
  return { ...state, reload: run }
}
