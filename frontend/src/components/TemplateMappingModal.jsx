import React, { useState } from "react";
import client from "../api/client.js";

/**
 * Shown when the Bank Parser can't auto-match a statement to a known
 * template. Lets the officer map raw columns -> canonical fields once;
 * the mapping is saved server-side and reused automatically next time.
 */
export default function TemplateMappingModal({ data, onSaved, onClose }) {
  const [bankName, setBankName] = useState("");
  const [mapping, setMapping] = useState({});

  const CANONICAL_FIELDS = ["date", "narration", "amount_debit", "amount_credit", "balance"];

  const handleSave = async () => {
    await client.post("/api/templates/", {
      bank_name: bankName || "unknown_bank",
      column_map: mapping,
      date_format: "%d/%m/%Y",
    });
    onSaved();
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 w-full max-w-lg">
        <h3 className="font-semibold mb-2">Map this bank's columns</h3>
        <p className="text-sm text-slate-400 mb-4">
          We couldn't auto-detect this bank format. Map each column below —
          it'll be remembered for next time.
        </p>

        <input
          placeholder="Bank name (e.g. Union Bank)"
          value={bankName}
          onChange={(e) => setBankName(e.target.value)}
          className="w-full mb-3 bg-slate-800 rounded-lg px-3 py-2 text-sm"
        />

        <div className="space-y-2 max-h-64 overflow-y-auto">
          {data.raw_headers?.map((header) => (
            <div key={header} className="flex items-center gap-2">
              <span className="text-sm w-1/2 truncate">{header}</span>
              <select
                className="w-1/2 bg-slate-800 rounded-lg px-2 py-1 text-sm"
                onChange={(e) => setMapping((m) => ({ ...m, [header]: e.target.value }))}
              >
                <option value="">-- ignore --</option>
                {CANONICAL_FIELDS.map((f) => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
            </div>
          ))}
        </div>

        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-3 py-1.5 text-sm text-slate-400">Cancel</button>
          <button onClick={handleSave} className="px-3 py-1.5 text-sm bg-blue-600 rounded-lg hover:bg-blue-500">
            Save Template
          </button>
        </div>
      </div>
    </div>
  );
}
