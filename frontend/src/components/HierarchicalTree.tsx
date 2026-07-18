import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ExternalLink, X } from "lucide-react";
import * as d3 from "d3";

export interface TreeNode {
  name: string;
  children?: TreeNode[];
  summary?: string;
  tags?: string[];
  contentSnippet?: string;
  type?: "root" | "category" | "asset";
}

interface HierarchicalTreeProps {
  data: TreeNode;
  height?: number;
  width?: number;
  onNodeClick?: (node: TreeNode) => void;
}

const HierarchicalTree: React.FC<HierarchicalTreeProps> = ({ 
  data, 
  height = 400, 
  width = 800,
  onNodeClick
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [selectedNodes, setSelectedNodes] = useState<Set<string>>(new Set());
  const [hoveredNode, setHoveredNode] = useState<{
    data: TreeNode;
    x: number;
    y: number;
  } | null>(null);
  const [selectedSideNode, setSelectedSideNode] = useState<TreeNode | null>(null);

  const isUrl = (str: string) => {
    try {
      new URL(str);
      return true;
    } catch {
      return str.startsWith("http://") || str.startsWith("https://");
    }
  };

  const selectedCount = selectedNodes.size;

  useEffect(() => {
    if (!svgRef.current || !data) return;

    const margin = { top: 60, right: 20, bottom: 60, left: 20 };

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    svg.on("click", () => {
      setSelectedSideNode(null);
    });

    // Create a zoom-able container group
    const zoomableGroup = svg.append("g").attr("class", "zoom-container");

    const zoomBehavior = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.5, 3])
      .on("start", () => {
        svg.style("cursor", "grabbing");
      })
      .on("zoom", (event) => {
        zoomableGroup.attr("transform", event.transform);
      })
      .on("end", () => {
        svg.style("cursor", "grab");
      });

    svg.call(zoomBehavior);
    svg.style("cursor", "grab");

    const g = zoomableGroup
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    const innerHeight = height - margin.top - margin.bottom;
    const treeLayout = d3
      .tree<TreeNode>()
      .size([width - margin.left - margin.right, innerHeight]);
    const root = d3.hierarchy(data);
    treeLayout(root);

    // Links (Reversed Y)
    g.selectAll(".link")
      .data(root.links())
      .join("path")
      .attr(
        "d",
        d3
          .linkVertical<
            d3.HierarchyLink<TreeNode>,
            d3.HierarchyPointNode<TreeNode>
          >()
          .x((d) => d.x!)
          .y((d) => innerHeight - d.y!),
      )
      .attr("fill", "none")
      .attr("stroke", "rgba(255, 122, 26, 0.12)")
      .attr("stroke-width", 2);

    // Nodes (Reversed Y)
    const node = g
      .selectAll(".node")
      .data(root.descendants())
      .join("g")
      .attr("transform", (d) => `translate(${d.x!},${innerHeight - d.y!})`)
      .style("cursor", "pointer")
      .on("click", (event, d) => {
        event.stopPropagation();
        const descendants = d.descendants().map((node) => node.data.name);
        const isCurrentlySelected = selectedNodes.has(d.data.name);

        setSelectedNodes((prev) => {
          const next = new Set(prev);
          if (isCurrentlySelected) {
            descendants.forEach((name) => next.delete(name));
          } else {
            descendants.forEach((name) => next.add(name));
          }
          return next;
        });

        if (onNodeClick) {
          onNodeClick(d.data);
        }
        
        if (d.data.type === "asset") {
          setSelectedSideNode(d.data);
        } else {
          setSelectedSideNode(null);
        }
      })
      .on("mouseenter", (event, d) => {
        // Only show tooltip for categories with assets or asset nodes
        if (d.data.type === "root") return;
        
        d3.select(event.currentTarget)
          .select("circle")
          .transition()
          .duration(200)
          .attr("r", 38);

        // Get relative position for tooltip
        const [mx, my] = d3.pointer(event, containerRef.current);
        setHoveredNode({
          data: d.data,
          x: mx,
          y: my,
        });
      })
      .on("mousemove", (event) => {
        const [mx, my] = d3.pointer(event, containerRef.current);
        setHoveredNode(prev => prev ? { ...prev, x: mx, y: my } : null);
      })
      .on("mouseleave", (event, d) => {
        d3.select(event.currentTarget)
          .select("circle")
          .transition()
          .duration(200)
          .attr("r", 32);
        
        setHoveredNode(null);
      });

    // Node Circle
    node
      .append("circle")
      .attr("r", 32)
      .attr("fill", (d) =>
        selectedNodes.has(d.data.name)
          ? "rgba(74, 222, 128, 0.08)"
          : "rgba(10, 10, 10, 0.8)",
      )
      .attr("stroke", (d) =>
        selectedNodes.has(d.data.name) ? "#4ade80" : "var(--accent)",
      )
      .attr("stroke-width", (d) => (selectedNodes.has(d.data.name) ? 3 : 2))
      .style("transition", "stroke 0.3s ease, fill 0.3s ease")
      .style("filter", (d) =>
        selectedNodes.has(d.data.name)
          ? "drop-shadow(0 0 12px rgba(74, 222, 128, 0.4))"
          : "drop-shadow(0 0 8px rgba(255, 122, 26, 0.15))",
      );

    // Node Label
    node
      .append("text")
      .attr("dy", "0.35em")
      .attr("text-anchor", "middle")
      .text((d) => d.data.name)
      .style("font-size", "10px")
      .style("font-weight", "700")
      .style("letter-spacing", "0.5px")
      .attr("fill", (d) =>
        selectedNodes.has(d.data.name) ? "#4ade80" : "#ffffff",
      )
      .style("pointer-events", "none");

    // Indicator Dot (Inverted placement)
    node
      .append("circle")
      .attr("r", 4)
      .attr("cy", 32)
      .attr("fill", (d) =>
        selectedNodes.has(d.data.name) ? "#4ade80" : "var(--accent)",
      )
      .style("pointer-events", "none");
  }, [data, selectedNodes, height, width]);

  return (
    <div
      ref={containerRef}
      style={{
        width: "100%",
        background: "rgba(0,0,0,0.4)",
        borderRadius: "24px",
        border: "1px solid var(--glass-border)",
        padding: "24px",
        overflow: "hidden",
        marginTop: "16px",
        position: "relative",
      }}
    >
      <svg
        ref={svgRef}
        width="100%"
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="xMidYMid meet"
      />

      <AnimatePresence>
        {hoveredNode && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            style={{
              position: "absolute",
              left: hoveredNode.x + 20,
              top: hoveredNode.y - 20,
              width: "280px",
              pointerEvents: "none",
              zIndex: 100,
              padding: "16px",
              borderRadius: "16px",
              background: "rgba(10, 10, 10, 0.95)",
              backdropFilter: "blur(20px)",
              border: "1px solid var(--glass-border)",
              boxShadow: "0 10px 40px rgba(0,0,0,0.6)",
            }}
          >
            <div style={{ marginBottom: "12px" }}>
              <span style={{ fontSize: "0.6rem", color: "var(--accent)", fontWeight: 800, letterSpacing: "1px" }}>
                {hoveredNode.data.type?.toUpperCase()} NAME
              </span>
              <h4 style={{ color: "white", fontSize: "1rem", marginTop: "2px" }}>{hoveredNode.data.name}</h4>
            </div>

            {hoveredNode.data.summary && (
              <div style={{ marginBottom: "12px" }}>
                <span style={{ fontSize: "0.6rem", color: "var(--accent)", opacity: 0.8, fontWeight: 700 }}>SUMMARY</span>
                <p style={{ color: "var(--text-secondary)", fontSize: "0.8rem", lineHeight: "1.4", marginTop: "4px" }}>
                  {hoveredNode.data.summary}
                </p>
              </div>
            )}

            {hoveredNode.data.tags && hoveredNode.data.tags.length > 0 && (
              <div style={{ marginBottom: "12px" }}>
                <span style={{ fontSize: "0.6rem", color: "var(--accent)", opacity: 0.8, fontWeight: 700 }}>KEYWORDS</span>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "6px" }}>
                  {hoveredNode.data.tags.map((tag, i) => (
                    <span 
                      key={i} 
                      style={{ 
                        fontSize: "0.7rem", 
                        background: "rgba(255, 255, 255, 0.05)", 
                        padding: "2px 8px", 
                        borderRadius: "4px",
                        color: "white" 
                      }}
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {hoveredNode.data.contentSnippet && (
              <div>
                <span style={{ fontSize: "0.6rem", color: "var(--accent)", opacity: 0.8, fontWeight: 700 }}>
                  CONTENT PREVIEW
                </span>
                <p style={{ 
                  color: "var(--text-secondary)", 
                  fontSize: "0.75rem", 
                  lineHeight: "1.4", 
                  marginTop: "4px",
                  display: "-webkit-box",
                  WebkitLineClamp: 3,
                  WebkitBoxOrient: "vertical",
                  overflow: "hidden"
                }}>
                  {hoveredNode.data.contentSnippet}
                </p>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: "12px",
          padding: "0 10px",
        }}
      >
        <div style={{ display: "flex", gap: "16px" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              fontSize: "0.7rem",
              color: "var(--text-secondary)",
            }}
          >
            <div
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                background: "var(--accent)",
              }}
            />{" "}
            Category
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              fontSize: "0.7rem",
              color: "var(--text-secondary)",
            }}
          >
            <div
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                background: "rgba(255, 255, 255, 0.2)",
              }}
            />{" "}
            Asset
          </div>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            fontSize: "0.75rem",
            fontWeight: 700,
            color: selectedCount > 0 ? "#4ade80" : "var(--text-secondary)",
          }}
        >
          SELECTED:{" "}
          <span
            style={{
              background:
                selectedCount > 0
                  ? "rgba(74, 222, 128, 0.1)"
                  : "rgba(255, 255, 255, 0.05)",
              padding: "4px 10px",
              borderRadius: "8px",
            }}
          >
            {selectedCount}
          </span>
        </div>
      </div>

      {/* Internal Side Panel */}
      <AnimatePresence>
        {selectedSideNode && (
          <motion.div
            initial={{ x: "100%", opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: "100%", opacity: 0 }}
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
            style={{
              position: "absolute",
              top: 0,
              right: 0,
              bottom: 0,
              width: "320px",
              background: "rgba(10, 10, 10, 0.98)",
              backdropFilter: "blur(25px)",
              borderLeft: "1px solid var(--glass-border)",
              padding: "30px 24px",
              zIndex: 150,
              display: "flex",
              flexDirection: "column",
              gap: "20px",
              boxShadow: "-10px 0 30px rgba(0,0,0,0.5)",
              overflowY: "auto",
            }}
          >
            <button
              onClick={(e) => {
                e.stopPropagation();
                setSelectedSideNode(null);
              }}
              style={{
                position: "absolute",
                top: "15px",
                right: "15px",
                background: "rgba(255,255,255,0.05)",
                border: "none",
                color: "white",
                cursor: "pointer",
                padding: "6px",
                borderRadius: "50%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <X size={16} />
            </button>

            <div style={{ marginTop: "10px" }}>
              <span style={{ fontSize: "0.6rem", color: "var(--accent)", fontWeight: 800, letterSpacing: "1.5px" }}>
                {selectedSideNode.type?.toUpperCase()} DETAILS
              </span>
              <h4 style={{ color: "white", fontSize: "1.2rem", marginTop: "4px", fontWeight: 700, lineHeight: 1.2 }}>
                {selectedSideNode.name}
              </h4>
            </div>

            {selectedSideNode.summary && (
              <div>
                <span style={{ fontSize: "0.6rem", color: "var(--accent)", opacity: 0.8, fontWeight: 700 }}>SUMMARY</span>
                <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem", lineHeight: "1.5", marginTop: "6px" }}>
                  {selectedSideNode.summary}
                </p>
              </div>
            )}

            {selectedSideNode.contentSnippet && (
              <div>
                <span style={{ fontSize: "0.6rem", color: "var(--accent)", opacity: 0.8, fontWeight: 700 }}>CONTENT</span>
                <div style={{ 
                  background: "rgba(255,255,255,0.03)", 
                  padding: "16px", 
                  borderRadius: "12px", 
                  border: "1px solid var(--glass-border)",
                  marginTop: "8px"
                }}>
                  {isUrl(selectedSideNode.contentSnippet) ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                      <a 
                        href={selectedSideNode.contentSnippet} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        style={{
                          background: "var(--accent)",
                          color: "white",
                          textDecoration: "none",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "8px",
                          padding: "8px 16px",
                          borderRadius: "8px",
                          fontWeight: 700,
                          fontSize: "0.8rem",
                          width: "fit-content"
                        }}
                      >
                        <ExternalLink size={14} />
                        Open Link
                      </a>
                    </div>
                  ) : (
                    <p style={{ color: "white", fontSize: "0.8rem", lineHeight: "1.5", whiteSpace: "pre-wrap" }}>
                      {selectedSideNode.contentSnippet}
                    </p>
                  )}
                </div>
              </div>
            )}

            {selectedSideNode.tags && selectedSideNode.tags.length > 0 && (
              <div>
                <span style={{ fontSize: "0.6rem", color: "var(--accent)", opacity: 0.8, fontWeight: 700 }}>TAGS</span>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "8px" }}>
                  {selectedSideNode.tags.map((tag, i) => (
                    <span 
                      key={i} 
                      style={{ 
                        fontSize: "0.7rem", 
                        background: "rgba(255, 122, 26, 0.1)", 
                        padding: "4px 10px", 
                        borderRadius: "6px",
                        color: "var(--accent)",
                        fontWeight: 600
                      }}
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default HierarchicalTree;
