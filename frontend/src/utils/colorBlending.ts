/**
 * Color blending utilities for Sankey chart visualization.
 * Supports N-way weighted blending for arbitrary number of category labels.
 */

interface RGBColor {
  r: number;
  g: number;
  b: number;
}

// Available gradient schemes
export type GradientScheme = 'red-blue' | 'yellow-cyan' | 'purple-green' | 'orange-teal' | 'pink-lime';

export const GRADIENT_SCHEMES: Record<GradientScheme, { start: RGBColor; end: RGBColor; name: string }> = {
  'red-blue': {
    start: { r: 220, g: 38, b: 127 },    // Deep Red
    end: { r: 59, g: 130, b: 246 },       // Blue
    name: 'Red → Blue'
  },
  'yellow-cyan': {
    start: { r: 255, g: 193, b: 7 },      // Bright Yellow
    end: { r: 6, g: 182, b: 212 },        // Bright Cyan
    name: 'Yellow → Cyan'
  },
  'purple-green': {
    start: { r: 147, g: 51, b: 234 },     // Purple
    end: { r: 34, g: 197, b: 94 },        // Green
    name: 'Purple → Green'
  },
  'orange-teal': {
    start: { r: 249, g: 115, b: 22 },     // Orange
    end: { r: 20, g: 184, b: 166 },       // Teal
    name: 'Orange → Teal'
  },
  'pink-lime': {
    start: { r: 236, g: 72, b: 153 },     // Pink
    end: { r: 132, g: 204, b: 22 },       // Lime
    name: 'Pink → Lime'
  }
};

/**
 * Get color for a position along the gradient scheme.
 * position: -1 maps to start color, +1 maps to end color.
 */
export function getGradientColor(position: number, gradientScheme: GradientScheme = 'red-blue'): RGBColor {
  position = Math.max(-1, Math.min(1, position));

  const gradient = GRADIENT_SCHEMES[gradientScheme];

  // Map [-1, 1] to [0, 1] for interpolation
  const t = (position + 1) / 2;

  return blendColors(gradient.start, gradient.end, 1 - t, t);
}


/**
 * Blend two RGB colors using additive blending
 */
export function blendColors(color1: RGBColor, color2: RGBColor, alpha1: number = 0.5, alpha2: number = 0.5): RGBColor {
  return {
    r: Math.min(255, Math.round(color1.r * alpha1 + color2.r * alpha2)),
    g: Math.min(255, Math.round(color1.g * alpha1 + color2.g * alpha2)),
    b: Math.min(255, Math.round(color1.b * alpha1 + color2.b * alpha2))
  };
}

/**
 * Convert RGB color to hex string for ECharts
 */
export function rgbToHex(color: RGBColor): string {
  const toHex = (n: number) => {
    const hex = Math.max(0, Math.min(255, Math.round(n))).toString(16);
    return hex.length === 1 ? '0' + hex : hex;
  };
  return `#${toHex(color.r)}${toHex(color.g)}${toHex(color.b)}`;
}

// Qualitative palette for N>2 categorical axes (ColorBrewer Set1-inspired)
const CATEGORICAL_PALETTE: RGBColor[] = [
  { r: 228, g: 26, b: 28 },    // red
  { r: 55, g: 126, b: 184 },   // blue
  { r: 77, g: 175, b: 74 },    // green
  { r: 152, g: 78, b: 163 },   // purple
  { r: 255, g: 127, b: 0 },    // orange
  { r: 166, g: 86, b: 40 },    // brown
  { r: 247, g: 129, b: 191 },  // pink
  { r: 0, g: 170, b: 160 },    // teal
];

/**
 * Map a discrete value to a color.
 *   2 values → gradient endpoints (binary comparison)
 *   N>2 values → distinct categorical colors from palette
 */
export function getAxisColor(value: string, sortedValues: string[], gradient: GradientScheme): RGBColor {
  const idx = sortedValues.indexOf(value);
  if (idx === -1) return { r: 128, g: 128, b: 128 }; // unknown → gray

  if (sortedValues.length <= 2) {
    // Binary: use gradient as before
    const position = sortedValues.length <= 1 ? 0 : -1 + (2 * idx / (sortedValues.length - 1));
    return getGradientColor(position, gradient);
  }

  // Categorical: distinct colors from palette
  return CATEGORICAL_PALETTE[idx % CATEGORICAL_PALETTE.length];
}

/**
 * Weighted RGB blend across N categories.
 * Each category gets its color from getAxisColor, weighted by its proportion.
 */
