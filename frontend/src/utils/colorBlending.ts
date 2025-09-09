/**
 * Color blending utilities for Sankey chart visualization with additive RGB blending
 * Supports 1-2 axis selection with meaningful color combinations
 */

// Temporary backwards compatibility
export type ColorAxis = 'sentiment' | 'concreteness' | 'pos' | 'action-content';

// Mapping of old axis types to category pairs
const AXIS_CATEGORY_MAP: Record<ColorAxis, { neg: string; pos: string }> = {
  sentiment: { neg: 'negative', pos: 'positive' },
  concreteness: { neg: 'abstract', pos: 'concrete' },
  pos: { neg: 'nouns', pos: 'verbs' },
  'action-content': { neg: 'action', pos: 'content' }
};

interface RGBColor {
  r: number;
  g: number;
  b: number;
}

// Available gradient schemes
export type GradientScheme = 'red-blue' | 'yellow-cyan' | 'purple-green' | 'orange-teal' | 'pink-lime';

export const GRADIENT_SCHEMES: Record<GradientScheme, { negative: RGBColor; positive: RGBColor; name: string }> = {
  'red-blue': {
    negative: { r: 220, g: 38, b: 127 },    // Deep Red
    positive: { r: 59, g: 130, b: 246 },    // Blue
    name: 'Red → Blue'
  },
  'yellow-cyan': {
    negative: { r: 255, g: 193, b: 7 },     // Bright Yellow
    positive: { r: 6, g: 182, b: 212 },     // Bright Cyan
    name: 'Yellow → Cyan'
  },
  'purple-green': {
    negative: { r: 147, g: 51, b: 234 },    // Purple
    positive: { r: 34, g: 197, b: 94 },     // Green
    name: 'Purple → Green'
  },
  'orange-teal': {
    negative: { r: 249, g: 115, b: 22 },    // Orange
    positive: { r: 20, g: 184, b: 166 },    // Teal
    name: 'Orange → Teal'
  },
  'pink-lime': {
    negative: { r: 236, g: 72, b: 153 },    // Pink
    positive: { r: 132, g: 204, b: 22 },    // Lime
    name: 'Pink → Lime'
  }
};

/**
 * Calculate position based on two selected categories
 * Returns value from -1 to +1 representing position between negative and positive categories
 */
export function calculateCategoryPosition(
  categoryDistribution: Record<string, number>, 
  negativeCategory: string, 
  positiveCategory: string
): number {
  const negCount = categoryDistribution[negativeCategory] || 0;
  const posCount = categoryDistribution[positiveCategory] || 0;
  const totalCount = negCount + posCount;
  
  if (totalCount === 0) {
    return 0; // Neutral position
  }
  
  const posRatio = posCount / totalCount;
  const negRatio = negCount / totalCount;
  
  // Position: -1 (fully negative category) to +1 (fully positive category)
  return posRatio - negRatio;
}

/**
 * Get color for gradient position using specified gradient scheme
 */
