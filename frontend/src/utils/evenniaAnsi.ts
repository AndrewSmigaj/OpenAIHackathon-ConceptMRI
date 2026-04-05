// Convert Evennia markup codes to ANSI escape sequences for xterm.js
// Reference: evennia/utils/ansi.py lines 146-197

const ESC = '\x1b['

const MARKUP_TO_ANSI: Record<string, string> = {
  // Reset
  '|n': `${ESC}0m`,
  // Bright foreground
  '|r': `${ESC}1;31m`,
  '|g': `${ESC}1;32m`,
  '|y': `${ESC}1;33m`,
  '|b': `${ESC}1;34m`,
  '|m': `${ESC}1;35m`,
  '|c': `${ESC}1;36m`,
  '|w': `${ESC}1;37m`,
  '|x': `${ESC}1;30m`,
  // Dark foreground
  '|R': `${ESC}0;31m`,
  '|G': `${ESC}0;32m`,
  '|Y': `${ESC}0;33m`,
  '|B': `${ESC}0;34m`,
  '|M': `${ESC}0;35m`,
  '|C': `${ESC}0;36m`,
  '|W': `${ESC}0;37m`,
  '|X': `${ESC}0;30m`,
  // Formatting
  '|u': `${ESC}4m`,
  '|i': `${ESC}3m`,
  '|s': `${ESC}9m`,
  '|*': `${ESC}7m`,
  '|^': `${ESC}5m`,
  // Background colors
  '|[r': `${ESC}41m`,
  '|[g': `${ESC}42m`,
  '|[y': `${ESC}43m`,
  '|[b': `${ESC}44m`,
  '|[m': `${ESC}45m`,
  '|[c': `${ESC}46m`,
  '|[w': `${ESC}47m`,
  '|[x': `${ESC}40m`,
  '|[R': `${ESC}41m`,
  '|[G': `${ESC}42m`,
  '|[Y': `${ESC}43m`,
  '|[B': `${ESC}44m`,
  '|[M': `${ESC}45m`,
  '|[C': `${ESC}46m`,
  '|[W': `${ESC}47m`,
  '|[X': `${ESC}40m`,
}

// Match background codes (|[X) before foreground (|X), then special chars (|*, |^, |n)
const MARKUP_PATTERN = /\|\[[a-zA-Z]|\|[rgybmcwxRGYBMCWXnuis*^]/g

const HTML_ENTITIES: Record<string, string> = {
  '&lt;': '<',
  '&gt;': '>',
  '&amp;': '&',
  '&#x27;': "'",
  '&quot;': '"',
  '&#39;': "'",
}

const ENTITY_PATTERN = /&(?:lt|gt|amp|quot|#x27|#39);/g

export function evenniaToAnsi(text: string): string {
  // Unescape HTML entities (Evennia HTML-escapes in raw mode)
  let result = text.replace(ENTITY_PATTERN, (match) => HTML_ENTITIES[match] || match)
  // Convert Evennia markup to ANSI
  result = result.replace(MARKUP_PATTERN, (match) => MARKUP_TO_ANSI[match] || '')
  return result
}
