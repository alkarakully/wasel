import { useEffect, useState } from 'react'

/** A tiny router for /admin/<section>/<id>. */
const BASE = import.meta.env.BASE_URL.replace(/\/$/, '')

function current() {
  const path = window.location.pathname.startsWith(BASE) ? window.location.pathname.slice(BASE.length) : '/'
  const [section = '', id = ''] = path.split('/').filter(Boolean)
  return { section, id, search: new URLSearchParams(window.location.search) }
}

export function navigate(to: string, replace = false) {
  const url = BASE + (to.startsWith('/') ? to : `/${to}`)
  if (url === window.location.pathname + window.location.search) return
  window.history[replace ? 'replaceState' : 'pushState'](null, '', url)
  window.dispatchEvent(new PopStateEvent('popstate'))
}

export function useRoute() {
  const [route, setRoute] = useState(current)
  useEffect(() => {
    const update = () => setRoute(current())
    window.addEventListener('popstate', update)
    return () => window.removeEventListener('popstate', update)
  }, [])
  return route
}
