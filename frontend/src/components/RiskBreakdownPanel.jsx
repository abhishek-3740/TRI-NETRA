import React, { useEffect, useState } from "react";
import { getRiskBreakdown } from "../api/client.js";

export default function RiskBreakdownPanel({ caseId }) {
  const [risk, setRisk] = useState(null);

  useEffect(() => {
    // TODO: wire to a real "top flagged entity for this case" endpoint
    getRiskBreakdown("acc_001")
      .then(({ data }) => setRisk(data))
      .catch(() => setRisk(null));
  }, [caseId]);

  return (
    <div className="border border-slate-800 rounded-xl p-4">
      <h3 className="font-semibold mb-3">Risk Breakdown</h3>
      {!risk ? (
        <p className="text-slate-400 text-sm">No entity selected.</p>
      ) : (
        <div className="space-y-2 text-sm">
          <Bar label="Rule-based" value={risk.rule_based_score} />
          <Bar label="Isolation Forest" value={risk.isolation_forest_score} />
          <Bar label="Graph ML (GraphSAGE/Node2Vec)" value={risk.graph_ml_score} />
          <div className="pt-2 border-t border-slate-800 flex justify-between font-semibold">
            <span>Final Risk Score</span>
            <span className={risk.is_mule_account ? "text-red-400" : "text-blue-400"}>
              {risk.final_risk_score}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

function Bar({ label, value }) {
  return (
    <div>
      <div className="flex justify-between text-slate-400">
        <span>{label}</span>
        <span>{value}</span>
      </div>
      <div className="h-1.5 bg-slate-800 rounded-full mt-1">
        <div className="h-1.5 bg-blue-500 rounded-full" style={{ width: `${value * 100}%` }} />
      </div>
    </div>
  );
}
