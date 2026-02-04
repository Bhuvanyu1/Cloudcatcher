import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API_BASE = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle token refresh on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      const refreshToken = localStorage.getItem("refresh_token");
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE}/auth/refresh`, {
            refresh_token: refreshToken
          });
          
          localStorage.setItem("access_token", response.data.access_token);
          localStorage.setItem("refresh_token", response.data.refresh_token);
          
          originalRequest.headers.Authorization = `Bearer ${response.data.access_token}`;
          return api(originalRequest);
        } catch (refreshError) {
          // Refresh failed, logout
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          localStorage.removeItem("user");
          window.location.href = "/login";
        }
      } else {
        // No refresh token, logout
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("user");
        window.location.href = "/login";
      }
    }
    
    return Promise.reject(error);
  }
);

// Health check
export const healthCheck = () => api.get("/health");

// Auth
export const login = (data) => api.post("/auth/login", data);
export const register = (data) => api.post("/auth/register", data);
export const logout = () => api.post("/auth/logout");
export const getCurrentUser = () => api.get("/auth/me");

// Users
export const getUsers = (params) => api.get("/users", { params });
export const deleteUser = (id) => api.delete(`/users/${id}`);

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

// Alerts
export const getAlerts = (params) => api.get("/alerts", { params });
export const runAnomalyDetection = () => api.post("/alerts/detect");

export default api;
