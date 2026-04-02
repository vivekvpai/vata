import React, { useState, useRef, useEffect } from "react";
import { Send, Sparkles, User, Bot, Check, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import * as d3 from "d3";

interface TreeNode {
  name: string;
  children?: TreeNode[];
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  type?: "text" | "tree";
  treeData?: TreeNode;
  showAction?: boolean;
}

const HierarchicalTree: React.FC<{ data: TreeNode }> = ({ data }) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [selectedNodes, setSelectedNodes] = useState<Set<string>>(new Set());
  const selectedCount = selectedNodes.size;

  useEffect(() => {
    if (!svgRef.current || !data) return;

    const width = 800;
    const height = 400;
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
  }, [data, selectedNodes]);

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
        height="400"
        viewBox="0 0 800 400"
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
            Orchestrator
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
            Agent
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

const Home = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      content:
        "Hello! I am Vata. I design hierarchical orchestration systems. Tell me your project goal.",
      type: "text",
    },
  ]);
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = (overrideInput?: string) => {
    const text = overrideInput || input;
    if (!text.trim()) return;

    setMessages((prev) => [
      ...prev,
      { id: Date.now().toString(), role: "user", content: text },
    ]);
    if (!overrideInput) setInput("");

    setTimeout(() => {
      const tree: TreeNode = {
        name: "CORE AGENT",
        children: [
          {
            name: "FRONTEND",
            children: [{ name: "DESIGNER" }, { name: "CODER" }],
          },
          {
            name: "BACKEND",
            children: [{ name: "DB MGR" }, { name: "API MGR" }],
          },
        ],
      };

      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content:
            "I have mapped out the hierarchy for your request. This infrastructure optimizes communication between specialized agents.",
          type: "tree",
          treeData: tree,
          showAction: true,
        },
      ]);
    }, 1000);
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        minHeight: "calc(100vh - 80px)",
        maxWidth: "1000px",
        margin: "0 auto",
      }}
    >
      <div style={{ paddingBottom: "24px" }}>
        <h1
          style={{
            fontSize: "2.5rem",
            fontWeight: 800,
            background: "linear-gradient(to bottom, #ffffff, #888888)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          Vata AI
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "1rem" }}>
          Hierarchical Multi-Agent Infrastructure.
        </p>
      </div>

      {/* Main chat section - No internal scroll, grows naturally */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          gap: "40px",
          padding: "24px 0",
        }}
      >
        <AnimatePresence>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              {msg.role === "assistant" ? (
                <div
                  style={{
                    display: "flex",
                    gap: "20px",
                    width: "100%",
                    padding: "0 10px",
                  }}
                >
                  <div
                    style={{
                      width: "36px",
                      height: "36px",
                      borderRadius: "10px",
                      background: "var(--accent)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                      marginTop: "4px",
                    }}
                  >
                    <Bot size={20} color="white" aria-hidden="true" />
                  </div>
                  <div style={{ flex: 1 }}>
                    <p
                      style={{
                        color: "#ffffff",
                        fontSize: "1.05rem",
                        lineHeight: 1.7,
                        whiteSpace: "pre-wrap",
                      }}
                    >
                      {msg.content}
                    </p>
                    {msg.type === "tree" && msg.treeData && (
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.2 }}
                      >
                        <HierarchicalTree data={msg.treeData} />
                        {msg.showAction && (
                          <div
                            style={{
                              marginTop: "24px",
                              display: "flex",
                              gap: "16px",
                            }}
                          >
                            <button
                              onClick={() => handleSend("Accept this plan.")}
                              aria-label="Confirm orchestration plan"
                              style={{
                                padding: "10px 24px",
                                background: "var(--accent)",
                                border: "none",
                                borderRadius: "10px",
                                color: "white",
                                fontWeight: 700,
                                cursor: "pointer",
                                display: "flex",
                                alignItems: "center",
                                gap: "8px",
                                transition:
                                  "background 0.2s ease, transform 0.1s ease",
                              }}
                            >
                              <Check size={18} aria-hidden="true" />
                              <span>Confirm Plan</span>
                            </button>
                            <button
                              onClick={() => handleSend("Reject this plan.")}
                              aria-label="Reject orchestration plan"
                              style={{
                                padding: "10px 24px",
                                background: "rgba(255, 255, 255, 0.05)",
                                border: "1px solid var(--glass-border)",
                                borderRadius: "10px",
                                color: "var(--text-secondary)",
                                fontWeight: 600,
                                cursor: "pointer",
                                display: "flex",
                                alignItems: "center",
                                gap: "8px",
                                transition:
                                  "background 0.2s ease, border-color 0.2s ease",
                              }}
                            >
                              <X size={18} aria-hidden="true" />
                              <span>Reject Plan</span>
                            </button>
                          </div>
                        )}
                      </motion.div>
                    )}
                  </div>
                </div>
              ) : (
                <div
                  style={{
                    display: "flex",
                    justifyContent: "flex-end",
                    width: "100%",
                    padding: "0 10px",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      gap: "16px",
                      maxWidth: "80%",
                      flexDirection: "row-reverse",
                    }}
                  >
                    <div
                      style={{
                        width: "36px",
                        height: "36px",
                        borderRadius: "10px",
                        background: "rgba(255, 255, 255, 0.1)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                      }}
                    >
                      <User size={20} color="white" aria-hidden="true" />
                    </div>
                    <div
                      className="glass"
                      style={{
                        padding: "16px 20px",
                        borderRadius: "20px",
                        borderTopRightRadius: "4px",
                        background: "rgba(255, 122, 26, 0.1)",
                        border: "1px solid rgba(255, 122, 26, 0.3)",
                      }}
                    >
                      <p
                        style={{
                          color: "#ffffff",
                          fontSize: "1rem",
                          lineHeight: 1.6,
                          whiteSpace: "pre-wrap",
                          overflowWrap: "break-word",
                          minWidth: 0,
                        }}
                      >
                        {msg.content}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </div>

      {/* Sticky footer for input */}
      <div
        style={{
          position: "sticky",
          bottom: "-30px",
          background:
            "linear-gradient(to top, var(--bg-black) 40%, transparent)",
          zIndex: 10,
        }}
      >
        <div
          className="glass-premium"
          style={{
            display: "flex",
            alignItems: "center",
            padding: "6px 12px",
            borderRadius: "24px",
            gap: "8px",
          }}
        >
          <div
            style={{
              padding: "8px",
              color: "var(--accent)",
              display: "flex",
              alignItems: "center",
            }}
          >
            <Sparkles size={20} aria-hidden="true" />
          </div>

          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            aria-label="Type your message"
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.ctrlKey || e.shiftKey)) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Describe your mission…"
            rows={3}
            style={{
              flex: 1,
              background: "transparent",
              border: "none",
              color: "white",
              padding: "12px 0",
              fontSize: "1rem",
              outline: "none",
              resize: "none",
              fontFamily: "inherit",
              lineHeight: "1.5",
            }}
          />

          <button
            onClick={() => handleSend()}
            disabled={!input.trim()}
            aria-label="Send message"
            className="accent-glow"
            style={{
              background: input.trim()
                ? "var(--accent)"
                : "rgba(255,255,255,0.05)",
              border: "none",
              borderRadius: "16px",
              width: "42px",
              height: "42px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              flexShrink: 0,
              transition: "all 0.2s ease",
            }}
          >
            <Send size={18} color="white" aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default Home;
