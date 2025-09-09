/**
 * Color blending utilities for Sankey chart visualization with additive RGB blending
 * Supports 1-2 axis selection with meaningful color combinations
 */

export type ColorAxis = 'sentiment' | 'concreteness' | 'pos';

interface RGBColor {
  r: number;
  g: number;
  b: number;
}

// Base color definitions for each axis - vibrant, high contrast colors
const AXIS_COLORS: Record<ColorAxis, Record<string, RGBColor>> = {
  sentiment: {
    positive: { r: 34, g: 197, b: 94 },    // Vibrant Green
    negative: { r: 239, g: 68, b: 68 },    // Vibrant Red  
    neutral: { r: 99, g: 102, b: 241 }     // Vibrant Blue (not grey!)
  },
  concreteness: {
    concrete: { r: 59, g: 130, b: 246 },   // Strong Blue
    abstract: { r: 245, g: 158, b: 11 }    // Strong Orange
  },
  pos: {
    nouns: { r: 139, g: 69, b: 19 },       // Brown
    verbs: { r: 220, g: 38, b: 127 }       // Magenta
  }
};

// Category mappings for each axis
const AXIS_CATEGORIES: Record<ColorAxis, string[]> = {
  sentiment: ['positive', 'negative', 'neutral'],
  concreteness: ['concrete', 'abstract'],
  pos: ['nouns', 'verbs']
};

/**
 * Calculate axis position based on category distribution
 * Returns value from -1 to +1 representing position on divergent axis
 */
export function calculateAxisPosition(categoryDistribution: Record<string, number>, axis: ColorAxis): number {
  const axisCategories = AXIS_CATEGORIES[axis];
  
  // Get total count for this axis
  let totalCount = 0;
  const counts: Record<string, number> = {};
  
  axisCategories.forEach(cat => {
    counts[cat] = categoryDistribution[cat] || 0;
    totalCount += counts[cat];
  });
  
  if (totalCount === 0) {
    return 0; // Neutral/middle position
  }
  
  switch (axis) {
    case 'sentiment':
      // Positive-Negative axis with neutral as middle
      const posRatio = counts['positive'] / totalCount;
      const negRatio = counts['negative'] / totalCount;
      
      // Position: -1 (fully negative) through 0 (neutral) to +1 (fully positive)
      return posRatio - negRatio;
      
    case 'concreteness':
      // Binary axis: concrete vs abstract
      const concreteRatio = counts['concrete'] / totalCount;
      const abstractRatio = counts['abstract'] / totalCount;
      
      // Position: -1 (fully abstract) to +1 (fully concrete)
      return concreteRatio - abstractRatio;
      
    case 'pos':
      // Binary axis: nouns vs verbs
      const nounRatio = counts['nouns'] / totalCount;
      const verbRatio = counts['verbs'] / totalCount;
      
      // Position: -1 (fully nouns) to +1 (fully verbs)
      return verbRatio - nounRatio;
      
    default:
      return 0;
  }
}

/**
 * Get color for axis position using divergent gradient
 */
export function getDivergentAxisColor(position: number, axis: ColorAxis): RGBColor {
  // Clamp position to [-1, 1]
  position = Math.max(-1, Math.min(1, position));
  
  const axisColors = AXIS_COLORS[axis];
  
  switch (axis) {
    case 'sentiment':
      if (Math.abs(position) < 0.05) {
        // Very close to neutral
        return axisColors.neutral;
      } else if (position > 0) {
        // Interpolate from neutral to positive
        const t = position;
        return blendColors(axisColors.neutral, axisColors.positive, 1 - t, t);
      } else {
        // Interpolate from neutral to negative  
        const t = Math.abs(position);
        return blendColors(axisColors.neutral, axisColors.negative, 1 - t, t);
      }
      
    case 'concreteness':
      const t = (position + 1) / 2; // Map [-1,1] to [0,1]
      return blendColors(axisColors.abstract, axisColors.concrete, 1 - t, t);
      
    case 'pos':
      const tPos = (position + 1) / 2; // Map [-1,1] to [0,1]  
      return blendColors(axisColors.nouns, axisColors.verbs, 1 - tPos, tPos);
      
    default:
      return { r: 99, g: 102, b: 241 }; // Fallback
  }
}

