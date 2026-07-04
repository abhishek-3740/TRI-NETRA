import React, { useState } from "react";
import { uploadBankStatement, uploadCDR, uploadIPDR } from "../api/client.js";
import TemplateMappingModal from "./TemplateMappingModal.jsx";

export default function UploadPanel({ caseId }) {
  const [status, setStatus] = useState(null);
  const [needsMapping, setNeedsMapping] = useState(null);

  const handleUpload = async (type, file) => {
    if (!file) return;
    setStatus(`Uploading ${type}...`);
    try {
      const uploader = { bank: uploadBankStatement, cdr: uploadCDR, ipdr: uploadIPDR }[type];
      const res = await uploader(file);
      if (res.data.status === "needs_manual_mapping") {
        setNeedsMapping(res.data);
      } else {
        setStatus(`${type.toUpperCase()} parsed: ${res.data.row_count ?? res.data.rows_parsed} rows.`);
      }
    } catch (err) {
      setStatus(`Upload failed: ${err.message}`);
    }
  };

  return (
    <div className="border border-slate-800 rounded-xl p-4">
      <h3 className="font-semibold mb-3">Upload Case Files</h3>
      <div className="space-y-3 text-sm">
        <FileRow label="Bank Statement (PDF)" accept=".pdf" onChange={(f) => handleUpload("bank", f)} />
        <FileRow label="CDR (CSV)" accept=".csv" onChange={(f) => handleUpload("cdr", f)} />
        <FileRow label="IPDR (CSV)" accept=".csv" onChange={(f) => handleUpload("ipdr", f)} />
      </div>
      {status && <p className="text-slate-400 mt-3 text-sm">{status}</p>}

      {needsMapping && (
        <TemplateMappingModal
          data={needsMapping}
          onSaved={() => {
            setNeedsMapping(null);
            setStatus("Template saved — re-upload the file to parse it automatically.");
          }}
          onClose={() => setNeedsMapping(null)}
        />
      )}
    </div>
  );
}

function FileRow({ label, accept, onChange }) {
  return (
    <label className="flex items-center justify-between gap-3">
      <span className="text-slate-300">{label}</span>
      <input
        type="file"
        accept={accept}
        onChange={(e) => onChange(e.target.files[0])}
        className="text-xs text-slate-400 file:mr-3 file:rounded-lg file:border-0 file:bg-blue-600 file:px-3 file:py-1.5 file:text-white hover:file:bg-blue-500"
      />
    </label>
  );
}
