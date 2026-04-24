import { useState, useEffect, useRef, useCallback } from 'react'
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
  const prevStatusRef = useRef<ConnectionStatus>('disconnected')
  const [inputValue, setInputValue] = useState('')

  // Write text to xterm.js, converting \n to \r\n for proper display
  const writeToTerminal = useCallback((text: string) => {
    if (!terminalRef.current) return
    // Evennia RAW mode sends \n — xterm.js needs \r\n
    let normalized = text.replace(/\r?\n/g, '\r\n')
    // Ensure each message ends with a newline so consecutive messages don't run together
    if (!normalized.endsWith('\r\n')) normalized += '\r\n'
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

  // Initialize xterm.js (output-only)
  useEffect(() => {
    if (!containerRef.current) return

    const terminal = new Terminal({
      cursorBlink: false,
      disableStdin: true,
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
  }, [])

  // Auto-connect on mount
  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])

  return (
    <div className="w-full h-full flex flex-col">
      <div ref={containerRef} className="flex-1 min-h-0" />
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (inputValue.trim()) {
            writeToTerminal(`\x1b[1;37m> ${inputValue}\x1b[0m`)
          }
          sendCommand(inputValue)
          setInputValue('')
        }}
        className="flex border-t border-gray-700"
      >
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Enter command..."
          className="flex-1 bg-gray-800 text-green-400 font-mono text-sm px-2 py-1.5 outline-none placeholder-gray-600"
          autoFocus
        />
      </form>
    </div>
  )
}