function weightedBlend(
  dist: Record<string, number>,
  allValues: string[],
  gradient: GradientScheme
): RGBColor {
  // Total only from values in allValues (ignore unknown labels)
  let total = 0;
  for (const [label, count] of Object.entries(dist)) {
    if (allValues.includes(label)) total += count;
  }
  if (total === 0) return getGradientColor(0, gradient); // neutral midpoint

  let r = 0, g = 0, b = 0;
  for (const [label, count] of Object.entries(dist)) {
    if (!allValues.includes(label)) continue;
    const weight = count / total;
    const color = getAxisColor(label, allValues, gradient);
    r += color.r * weight;
    g += color.g * weight;
    b += color.b * weight;
  }
  return { r: Math.round(r), g: Math.round(g), b: Math.round(b) };
}

/**
 * Get blended color for a node/link based on its category distribution.
 * Supports N-way blending: each category in the distribution contributes
 * its color weighted by its proportion.
 *
 * For dual-axis: primary and secondary are blended at 50/50.
 */
export function getNodeColor(
  primaryDist: Record<string, number>,
  primaryValues: string[],
  primaryGradient: GradientScheme = 'red-blue',
  secondaryDist?: Record<string, number> | null,
  secondaryValues?: string[],
  secondaryGradient?: GradientScheme,
): string {
  const primaryColor = weightedBlend(primaryDist, primaryValues, primaryGradient);

  if (!secondaryDist || !secondaryValues || secondaryValues.length === 0) {
    return rgbToHex(primaryColor);
  }

  const secGrad = secondaryGradient || GRADIENT_AUTO_PAIRS[primaryGradient];
  const secondaryColor = weightedBlend(secondaryDist, secondaryValues, secGrad);
  return rgbToHex(blendColors(primaryColor, secondaryColor, 0.5, 0.5));
}

/**
 * Auto-pairing table: each primary gradient maps to a complementary secondary gradient.
 * Pairs are chosen so the 4 blended corners are perceptually distinct.
 */
export const GRADIENT_AUTO_PAIRS: Record<GradientScheme, GradientScheme> = {
  'red-blue': 'yellow-cyan',
  'yellow-cyan': 'red-blue',
  'purple-green': 'orange-teal',
  'orange-teal': 'purple-green',
  'pink-lime': 'yellow-cyan',
};

/**
 * Get color for a single data point (trajectory, probe) based on discrete axis values.
 * Unlike getNodeColor() which works with distributions, this works with individual values.
 * Supports blending two axes — primary uses user-selected gradient, secondary auto-pairs.
 */
export function getPointColor(
  primaryValue: string,
  primaryValues: string[],
  primaryGradient: GradientScheme = 'red-blue',
  secondaryValue?: string,
  secondaryValues?: string[],
): string {
  const color1 = getAxisColor(primaryValue, primaryValues, primaryGradient);
  if (!secondaryValue || !secondaryValues || secondaryValues.length === 0) {
    return rgbToHex(color1);
  }
  const secGrad = GRADIENT_AUTO_PAIRS[primaryGradient];
  const color2 = getAxisColor(secondaryValue, secondaryValues, secGrad);
  return rgbToHex(blendColors(color1, color2, 0.5, 0.5));
}

/**
 * Get preview colors for axis combinations. Works for any axis cardinality.
 * Returns array of {label, color} entries for all value combinations.
 */
export function getAxisPreview(
  primaryValues: string[],
  primaryGradient: GradientScheme,
  secondaryValues?: string[],
): Array<{ label: string; color: string }> {
  const results: Array<{ label: string; color: string }> = [];
  const secGrad = GRADIENT_AUTO_PAIRS[primaryGradient];

  if (!secondaryValues || secondaryValues.length === 0) {
    // Single axis: show color for each value
    for (const val of primaryValues) {
      const color = getAxisColor(val, primaryValues, primaryGradient);
      results.push({ label: val, color: rgbToHex(color) });
    }
  } else {
    // Dual axis: show N×M grid
    for (const pVal of primaryValues) {
      for (const sVal of secondaryValues) {
        const c1 = getAxisColor(pVal, primaryValues, primaryGradient);
        const c2 = getAxisColor(sVal, secondaryValues, secGrad);
        const blended = blendColors(c1, c2, 0.5, 0.5);
        results.push({ label: `${pVal} + ${sVal}`, color: rgbToHex(blended) });
      }
    }
  }

  return results;
}

/**
 * Calculate visual properties based on traffic volume
 * Returns opacity and line width for route visualization
 */
export function getTrafficVisualProperties(value: number, maxValue: number): { opacity: number; lineWidth: number } {
  if (maxValue === 0) {
    return { opacity: 0.3, lineWidth: 1 };
  }

  // Square-root scale for proportional differentiation
  const normalizedValue = Math.sqrt(value) / Math.sqrt(maxValue);

  // Opacity: 0.3 to 0.9 range
  const opacity = 0.3 + (normalizedValue * 0.6);

  // Line width: 1 to 6 pixel range
  const lineWidth = 1 + (normalizedValue * 5);

  return { opacity, lineWidth };
}
