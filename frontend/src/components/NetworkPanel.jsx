import React, { useEffect, useRef, useState } from "react";
import cytoscape from "cytoscape";
import { getNetworkGraph } from "../api/client.js";

/**
 * Renders the money-flow graph. This component ONLY ever receives plain
 * JSON from FastAPI (GET /api/fusion/network/{caseId}) — it never queries
 * Neo4j itself. Risk-based node coloring is already applied server-side.
 */
export default function NetworkPanel({ caseId }) {
  const containerRef = useRef(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cy;
    getNetworkGraph(caseId)
      .then(({ data }) => {
        const elements = [
          ...data.nodes.map((n) => ({ data: { id: n.id, label: n.label }, style: { "background-color": n.color } })),
          ...data.edges.map((e) => ({ data: { source: e.source, target: e.target, label: `₹${e.amount ?? ""}` } })),
        ];

        if (containerRef.current) {
          cy = cytoscape({
            container: containerRef.current,
            elements,
            style: [
              { selector: "node", style: { label: "data(label)", "font-size": 8, color: "#e2e8f0" } },
              { selector: "edge", style: { "curve-style": "bezier", "target-arrow-shape": "triangle", label: "data(label)", "font-size": 7 } },
            ],
            layout: { name: "cose" },
          });
        }
      })
      .catch((err) => setError(err.message));

    return () => cy?.destroy();
  }, [caseId]);

  return (
    <div className="border border-slate-800 rounded-xl p-4">
      <h3 className="font-semibold mb-3">Money Flow Network</h3>
      {error && <p className="text-red-400 text-sm">{error}</p>}
      <div ref={containerRef} className="bg-slate-900 rounded-lg h-[260px]" />
    </div>
  );
}
