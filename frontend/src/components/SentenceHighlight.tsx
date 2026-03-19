import React from 'react'

interface SentenceHighlightProps {
  text: string
  targetWord: string
  color: string
}

/**
 * Renders a sentence with the target word highlighted in the given color.
 * Uses case-insensitive word-boundary matching.
 */
export default function SentenceHighlight({ text, targetWord, color }: SentenceHighlightProps) {
  if (!text || !targetWord) {
    return <span>{text || ''}</span>
  }

  // Escape special regex characters in targetWord
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
