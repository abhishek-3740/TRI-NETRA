import React, { useState } from "react";
import ScenarioSelect from "./pages/ScenarioSelect.jsx";
import Dashboard from "./pages/Dashboard.jsx";

export default function App() {
  const [caseId, setCaseId] = useState(null);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 px-6 py-4">
        <h1 className="text-xl font-bold tracking-tight">🎯 Project Trinetra</h1>
        <p className="text-sm text-slate-400">
          100% local, air-gapped Bank · CDR · IPDR fusion engine
        </p>
      </header>

      <main className="p-6">
        {!caseId ? (
          <ScenarioSelect onSelect={setCaseId} />
        ) : (
          <Dashboard caseId={caseId} onBack={() => setCaseId(null)} />
        )}
      </main>
    </div>
  );
}
