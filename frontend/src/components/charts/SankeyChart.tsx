import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import type { SankeyNode, SankeyLink } from '../../types/api';
import { getNodeColor, getAxisColor, rgbToHex, getTrafficVisualProperties, type GradientScheme } from '../../utils/colorBlending';

interface SankeyChartProps {
  nodes: SankeyNode[];
  links: SankeyLink[];
  primaryValues: string[];
  gradient?: GradientScheme;
  secondaryValues?: string[];
  secondaryGradient?: GradientScheme;
  secondaryAxisId?: string;
  outputPrimaryValues?: string[];
  outputGradient?: GradientScheme;
  outputSecondaryValues?: string[];
  outputSecondaryGradient?: GradientScheme;
  outputSecondaryAxisId?: string;
  outputColorAxisId?: string;
  onNodeClick?: (nodeId: string, nodeData: SankeyNode) => void;
  onLinkClick?: (linkData: SankeyLink) => void;
  height?: number;
  width?: number;
  nodeWidth?: number;
}

const SankeyChart: React.FC<SankeyChartProps> = ({
  nodes,
  links,
  primaryValues,
  gradient = 'red-blue',
  secondaryValues,
  secondaryGradient = 'yellow-cyan',
  secondaryAxisId,
  outputPrimaryValues,
  outputGradient = 'purple-green',
  outputSecondaryValues,
  outputSecondaryGradient = 'yellow-cyan',
  outputSecondaryAxisId,
  outputColorAxisId,
  onNodeClick,
  onLinkClick,
  height = 600,
  width = 800,
  nodeWidth: nodeWidthProp = 6
}) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  const nodesRef = useRef(nodes);
  const linksRef = useRef(links);
  const onNodeClickRef = useRef(onNodeClick);
  const onLinkClickRef = useRef(onLinkClick);

  // Update refs when props change
  nodesRef.current = nodes;
  linksRef.current = links;
  onNodeClickRef.current = onNodeClick;
  onLinkClickRef.current = onLinkClick;

  useEffect(() => {
    if (!chartRef.current) return;

    // Initialize chart
    chartInstance.current = echarts.init(chartRef.current);

    // Handle click events
    const handleClick = (params: any) => {
      if (params.dataType === 'node' && onNodeClickRef.current) {
        // Match by name — ECharts Sankey uses name as the node key
        const nodeName = params.data.name || params.data.id;
        const node = nodesRef.current.find(n => n.name === nodeName || n.id === nodeName);
        if (node) {
          onNodeClickRef.current(node.id, node);
        }
      } else if (params.dataType === 'edge' && onLinkClickRef.current) {
        const link = linksRef.current.find(l =>
          l.source === params.data.source && l.target === params.data.target
        );
        if (link) {
          onLinkClickRef.current(link);
        }
      }
    };

    chartInstance.current.on('click', handleClick);

    // Handle resize — observe container, not just window
    const handleResize = () => {
      chartInstance.current?.resize();
    };
    window.addEventListener('resize', handleResize);

    const resizeObserver = new ResizeObserver(() => {
      chartInstance.current?.resize();
    });
    resizeObserver.observe(chartRef.current);

    return () => {
      chartInstance.current?.off('click', handleClick);
      window.removeEventListener('resize', handleResize);
      resizeObserver.disconnect();
      chartInstance.current?.dispose();
    };
  }, []);

  // Resize chart when container dimensions might change
  useEffect(() => {
    const resizeChart = () => {
      if (chartInstance.current) {
        setTimeout(() => {
          chartInstance.current?.resize();
        }, 100);
      }
    };

    resizeChart();
  }, [width, height]);

  // Update chart when data or colors change
  useEffect(() => {
    if (!chartInstance.current) return;

    // Get the distribution for a given axis from a node/link
    const getDistForAxis = (item: { label_distribution?: Record<string, number> | null; target_word_distribution?: Record<string, number> | null; category_distributions?: Record<string, Record<string, number>> | null }, axisId?: string) => {
      if (!axisId) return undefined;
      if (axisId === 'label') return item.label_distribution;
      if (axisId === 'target_word') return item.target_word_distribution;
      return item.category_distributions?.[axisId];
    };

    // Compute depth offset for proper column placement
    const minLayer = nodes.length > 0 ? Math.min(...nodes.map(n => n.layer)) : 0;

    // Build extended values list that includes output categories for "match input" fallback
    const outputCategories = nodes
      .filter(n => n.name.startsWith('Generated:'))
      .map(n => n.name.replace('Generated:', ''));
    const extendedPrimaryValues = [...primaryValues];
    for (const cat of outputCategories) {
      if (!extendedPrimaryValues.includes(cat)) {
        extendedPrimaryValues.push(cat);
      }
    }

    // Prepare node data with colors
    const sankeyNodes = nodes.map(node => {
      const isOutputNode = node.name.startsWith('Generated:');

      let nodeColor: string;
      if (isOutputNode) {
        // Output nodes: use output color axis if configured, otherwise match input colors
        const outputAxisDist = outputColorAxisId ? getDistForAxis(node, outputColorAxisId) : null;
        if (outputAxisDist && Object.keys(outputAxisDist).length > 0 && outputPrimaryValues && outputPrimaryValues.length > 0) {
          const outputSecDist = outputSecondaryAxisId ? getDistForAxis(node, outputSecondaryAxisId) : undefined;
          nodeColor = getNodeColor(outputAxisDist, outputPrimaryValues, outputGradient, outputSecDist, outputSecondaryValues, outputSecondaryGradient);
        } else {
          // Fallback: match category name against input colors (extended to include output-only categories)
          const category = node.name.replace('Generated:', '');
          nodeColor = rgbToHex(getAxisColor(category, extendedPrimaryValues, gradient));
        }
      } else {
        // Regular nodes: primary = label_distribution, secondary from axis
        const primaryDist = node.label_distribution || {};
        const secondaryDist = getDistForAxis(node, secondaryAxisId);
        nodeColor = getNodeColor(primaryDist, primaryValues, gradient, secondaryDist, secondaryValues, secondaryGradient);
      }

      return {
        id: node.id,
        name: node.name,
        value: Math.max(1, node.token_count),
        depth: node.layer - minLayer,
        itemStyle: {
          color: nodeColor
        }
      };
    });

    // Find max value for traffic-based scaling
    const maxLinkValue = Math.max(...links.map(l => l.value));

    // Prepare link data with colors and traffic-based styling
    const sankeyLinks = links.map(link => {
      const primaryDist = link.label_distribution || {};
      const secondaryDist = getDistForAxis(link, secondaryAxisId);
      const isOutputLink = link.target.startsWith('Generated:');

      let linkColor: string;
      if (isOutputLink && outputColorAxisId && outputPrimaryValues && outputPrimaryValues.length > 0) {
        const outDist = getDistForAxis(link, outputColorAxisId);
        if (outDist && Object.keys(outDist).length > 0) {
          const outSecDist = outputSecondaryAxisId ? getDistForAxis(link, outputSecondaryAxisId) : undefined;
          linkColor = getNodeColor(outDist, outputPrimaryValues, outputGradient, outSecDist, outputSecondaryValues, outputSecondaryGradient);
        } else {
          linkColor = Object.keys(primaryDist).length > 0
            ? getNodeColor(primaryDist, primaryValues, gradient, secondaryDist, secondaryValues, secondaryGradient)
            : '#5470c6';
        }
      } else {
        linkColor = Object.keys(primaryDist).length > 0
          ? getNodeColor(primaryDist, primaryValues, gradient, secondaryDist, secondaryValues, secondaryGradient)
          : '#5470c6';
      }

      // Get traffic-based visual properties
      const { opacity, lineWidth } = getTrafficVisualProperties(link.value, maxLinkValue);

      return {
        source: link.source,
        target: link.target,
        value: Math.max(0.5, link.value),
        lineStyle: {
          color: linkColor,
          opacity: opacity,
          width: lineWidth,
          curveness: 0.3
        },
      };
    });

    const option: echarts.EChartsOption = {
      tooltip: {
        trigger: 'item',
        formatter: function(params: any) {
          if (params.dataType === 'node') {
            const node = nodes.find(n => n.name === params.data.name);
            if (!node) return '';

            // Output node tooltip
            if (node.name.startsWith('Generated:')) {
              const category = node.name.replace('Generated:', '');
              return `
                <div style="max-width: 300px;">
                  <strong>Generated: ${category}</strong><br/>
                  <hr style="margin: 4px 0;"/>
                  Probes: ${node.token_count}<br/>
                  Labels: ${node.label_distribution ? Object.entries(node.label_distribution).map(([k, v]) => `${k}: ${v}`).join(', ') : 'N/A'}
                  ${node.category_distributions ? '<br/>Categories: ' + Object.entries(node.category_distributions).map(([axis, dist]) => `${axis}: ${Object.entries(dist).map(([k, v]) => `${k}(${v})`).join(', ')}`).join('; ') : ''}
                </div>
              `;
            }

            return `
              <div style="max-width: 300px;">
                <strong>${node.name}</strong><br/>
                <hr style="margin: 4px 0;"/>
                Expert: ${node.expert_id}<br/>
                Layer: ${node.layer}<br/>
                Token Count: ${node.token_count}<br/>
                Labels: ${node.label_distribution ? Object.entries(node.label_distribution).map(([k, v]) => `${k}: ${v}`).join(', ') : 'N/A'}
              </div>
            `;
          } else if (params.dataType === 'edge') {
            const link = links.find(l => l.source === params.data.source && l.target === params.data.target);
            if (!link) return '';
            return `
              <div style="max-width: 300px;">
                <strong>Route</strong><br/>
                <hr style="margin: 4px 0;"/>
                ${link.source} → ${link.target}<br/>
                Flow: ${link.value} tokens<br/>
                Route: ${link.route_signature}
              </div>
            `;
          }
          return '';
        }
      },
      series: [{
        type: 'sankey',
        emphasis: {
          focus: 'adjacency',
          label: {
            fontWeight: 'bold'
          }
        },
        data: sankeyNodes,
        links: sankeyLinks,
        nodeAlign: 'justify',
        nodeGap: 8,
        nodeWidth: nodeWidthProp,
        layoutIterations: 32,
        left: '2%',
        right: '15%',
        top: '2%',
        bottom: '2%',
        label: {
          show: true,
          position: 'right',
          fontSize: 7,
          color: '#555'
        }
      }],
      animation: true,
      animationDuration: 1000
    };

    chartInstance.current.setOption(option);
  }, [nodes, links, primaryValues, gradient, secondaryValues, secondaryGradient, secondaryAxisId, outputPrimaryValues, outputGradient, outputSecondaryValues, outputSecondaryGradient, outputSecondaryAxisId, outputColorAxisId]);

  return (
    <div
      ref={chartRef}
      style={{ width: '100%', height: `${height}px` }}
      className="sankey-chart border border-gray-200 rounded-lg bg-white"
    />
  );
};

export default SankeyChart;
