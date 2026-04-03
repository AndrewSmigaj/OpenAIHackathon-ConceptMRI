import { useEffect, useRef } from 'react'
import { Terminal } from '@xterm/xterm'
import '@xterm/xterm/css/xterm.css'

export default function MUDTerminal() {
  const containerRef = useRef<HTMLDivElement>(null)

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
      },
    })

    terminal.open(containerRef.current)
    terminal.write('Terminal ready. Evennia connection in Phase 2.\r\n')

    return () => {
      terminal.dispose()
    }
  }, [])

  return <div ref={containerRef} className="w-full h-full" />
}
