import { Navigate, useLocation } from "react-router-dom";

export function ProtectedRoute({ children }) {
  const location = useLocation();
  const token = localStorage.getItem("access_token");

  if (!token) {
    // Redirect to login but save the attempted URL
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}

export function PublicRoute({ children }) {
  const token = localStorage.getItem("access_token");

  if (token) {
    // Already logged in, redirect to dashboard
    return <Navigate to="/" replace />;
  }

  return children;
}

export function getUser() {
  const userStr = localStorage.getItem("user");
  if (!userStr) return null;
  
  try {
    return JSON.parse(userStr);
  } catch {
    return null;
  }
}

export function getToken() {
  return localStorage.getItem("access_token");
}

export function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("user");
  window.location.href = "/login";
}

export function isAdmin() {
  const user = getUser();
  return user?.role === "admin" || user?.role === "msp_admin";
}
