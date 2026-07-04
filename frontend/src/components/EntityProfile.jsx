import React, { useEffect, useState } from "react";
import { getEntity } from "../api/client.js";

export default function EntityProfile({ entityId }) {
  const [entity, setEntity] = useState(null);

  useEffect(() => {
    if (!entityId) return;
    getEntity(entityId).then(({ data }) => setEntity(data)).catch(() => setEntity(null));
  }, [entityId]);

  if (!entity) return <p className="text-slate-400 text-sm">No entity selected.</p>;

  return (
    <div className="border border-slate-800 rounded-xl p-4 text-sm">
      <h3 className="font-semibold mb-2">Entity: {entity.id}</h3>
      <p className="text-slate-400">Type: {entity.type}</p>
      <p className="text-slate-400">Phone: {entity.linked_phone}</p>
      <p className="text-slate-400">UPI: {entity.linked_upi}</p>
      <p className="text-slate-400">Risk: {entity.risk_score}</p>
      <p className="text-slate-400">Flags: {(entity.flags || []).join(", ")}</p>
    </div>
  );
}
