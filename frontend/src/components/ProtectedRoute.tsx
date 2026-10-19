import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Loader2 } from "lucide-react";

interface Props {
  children: React.ReactNode;
  requiredRole?: "admin" | "user" | "viewer";
}

export default function ProtectedRoute({ children, requiredRole }: Props) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="auth-loading">
        <Loader2 size={32} className="spin" />
        <span>Loading session…</span>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requiredRole === "admin" && user.role !== "admin") {
    return (
      <div className="auth-forbidden">
        <h2>Access Denied</h2>
        <p>This page requires <strong>admin</strong> access. Your role is <strong>{user.role}</strong>.</p>
        <a href="/">← Back to dashboard</a>
      </div>
    );
  }

  return <>{children}</>;
}
