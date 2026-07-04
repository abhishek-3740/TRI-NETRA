import React from "react";
import TimelinePanel from "../components/TimelinePanel.jsx";
import NetworkPanel from "../components/NetworkPanel.jsx";
import MapPanel from "../components/MapPanel.jsx";
import RiskBreakdownPanel from "../components/RiskBreakdownPanel.jsx";
import ReportButtons from "../components/ReportButtons.jsx";
import UploadPanel from "../components/UploadPanel.jsx";

export default function Dashboard({ caseId, onBack }) {
  return (
    <div>
      <button onClick={onBack} className="text-sm text-slate-400 hover:text-slate-200 mb-4">
        ← Back to scenarios
      </button>
      <h2 className="text-lg font-semibold mb-4">Case: {caseId}</h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <TimelinePanel caseId={caseId} />
        <NetworkPanel caseId={caseId} />
        <MapPanel caseId={caseId} />
        <RiskBreakdownPanel caseId={caseId} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <UploadPanel caseId={caseId} />
        <ReportButtons caseId={caseId} />
      </div>
    </div>
  );
}
