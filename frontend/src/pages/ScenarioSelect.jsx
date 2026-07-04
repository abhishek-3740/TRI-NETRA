import React from "react";

const SCENARIOS = [
  { id: "scenario_a", title: "A — UPI Investment Scam", desc: "Call → login → transfer → mule hops in minutes." },
  { id: "scenario_b", title: "B — Loan App Extortion", desc: "One mastermind, five mule VPAs, circular flow." },
  { id: "scenario_c", title: "C — SIM-Swap Co-location", desc: "ST-DBSCAN proves suspects met before the fraud." },
  { id: "scenario_d", title: "D — Unknown Bank Format", desc: "Live demo of the self-healing Template Engine." },
];

export default function ScenarioSelect({ onSelect }) {
  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">Select a demo scenario</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {SCENARIOS.map((s) => (
          <button
            key={s.id}
            onClick={() => onSelect(s.id)}
            className="text-left border border-slate-800 rounded-xl p-4 hover:border-blue-500 hover:bg-slate-900 transition"
          >
            <div className="font-semibold">{s.title}</div>
            <div className="text-sm text-slate-400 mt-1">{s.desc}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