/**
 * Get the RGB color for a single axis using category distribution
 */
export function getAxisColor(categoryDistribution: Record<string, number>, axis: ColorAxis): RGBColor {
  const position = calculateAxisPosition(categoryDistribution, axis);
  return getDivergentAxisColor(position, axis);
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
 * Get the final blended color for a node based on selected axes and category distribution
 */
export function getNodeColor(
  categoryDistribution: Record<string, number>,
  primaryAxis: ColorAxis, 
  secondaryAxis?: ColorAxis
): string {
  if (!secondaryAxis) {
    // Single axis - return gradient color based on distribution
    const color = getAxisColor(categoryDistribution, primaryAxis);
    return rgbToHex(color);
  }
  
  // Dual axis - blend gradient colors from both axes
  const color1 = getAxisColor(categoryDistribution, primaryAxis);
  const color2 = getAxisColor(categoryDistribution, secondaryAxis);
  
  // Blend with primary axis weighted more heavily
  const blendedColor = blendColors(color1, color2, 0.6, 0.4);
  return rgbToHex(blendedColor);
}

/**
 * Get a preview showing gradient extremes and key points for the selected axis combination
 */
export function getColorPreview(primaryAxis: ColorAxis, secondaryAxis?: ColorAxis): Record<string, string> {
  const preview: Record<string, string> = {};
  
  if (!secondaryAxis) {
    // Single axis preview - show gradient extremes and middle
    switch (primaryAxis) {
      case 'sentiment':
        preview['Very Negative'] = rgbToHex(getDivergentAxisColor(-1, primaryAxis));
        preview['Neutral'] = rgbToHex(getDivergentAxisColor(0, primaryAxis));
        preview['Very Positive'] = rgbToHex(getDivergentAxisColor(1, primaryAxis));
        break;
      case 'concreteness':
        preview['Very Abstract'] = rgbToHex(getDivergentAxisColor(-1, primaryAxis));
        preview['Mixed'] = rgbToHex(getDivergentAxisColor(0, primaryAxis));
        preview['Very Concrete'] = rgbToHex(getDivergentAxisColor(1, primaryAxis));
        break;
      case 'pos':
        preview['All Nouns'] = rgbToHex(getDivergentAxisColor(-1, primaryAxis));
        preview['Mixed'] = rgbToHex(getDivergentAxisColor(0, primaryAxis));
        preview['All Verbs'] = rgbToHex(getDivergentAxisColor(1, primaryAxis));
        break;
    }
  } else {
    // Dual axis preview - show combinations of extremes
    const getAxisLabel = (axis: ColorAxis, position: number) => {
      switch (axis) {
        case 'sentiment':
          return position === -1 ? 'Neg' : position === 0 ? 'Neu' : 'Pos';
        case 'concreteness':
          return position === -1 ? 'Abs' : position === 0 ? 'Mix' : 'Con';
        case 'pos':
          return position === -1 ? 'N' : position === 0 ? 'Mix' : 'V';
      }
    };
    
    const positions = [-1, 0, 1];
    
    positions.forEach((pos1) => {
      positions.forEach((pos2) => {
        const color1 = getDivergentAxisColor(pos1, primaryAxis);
        const color2 = getDivergentAxisColor(pos2, secondaryAxis);
        const blended = blendColors(color1, color2, 0.6, 0.4);
        const label = `${getAxisLabel(primaryAxis, pos1)}+${getAxisLabel(secondaryAxis, pos2)}`;
        preview[label] = rgbToHex(blended);
      });
    });
  }
  
  return preview;
}

/**
 * Get readable label for axis
 */
export function getAxisLabel(axis: ColorAxis): string {
  switch (axis) {
    case 'sentiment': return 'Sentiment';
    case 'concreteness': return 'Concreteness';
    case 'pos': return 'Part of Speech';
    default: return axis;
  }
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