export function getGradientColor(position: number, gradientScheme: GradientScheme = 'red-blue'): RGBColor {
  // Clamp position to [-1, 1]
  position = Math.max(-1, Math.min(1, position));
  
  const gradient = GRADIENT_SCHEMES[gradientScheme];
  
  // Map position [-1, 1] to [0, 1] for interpolation
  const t = (position + 1) / 2;
  
  return blendColors(gradient.negative, gradient.positive, 1 - t, t);
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
 * Get the final blended color for a node based on selected categories and distribution
 */
export function getNodeColor(
  categoryDistribution: Record<string, number>,
  primaryNegCategory: string,
  primaryPosCategory: string,
  secondaryNegCategory?: string,
  secondaryPosCategory?: string,
  primaryGradient: GradientScheme = 'red-blue',
  secondaryGradient: GradientScheme = 'yellow-cyan'
): string {
  // Calculate primary axis position and color
  const primaryPosition = calculateCategoryPosition(categoryDistribution, primaryNegCategory, primaryPosCategory);
  const primaryColor = getGradientColor(primaryPosition, primaryGradient);
  
  if (!secondaryNegCategory || !secondaryPosCategory) {
    // Single axis - return primary gradient color
    return rgbToHex(primaryColor);
  }
  
  // Dual axis - blend gradient colors from both axes with equal weighting
  const secondaryPosition = calculateCategoryPosition(categoryDistribution, secondaryNegCategory, secondaryPosCategory);
  const secondaryColor = getGradientColor(secondaryPosition, secondaryGradient);
  
  // Equal weighting for both axes
  const blendedColor = blendColors(primaryColor, secondaryColor, 0.5, 0.5);
  return rgbToHex(blendedColor);
}

/**
 * Get a preview showing gradient extremes and key points for the selected categories
 */
export function getColorPreview(
  primaryNegCategory: string,
  primaryPosCategory: string,
  secondaryNegCategory?: string,
  secondaryPosCategory?: string,
  primaryGradient: GradientScheme = 'red-blue',
  secondaryGradient: GradientScheme = 'yellow-cyan'
): Record<string, string> {
  const preview: Record<string, string> = {};
  
  if (!secondaryNegCategory || !secondaryPosCategory) {
    // Single axis preview - show gradient extremes and middle
    preview[`All ${primaryNegCategory}`] = rgbToHex(getGradientColor(-1, primaryGradient));
    preview['Mixed'] = rgbToHex(getGradientColor(0, primaryGradient));
    preview[`All ${primaryPosCategory}`] = rgbToHex(getGradientColor(1, primaryGradient));
  } else {
    // Dual axis preview - show combinations of extremes
    const positions = [-1, 0, 1];
    const getLabel = (pos: number, negCat: string, posCat: string) => {
      return pos === -1 ? negCat.substring(0, 3) : pos === 0 ? 'Mix' : posCat.substring(0, 3);
    };
    
    positions.forEach((pos1) => {
      positions.forEach((pos2) => {
        const color1 = getGradientColor(pos1, primaryGradient);
        const color2 = getGradientColor(pos2, secondaryGradient);
        const blended = blendColors(color1, color2, 0.5, 0.5);
        const label = `${getLabel(pos1, primaryNegCategory, primaryPosCategory)}+${getLabel(pos2, secondaryNegCategory, secondaryPosCategory)}`;
        preview[label] = rgbToHex(blended);
      });
    });
  }
  
  return preview;
}


// Backwards compatibility wrappers
export function getAxisLabel(axis: ColorAxis): string {
  switch (axis) {
    case 'sentiment': return 'Sentiment';
    case 'concreteness': return 'Concreteness';
    case 'pos': return 'Part of Speech';
    case 'action-content': return 'Action-Content';
    default: return axis;
  }
}

export function getAxisColor(categoryDistribution: Record<string, number>, axis: ColorAxis): RGBColor {
  const { neg, pos } = AXIS_CATEGORY_MAP[axis];
  const position = calculateCategoryPosition(categoryDistribution, neg, pos);
  return getGradientColor(position, 'red-blue');
}

export function getDivergentAxisColor(position: number, axis: ColorAxis): RGBColor {
  return getGradientColor(position, 'red-blue');
}

// getNodeColor with ColorAxis and gradient support
export function getNodeColorWithGradients(
  categoryDistribution: Record<string, number>,
  primaryAxis: ColorAxis,
  secondaryAxis?: ColorAxis,
  primaryGradient: GradientScheme = 'red-blue',
  secondaryGradient: GradientScheme = 'yellow-cyan'
): string {
  const primary = AXIS_CATEGORY_MAP[primaryAxis];
  const secondary = secondaryAxis ? AXIS_CATEGORY_MAP[secondaryAxis] : undefined;
  
  return getNodeColor(categoryDistribution, primary.neg, primary.pos, secondary?.neg, secondary?.pos, primaryGradient, secondaryGradient);
}

// Legacy getColorPreview with ColorAxis
export function getColorPreviewLegacy(primaryAxis: ColorAxis, secondaryAxis?: ColorAxis): Record<string, string> {
  const primary = AXIS_CATEGORY_MAP[primaryAxis];
  const secondary = secondaryAxis ? AXIS_CATEGORY_MAP[secondaryAxis] : undefined;
  
  return getColorPreview(primary.neg, primary.pos, secondary?.neg, secondary?.pos, 'red-blue', 'yellow-cyan');
}

/**
 * Calculate visual properties based on traffic volume
 * Returns opacity and line width for route visualization
 */
export function getTrafficVisualProperties(value: number, maxValue: number): { opacity: number; lineWidth: number } {
  if (maxValue === 0) {
    return { opacity: 0.3, lineWidth: 1 };
  }
  
  // Logarithmic scale for better differentiation
  const normalizedValue = Math.log(value + 1) / Math.log(maxValue + 1);
  
  // Opacity: 0.3 to 0.9 range
  const opacity = 0.3 + (normalizedValue * 0.6);
  
  // Line width: 1 to 6 pixel range  
  const lineWidth = 1 + (normalizedValue * 5);
  
  return { opacity, lineWidth };
}