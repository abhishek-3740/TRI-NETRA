import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { getMapClusters } from "../api/client.js";

export default function MapPanel({ caseId }) {
  const [clusters, setClusters] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    getMapClusters(caseId)
      .then(({ data }) => setClusters(data.clusters || []))
      .catch((err) => setError(err.message));
  }, [caseId]);

  return (
    <div className="border border-slate-800 rounded-xl p-4">
      <h3 className="font-semibold mb-3">Co-location Heatmap (ST-DBSCAN)</h3>
      {error && <p className="text-red-400 text-sm">{error}</p>}
      <div className="rounded-lg overflow-hidden h-[260px]">
        <MapContainer center={[21.17, 72.83]} zoom={12} style={{ height: "100%", width: "100%" }}>
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          {clusters.map((cluster) =>
            cluster.members.map((m, i) => (
              <CircleMarker key={`${cluster.cluster_id}-${i}`} center={[m.lat, m.lon]} radius={8} color="#dc2626">
                <Popup>Cluster {cluster.cluster_id}</Popup>
              </CircleMarker>
            ))
          )}
        </MapContainer>
      </div>
    </div>
  );
}
