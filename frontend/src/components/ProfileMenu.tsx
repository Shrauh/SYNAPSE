import { useState, useRef, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { User, Settings, Shield, LogOut, LogIn, UserPlus } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function ProfileMenu() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleLogout = async () => {
    setOpen(false);
    await logout();
    nav("/login");
  };

  const initials = user
    ? (user.full_name || user.username).slice(0, 2).toUpperCase()
    : "?";

  return (
    <div className="profile-menu-wrap" ref={ref}>
      <button
        className={`profile-avatar-btn ${user ? `role-avatar-${user.role}` : ""}`}
        onClick={() => setOpen(o => !o)}
        title={user ? `${user.username} (${user.role})` : "Account"}
      >
        {initials}
      </button>

      {open && (
        <div className="profile-dropdown">
          {user ? (
            <>
              <div className="dropdown-header">
                <div className="dropdown-avatar">{initials}</div>
                <div>
                  <div className="dropdown-name">{user.full_name || user.username}</div>
                  <div className="dropdown-email">{user.email}</div>
                  <span className={`role-pill role-pill-${user.role}`}>{user.role}</span>
                </div>
              </div>
              <div className="dropdown-divider" />
              <Link to="/profile" className="dropdown-item" onClick={() => setOpen(false)}>
                <User size={15} /> Profile
              </Link>
              <Link to="/profile?tab=security" className="dropdown-item" onClick={() => setOpen(false)}>
                <Shield size={15} /> Security Settings
              </Link>
              {user.role === "admin" && (
                <Link to="/admin" className="dropdown-item" onClick={() => setOpen(false)}>
                  <Settings size={15} /> Admin Panel
                </Link>
              )}
              <div className="dropdown-divider" />
              <button className="dropdown-item dropdown-item-danger" onClick={handleLogout}>
                <LogOut size={15} /> Sign out
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="dropdown-item" onClick={() => setOpen(false)}>
                <LogIn size={15} /> Sign in
              </Link>
              <Link to="/register" className="dropdown-item" onClick={() => setOpen(false)}>
                <UserPlus size={15} /> Create account
              </Link>
            </>
          )}
        </div>
      )}
    </div>
  );
}
