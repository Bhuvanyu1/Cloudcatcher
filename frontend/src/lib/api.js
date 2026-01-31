import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API_BASE = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
});

// Health check
export const healthCheck = () => api.get("/health");

// Cloud Accounts
export const getCloudAccounts = (params) => api.get("/cloud-accounts", { params });
export const getCloudAccount = (id) => api.get(`/cloud-accounts/${id}`);
export const createCloudAccount = (data) => api.post("/cloud-accounts", data);
export const updateCloudAccount = (id, data) => api.patch(`/cloud-accounts/${id}`, data);
export const deleteCloudAccount = (id) => api.delete(`/cloud-accounts/${id}`);

// Sync
export const syncAllAccounts = () => api.post("/sync");
export const syncAccount = (id) => api.post(`/sync/${id}`);

// Instances
export const getInstances = (params) => api.get("/instances", { params });
export const getInstance = (id) => api.get(`/instances/${id}`);

// Recommendations
export const getRecommendations = (params) => api.get("/recommendations", { params });
export const updateRecommendationStatus = (id, status) => 
  api.patch(`/recommendations/${id}?status=${status}`);
export const runRecommendations = () => api.post("/recommendations/run");

// Dashboard
export const getDashboardStats = () => api.get("/dashboard/stats");

// Audit Events
export const getAuditEvents = (params) => api.get("/audit-events", { params });

export default api;
