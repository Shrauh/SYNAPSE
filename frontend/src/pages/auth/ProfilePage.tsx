import { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { apiClient } from "../../api/client";
import {
  User, Shield, Key, Eye, EyeOff, Loader2,
  CheckCircle2, AlertTriangle, Settings
} from "lucide-react";

type Tab = "profile" | "security";

export default function ProfilePage() {
  const { user, refreshUser } = useAuth();
  const [tab, setTab] = useState<Tab>("profile");

  // Profile tab state
  const [fullName, setFullName] = useState(user?.full_name || "");
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileMsg, setProfileMsg] = useState<{ type: "ok"|"err"; text: string } | null>(null);

  // Security tab state
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [secLoading, setSecLoading] = useState(false);
  const [secMsg, setSecMsg] = useState<{ type: "ok"|"err"; text: string } | null>(null);

  const saveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileLoading(true); setProfileMsg(null);
    try {
      await apiClient.put("/auth/me", { full_name: fullName });
      await refreshUser();
      setProfileMsg({ type: "ok", text: "Profile updated successfully." });
    } catch (err: any) {
      setProfileMsg({ type: "err", text: err?.response?.data?.detail || "Update failed." });
    } finally { setProfileLoading(false); }
  };

  const changePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPw !== confirmPw) { setSecMsg({ type: "err", text: "New passwords do not match." }); return; }
    setSecLoading(true); setSecMsg(null);
    try {
      await apiClient.post("/auth/change-password", {
        current_password: currentPw,
        new_password: newPw,
        confirm_new_password: confirmPw,
      });
      setSecMsg({ type: "ok", text: "Password changed successfully." });
      setCurrentPw(""); setNewPw(""); setConfirmPw("");
    } catch (err: any) {
      setSecMsg({ type: "err", text: err?.response?.data?.detail || "Password change failed." });
    } finally { setSecLoading(false); }
  };

  if (!user) return null;

  return (
    <div className="profile-page">
      <div className="profile-header">
        <div className="profile-avatar-lg">
          {user.full_name?.[0]?.toUpperCase() || user.username[0].toUpperCase()}
        </div>
        <div>
          <h1 className="profile-name">{user.full_name || user.username}</h1>
          <p className="profile-email">{user.email}</p>
          <span className={`role-badge role-${user.role}`}>{user.role.toUpperCase()}</span>
        </div>
      </div>

      <div className="profile-tabs">
        <button className={`profile-tab ${tab === "profile" ? "active" : ""}`} onClick={() => setTab("profile")}>
          <User size={16} /> Profile
        </button>
        <button className={`profile-tab ${tab === "security" ? "active" : ""}`} onClick={() => setTab("security")}>
          <Shield size={16} /> Security
        </button>
      </div>

      {tab === "profile" && (
        <div className="profile-section">
          <h2 className="section-title"><Settings size={18} /> Account Details</h2>
          <form onSubmit={saveProfile} className="profile-form">
            {profileMsg && (
              <div className={`profile-msg ${profileMsg.type === "ok" ? "msg-ok" : "msg-err"}`}>
                {profileMsg.type === "ok" ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
                {profileMsg.text}
              </div>
            )}
            <div className="form-row">
              <div className="form-group">
                <label>Username</label>
                <input type="text" value={user.username} disabled className="form-input form-input-disabled" />
              </div>
              <div className="form-group">
                <label>Email</label>
                <input type="email" value={user.email} disabled className="form-input form-input-disabled" />
              </div>
            </div>
            <div className="form-group">
              <label>Display name</label>
              <input type="text" value={fullName} onChange={e => setFullName(e.target.value)} className="form-input" placeholder="Your full name" />
            </div>
            <div className="form-group">
              <label>Role</label>
              <input type="text" value={user.role} disabled className="form-input form-input-disabled" />
            </div>
            <button type="submit" disabled={profileLoading} className="btn-primary">
              {profileLoading ? <Loader2 size={16} className="spin" /> : null}
              {profileLoading ? "Saving…" : "Save changes"}
            </button>
          </form>
        </div>
      )}

      {tab === "security" && (
        <div className="profile-section">
          <h2 className="section-title"><Key size={18} /> Change Password</h2>
          <form onSubmit={changePassword} className="profile-form">
            {secMsg && (
              <div className={`profile-msg ${secMsg.type === "ok" ? "msg-ok" : "msg-err"}`}>
                {secMsg.type === "ok" ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
                {secMsg.text}
              </div>
            )}
            <div className="form-group">
              <label>Current password</label>
              <div className="input-with-icon">
                <input type={showPw ? "text" : "password"} value={currentPw} onChange={e => setCurrentPw(e.target.value)} required className="form-input" placeholder="••••••••" />
                <button type="button" className="pw-toggle" onClick={() => setShowPw(p => !p)}>
                  {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>New password</label>
                <input type={showPw ? "text" : "password"} value={newPw} onChange={e => setNewPw(e.target.value)} required className="form-input" placeholder="••••••••" />
              </div>
              <div className="form-group">
                <label>Confirm new password</label>
                <input type="password" value={confirmPw} onChange={e => setConfirmPw(e.target.value)} required className="form-input" placeholder="••••••••" />
              </div>
            </div>
            <button type="submit" disabled={secLoading} className="btn-primary">
              {secLoading ? <Loader2 size={16} className="spin" /> : null}
              {secLoading ? "Changing…" : "Change password"}
            </button>
          </form>

          <div className="security-info-box">
            <h3><Shield size={14} /> Security Information</h3>
            <ul>
              <li>Passwords are hashed with bcrypt — never stored in plain text</li>
              <li>Sessions use httpOnly cookies — protected from XSS</li>
              <li>Access tokens expire after 30 minutes</li>
              <li>Refresh tokens expire after 7 days and rotate on use</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
