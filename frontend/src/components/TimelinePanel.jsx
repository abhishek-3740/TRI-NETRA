import React, { useEffect, useRef, useState } from "react";
import { Timeline } from "vis-timeline/standalone";
import "vis-timeline/styles/vis-timeline-graph2d.css";
import { getTimeline } from "../api/client.js";

export default function TimelinePanel({ caseId }) {
  const containerRef = useRef(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let timeline;
    getTimeline(caseId)
      .then(({ data }) => {
        const items = (data.events || []).map((e, i) => ({
          id: i,
          content: e.type,
          start: new Date(e.timestamp * 1000),
        }));
        if (containerRef.current) {
          timeline = new Timeline(containerRef.current, items, {});
        }
      })
      .catch((err) => setError(err.message));

    return () => timeline?.destroy();
  }, [caseId]);

  return (
    <div className="border border-slate-800 rounded-xl p-4">
      <h3 className="font-semibold mb-3">Timeline — Smoking Gun View</h3>
      {error && <p className="text-red-400 text-sm">{error}</p>}
      <div ref={containerRef} className="bg-slate-900 rounded-lg min-h-[200px]" />
    </div>
  );
}
