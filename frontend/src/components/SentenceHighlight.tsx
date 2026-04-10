import React from 'react'

interface SentenceHighlightProps {
  text: string
  targetWord: string
  color: string
  charOffset?: number
}

/**
 * Renders a sentence with the target word highlighted in the given color.
 *
 * When charOffset is provided, highlights only the occurrence at that
 * character position. Otherwise falls back to highlighting all occurrences
 * via case-insensitive word-boundary matching.
 */
export default function SentenceHighlight({ text, targetWord, color, charOffset }: SentenceHighlightProps) {
  if (!text || !targetWord) {
    return <span>{text || ''}</span>
  }

  // Single-occurrence mode: highlight only at the specific character offset
  if (charOffset != null && charOffset >= 0 && charOffset < text.length) {
    const before = text.slice(0, charOffset)
    const match = text.slice(charOffset, charOffset + targetWord.length)
    const after = text.slice(charOffset + targetWord.length)
    return (
      <span>
        <span>{before}</span>
        <span style={{ color, fontWeight: 'bold' }}>{match}</span>
        <span>{after}</span>
      </span>
    )
  }

  // Global mode: highlight all occurrences (sentence sets, old sessions)
  const escaped = targetWord.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const splitRegex = new RegExp(`(\\b${escaped}\\b)`, 'gi')
  const matchRegex = new RegExp(`^${escaped}$`, 'i')
  const parts = text.split(splitRegex)

  return (
    <span>
      {parts.map((part, i) =>
        matchRegex.test(part) ? (
          <span key={i} style={{ color, fontWeight: 'bold' }}>{part}</span>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </span>
  )
}
