import { useEffect, useRef, useState, useCallback, type FC } from "react";
import { aiKGGraph, aiKGStats, type KGGraphNode, type KGGraphEdge } from "@/api/client";

// ── Force simulation types ─────────────────────────────────────────────────

interface SimNode {
  id: string;
  label: string;
  type: string;
  description: string;
  degree: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  color: string;
  pinned: boolean;
}

interface SimEdge {
  source: SimNode;
  target: SimNode;
  label: string;
  weight: number;
}

// ── Color palette ──────────────────────────────────────────────────────────

const PALETTE = [
  "#7c3aed", "#2563eb", "#059669", "#d97706", "#dc2626",
  "#db2777", "#0891b2", "#65a30d", "#ea580c", "#6366f1",
  "#14b8a6", "#f59e0b", "#ef4444", "#8b5cf6", "#0d9488",
];

const typeColorMap = new Map<string, string>();
let nextColor = 0;

function getColor(type: string): string {
  if (!typeColorMap.has(type)) {
    typeColorMap.set(type, PALETTE[nextColor % PALETTE.length]);
    nextColor++;
  }
  return typeColorMap.get(type)!;
}

// ── Component ──────────────────────────────────────────────────────────────

const KnowledgeGraph: FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState({ nodes: 0, edges: 0, entities: 0, relations: 0 });
  const [hoveredNode, setHoveredNode] = useState<SimNode | null>(null);
  const [selectedNode, setSelectedNode] = useState<SimNode | null>(null);
  const [types, setTypes] = useState<string[]>([]);

  // Mutable simulation state (refs to avoid re-renders during animation)
  const nodesRef = useRef<SimNode[]>([]);
  const edgesRef = useRef<SimEdge[]>([]);
  const transform = useRef({ x: 0, y: 0, scale: 1 });
  const drag = useRef<{
    node: SimNode | null;
    startX: number;
    startY: number;
    isPan: boolean;
  }>({ node: null, startX: 0, startY: 0, isPan: false });
  const panStart = useRef({ x: 0, y: 0, tx: 0, ty: 0 });
  const animFrame = useRef(0);
  const alpha = useRef(1);
  const hoveredRef = useRef<SimNode | null>(null);
  const selectedRef = useRef<SimNode | null>(null);

  // ── Load graph data ────────────────────────────────────────────────────

  const loadGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [graphData, kgStats] = await Promise.all([
        aiKGGraph(300),
        aiKGStats().catch(() => ({ entities: 0, relations: 0 })),
      ]);

      if (graphData.nodes.length === 0) {
        setError("Knowledge graph is empty. Ingest some notes first.");
        setLoading(false);
        return;
      }

      // Build node map
      const nodeMap = new Map<string, SimNode>();
      const cx = (containerRef.current?.clientWidth ?? 800) / 2;
      const cy = (containerRef.current?.clientHeight ?? 600) / 2;
      const spread = Math.min(cx, cy) * 0.8;

      graphData.nodes.forEach((n: KGGraphNode, i: number) => {
        const angle = (2 * Math.PI * i) / graphData.nodes.length;
        const r = spread * (0.3 + Math.random() * 0.7);
        const simNode: SimNode = {
          id: n.id,
          label: n.label,
          type: n.type,
          description: n.description,
          degree: n.degree,
          x: cx + Math.cos(angle) * r,
          y: cy + Math.sin(angle) * r,
          vx: 0,
          vy: 0,
          radius: Math.max(4, Math.min(20, 4 + n.degree * 1.5)),
          color: getColor(n.type),
          pinned: false,
        };
        nodeMap.set(n.id, simNode);
      });

      const simEdges: SimEdge[] = [];
      graphData.edges.forEach((e: KGGraphEdge) => {
        const src = nodeMap.get(e.source);
        const tgt = nodeMap.get(e.target);
        if (src && tgt) {
          simEdges.push({ source: src, target: tgt, label: e.label, weight: e.weight });
        }
      });

      nodesRef.current = Array.from(nodeMap.values());
      edgesRef.current = simEdges;
      alpha.current = 1;
      transform.current = { x: 0, y: 0, scale: 1 };

      const typeSet = new Set(graphData.nodes.map((n) => n.type));
      setTypes(Array.from(typeSet).sort());
      setStats({
        nodes: graphData.nodes.length,
        edges: graphData.edges.length,
        entities: kgStats.entities,
        relations: kgStats.relations,
      });
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load graph");
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  // ── Force simulation + render loop ─────────────────────────────────────

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || loading) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let running = true;

    function resize() {
      if (!canvas || !containerRef.current) return;
      const dpr = window.devicePixelRatio || 1;
      const w = containerRef.current.clientWidth;
      const h = containerRef.current.clientHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();
    const resizeObs = new ResizeObserver(resize);
    if (containerRef.current) resizeObs.observe(containerRef.current);

    function tick() {
      if (!running || !ctx || !canvas) return;
      const nodes = nodesRef.current;
      const edges = edgesRef.current;
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      const cx = w / 2;
      const cy = h / 2;

      // ── Force simulation step ──
      if (alpha.current > 0.001) {
        const a = alpha.current;

        // Repulsion (Coulomb)
        for (let i = 0; i < nodes.length; i++) {
          for (let j = i + 1; j < nodes.length; j++) {
            const ni = nodes[i];
            const nj = nodes[j];
            let dx = ni.x - nj.x;
            let dy = ni.y - nj.y;
            let d2 = dx * dx + dy * dy;
            if (d2 < 1) d2 = 1;
            const d = Math.sqrt(d2);
            const force = (800 * a) / d2;
            const fx = (dx / d) * force;
            const fy = (dy / d) * force;
            if (!ni.pinned) { ni.vx += fx; ni.vy += fy; }
            if (!nj.pinned) { nj.vx -= fx; nj.vy -= fy; }
          }
        }

        // Attraction (spring along edges)
        for (const edge of edges) {
          const { source: s, target: t } = edge;
          let dx = t.x - s.x;
          let dy = t.y - s.y;
          const d = Math.sqrt(dx * dx + dy * dy) || 1;
          const restLen = 80;
          const force = ((d - restLen) * 0.03 * a);
          const fx = (dx / d) * force;
          const fy = (dy / d) * force;
          if (!s.pinned) { s.vx += fx; s.vy += fy; }
          if (!t.pinned) { t.vx -= fx; t.vy -= fy; }
        }

        // Centering
        for (const n of nodes) {
          if (n.pinned) continue;
          n.vx += (cx - n.x) * 0.0005 * a;
          n.vy += (cy - n.y) * 0.0005 * a;
        }

        // Velocity integration + damping
        for (const n of nodes) {
          if (n.pinned) continue;
          n.vx *= 0.6;
          n.vy *= 0.6;
          n.x += n.vx;
          n.y += n.vy;
        }

        alpha.current *= 0.995;
      }

      // ── Render ──
      const t = transform.current;
      ctx.clearRect(0, 0, w, h);
      ctx.save();
      ctx.translate(t.x, t.y);
      ctx.scale(t.scale, t.scale);

      const hovered = hoveredRef.current;
      const selected = selectedRef.current;
      const highlightSet = new Set<string>();
      const activeNode = selected || hovered;
      if (activeNode) {
        highlightSet.add(activeNode.id);
        for (const e of edges) {
          if (e.source.id === activeNode.id) highlightSet.add(e.target.id);
          if (e.target.id === activeNode.id) highlightSet.add(e.source.id);
        }
      }

      // Edges
      for (const edge of edges) {
        const isHighlighted = activeNode &&
          (edge.source.id === activeNode.id || edge.target.id === activeNode.id);
        ctx.beginPath();
        ctx.moveTo(edge.source.x, edge.source.y);
        ctx.lineTo(edge.target.x, edge.target.y);
        ctx.strokeStyle = isHighlighted
          ? "rgba(124, 58, 237, 0.6)"
          : activeNode
            ? "rgba(100, 116, 139, 0.08)"
            : "rgba(100, 116, 139, 0.2)";
        ctx.lineWidth = isHighlighted ? 1.5 : 0.5;
        ctx.stroke();

        // Edge label on hover
        if (isHighlighted && edge.label && t.scale > 0.5) {
          const mx = (edge.source.x + edge.target.x) / 2;
          const my = (edge.source.y + edge.target.y) / 2;
          ctx.font = "9px sans-serif";
          ctx.fillStyle = "rgba(148, 163, 184, 0.9)";
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          const labelText = edge.label.length > 30
            ? edge.label.slice(0, 30) + "..."
            : edge.label;
          ctx.fillText(labelText, mx, my);
        }
      }

      // Nodes
      for (const node of nodes) {
        const isActive = activeNode?.id === node.id;
        const isNeighbor = highlightSet.has(node.id);
        const dimmed = activeNode && !isNeighbor;

        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, 2 * Math.PI);
        ctx.fillStyle = dimmed
          ? `${node.color}22`
          : isActive
            ? node.color
            : `${node.color}cc`;
        ctx.fill();

        if (isActive) {
          ctx.strokeStyle = "#fff";
          ctx.lineWidth = 2;
          ctx.stroke();
        }

        // Labels
        if (t.scale > 0.4 && (isNeighbor || !activeNode || node.degree > 3)) {
          const label = node.label.length > 24
            ? node.label.slice(0, 24) + "..."
            : node.label;
          const fontSize = Math.max(8, Math.min(12, 8 + node.degree * 0.5));
          ctx.font = `${isActive ? "bold " : ""}${fontSize}px sans-serif`;
          ctx.fillStyle = dimmed
            ? "rgba(148, 163, 184, 0.2)"
            : isActive
              ? "#f1f5f9"
              : "rgba(203, 213, 225, 0.85)";
          ctx.textAlign = "center";
          ctx.textBaseline = "top";
          ctx.fillText(label, node.x, node.y + node.radius + 3);
        }
      }

      ctx.restore();
      animFrame.current = requestAnimationFrame(tick);
    }

    animFrame.current = requestAnimationFrame(tick);

    return () => {
      running = false;
      cancelAnimationFrame(animFrame.current);
      resizeObs.disconnect();
    };
  }, [loading]);

  // ── Mouse interaction ──────────────────────────────────────────────────

  const screenToWorld = useCallback((sx: number, sy: number) => {
    const t = transform.current;
    return {
      x: (sx - t.x) / t.scale,
      y: (sy - t.y) / t.scale,
    };
  }, []);

  const findNodeAt = useCallback((wx: number, wy: number): SimNode | null => {
    const nodes = nodesRef.current;
    for (let i = nodes.length - 1; i >= 0; i--) {
      const n = nodes[i];
      const dx = wx - n.x;
      const dy = wy - n.y;
      if (dx * dx + dy * dy <= (n.radius + 4) * (n.radius + 4)) {
        return n;
      }
    }
    return null;
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const sx = e.clientX - rect.left;
    const sy = e.clientY - rect.top;
    const { x: wx, y: wy } = screenToWorld(sx, sy);
    const node = findNodeAt(wx, wy);

    if (node) {
      drag.current = { node, startX: wx, startY: wy, isPan: false };
      node.pinned = true;
      alpha.current = Math.max(alpha.current, 0.3);
    } else {
      drag.current = { node: null, startX: sx, startY: sy, isPan: true };
      panStart.current = {
        x: sx, y: sy,
        tx: transform.current.x,
        ty: transform.current.y,
      };
    }
  }, [screenToWorld, findNodeAt]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const sx = e.clientX - rect.left;
    const sy = e.clientY - rect.top;

    if (drag.current.isPan) {
      transform.current.x = panStart.current.tx + (sx - panStart.current.x);
      transform.current.y = panStart.current.ty + (sy - panStart.current.y);
      return;
    }

    if (drag.current.node) {
      const { x: wx, y: wy } = screenToWorld(sx, sy);
      drag.current.node.x = wx;
      drag.current.node.y = wy;
      drag.current.node.vx = 0;
      drag.current.node.vy = 0;
      alpha.current = Math.max(alpha.current, 0.1);
      return;
    }

    // Hover detection
    const { x: wx, y: wy } = screenToWorld(sx, sy);
    const node = findNodeAt(wx, wy);
    hoveredRef.current = node;
    if (node !== hoveredNode) setHoveredNode(node);
    if (canvasRef.current) {
      canvasRef.current.style.cursor = node ? "grab" : "default";
    }
  }, [screenToWorld, findNodeAt, hoveredNode]);

  const handleMouseUp = useCallback(() => {
    if (drag.current.node) {
      drag.current.node.pinned = false;
    }
    drag.current = { node: null, startX: 0, startY: 0, isPan: false };
  }, []);

  const handleClick = useCallback((e: React.MouseEvent) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const sx = e.clientX - rect.left;
    const sy = e.clientY - rect.top;
    const { x: wx, y: wy } = screenToWorld(sx, sy);
    const node = findNodeAt(wx, wy);
    selectedRef.current = node;
    setSelectedNode(node);
  }, [screenToWorld, findNodeAt]);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const sx = e.clientX - rect.left;
    const sy = e.clientY - rect.top;
    const t = transform.current;
    const zoom = e.deltaY < 0 ? 1.1 : 0.9;
    const newScale = Math.max(0.1, Math.min(5, t.scale * zoom));
    const ratio = newScale / t.scale;
    t.x = sx - (sx - t.x) * ratio;
    t.y = sy - (sy - t.y) * ratio;
    t.scale = newScale;
  }, []);

  // ── Render ─────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-vault-muted text-sm">
        <svg className="animate-spin h-4 w-4 mr-2" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" opacity="0.25" />
          <path d="M12 2a10 10 0 019.95 9" opacity="0.75" />
        </svg>
        Loading knowledge graph...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3 text-vault-muted text-sm p-6">
        <svg className="w-10 h-10 text-vault-muted/40" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3">
          <circle cx="4" cy="4" r="1.5" />
          <circle cx="12" cy="4" r="1.5" />
          <circle cx="8" cy="12" r="1.5" />
          <path d="M5.3 5.2L7 10.5M10.7 5.2L9 10.5M5.5 4h5" />
        </svg>
        <p>{error}</p>
        <button
          onClick={loadGraph}
          className="px-3 py-1.5 rounded-md text-xs font-medium bg-vault-accent-subtle text-vault-accent hover:bg-vault-accent/20 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-vault-border/30">
        <div className="flex items-center gap-3 text-xs text-vault-muted">
          <span>{stats.nodes} nodes</span>
          <span className="text-vault-border">&middot;</span>
          <span>{stats.edges} edges</span>
          {stats.entities > stats.nodes && (
            <>
              <span className="text-vault-border">&middot;</span>
              <span className="text-vault-text-secondary">{stats.entities} total entities</span>
            </>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => { transform.current = { x: 0, y: 0, scale: 1 }; }}
            className="px-2 py-1 rounded text-[10px] font-medium text-vault-muted hover:text-vault-text hover:bg-vault-surface-hover transition-colors"
            title="Reset zoom"
          >
            Reset View
          </button>
          <button
            onClick={() => { alpha.current = 1; }}
            className="px-2 py-1 rounded text-[10px] font-medium text-vault-muted hover:text-vault-text hover:bg-vault-surface-hover transition-colors"
            title="Re-run layout"
          >
            Re-layout
          </button>
          <button
            onClick={loadGraph}
            className="px-2 py-1 rounded text-[10px] font-medium text-vault-muted hover:text-vault-text hover:bg-vault-surface-hover transition-colors"
            title="Reload data"
          >
            Reload
          </button>
        </div>
      </div>

      {/* Canvas + overlay */}
      <div ref={containerRef} className="flex-1 relative min-h-0 bg-vault-bg">
        <canvas
          ref={canvasRef}
          className="absolute inset-0"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onClick={handleClick}
          onWheel={handleWheel}
        />

        {/* Legend */}
        {types.length > 0 && (
          <div className="absolute top-3 left-3 bg-vault-surface/90 backdrop-blur-sm border border-vault-border/50 rounded-lg px-3 py-2 max-w-[180px]">
            <p className="text-[10px] font-semibold text-vault-muted uppercase tracking-wider mb-1.5">Entity Types</p>
            <div className="space-y-1">
              {types.slice(0, 12).map((t) => (
                <div key={t} className="flex items-center gap-2">
                  <span
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: getColor(t) }}
                  />
                  <span className="text-[10px] text-vault-text-secondary truncate">{t}</span>
                </div>
              ))}
              {types.length > 12 && (
                <p className="text-[9px] text-vault-muted">+{types.length - 12} more</p>
              )}
            </div>
          </div>
        )}

        {/* Node detail panel */}
        {(selectedNode || hoveredNode) && (
          <div className="absolute bottom-3 left-3 right-3 max-w-sm bg-vault-surface/95 backdrop-blur-sm border border-vault-border/50 rounded-lg px-4 py-3">
            <div className="flex items-center gap-2 mb-1">
              <span
                className="w-3 h-3 rounded-full shrink-0"
                style={{ backgroundColor: (selectedNode || hoveredNode)!.color }}
              />
              <span className="text-sm font-medium text-vault-text truncate">
                {(selectedNode || hoveredNode)!.label}
              </span>
              <span className="text-[10px] text-vault-muted ml-auto">
                {(selectedNode || hoveredNode)!.type}
              </span>
            </div>
            {(selectedNode || hoveredNode)!.description && (
              <p className="text-xs text-vault-text-secondary line-clamp-2 mt-1">
                {(selectedNode || hoveredNode)!.description}
              </p>
            )}
            <p className="text-[10px] text-vault-muted mt-1">
              {(selectedNode || hoveredNode)!.degree} connections
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default KnowledgeGraph;
