import { useEffect, useRef, useCallback } from 'react'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'
import { useEvennia, type ConnectionStatus } from '../../hooks/useEvennia'
import { evenniaToAnsi } from '../../utils/evenniaAnsi'

interface MUDTerminalProps {
  onOOB?: (cmdname: string, args: unknown[], kwargs: Record<string, unknown>) => void
}

const STATUS_COLORS: Record<ConnectionStatus, string> = {
  connected: '\x1b[32m',     // green
  connecting: '\x1b[33m',    // yellow
  reconnecting: '\x1b[33m',  // yellow
  disconnected: '\x1b[31m',  // red
}

export default function MUDTerminal({ onOOB }: MUDTerminalProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const terminalRef = useRef<Terminal | null>(null)
  const fitAddonRef = useRef<FitAddon | null>(null)
  const lineBufferRef = useRef('')
  const prevStatusRef = useRef<ConnectionStatus>('disconnected')

  // Write text to xterm.js, converting \n to \r\n for proper display
  const writeToTerminal = useCallback((text: string) => {
    if (!terminalRef.current) return
    // Evennia RAW mode sends \n — xterm.js needs \r\n
    const normalized = text.replace(/\r?\n/g, '\r\n')
    terminalRef.current.write(normalized)
  }, [])

  const handleText = useCallback((text: string) => {
    writeToTerminal(evenniaToAnsi(text))
  }, [writeToTerminal])

  const { status, connect, disconnect, sendCommand } = useEvennia({
    onText: handleText,
    onOOB,
  })

  // Show status changes in terminal
  useEffect(() => {
    if (!terminalRef.current || status === prevStatusRef.current) return
    prevStatusRef.current = status
    const color = STATUS_COLORS[status]
    terminalRef.current.write(`\r\n${color}[${status}]\x1b[0m\r\n`)
  }, [status])

  // Initialize xterm.js
  useEffect(() => {
    if (!containerRef.current) return

    const terminal = new Terminal({
      cursorBlink: true,
      disableStdin: false,
      fontSize: 12,
      fontFamily: 'monospace',
      theme: {
        background: '#111827',
        foreground: '#4ade80',
        cursor: '#4ade80',
      },
    })

    const fitAddon = new FitAddon()
    terminal.loadAddon(fitAddon)
    terminal.open(containerRef.current)
    fitAddon.fit()

    terminalRef.current = terminal
    fitAddonRef.current = fitAddon

    // Line-based input handling
    terminal.onData((data: string) => {
      for (const char of data) {
        if (char === '\r' || char === '\n') {
          // Enter — send buffered line
          terminal.write('\r\n')
          sendCommand(lineBufferRef.current)
          lineBufferRef.current = ''
        } else if (char === '\x7f' || char === '\b') {
          // Backspace/Delete
          if (lineBufferRef.current.length > 0) {
            lineBufferRef.current = lineBufferRef.current.slice(0, -1)
            terminal.write('\b \b')
          }
        } else if (char >= ' ') {
          // Printable character — echo and buffer
          lineBufferRef.current += char
          terminal.write(char)
        }
      }
    })

    // Resize handling
    const resizeObserver = new ResizeObserver(() => {
      requestAnimationFrame(() => fitAddon.fit())
    })
    resizeObserver.observe(containerRef.current)

    return () => {
      resizeObserver.disconnect()
      terminal.dispose()
      terminalRef.current = null
      fitAddonRef.current = null
    }
  }, [sendCommand])

  // Auto-connect on mount
  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])

  return <div ref={containerRef} className="w-full h-full" />
}
