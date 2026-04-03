/**
 * Single source of truth for the output-category node name prefix.
 * Backend produces nodes like "Generated:aquarium"; frontend uses these
 * helpers to filter, split, and test output nodes without magic strings.
 */

export const OUTPUT_NODE_PREFIX = 'Generated:'

export function isOutputNode(name: string): boolean {
  return name.startsWith(OUTPUT_NODE_PREFIX)
}

export function isOutputLink(link: { target: string }): boolean {
  return link.target.startsWith(OUTPUT_NODE_PREFIX)
}

export function stripOutputPrefix(name: string): string {
  return name.startsWith(OUTPUT_NODE_PREFIX)
    ? name.slice(OUTPUT_NODE_PREFIX.length)
    : name
}
