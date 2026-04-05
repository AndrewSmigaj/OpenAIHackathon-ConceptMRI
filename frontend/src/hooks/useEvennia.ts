import { useRef, useCallback, useEffect, useState } from 'react'

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting'

/** Parsed Evennia message: [cmdname, args, kwargs] */
export type EvenniaMessage = [string, unknown[], Record<string, unknown>]

interface UseEvenniaOptions {
  /** WebSocket URL (default: ws://localhost:4002) */
  url?: string
  /** Called for text/prompt messages — raw text content */
  onText?: (text: string) => void
  /** Called for non-text OOB messages (room_entered, room_left, etc.) */
  onOOB?: (cmdname: string, args: unknown[], kwargs: Record<string, unknown>) => void
  /** Auto-reconnect on disconnect (default: true) */
  autoReconnect?: boolean
}

export function useEvennia(options: UseEvenniaOptions = {}) {
  const {
    url = 'ws://localhost:4002',
    onText,
    onOOB,
    autoReconnect = true,
  } = options

  const [status, setStatus] = useState<ConnectionStatus>('disconnected')
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectDelay = useRef(1000)
  const intentionalClose = useRef(false)

  // Keep callbacks in refs to avoid reconnection on callback change
  const onTextRef = useRef(onText)
  const onOOBRef = useRef(onOOB)
  onTextRef.current = onText
  onOOBRef.current = onOOB

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current)
      reconnectTimer.current = null
    }
  }, [])

  const connect = useCallback(() => {
    // Clean up existing connection
    if (wsRef.current) {
      intentionalClose.current = true
      wsRef.current.close()
      wsRef.current = null
    }
    clearReconnectTimer()
    intentionalClose.current = false

    setStatus('connecting')
    const ws = new WebSocket(url)

    ws.onopen = () => {
      setStatus('connected')
      reconnectDelay.current = 1000 // reset backoff

      // Request RAW mode — Evennia sends ANSI instead of HTML
      ws.send(JSON.stringify(['client_options', [], { raw: true }]))
    }

    ws.onmessage = (event) => {
      try {
        const msg: EvenniaMessage = JSON.parse(event.data)
        const [cmdname, args, kwargs] = msg

        if (cmdname === 'text' || cmdname === 'prompt') {
          // Text output from Evennia
          const text = Array.isArray(args) ? args.map(String).join('') : String(args)
          onTextRef.current?.(text)
        } else {
          // OOB message (room_entered, room_left, client_options response, etc.)
          onOOBRef.current?.(cmdname, args || [], kwargs || {})
        }
      } catch {
        // Non-JSON message — treat as raw text
        onTextRef.current?.(event.data)
      }
    }

    ws.onclose = () => {
      wsRef.current = null
      if (intentionalClose.current) {
        setStatus('disconnected')
        return
      }

      if (autoReconnect) {
        setStatus('reconnecting')
        reconnectTimer.current = setTimeout(() => {
          reconnectDelay.current = Math.min(reconnectDelay.current * 2, 30000)
          connect()
        }, reconnectDelay.current)
      } else {
        setStatus('disconnected')
      }
    }

    ws.onerror = () => {
      // onclose will fire after onerror — reconnection handled there
    }

    wsRef.current = ws
  }, [url, autoReconnect, clearReconnectTimer])

  const disconnect = useCallback(() => {
    intentionalClose.current = true
    clearReconnectTimer()
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setStatus('disconnected')
  }, [clearReconnectTimer])

  /** Send a text command to Evennia */
  const sendCommand = useCallback((text: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(['text', [text], {}]))
    }
  }, [])

  /** Send a raw OOB message to Evennia */
  const sendOOB = useCallback((cmdname: string, args: unknown[] = [], kwargs: Record<string, unknown> = {}) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify([cmdname, args, kwargs]))
    }
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      intentionalClose.current = true
      clearReconnectTimer()
      wsRef.current?.close()
    }
  }, [clearReconnectTimer])

  return { status, connect, disconnect, sendCommand, sendOOB }
}
