/**
 * Color blending utilities for Sankey chart visualization with additive RGB blending.
 * Colors nodes/links along a single axis defined by two label strings (e.g. "aquatic" vs "military").
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
 * Calculate position along a gradient axis from two category counts.
 * Returns value from -1 (fully categoryA) to +1 (fully categoryB).
 */
export function calculateCategoryPosition(
  categoryDistribution: Record<string, number>,
  categoryA: string,
  categoryB: string
): number {
  const countA = categoryDistribution[categoryA] || 0;
  const countB = categoryDistribution[categoryB] || 0;
  const total = countA + countB;

  if (total === 0) {
    return 0; // Neutral — no data for either label
  }

  // -1 = fully A, +1 = fully B
  return (countB / total) - (countA / total);
}

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

/**
 * Get the final blended color for a node based on selected categories and distribution.
 * primaryCategoryA/B define the single color axis. Secondary params are for future dual-axis support.
 */
export function getNodeColor(
  categoryDistribution: Record<string, number>,
  primaryCategoryA: string,
  primaryCategoryB: string,
  secondaryCategoryA?: string,
  secondaryCategoryB?: string,
  primaryGradient: GradientScheme = 'red-blue',
  secondaryGradient: GradientScheme = 'yellow-cyan'
): string {
  const primaryPosition = calculateCategoryPosition(categoryDistribution, primaryCategoryA, primaryCategoryB);
  const primaryColor = getGradientColor(primaryPosition, primaryGradient);

  if (!secondaryCategoryA || !secondaryCategoryB) {
    return rgbToHex(primaryColor);
  }

  // Dual axis — blend gradient colors from both axes with equal weighting
  const secondaryPosition = calculateCategoryPosition(categoryDistribution, secondaryCategoryA, secondaryCategoryB);
  const secondaryColor = getGradientColor(secondaryPosition, secondaryGradient);

  const blendedColor = blendColors(primaryColor, secondaryColor, 0.5, 0.5);
  return rgbToHex(blendedColor);
}

/**
 * Get a preview showing gradient extremes and key points for the selected categories
 */
export function getColorPreview(
  primaryCategoryA: string,
  primaryCategoryB: string,
  secondaryCategoryA?: string,
  secondaryCategoryB?: string,
  primaryGradient: GradientScheme = 'red-blue',
  secondaryGradient: GradientScheme = 'yellow-cyan'
): Record<string, string> {
  const preview: Record<string, string> = {};

  if (!secondaryCategoryA || !secondaryCategoryB) {
    // Single axis preview — gradient extremes and middle
    preview[`All ${primaryCategoryA}`] = rgbToHex(getGradientColor(-1, primaryGradient));
    preview['Mixed'] = rgbToHex(getGradientColor(0, primaryGradient));
    preview[`All ${primaryCategoryB}`] = rgbToHex(getGradientColor(1, primaryGradient));
  } else {
    // Dual axis preview — combinations of extremes
    const positions = [-1, 0, 1];
    const getLabel = (p: number, catA: string, catB: string) => {
      return p === -1 ? catA.substring(0, 3) : p === 0 ? 'Mix' : catB.substring(0, 3);
    };

    positions.forEach((p1) => {
      positions.forEach((p2) => {
        const color1 = getGradientColor(p1, primaryGradient);
        const color2 = getGradientColor(p2, secondaryGradient);
        const blended = blendColors(color1, color2, 0.5, 0.5);
        const label = `${getLabel(p1, primaryCategoryA, primaryCategoryB)}+${getLabel(p2, secondaryCategoryA, secondaryCategoryB)}`;
        preview[label] = rgbToHex(blended);
      });
    });
  }

  return preview;
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
 * Map a discrete value to a color on a gradient.
 * Values are mapped to evenly-spaced positions from -1 to +1:
 *   2 values → [-1, +1] (gradient endpoints)
 *   3 values → [-1, 0, +1]
 *   N values → evenly spaced
 */
export function getAxisColor(value: string, sortedValues: string[], gradient: GradientScheme): RGBColor {
  const idx = sortedValues.indexOf(value);
  if (idx === -1) return getGradientColor(0, gradient); // unknown → midpoint
  const position = sortedValues.length <= 1 ? 0 : -1 + (2 * idx / (sortedValues.length - 1));
  return getGradientColor(position, gradient);
}

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
