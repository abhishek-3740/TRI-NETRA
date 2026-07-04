import axios from "axios";

// All calls go through FastAPI. The frontend NEVER talks to Neo4j directly —
// FastAPI runs the Cypher query, attaches risk scores/colors, and returns
// plain JSON here.
const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
});

export const getTimeline = (caseId) => client.get(`/api/fusion/timeline/${caseId}`);
export const getNetworkGraph = (caseId) => client.get(`/api/fusion/network/${caseId}`);
export const getMapClusters = (caseId) => client.get(`/api/fusion/map/${caseId}`);
export const getEntity = (entityId) => client.get(`/api/entities/${entityId}`);
export const getRiskBreakdown = (entityId) => client.get(`/api/risk/${entityId}`);
export const uploadBankStatement = (file) => {
  const form = new FormData();
  form.append("file", file);
  return client.post("/api/upload/bank", form);
};
export const uploadCDR = (file) => {
  const form = new FormData();
  form.append("file", file);
  return client.post("/api/upload/cdr", form);
};
export const uploadIPDR = (file) => {
  const form = new FormData();
  form.append("file", file);
  return client.post("/api/upload/ipdr", form);
};
export const downloadSTR = (caseId) => `${client.defaults.baseURL}/api/report/str/${caseId}`;
export const downloadLERSDraft = (caseId) => `${client.defaults.baseURL}/api/report/lers/${caseId}`;

export default client;
