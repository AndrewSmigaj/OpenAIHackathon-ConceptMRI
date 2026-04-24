// Convert Evennia output (HTML or markup) to ANSI escape sequences for xterm.js

const ESC = '\x1b['

// Evennia HTML color classes → ANSI (color-000 through color-015)
const HTML_COLOR_TO_ANSI: Record<string, string> = {
  '000': `${ESC}30m`,   '001': `${ESC}31m`,   '002': `${ESC}32m`,   '003': `${ESC}33m`,
  '004': `${ESC}34m`,   '005': `${ESC}35m`,   '006': `${ESC}36m`,   '007': `${ESC}37m`,
  '008': `${ESC}90m`,   '009': `${ESC}91m`,   '010': `${ESC}92m`,   '011': `${ESC}93m`,
  '012': `${ESC}94m`,   '013': `${ESC}95m`,   '014': `${ESC}96m`,   '015': `${ESC}97m`,
}

// Evennia |x markup → ANSI
const MARKUP_TO_ANSI: Record<string, string> = {
  '|n': `${ESC}0m`,
  '|r': `${ESC}1;31m`, '|g': `${ESC}1;32m`, '|y': `${ESC}1;33m`, '|b': `${ESC}1;34m`,
  '|m': `${ESC}1;35m`, '|c': `${ESC}1;36m`, '|w': `${ESC}1;37m`, '|x': `${ESC}1;30m`,
  '|R': `${ESC}0;31m`, '|G': `${ESC}0;32m`, '|Y': `${ESC}0;33m`, '|B': `${ESC}0;34m`,
  '|M': `${ESC}0;35m`, '|C': `${ESC}0;36m`, '|W': `${ESC}0;37m`, '|X': `${ESC}0;30m`,
  '|u': `${ESC}4m`, '|i': `${ESC}3m`, '|s': `${ESC}9m`, '|*': `${ESC}7m`, '|^': `${ESC}5m`,
  '|[r': `${ESC}41m`, '|[g': `${ESC}42m`, '|[y': `${ESC}43m`, '|[b': `${ESC}44m`,
  '|[m': `${ESC}45m`, '|[c': `${ESC}46m`, '|[w': `${ESC}47m`, '|[x': `${ESC}40m`,
  '|[R': `${ESC}41m`, '|[G': `${ESC}42m`, '|[Y': `${ESC}43m`, '|[B': `${ESC}44m`,
  '|[M': `${ESC}45m`, '|[C': `${ESC}46m`, '|[W': `${ESC}47m`, '|[X': `${ESC}40m`,
}

const MARKUP_PATTERN = /\|\[[a-zA-Z]|\|[rgybmcwxRGYBMCWXnuis*^]/g

const HTML_ENTITIES: Record<string, string> = {
  '&lt;': '<', '&gt;': '>', '&amp;': '&', '&#x27;': "'", '&quot;': '"', '&#39;': "'",
}
const ENTITY_PATTERN = /&(?:lt|gt|amp|quot|#x27|#39);/g

export function evenniaToAnsi(text: string): string {
  let result = text

  // HTML mode: convert <br> to newlines, <span class="color-NNN"> to ANSI, strip </span>
  if (result.includes('<')) {
    result = result.replace(/<br\s*\/?>/gi, '\n')
    result = result.replace(/<span class="color-(\d{3})">/g, (_match, code) => {
      return HTML_COLOR_TO_ANSI[code] || ''
    })
    result = result.replace(/<\/span>/g, `${ESC}0m`)
    result = result.replace(/<[^>]+>/g, '')
  }

  // Unescape HTML entities
  result = result.replace(ENTITY_PATTERN, (match) => HTML_ENTITIES[match] || match)

  // Convert Evennia markup codes
  result = result.replace(MARKUP_PATTERN, (match) => MARKUP_TO_ANSI[match] || '')

  return result
}
