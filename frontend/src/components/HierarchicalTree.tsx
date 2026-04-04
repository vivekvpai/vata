import React, { useState, useRef, useEffect } from "react";
import * as d3 from "d3";

export interface TreeNode {
  name: string;
  children?: TreeNode[];
}

interface HierarchicalTreeProps {
  data: TreeNode;
  height?: number;
  width?: number;
}

const HierarchicalTree: React.FC<HierarchicalTreeProps> = ({ 
  data, 
  height = 400, 
  width = 800 
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [selectedNodes, setSelectedNodes] = useState<Set<string>>(new Set());
  const selectedCount = selectedNodes.size;

  useEffect(() => {
    if (!svgRef.current || !data) return;

    const margin = { top: 60, right: 20, bottom: 60, left: 20 };

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

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

        // Get all descendant names
        const descendants = d.descendants().map((node) => node.data.name);
        const isCurrentlySelected = selectedNodes.has(d.data.name);

        setSelectedNodes((prev) => {
          const next = new Set(prev);
          if (isCurrentlySelected) {
            // Deselect node and all children
            descendants.forEach((name) => next.delete(name));
          } else {
            // Select node and all children
            descendants.forEach((name) => next.add(name));
          }
          return next;
        });
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
      );

    // Indicator Dot (Inverted placement)
    node
      .append("circle")
      .attr("r", 4)
      .attr("cy", 32)
      .attr("fill", (d) =>
        selectedNodes.has(d.data.name) ? "#4ade80" : "var(--accent)",
      );
  }, [data, selectedNodes, height, width]);

  return (
    <div
      style={{
        width: "100%",
        background: "rgba(0,0,0,0.4)",
        borderRadius: "24px",
        border: "1px solid var(--glass-border)",
        padding: "24px",
        overflow: "hidden",
        marginTop: "16px",
      }}
    >
      <svg
        ref={svgRef}
        width="100%"
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="xMidYMid meet"
      />
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
    </div>
  );
};

export default HierarchicalTree;
