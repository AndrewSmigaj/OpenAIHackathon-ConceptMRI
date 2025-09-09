import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import type { SankeyNode, SankeyLink } from '../../types/api';
import { getNodeColor, getTrafficVisualProperties, type ColorAxis } from '../../utils/colorBlending';

interface SankeyChartProps {
  nodes: SankeyNode[];
  links: SankeyLink[];
  primaryAxis: ColorAxis;
  secondaryAxis?: ColorAxis;
  onNodeClick?: (nodeId: string, nodeData: SankeyNode) => void;
  onLinkClick?: (linkData: SankeyLink) => void;
  height?: number;
  width?: number;
}

const SankeyChart: React.FC<SankeyChartProps> = ({
  nodes,
  links,
  primaryAxis,
  secondaryAxis,
  onNodeClick,
  onLinkClick,
  height = 600,
  width = 800
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
        const node = nodesRef.current.find(n => n.id === params.data.id);
        if (node) {
          onNodeClickRef.current(params.data.id, node);
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

    // Handle resize
    const handleResize = () => {
      chartInstance.current?.resize();
    };
    window.addEventListener('resize', handleResize);

    return () => {
      chartInstance.current?.off('click', handleClick);
      window.removeEventListener('resize', handleResize);
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

    // Prepare node data with colors
    const sankeyNodes = nodes.map(node => ({
      id: node.id,
      name: node.name,
      value: node.token_count,
      itemStyle: {
        color: getNodeColor(node.category_distribution, primaryAxis, secondaryAxis)
      },
      // Store original data for tooltips
      originalData: node
    }));

    // Find max value for traffic-based scaling
    const maxLinkValue = Math.max(...links.map(l => l.value));
    
    // Prepare link data with colors and traffic-based styling
    const sankeyLinks = links.map(link => {
      // Use the route's own category distribution for coloring instead of source node
      const linkColor = link.category_distribution && Object.keys(link.category_distribution).length > 0 ?
        getNodeColor(link.category_distribution, primaryAxis, secondaryAxis) : '#5470c6';
      
      // Get traffic-based visual properties
      const { opacity, lineWidth } = getTrafficVisualProperties(link.value, maxLinkValue);
      
      return {
        source: link.source,
        target: link.target,
        value: link.value,
        lineStyle: {
          color: linkColor,
          opacity: opacity,
          width: lineWidth,
          curveness: 0.3
        },
        // Store original data for tooltips
        originalData: link
      };
    });

    const option: echarts.EChartsOption = {
      tooltip: {
        trigger: 'item',
        formatter: function(params: any) {
          if (params.dataType === 'node') {
            const node = params.data.originalData as SankeyNode;
            return `
              <div style="max-width: 300px;">
                <strong>${node.name}</strong><br/>
                <hr style="margin: 4px 0;"/>
                Expert: ${node.expert_id}<br/>
                Layer: ${node.layer}<br/>
                Token Count: ${node.token_count}<br/>
                Categories: ${node.categories.join(', ')}
              </div>
            `;
          } else if (params.dataType === 'edge') {
            const link = params.data.originalData as SankeyLink;
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
        layout: 'none',
        emphasis: {
          focus: 'adjacency',
          label: {
            fontWeight: 'bold'
          }
        },
        data: sankeyNodes,
        links: sankeyLinks,
        nodeAlign: 'justify',
        nodeGap: 12,
        nodeWidth: 24,
        layoutIterations: 32,
        left: '8%',
        right: '12%',
        top: '8%',
        bottom: '8%',
        label: {
          show: true,
          position: 'right',
          fontSize: 11,
          color: '#333'
        }
      }],
      animation: true,
      animationDuration: 1000
    };

    chartInstance.current.setOption(option);
  }, [nodes, links, primaryAxis, secondaryAxis]);

  return (
    <div 
      ref={chartRef} 
      style={{ width: `${width}px`, height: `${height}px` }}
      className="sankey-chart border border-gray-200 rounded-lg bg-white"
    />
  );
};

export default SankeyChart;