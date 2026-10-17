import { useCallback, useEffect, useRef, useState } from 'react'

import { Api, ApiError, BOARD_STATUSES, type Order } from './api'

/**
 * Open orders for the signed-in owner's stores, kept current over the live
 * socket. Reconnects with backoff and reloads after reconnecting so nothing
 * missed while offline is lost.
 */
export function useLiveOrders(api: Api, onUnauthorized: () => void) {
  const [orders, setOrders] = useState<Order[]>([])
  const [loaded, setLoaded] = useState(false)
  const [connected, setConnected] = useState(true)
  const unauthorized = useRef(onUnauthorized)
  useEffect(() => {
    unauthorized.current = onUnauthorized
  }, [onUnauthorized])

  const reload = useCallback(async () => {
    try {
      setOrders(await api.openOrders())
      setLoaded(true)
    } catch (error) {
      if (error instanceof ApiError && error.code === 'unauthorized') unauthorized.current()
    }
  }, [api])

  /** Put a fresh copy of an order on the board, or take it off when it's done. */
  const upsert = useCallback((order: Order) => {
    setOrders((current) => {
      const others = current.filter((o) => o.id !== order.id)
      return BOARD_STATUSES.includes(order.status) ? [...others, order] : others
    })
  }, [])

  useEffect(() => {
    let socket: WebSocket | null = null
    let retry = 0
    let stopped = false
    let reconnectTimer: ReturnType<typeof setTimeout>
    let pingTimer: ReturnType<typeof setInterval>

    const connect = () => {
      socket = new WebSocket(api.socketUrl())
      socket.onmessage = (event) => {
        const message = JSON.parse(event.data)
        if (message.type === 'connected') {
          retry = 0
          setConnected(true)
          reload()
        } else if (message.type === 'order.updated') {
          upsert(message.order)
        }
      }
      socket.onclose = (event) => {
        clearInterval(pingTimer)
        if (stopped) return
        if (event.code === 4401) {
          unauthorized.current()
          return
        }
        setConnected(false)
        reconnectTimer = setTimeout(connect, Math.min(30000, 1000 * 2 ** retry++))
      }
      pingTimer = setInterval(() => socket?.readyState === WebSocket.OPEN && socket.send('{"type":"ping"}'), 25000)
    }

    connect()
    return () => {
      stopped = true
      clearTimeout(reconnectTimer)
      clearInterval(pingTimer)
      socket?.close()
    }
  }, [api, reload, upsert])

  return { orders, loaded, connected, reload, upsert }
}
