'use client';

import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

interface NodeData {
  id: string;
  type: 'company' | 'counterparty';
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
}

interface LinkData {
  source: string | NodeData;
  target: string | NodeData;
  value: number;
  confidence?: string;
  signals?: string[];
}

export default function FraudGraph({
  nodes,
  links,
}: {
  nodes: NodeData[];
  links: LinkData[];
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null);

  useEffect(() => {
    if (!svgRef.current || !containerRef.current) return;
    if (!nodes || nodes.length === 0) return;

    const containerWidth = containerRef.current.clientWidth || 560;
    const width = containerWidth;
    const height = Math.max(280, Math.min(360, containerWidth * 0.6));

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    svg.attr('viewBox', `0 0 ${width} ${height}`).attr('width', '100%').attr('height', height);

    // Deep-copy nodes/links so D3 can mutate them
    const simNodes: NodeData[] = nodes.map((n) => ({ ...n }));
    const simLinks: LinkData[] = links.map((l) => ({
      ...l,
      source: typeof l.source === 'string' ? l.source : (l.source as NodeData).id,
      target: typeof l.target === 'string' ? l.target : (l.target as NodeData).id,
    }));

    const simulation = d3
      .forceSimulation<NodeData>(simNodes)
      .force(
        'link',
        d3
          .forceLink<NodeData, LinkData>(simLinks)
          .id((d) => d.id)
          .distance(120)
      )
      .force('charge', d3.forceManyBody().strength(-280))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide(22));

    // Edge colour by confidence
    const edgeColor = (d: LinkData) => {
      if (d.confidence === 'HIGH') return 'rgba(255, 100, 100, 0.7)';
      if (d.confidence === 'MEDIUM') return 'rgba(255, 180, 80, 0.7)';
      return 'rgba(120, 180, 255, 0.5)';
    };

    const linkGroup = svg.append('g');
    const link = linkGroup
      .selectAll('line')
      .data(simLinks)
      .enter()
      .append('line')
      .attr('stroke', edgeColor)
      .attr('stroke-opacity', 0.85)
      .attr('stroke-width', (d) => Math.max(1.5, (d.value || 20) / 20));

    const nodeGroup = svg.append('g');
    const node = nodeGroup
      .selectAll('circle')
      .data(simNodes)
      .enter()
      .append('circle')
      .attr('r', (d) => (d.type === 'company' ? 14 : 10))
      .attr('fill', (d) =>
        d.type === 'company' ? 'var(--ob-text)' : 'rgba(255, 140, 80, 0.85)'
      )
      .attr('stroke', 'var(--ob-bg)')
      .attr('stroke-width', 2)
      .style('cursor', 'grab')
      .on('mouseover', (event, d) => {
        const rect = containerRef.current?.getBoundingClientRect();
        if (!rect) return;
        setTooltip({
          x: event.clientX - rect.left,
          y: event.clientY - rect.top - 36,
          text: d.type === 'company' ? `🏢 ${d.id}` : `⚠️ ${d.id}`,
        });
      })
      .on('mouseout', () => setTooltip(null))
      .call(
        d3
          .drag<SVGCircleElement, NodeData>()
          .on('start', (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on('drag', (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on('end', (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
      );

    const textGroup = svg.append('g');
    const text = textGroup
      .selectAll('text')
      .data(simNodes)
      .enter()
      .append('text')
      .text((d) => (d.id.length > 18 ? d.id.slice(0, 16) + '…' : d.id))
      .attr('font-size', 10)
      .attr('font-family', 'DM Mono, monospace')
      .attr('fill', 'var(--ob-muted)')
      .attr('pointer-events', 'none');

    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => Math.max(14, Math.min(width - 14, d.source.x ?? 0)))
        .attr('y1', (d: any) => Math.max(14, Math.min(height - 14, d.source.y ?? 0)))
        .attr('x2', (d: any) => Math.max(14, Math.min(width - 14, d.target.x ?? 0)))
        .attr('y2', (d: any) => Math.max(14, Math.min(height - 14, d.target.y ?? 0)));

      node
        .attr('cx', (d: any) => Math.max(14, Math.min(width - 14, d.x ?? 0)))
        .attr('cy', (d: any) => Math.max(14, Math.min(height - 14, d.y ?? 0)));

      text
        .attr('x', (d: any) => Math.max(14, Math.min(width - 14, (d.x ?? 0) + 14)))
        .attr('y', (d: any) => Math.max(14, Math.min(height - 14, (d.y ?? 0) + 4)));
    });

    return () => {
      simulation.stop();
    };
  }, [nodes, links]);

  if (!nodes || nodes.length === 0) {
    return (
      <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
        <p className="font-mono text-[9px] font-normal tracking-[0.14em] uppercase text-ob-dim mb-2.5">
          Fraud Fingerprinting Graph
        </p>
        <p className="text-ob-muted text-[13px]">No confirmed fraud network connections detected.</p>
      </div>
    );
  }

  return (
    <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
      <div className="flex items-center justify-between mb-3">
        <p className="font-mono text-[9px] font-normal tracking-[0.14em] uppercase text-ob-dim">
          Fraud Fingerprinting Graph
        </p>
        <div className="flex items-center gap-3 text-[9px] font-mono text-ob-muted">
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-0.5 bg-[rgba(255,100,100,0.7)]" />HIGH
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-0.5 bg-[rgba(255,180,80,0.7)]" />MEDIUM
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-ob-text inline-block" />Company
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-[rgba(255,140,80,0.85)] inline-block" />Entity
          </span>
        </div>
      </div>
      <div ref={containerRef} className="relative rounded-[8px] bg-ob-glass2 overflow-hidden">
        <svg
          ref={svgRef}
          className="w-full block"
          style={{ minHeight: 280 }}
        />
        {tooltip && (
          <div
            className="absolute z-10 pointer-events-none px-2 py-1 bg-ob-surface border border-ob-edge rounded text-[11px] font-mono text-ob-text whitespace-nowrap"
            style={{ left: tooltip.x, top: tooltip.y }}
          >
            {tooltip.text}
          </div>
        )}
      </div>
      <p className="text-[10px] text-ob-muted mt-2">
        {nodes.length} entities · {links.length} confirmed connections · Drag nodes to explore
      </p>
    </div>
  );
}
