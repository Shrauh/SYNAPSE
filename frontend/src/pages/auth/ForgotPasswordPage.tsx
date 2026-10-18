import { useState } from "react";
import { Link } from "react-router-dom";
import { Loader2, ShieldCheck, ArrowLeft } from "lucide-react";
import { apiClient } from "../../api/client";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [devToken, setDevToken] = useState("");
  const [error, setError] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await apiClient.post<any>("/auth/forgot-password", { email });
      setSent(true);
      if (res.data._dev_reset_token) setDevToken(res.data._dev_reset_token);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Request failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <div className="auth-logo"><ShieldCheck size={32} /></div>
          <h1 className="auth-title">Reset password</h1>
          <p className="auth-subtitle">Enter your email to receive a reset link</p>
        </div>

        {!sent ? (
          <form onSubmit={submit} className="auth-form">
            {error && <div className="auth-error">{error}</div>}
            <div className="form-group">
              <label>Email address</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" required className="form-input" autoFocus />
            </div>
            <button type="submit" disabled={loading} className="btn-primary btn-full">
              {loading ? <Loader2 size={16} className="spin" /> : null}
              {loading ? "Sending…" : "Send reset link"}
            </button>
          </form>
        ) : (
          <div className="auth-success">
            <p>✅ If that email is registered, a reset link has been sent.</p>
            {devToken && (
              <div className="dev-info">
                <strong>Dev mode — reset token:</strong>
                <code>{devToken}</code>
                <Link to={`/reset-password?token=${devToken}`} className="auth-link">Use token →</Link>
              </div>
            )}
          </div>
        )}

        <p className="auth-footer">
          <Link to="/login" className="auth-link"><ArrowLeft size={14} /> Back to login</Link>
        </p>
      </div>
    </div>
  );
}
