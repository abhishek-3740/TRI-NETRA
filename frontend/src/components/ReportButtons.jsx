import React from "react";
import { downloadSTR, downloadLERSDraft } from "../api/client.js";

export default function ReportButtons({ caseId }) {
  return (
    <div className="border border-slate-800 rounded-xl p-4">
      <h3 className="font-semibold mb-3">Reports</h3>
      <div className="flex gap-3 text-sm">
        <a
          href={downloadSTR(caseId)}
          className="px-3 py-1.5 bg-blue-600 rounded-lg hover:bg-blue-500"
          target="_blank" rel="noreferrer"
        >
          Download STR (PDF)
        </a>
        <a
          href={downloadLERSDraft(caseId)}
          className="px-3 py-1.5 bg-slate-700 rounded-lg hover:bg-slate-600"
          target="_blank" rel="noreferrer"
        >
          Download LERS Draft (docx)
        </a>
      </div>
      <p className="text-xs text-slate-500 mt-2">
        LERS output is a draft only — review, sign, and submit manually through proper legal channels.
      </p>
    </div>
  );
}
