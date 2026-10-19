import { useCallback, useEffect, useRef, useState } from 'react'

import { ApiError, api } from './api'

/** Load a console endpoint; reloads when the path changes. `every` polls (ms) while the tab is visible. */
export function useLoad<T>(path: string | null, every?: number) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<ApiError | null>(null)
  const [loading, setLoading] = useState(path !== null)
  const latest = useRef(path)
  latest.current = path

  const load = useCallback(
    async (quiet = false) => {
      if (path === null) return
      if (!quiet) setLoading(true)
      try {
        const result = await api<T>(path)
        if (latest.current === path) {
          setData(result)
          setError(null)
        }
      } catch (e) {
        if (latest.current === path) setError(e instanceof ApiError ? e : new ApiError(0, null))
      } finally {
        if (latest.current === path) setLoading(false)
      }
    },
    [path],
  )

  useEffect(() => {
    void load()
    if (!every) return
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') void load(true)
    }, every)
    return () => window.clearInterval(timer)
  }, [load, every])

  return { data, error, loading, reload: () => load(true), setData }
}

/** Run an action (a POST/PATCH); keeps busy and error state for the form that started it. */
export function useAction() {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)
  const run = useCallback(async <T>(action: () => Promise<T>): Promise<T | undefined> => {
    setBusy(true)
    setError(null)
    try {
      return await action()
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError(0, null))
      return undefined
    } finally {
      setBusy(false)
    }
  }, [])
  return { busy, error, run, clear: () => setError(null) }
}
