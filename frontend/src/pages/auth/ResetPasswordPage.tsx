import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Eye, EyeOff, Loader2, ShieldCheck, Check, X } from "lucide-react";
import { apiClient } from "../../api/client";

const rules = [
  { label: "8+ characters", test: (p: string) => p.length >= 8 },
  { label: "Uppercase letter", test: (p: string) => /[A-Z]/.test(p) },
  { label: "Lowercase letter", test: (p: string) => /[a-z]/.test(p) },
  { label: "Number", test: (p: string) => /\d/.test(p) },
];

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const nav = useNavigate();
  const token = searchParams.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirm) { setError("Passwords do not match."); return; }
    setLoading(true); setError("");
    try {
      await apiClient.post("/auth/reset-password", { token, new_password: password });
      setSuccess(true);
      setTimeout(() => nav("/login"), 2000);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Reset failed. Token may be expired.");
    } finally { setLoading(false); }
  };

  if (!token) return (
    <div className="auth-page"><div className="auth-card">
      <div className="auth-error">Invalid or missing reset token.</div>
      <Link to="/forgot-password" className="auth-link">Request a new one →</Link>
    </div></div>
  );

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <div className="auth-logo"><ShieldCheck size={32} /></div>
          <h1 className="auth-title">New password</h1>
          <p className="auth-subtitle">Choose a strong password for your account</p>
        </div>

        {success ? (
          <div className="auth-success">✅ Password reset! Redirecting to login…</div>
        ) : (
          <form onSubmit={submit} className="auth-form">
            {error && <div className="auth-error">{error}</div>}
            <div className="form-group">
              <label>New password</label>
              <div className="input-with-icon">
                <input type={showPw ? "text" : "password"} value={password} onChange={e => setPassword(e.target.value)} required className="form-input" placeholder="••••••••" />
                <button type="button" className="pw-toggle" onClick={() => setShowPw(p => !p)}>
                  {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {password && (
                <div className="pw-rules">
                  {rules.map(r => (
                    <span key={r.label} className={`pw-rule ${r.test(password) ? "pw-rule-ok" : "pw-rule-fail"}`}>
                      {r.test(password) ? <Check size={12} /> : <X size={12} />} {r.label}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <div className="form-group">
              <label>Confirm password</label>
              <input type="password" value={confirm} onChange={e => setConfirm(e.target.value)} required className="form-input" placeholder="••••••••" />
            </div>
            <button type="submit" disabled={loading} className="btn-primary btn-full">
              {loading ? <Loader2 size={16} className="spin" /> : null}
              {loading ? "Resetting…" : "Set new password"}
            </button>
          </form>
        )}
        <p className="auth-footer"><Link to="/login" className="auth-link">Back to login</Link></p>
      </div>
    </div>
  );
}
